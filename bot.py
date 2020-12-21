#!/usr/bin/env python3
import json
import os
import re
from datetime import datetime
from os.path import exists
from sys import argv
from time import sleep

import aiofiles
import discord
from discord.ext import commands

##### ======= #####
##### GLOBALS #####
##### ======= #####
client = commands.Bot(command_prefix='/', intents=discord.Intents.all())
dumbass_scores = {}


##### =========== #####
##### CORE EVENTS #####
##### =========== #####
@client.event
async def on_ready():
    global reaction_roles
    global dumbass_scores

    await log('Starting up...')

    # Load dumbass scores
    if exists('dumbass_scores.json'):
        with open('dumbass_scores.json', 'r') as f:
            dumbass_scores = json.loads(f.read())

    # Show the bot as online
    await client.change_presence(activity=discord.Game('Hello, sir'), status=None, afk=False)
    await log('Startup completed')


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
    # TODO: Display this at the top of the server
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


@client.command()
@commands.has_permissions(administrator=True)
async def status(ctx, *, status):
    status = status.strip()
    if status.lower() == 'none':
        await client.change_presence(activity=None)
        await log(f'{ctx.author} disabled the custom status')
    elif len(status) <= 128:
        await client.change_presence(activity=discord.Game(status))
        await log(f'{ctx.author} changed the custom status to "Playing {status}"')


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
    # Read in credentials
    with open('certs.json', 'r') as f:
        certs = json.loads(f.read())

    # Start the bot
    client.run(certs['token'])
