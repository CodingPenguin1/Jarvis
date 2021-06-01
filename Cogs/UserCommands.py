from time import time

import discord
import pandas as pd
from discord.ext import commands
from discord_components import (Button, ButtonStyle, DiscordComponents,
                                InteractionType)
from utils import *


def setup(bot):
    bot.add_cog(UserCommands(bot))


class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dumbasses = pd.read_csv('dumbasses.csv')

    @commands.command()
    async def poll(self, ctx, question, *options: str):
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
        # . 0 = /
        empty_button = Button(style=ButtonStyle.gray, label=' ')
        components = [[empty_button, empty_button, empty_button, empty_button] for _ in range(4)]
        components.append([empty_button, empty_button])

        # Numbers
        components[0][0] = Button(style=ButtonStyle.blue, label='7')
        components[0][1] = Button(style=ButtonStyle.blue, label='8')
        components[0][2] = Button(style=ButtonStyle.blue, label='9')
        components[1][0] = Button(style=ButtonStyle.blue, label='4')
        components[1][1] = Button(style=ButtonStyle.blue, label='5')
        components[1][2] = Button(style=ButtonStyle.blue, label='6')
        components[2][0] = Button(style=ButtonStyle.blue, label='1')
        components[2][1] = Button(style=ButtonStyle.blue, label='2')
        components[2][2] = Button(style=ButtonStyle.blue, label='3')
        components[3][1] = Button(style=ButtonStyle.blue, label='0')

        # Other functions
        components[3][0] = Button(style=ButtonStyle.gray, label='.')
        components[3][2] = Button(style=ButtonStyle.green, label='=')
        components[0][3] = Button(style=ButtonStyle.red, label='+')
        components[1][3] = Button(style=ButtonStyle.red, label='-')
        components[2][3] = Button(style=ButtonStyle.red, label='*')
        components[3][3] = Button(style=ButtonStyle.red, label='/')
        components[4][0] = Button(style=ButtonStyle.gray, label='c')
        components[4][1] = Button(style=ButtonStyle.gray, label='<-')

        # Creating print line
        calc_string = ''
        formatted_calc_string = '`' + (34 - len(calc_string)) * ' ' + calc_string + '`'

        # Send message
        await ctx.channel.send(formatted_calc_string, components=components)

        # Update message
        while True:
            # interaction = await bot.wait_for("button_click", check=lambda i: i.component.label.startswith("WOW"))
            res = await self.bot.wait_for("button_click")

            # If number or decimal clicked, just add to string
            if res.component.label in '.1234567890':
                calc_string += res.component.label
            # If other thing clicked, add it with space padding
            elif res.component.label in '+-*/':
                calc_string += f' {res.component.label} '
            # If <- pressed, delete last char
            elif res.component.label == '<-':
                calc_string = calc_string[:-1]
            # If c pressed, clear
            elif res.component.label == 'c':
                calc_string = ''
            # If = pressed, do math
            else:
                calc_string = str(eval(calc_string))

            # Update calc string
            formatted_calc_string = '`' + (34 - len(calc_string)) * ' ' + calc_string + '`'

            await res.respond(type=InteractionType.UpdateMessage, content=formatted_calc_string, components=components)

    @commands.command(aliases=['dinc'])
    async def dumbass_increment(self, ctx, member_id='0', *, reason):
        # Arg parsing
        if member_id == '0':
            member_id = ctx.author.id
        member_id = member_id.strip('<@!>')

        if reason is None:
            await ctx.send('Rerun command with reason')
            return

        # Add to csv and save
        self.dumbasses = self.dumbasses.append({'id': member_id, 'reason': reason, 'timestamp': time()}, ignore_index=True)
        self.dumbasses.to_csv('dumbasses.csv')

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
        scores = self.dumbasses['id'].value_counts()
        for member_id, count in scores.iteritems():
            member = await get_member(ctx.guild, member_id)
            await category.create_text_channel(f'({count}) {member.display_name}')

    @commands.command()
    async def dumbasses(self, ctx):
        # Button styles: blue, gray, green, grey, randomColor, red, URL
        components = []
        for i in range(5):
            line = [Button(style=ButtonStyle.blue, label=str(i * j)) for j in range(5)]
            components.append(line)
        await ctx.channel.send(
            'Lookie! Pretty buttons!',
            components=components
            # components=[
            #     Button(style=ButtonStyle.blue, label="Blue"),
            #     Button(style=ButtonStyle.red, label="Red"),
            #     Button(style=ButtonStyle.URL, label="url", url="https://example.org"),
            # ],
        )

        res = await self.bot.wait_for("button_click")
        await res.respond(type=InteractionType.ChannelMessageWithSource, content=f'{res.component.label} clicked')

    # @commands.Cog.listener()
    # async def on_button_click(self, res):
    #     """
        # Pong
        # ChannelMessageWithSource         - replies just to you
        # DeferredChannelMessageWithSource - replies to message with content, thinks forever
        # DeferredUpdateMessage
        # UpdateMessage                    - edits the message
    #     """
    #     # await res.respond(
    #     #     type=InteractionType.ChannelMessageWithSource, content=f"{res.component.label} pressed"
    #     # )
    #     await res.respond(type=InteractionType.ChannelMessageWithSource, content=f'{res.component.label} clicked')
