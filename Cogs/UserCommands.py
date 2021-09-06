from datetime import datetime, timedelta
from time import time, sleep

import discord
import pandas as pd
from discord.ext import commands
from discord_components import Button, ButtonStyle, InteractionType
from utils import *


def setup(bot):
    bot.add_cog(UserCommands(bot))


class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Dumbass list
        self.dumbass_list = pd.read_csv('dumbasses.csv')
        self.dumbass_list_indicies = {}
        self.dumbass_list_components = []
        self.dinc_polls = {}

        # Calculator
        self.calc_strings = {}
        self.calculator_components = []

    @commands.command()
    async def poll(self, ctx, question, *options: str):
        # Delete sender's message
        await ctx.message.delete()

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

    @commands.command()
    async def ping(self, ctx):
        await ctx.send(f'{round(self.bot.latency * 1000)} ms')

    @commands.command()
    async def weather(self, ctx, location='fairborn'):
        pass
        # weather = await get_weather(location)

        # message = f'__**Weather: {weather["name"]}**__\n'
        # message += f'Temperature: {weather["temp"]}°F (feels like {weather["temp feels like"]}°F) {weather["temp min"]}°F / {weather["temp max"]}°F\n'
        # message += f'Weather: {weather["weather description"]}\n'
        # message += f'Wind: {weather["wind speed"]} mph {weather["wind direction"]}\n'
        # message += f'Cloud Cover: {weather["cloud cover"]}%\n'
        # message += f'Pressure: {weather["pressure"]} bar\n'
        # message += f'Humidity: {weather["humidity"]}%'

        # await ctx.send(message)

    @commands.command(aliases=['calc'])
    async def calculator(self, ctx):
        # Setting up buttons
        # 7 8 9 +
        # 4 5 6 -
        # 1 2 3 *
        # . 0 < /
        # C ( ) =
        empty_button = Button(style=ButtonStyle.gray, label=' ')
        self.calculator_components = [[empty_button, empty_button, empty_button, empty_button] for _ in range(5)]

        # Numbers
        self.calculator_components[0][0] = Button(style=ButtonStyle.blue, label='7')
        self.calculator_components[0][1] = Button(style=ButtonStyle.blue, label='8')
        self.calculator_components[0][2] = Button(style=ButtonStyle.blue, label='9')
        self.calculator_components[1][0] = Button(style=ButtonStyle.blue, label='4')
        self.calculator_components[1][1] = Button(style=ButtonStyle.blue, label='5')
        self.calculator_components[1][2] = Button(style=ButtonStyle.blue, label='6')
        self.calculator_components[2][0] = Button(style=ButtonStyle.blue, label='1')
        self.calculator_components[2][1] = Button(style=ButtonStyle.blue, label='2')
        self.calculator_components[2][2] = Button(style=ButtonStyle.blue, label='3')
        self.calculator_components[3][1] = Button(style=ButtonStyle.blue, label='0')

        # Other functions
        self.calculator_components[0][3] = Button(style=ButtonStyle.red, label='+')
        self.calculator_components[1][3] = Button(style=ButtonStyle.red, label='-')
        self.calculator_components[2][3] = Button(style=ButtonStyle.red, label='*')

        self.calculator_components[3][0] = Button(style=ButtonStyle.gray, label='.')
        self.calculator_components[3][2] = Button(style=ButtonStyle.gray, label='<-')
        self.calculator_components[3][3] = Button(style=ButtonStyle.red, label='/')

        self.calculator_components[4][0] = Button(style=ButtonStyle.gray, label='C')
        self.calculator_components[4][1] = Button(style=ButtonStyle.gray, label='(')
        self.calculator_components[4][2] = Button(style=ButtonStyle.gray, label=')')
        self.calculator_components[4][3] = Button(style=ButtonStyle.green, label='=')

        # Send message
        message = await ctx.channel.send('`' + 34 * ' ' + '`', components=self.calculator_components)
        self.calc_strings[message.id] = ''

    @commands.Cog.listener()
    async def on_button_click(self, res):
        msg_id = res.message.id

        # If for calculator
        if msg_id in self.calc_strings.keys():
            # Clear ERROR
            if self.calc_strings[msg_id] == 'ERROR':
                self.calc_strings[msg_id] = ''

            # If number, decimal, or parenthesis clicked, just add to string
            if res.component.label in '.1234567890()':
                self.calc_strings[msg_id] += res.component.label
            # If other thing clicked, add it with space padding
            elif res.component.label in '+-*/':
                self.calc_strings[msg_id] += f' {res.component.label} '
            # If <- pressed, delete last char
            elif res.component.label == '<-':
                self.calc_strings[msg_id] = self.calc_strings[msg_id][:-1]
            # If c pressed, clear
            elif res.component.label == 'C':
                self.calc_strings[msg_id] = ''
            # If = pressed, do math
            else:
                try:
                    calc_list = self.calc_strings[msg_id].split(' ')
                    for i in range(len(calc_list)):
                        if calc_list[i] != '0':
                            calc_list[i] = calc_list[i].lstrip('0')
                    self.calc_strings[msg_id] = ' '.join(calc_list)
                    if len(self.calc_strings[msg_id]) == 0:
                        self.calc_strings[msg_id] = '0'
                    self.calc_strings[msg_id] = str(round(eval(self.calc_strings[msg_id]), 15))

                except (SyntaxError, ZeroDivisionError):
                    self.calc_strings[msg_id] = 'ERROR'

            # Update calc string
            formatted_calc_string = '`' + (34 - len(self.calc_strings[msg_id])) * ' ' + self.calc_strings[msg_id] + '`'
            await res.respond(type=InteractionType.UpdateMessage, content=formatted_calc_string, components=self.calculator_components)

        # If for dumbass display
        elif msg_id in self.dumbass_list_indicies.keys():
            # Initial value modification
            if res.component.label == '⏪':
                self.dumbass_list_indicies[msg_id] = self.dumbass_list_indicies[msg_id] - 10
            elif res.component.label == '◀':
                self.dumbass_list_indicies[msg_id] = self.dumbass_list_indicies[msg_id] - 1
            elif res.component.label == '▶':
                self.dumbass_list_indicies[msg_id] = self.dumbass_list_indicies[msg_id] + 1
            elif res.component.label == '⏩':
                self.dumbass_list_indicies[msg_id] = self.dumbass_list_indicies[msg_id] + 10
            elif str(res.component.emoji) == '✖':
                try:
                    is_admin = res.user.permissions_in(res.message.channel).administrator
                    if is_admin:
                        self.dumbass_list = self.dumbass_list.drop(self.dumbass_list_indicies[msg_id])
                        self.dumbass_list.to_csv('dumbasses.csv', index=False)
                        self.dumbass_list_indicies[msg_id] -= 1
                        await self._build_dumbass_leaderboard(res.message.guild)
                    else:
                        await res.respond(type=InteractionType.ChannelMessageWithSource, content='Only admins can delete dincs!')
                except AttributeError:
                    await res.respond(type=InteractionType.ChannelMessageWithSource, content='Only admins can delete dincs!')

            # Keep index in range
            if self.dumbass_list_indicies[msg_id] < 0:
                self.dumbass_list_indicies[msg_id] += len(self.dumbass_list)
            elif self.dumbass_list_indicies[msg_id] >= len(self.dumbass_list):
                self.dumbass_list_indicies[msg_id] %= len(self.dumbass_list)

            self.dumbass_list_components[0][2] = Button(style=ButtonStyle.red, label=f'{self.dumbass_list_indicies[msg_id] + 1} / {len(self.dumbass_list)}', emoji='✖')
            await res.respond(type=InteractionType.UpdateMessage, components=self.dumbass_list_components, embed=await self._dumbass_embed(res.message.guild, self.dumbass_list_indicies[msg_id]))

        # If for dinc poll
        elif msg_id in self.dinc_polls.keys():
            target = await get_member(res.message.guild, self.dinc_polls[msg_id][0])
            target = target.id

            # If yes vote
            if str(res.component.emoji) == '✔':
                # If target votes yes, approve
                if res.user.id == target:
                    # Add to csv and save, delete poll
                    reason = ' '.join(res.message.content.split(' ')[3:])[:-1]
                    await res.message.delete()
                    self.dumbass_list = self.dumbass_list.append({'id': target, 'reason': reason, 'timestamp': time()}, ignore_index=True)
                    self.dumbass_list.to_csv('dumbasses.csv', index=False)
                    await self._build_dumbass_leaderboard(res.message.guild)
                    del self.dinc_polls[msg_id]
                    return
                else:
                    # Add to yes list
                    if res.user.id not in self.dinc_polls[msg_id][1]:
                        self.dinc_polls[msg_id][1].append(res.user.id)
                    # Or remove from yes list
                    else:
                        self.dinc_polls[msg_id][1].remove(res.user.id)
                    # Remove from no list
                    if res.user.id in self.dinc_polls[msg_id][2]:
                        self.dinc_polls[msg_id][2].remove(res.user.id)

            # If no vote
            elif str(res.component.emoji) == '✖':
                if res.user.id != target:
                    # Add to no list
                    if res.user.id not in self.dinc_polls[msg_id][2]:
                        self.dinc_polls[msg_id][2].append(res.user.id)
                    # Or remove from no list
                    else:
                        self.dinc_polls[msg_id][2].remove(res.user.id)
                    # Remove from yes list
                    if res.user.id in self.dinc_polls[msg_id][1]:
                        self.dinc_polls[msg_id][1].remove(res.user.id)
                else:
                    await res.respond(type=InteractionType.ChannelMessageWithSource, content="You can't vote no when you're getting dinc'd")

            poll_components = [[Button(style=ButtonStyle.green, emoji='✔', label=f'[{len(self.dinc_polls[msg_id][1])}]'),
                                Button(style=ButtonStyle.red, emoji='✖', label=f'[{len(self.dinc_polls[msg_id][2])}]')]]
            await res.respond(type=InteractionType.UpdateMessage, content=res.message.content, components=poll_components)

    @commands.command(aliases=['dinc'])
    async def dumbass_increment(self, ctx, member_id='0', *, reason):
        # Arg parsing
        if member_id == '0':
            member_id = ctx.author.id
        member_id = member_id.strip('<@!>')
        if reason is None:
            await ctx.send('Rerun command with reason')
            return

        # If author is dincing themselves, approve
        author = ctx.author
        target = await get_member(ctx.guild, member_id)
        if target.id == author.id:
            # Add to csv and save
            self.dumbass_list = self.dumbass_list.append({'id': int(member_id), 'reason': reason, 'timestamp': time()}, ignore_index=True)
            self.dumbass_list.to_csv('dumbasses.csv', index=False)

            # Make leaderboard
            await self._build_dumbass_leaderboard(ctx.guild)

        # If author is dincing someone else
        else:
            POLL_TIME = 60
            await ctx.message.delete()
            # Make a 60s timed poll to get approval from members (ignoring the target). Author auto votes yes
            poll_components = [[Button(style=ButtonStyle.green, emoji='✔', label=f'[1]'),
                                Button(style=ButtonStyle.red, emoji='✖', label='[0]')]]
            message = await ctx.channel.send(f'**[{str(timedelta(seconds=POLL_TIME))[2:]}]** Dinc {target.mention} for {reason}?', components=poll_components)
            self.dinc_polls[message.id] = (target.id, [author.id], [])  # Target, vote yes, vote no
            for timer in range(POLL_TIME - 1, -1, -1):
                sleep(1)
                await message.edit(content=f'**[{str(timedelta(seconds=timer))[2:]}]** Dinc {target.mention} for {reason}?', components=message.components)

            # Process results of poll
            # If more yes votes than no votes
            if len(self.dinc_polls[message.id][1]) - 1 > len(self.dinc_polls[message.id][2]):
                # If dinc with this reason not already recently added to dataframe
                df = self.dumbass_list.tail(10)
                for _, row in df.iterrows():
                    if row['id'] == target.id and row['reason'] == reason:
                        return

                # Add to csv and save, delete poll
                await message.delete()
                self.dumbass_list = self.dumbass_list.append({'id': target.id, 'reason': reason, 'timestamp': time()}, ignore_index=True)
                self.dumbass_list.to_csv('dumbasses.csv', index=False)
                await self._build_dumbass_leaderboard(message.guild)
                del self.dinc_polls[message.id]

    async def _build_dumbass_leaderboard(self, guild):
        # Check if category exists. If not, make it
        category = None
        category_name = 'Top Dumbasses'
        for c in guild.categories:
            if c.name == category_name:
                category = c
                break
        if category is None:
            category = await guild.create_category('Top Dumbasses', position=0)
            await category.edit(position=0)  # Ensuring it actually goes to the top

        # Delete every channel under it
        for channel in category.channels:
            await channel.delete()

        # Remake channels for leaderboard
        scores = self.dumbass_list['id'].value_counts()
        for member_id, count in scores.iteritems():
            member = await get_member(guild, member_id)
            await category.create_text_channel(f'({count}) {member.display_name}')

    async def _dumbass_embed(self, guild, index):
        # Properties of dinc
        member = await get_member(guild, self.dumbass_list.at[index, 'id'])
        reason = str(self.dumbass_list.at[index, 'reason'])
        if reason == 'nan':
            reason = 'Unknown reason'
        timestamp = self.dumbass_list.at[index, 'timestamp']
        try:
            timestamp = datetime.utcfromtimestamp(timestamp).strftime('%c')
        except ValueError:
            timestamp = 'Unknown timestamp'

        # Create the embed
        embed = discord.Embed(title=timestamp, description=reason)
        embed.set_author(name=member.display_name, icon_url=str(member.avatar_url))
        return embed

    @commands.command()
    async def dumbasses(self, ctx):
        # Create menu
        index = len(self.dumbass_list) - 1
        self.dumbass_list_components = [[Button(style=ButtonStyle.green, label='⏪'),
                                        Button(style=ButtonStyle.green, label='◀'),
                                        Button(style=ButtonStyle.red, label=f'{index + 1} / {len(self.dumbass_list)}', emoji='✖'),
                                        Button(style=ButtonStyle.green, label='▶'),
                                        Button(style=ButtonStyle.green, label='⏩')]]
        embed = await self._dumbass_embed(ctx.guild, index)

        # Set index for message
        message = await ctx.channel.send(embed=embed, components=self.dumbass_list_components)
        self.dumbass_list_indicies[message.id] = index
