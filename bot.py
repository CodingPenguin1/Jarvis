#!/usr/bin/env python3
import csv
import datetime
import json
import re
import urllib.request
from datetime import datetime
from os.path import exists
from time import sleep, strftime

import aiofiles
import discord
import matplotlib.pyplot as plt
import pandas as pd
import requests
from bs4 import BeautifulSoup
from discord.ext import commands, tasks

##### ======= #####
##### GLOBALS #####
##### ======= #####
client = commands.Bot(command_prefix='-', intents=discord.Intents.all())
dumbass_scores = {}
status = ''


##### =========== #####
##### CORE EVENTS #####
##### =========== #####
@client.event
async def on_ready():
    global reaction_roles
    global dumbass_scores
    global status

    await log('Starting up...')

    # Load dumbass scores
    if exists('dumbass_scores.json'):
        with open('dumbass_scores.json', 'r') as f:
            dumbass_scores = json.loads(f.read())

    # Set status
    weather = await get_weather()
    if exists('status'):
        with open('status', 'r') as f:
            status = f.readline().strip()
            if len(status) > 0:
                status = f'{weather["temp"]}°F {status}'
            else:
                status = f'{weather["temp"]}°F in Fairborn, OH'
    else:
        status = f'{weather["temp"]}°F in Fairborn, OH'
    await client.change_presence(activity=discord.Game(status), status=None, afk=False)

    # Start tasks
    await log('Starting task: update_status_temperature')
    update_status_temperature.start()
    # await log('Starting task: wsu_covid_stats_message')
    # wsu_covid_stats_message.start()

    # Show the bot as online
    await log('Startup completed')


@tasks.loop(seconds=1200)
# @tasks.loop(seconds=5)
async def update_status_temperature():
    global status

    weather = await get_weather()

    if '|' in status:
        status = status.split(' | ')[1].strip()
        status = f'{weather["temp"]}°F | {status}'
    if len(status) == 0:
        status = f'{weather["temp"]}°F'

    await client.change_presence(activity=discord.Game(status), status=None, afk=False)
    await log('Updated status temperature')


@tasks.loop(seconds=3600)
async def wsu_covid_stats_message():
    # Get channel
    for guild in client.guilds:
        for channel in guild.channels:
            if channel.name == 'wsu-covid-stats':
                await channel.purge(limit=100)
                # Generate message
                dataframe = await get_wsu_covid_stats()
                date = strftime('%d-%m-%Y')
                message = f'__**ACTIVE WRIGHT STATE COVID-19 CASES ({date})**__\n```{dataframe}```Data collected from https://www.wright.edu/coronavirus/covid-19-dashboard'
                await channel.send(message, file=discord.File('wsu_covid_plot.png'))


##### ================ #####
##### GENERAL COMAMNDS #####
##### ================ #####
@client.command()
async def poll(ctx, question, *options: str):
    # Delete sender's message
    await ctx.channel.purge(limit=1)

    # Need between 2 and 10 options for a poll
    if not (1 < len(options) <= 10):
        await ctx.send('Enter between 2 and 10 answers')
        return

    # Define reactions
    if len(options) == 2 and options[0] == 'yes' and options[1] == 'no':
        reactions = ['✅', '❌']
    else:
        reactions = ['1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '6⃣', '7⃣', '8⃣', '9⃣', '🔟']

    description = []
    for i, option in enumerate(options):
        description += '\n {} {}'.format(reactions[i], option)
    embed = discord.Embed(title=question, description=''.join(description))

    react_message = await ctx.send(embed=embed)
    for reaction in reactions[:len(options)]:
        await react_message.add_reaction(reaction)

    # Logging
    await log(f'{ctx.author} started a poll in #{ctx.channel}:')
    await log(question, False)
    for option in options:
        await log(f'{option}', False)


@client.command()
async def ping(ctx):
    latency = round(client.latency * 1000)
    await ctx.send(f'{latency} ms')
    await log(f'{ctx.author} pinged from #{ctx.channel}, response took {latency} ms')


@client.command(aliases=['dinc'])
async def dumbass_increment(ctx, member_id='0', amount='0'):
    global dumbass_scores

    # If 0 params passed, default to ctx.author +1
    if member_id == '0' and amount == '0':
        member = ctx.author
        amount = 1
    # If one parameter passed, default to ctx.author, but take member_id as amount
    elif member_id != '0' and amount == '0':
        # If can't cast, the author was specified instead of the value
        try:
            member = ctx.author
            amount = int(member_id)
        except ValueError:
            member_id = int(member_id.replace('<@', '').replace('>', '').replace('!', ''))
            amount = 1
            member = await get_member(ctx.guild, member_id)
            if member is None:
                return
    # If both parameters passed, get member from @mention
    else:
        member_id = int(member_id.replace('<@', '').replace('>', '').replace('!', ''))
        amount = int(amount)
        member = await get_member(ctx.guild, member_id)
        if member is None:
            return

    # If member is not admin, assert amount > 0 and sender is same person as member_id
    if not ctx.author.guild_permissions.administrator:
        if amount <= 0:
            await ctx.send('You are not an admin. You cannot decrement your own score')
            return
        if member != ctx.author:
            await ctx.send('You are not an admin. You cannot modify someone else\'s score')
            return

    # Set up guild in dumbass_scores if it isn't there already
    guild_id = str(ctx.guild.id)
    if guild_id not in dumbass_scores.keys():
        dumbass_scores[guild_id] = {}

    # Increment member's dumbass score
    # If they aren't in the list, add them and set score to 1
    if str(member.id) not in dumbass_scores[guild_id].keys():
        dumbass_scores[guild_id][str(member.id)] = amount
    # Otherwise, increment normally
    else:
        dumbass_scores[guild_id][str(member.id)] += amount
    await ctx.send(f'{member.name}: {dumbass_scores[guild_id][str(member.id)]} (+{amount})')

    # If total score is 0, remove member
    if dumbass_scores[guild_id][str(member.id)] == 0:
        del dumbass_scores[guild_id][str(member.id)]

    # Write JSON
    async with aiofiles.open('dumbass_scores.json', mode='w') as f:
        json_string = json.dumps(dumbass_scores, indent=4)
        for line in json_string:
            await f.write(line)

    # Make leaderboard
    # Check if category exists. If not, make it
    category = None
    category_name = 'Top Dumbasses'
    for c in ctx.guild.categories:
        if c.name == category_name:
            category = c
            break
    if category is None:
        category = await ctx.guild.create_category('Top Dumbasses', position=0)
        await category.edit(position=0)  # Ensuring it actually goes to the top

    # Delete every channel under it
    for channel in category.channels:
        await channel.delete()

    # Remake channels for leaderboard
    scores = []
    for member_id in dumbass_scores[str(ctx.guild.id)].keys():
        member = await get_member(ctx.guild, member_id)
        scores.append((member.nick, dumbass_scores[str(ctx.guild.id)][member_id]))

    # Sort scores
    scores.sort(key=lambda tup: tup[1])
    scores.reverse()

    # Create channels
    for score in scores:
        await category.create_text_channel(f'({score[1]}) {score[0]}')


@client.command()
async def dumbasses(ctx):
    global dumbass_scores

    if str(ctx.guild.id) in dumbass_scores.keys():
        # Move scores into a list of tuples to sort
        scores = []
        for member_id in dumbass_scores[str(ctx.guild.id)].keys():
            member = await get_member(ctx.guild, member_id)
            scores.append((member.name, dumbass_scores[str(ctx.guild.id)][member_id]))

        # If no scores, don't bother sorting and send a no scores message
        if len(scores) == 0:
            await ctx.send(f'Looks like you guys aren\'t that dumb...')
            return

        # Sort scores
        scores.sort(key=lambda tup: tup[1])
        scores.reverse()

        # Generate message to send
        message = '__**TOP DUMBASSES**__\n'
        for i, score in enumerate(scores):
            message += f'{i + 1}) {score[0]}: {score[1]}\n'
        await ctx.send(message)
    else:
        await ctx.send(f'Looks like you guys aren\'t that dumb...')


@client.command()
async def weather(ctx, location='fairborn'):
    weather = await get_weather(location)

    message = f'__**Weather: {weather["name"]}**__\n'
    message += f'Temperature: {weather["temp"]}°F (feels like {weather["temp feels like"]}°F) {weather["temp min"]}°F / {weather["temp max"]}°F\n'
    message += f'Weather: {weather["weather description"]}\n'
    message += f'Wind: {weather["wind speed"]} mph {weather["wind direction"]}\n'
    message += f'Cloud Cover: {weather["cloud cover"]}%\n'
    message += f'Pressure: {weather["pressure"]} bar\n'
    message += f'Humidity: {weather["humidity"]}%'

    await ctx.send(message)


@client.command()
async def covid(ctx):
    dataframe = await get_wsu_covid_stats()
    date = strftime('%d-%m-%Y')
    message = f'__**ACTIVE WRIGHT STATE COVID-19 CASES ({date})**__\n```{dataframe}```Data collected from https://www.wright.edu/coronavirus/covid-19-dashboard'
    await ctx.send(message, file=discord.File('wsu_covid_plot.png'))


@client.command()
async def owe(ctx, target=None, amount=None):
    # Get objects for ctx.author, target, and amount
    user = ctx.author
    if target is not None:
        target = re.sub('\\D', '', target)
        target = await get_member_by_id(target)
    if amount is not None:
        amount = round(float(amount), 2)
        if amount <= 0:
            amount = None

    if target is not None and amount is not None:
        await debt_utility(ctx, target, user, -amount)


@client.command()
async def pay(ctx, target=None, amount=None):
    # Get objects for ctx.author, target, and amount
    user = ctx.author
    if target is not None:
        target = re.sub('\\D', '', target)
        target = await get_member_by_id(target)
    if amount is not None:
        amount = round(float(amount), 2)
        if amount <= 0:
            amount = None

    if target is not None and amount is not None:
        await debt_utility(ctx, target, user, amount)


@client.command()
async def debt(ctx, target=None, amount=None):
    # Get objects for ctx.author, target, and amount
    user = ctx.author
    if target is not None:
        target = re.sub('\\D', '', target)
        target = await get_member_by_id(target)
    if amount is not None:
        amount = round(float(amount), 2)
        if amount <= 0:
            amount = None

    # Target owes ctx.author amount
    if target is not None and amount is not None:
        await debt_utility(ctx, target, user, amount)

    # Print how much ctx.author owes target, or vice versa
    elif target is not None and amount is None:
        message = '__Debt__\n'
        # Read from csv and append to message
        with open('debt_data.csv') as f:
            csv_reader = csv.reader(f, delimiter=',')
            for row in csv_reader:
                if str(target.id) in str(row[0]) or str(target.id) in str(row[1]):
                    ower = (await get_member_by_id(row[0])).nick if (await get_member_by_id(row[0])).nick is not None else (await get_member_by_id(row[0])).name
                    owed = (await get_member_by_id(row[1])).nick if (await get_member_by_id(row[1])).nick is not None else (await get_member_by_id(row[1])).name

                    message += f'{ower} owes {owed} {await format_money(float(row[2]))}\n'
        if message == '__Debt__\n':
            await ctx.send('You have no debt and no one owes you')
        else:
            await ctx.send(message)

    # Print every debt
    elif target is None and amount is None:
        message = '__Debt__\n'
        # Read from csv and append to message
        with open('debt_data.csv') as f:
            csv_reader = csv.reader(f, delimiter=',')
            for row in csv_reader:
                ower = (await get_member_by_id(row[0])).nick if (await get_member_by_id(row[0])).nick is not None else (await get_member_by_id(row[0])).name
                owed = (await get_member_by_id(row[1])).nick if (await get_member_by_id(row[1])).nick is not None else (await get_member_by_id(row[1])).name

                message += f'{ower} owes {owed} {await format_money(float(row[2]))}\n'
        await ctx.send(message)

    # Otherwise something broke, so do nothing
    else:
        pass


##### ============== #####
##### ADMIN COMMANDS #####
##### ============== #####


@client.command()
@commands.has_permissions(administrator=True)
async def clear(ctx, amount=''):
    if amount == 'all':
        await ctx.send(f'Clearing all messages from this channel')
        await log(f'{ctx.author} cleared {amount} messages from #{ctx.channel}')
        amount = 999999999999999999999999999999999999999999
    elif amount == '':
        await ctx.send(f'No args passed. Use `/clear AMOUNT` to clear AMOUNT messages. Use `/clear all` to clear all messages from this channel')
        await log(f'{ctx.author} attempted to clear messages from #{ctx.channel}, but it failed because parameter "amount" was not passed')
        return
    else:
        await ctx.send(f'Clearing {amount} messages from this channel')
        await log(f'{ctx.author} cleared {amount} messages from #{ctx.channel}')
    sleep(1)
    await ctx.channel.purge(limit=int(float(amount)) + 2)


@client.command()
@commands.has_permissions(administrator=True)
async def admin(ctx):
    await ctx.send(f'You\'re an admin, Harry!')


@client.command(aliases=['status'])
@commands.has_permissions(administrator=True)
async def change_status(ctx, *, new_status=''):
    global status

    # Only I can change the status
    if ctx.author.id != 472419156394901524:
        return

    new_status = new_status.strip()
    if new_status.lower() == 'none' or len(new_status) == 0:
        await client.change_presence(activity=None)
        await log(f'{ctx.author} disabled the custom status')
        weather = await get_weather()
        status = f'{weather["temp"]}°F'
        await client.change_presence(activity=discord.Game(status))
        with open('status', 'w') as f:
            f.write('')
    elif len(new_status) <= 128:
        with open('status', 'w') as f:
            f.write(new_status)

        # Prepend weather to status
        weather = await get_weather()
        new_status = f'{weather["temp"]}°F | ' + new_status

        await client.change_presence(activity=discord.Game(new_status))
        await log(f'{ctx.author} changed the custom status to "{new_status}"')
        status = new_status


##### ================= #####
##### UTILITY FUNCTIONS #####
##### ================= #####
async def log(string, timestamp=True):
    # Log to stdout
    timestamp_string = ''
    if timestamp:
        timestamp_string = f'[{str(datetime.now())[:-7]}]'
    print(timestamp_string + ' ' + string)

    # Log to channel
    for guild in client.guilds:
        for channel in guild.text_channels:
            if channel.name == 'bot-logs':
                await channel.send(string)

    # Log to file
    try:
        async with aiofiles.open('log', mode='r') as f:
            previous_logs = await f.readlines()
    except FileNotFoundError:
        previous_logs = []

    async with aiofiles.open('log', mode='w') as f:
        for line in previous_logs:
            await f.write(line.strip() + '\n')
        await f.write(timestamp_string + ' ' + string + '\n')


async def format_money(value):
    return '${:,.2f}'.format(value)


async def get_member_by_id(member_id):
    for guild in client.guilds:
        for member in guild.members:
            if str(member.id) == member_id:
                return member


async def debt_utility(ctx, target, user, amount):
    # Target owes user amount

    # Read existing data from file
    data = []
    if exists('debt_data.csv'):
        with open('debt_data.csv', 'r') as f:
            csv_reader = csv.reader(f, delimiter=',')
            for row in csv_reader:
                row[2] = float(row[2])
                data.append(row)
    else:
        pass

    # If amount is nothing, do nothing
    if amount == 0:
        return

    # If amount is positive, target owes user amount
    elif amount > 0:
        target_owes_user = await owes(data, str(target.id), str(user.id))
        user_owes_target = await owes(data, str(user.id), str(target.id))

        if target_owes_user is not False:
            data[target_owes_user][2] += amount
            if data[target_owes_user][2] == 0:
                data.pop(target_owes_user)

        elif user_owes_target is not False:
            data[user_owes_target][2] -= amount
            if data[user_owes_target][2] == 0:
                data.pop(user_owes_target)

        elif target_owes_user is False and user_owes_target is False:
            if amount != 0:
                data.append([target.id, user.id, amount])

    # If amount is negative, user owes target amount
    else:
        target_owes_user = await owes(data, str(target.id), str(user.id))
        user_owes_target = await owes(data, str(user.id), str(target.id))

        if target_owes_user is not False:
            data[target_owes_user][2] += amount
            if data[target_owes_user][2] == 0:
                data.pop(target_owes_user)
            elif data[target_owes_user][2] < 0:
                data[target_owes_user][0], data[target_owes_user][1] = data[target_owes_user][1], data[target_owes_user][0]
                data[target_owes_user][2] *= -1

        elif user_owes_target is not False:
            data[target_owes_user][2] -= amount
            if data[target_owes_user][2] == 0:
                data.pop(target_owes_user)
            elif data[target_owes_user][2] < 0:
                data[target_owes_user][0], data[target_owes_user][1] = data[target_owes_user][1], data[target_owes_user][0]
                data[target_owes_user][2] *= -1

        elif target_owes_user is False and user_owes_target is False:
            if amount != 0:
                data.append([user.id, target.id, -amount])

    # Write to csv
    with open('debt_data.csv', 'w') as f:
        writer = csv.writer(f, delimiter=',')
        for row in data:
            writer.writerow([row[0], row[1], round(row[2], 2)])

    # Print new debt values
    message = '__Debt__\n'
    # Read from csv and append to message
    with open('debt_data.csv') as f:
        csv_reader = csv.reader(f, delimiter=',')
        for row in csv_reader:
            if str(ctx.author.id) in str(row[0]) or str(ctx.author.id) in str(row[1]):
                ower = (await get_member_by_id(row[0])).nick if (await get_member_by_id(row[0])).nick is not None else (await get_member_by_id(row[0])).name
                owed = (await get_member_by_id(row[1])).nick if (await get_member_by_id(row[1])).nick is not None else (await get_member_by_id(row[1])).name
                message += f'{ower} owes {owed} {await format_money(float(row[2]))}\n'

    if message == '__Debt__\n':
        await ctx.send('You have no debt and no one owes you')
    else:
        await ctx.send(message)


async def owes(data, target, user):
    for i, row in enumerate(data):
        if str(row[0]) == str(target) and str(row[1]) == str(user):
            return i
    return False


async def generate_covid_plot(dataframe):
    def convert_to_active_cases(weeks):
        # Active cases are the sum of confirmed and self-reported cases across both campuses for the current week plus the previous two weeks.
        active_cases = []
        for i in range(2, len(weeks)):
            active_cases.append(weeks[i] + weeks[i - 1] + weeks[i - 2])
        return active_cases

    colors = ['black', 'red', 'blue', 'green', 'orange', 'purple']

    datasets = []
    # datasets.append(list(dataframe['dayton_students']))
    datasets.append(convert_to_active_cases(dataframe['dayton_students']))
    datasets.append(convert_to_active_cases(dataframe['dayton_employees']))
    datasets.append(convert_to_active_cases(dataframe['lake_students']))
    datasets.append(convert_to_active_cases(dataframe['lake_employees']))

    dates = list(dataframe['date'])[2:]

    dataset_labels = ['Dayton Students', 'Dayton Employees', 'Lake Students', 'Lake Employees']

    fig = plt.figure()
    ax1 = fig.add_subplot(111)

    # Iterate through different datasets
    for i in range(len(datasets)):
        ax1.plot(dates, datasets[i], c=colors[i], label=dataset_labels[i], linestyle='-')

    # plt.xticks([dates[i] for i in range(0, len(dates) + 1, len(dates) // 4)])
    cleaned_dates = []
    [cleaned_dates.append(x) for x in dates if x not in cleaned_dates]
    dates = cleaned_dates.copy()
    plt.xticks([dates[i] for i in range(0, len(dates), len(dates) // 4)])
    plt.legend(loc='upper left')
    plt.title('Active Wright State University COVID-19 Cases')

    plt.savefig('wsu_covid_plot.png')


async def format_covid_date(date):
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

    month_day = date[:date.find('–')]
    month = months.index(month_day[:month_day.find(' ')]) + 1
    day = month_day[-2:].strip()
    year = date[date.rfind(', ') + 1:].strip()

    return f'{day}-{month}-{year}'


async def get_wsu_covid_stats():
    page = urllib.request.urlopen('https://www.wright.edu/coronavirus/covid-19-dashboard')
    soup = BeautifulSoup(page, features='html.parser')
    # print(soup.prettify())

    # Parse tables
    tables = soup.find_all('table', attrs={'cellpadding': '1', 'cellspacing': '1'})
    columns = ['date', 'dayton_students', 'dayton_employees', 'lake_students', 'lake_employees']
    data = []
    for table_num, table in enumerate(tables):
        table_body = table.find('tbody')

        rows = table_body.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if str(cols[0]) != '<td><strong>Totals</strong></td>':
                date = await format_covid_date(str(cols[0]).strip('</td>\np'))
                # Check if date not in data
                if not any(date in i for i in data):
                    # If so, make new row
                    data.append([date, 0, 0, 0, 0])

                # Append data
                for i in range(len(data)):
                    if data[i][0] == date:
                        confirmed = int(str(cols[1]).replace('strong>', '').strip('<>/td'))
                        self_reported = int(str(cols[2]).replace('strong>', '').strip('<>/td'))
                        data[i][table_num + 1] = confirmed + self_reported
    data.reverse()

    # Format data and put into DF
    dataframe = pd.DataFrame(data, columns=columns)
    dataframe.to_csv('wsu_covid_cases.csv', index=False)

    # Generate plot
    await generate_covid_plot(dataframe)

    return dataframe


async def get_weather(location='fairborn'):
    global certs
    api_key = certs['openweather api key']

    base_url = "http://api.openweathermap.org/data/2.5/weather?"
    complete_url = base_url + "appid=" + api_key + "&q=" + location

    response = requests.get(complete_url).json()

    dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']

    # Pull the parts we care about and put them into a dictionary
    weather = {'name': response['name'],
               'weather icon': response['weather'][0]['icon'],
               'weather icon url': f'http://openweathermap.org/img/w/{response["weather"][0]["icon"]}.png',
               'weather description': response['weather'][0]['main'].lower(),
               'temp': int((response['main']['temp'] - 273.15) * 1.8 + 32),  # Convert from K to F
               'temp min': int((response['main']['temp_min'] - 273.15) * 1.8 + 32),  # Convert from K to F
               'temp max': int((response['main']['temp_max'] - 273.15) * 1.8 + 32),  # Convert from K to F
               'temp feels like': int((response['main']['feels_like'] - 273.15) * 1.8 + 32),  # Convert from K to F
               'pressure': round(response['main']['pressure'] * 0.001, 2),  # Convert from hPa to bar
               'humidity': response['main']['humidity'],
               'wind speed': round(response['wind']['speed'] * 2.23694, 2),  # Convert m/s to mph
               'wind direction': dirs[round(response['wind']['deg'] / (360. / len(dirs))) % len(dirs)],  # Convert from deg to cardinal directions
               'cloud cover': response['clouds']['all'],
               }

    return weather


async def get_member(guild, member_id):
    # Primary method
    member = guild.get_member(member_id)
    if member is not None:
        return member

    # Secondary method
    for member in guild.members:
        if str(member.id) == str(member_id):
            return member

    # If can't find member, refresh member lists and retry
    async for member in guild.fetch_members():
        if member.id == member_id:
            return member

    # If all else fails, return None
    return None


async def confirmation(ctx, confirm_string):
    # Ask for confirmation
    await ctx.send(f'Enter `{confirm_string}` to confirm action')

    # Wait for confirmation
    msg = await client.wait_for('message', check=lambda message: message.author == ctx.author)
    if msg.content == confirm_string:
        await ctx.send(f'Action confirmed, executing')
        return True
    else:
        await ctx.send(f'Confirmation failed, terminating execution')
        return False


async def dm(member, content):
    channel = await member.create_dm()
    await channel.send(content)


if __name__ == '__main__':
    global certs

    # Read in credentials
    with open('certs.json', 'r') as f:
        certs = json.loads(f.read())

    # Start the bot
    client.run(certs['token'])
