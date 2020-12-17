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
client = discord.Client()
client = commands.Bot(command_prefix='/')
reaction_roles = {}  # list of dicts of tuples: {guild_id: (guild, reaction roles dict)}
reaction_message_ids = []


##### =========== #####
##### CORE EVENTS #####
##### =========== #####
@client.event
async def on_ready():
    global reaction_roles

    await log('Starting up...')

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
