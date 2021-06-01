#!/usr/bin/env python3
import os
from os.path import exists

import discord
from discord.ext import commands
from discord_components import (Button, ButtonStyle, DiscordComponents,
                                InteractionType)
from dotenv import load_dotenv

##### =========== #####
##### = GLOBALS = #####
##### =========== #####
client = discord.Client()
client = commands.Bot(command_prefix='-', intents=discord.Intents.all())
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')


##### =============== #####
##### = CORE EVENTS = #####
##### =============== #####
@client.event
async def on_ready():
    DiscordComponents(client)

    # Load all cogs
    for file in os.listdir('Cogs'):
        if not file.startswith('__') and file.endswith('.py'):
            try:
                client.load_extension(f'Cogs.{file[:-3]}')
            except commands.errors.NoEntryPointError:
                pass
    print('Cogs loaded')


@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply(f'Missing required arguement\n{error}')
    elif isinstance(error, commands.MissingRole):
        await ctx.reply('Missing role')
    elif isinstance(error, commands.CommandNotFound):
        await ctx.reply('Command not found')
    else:
        await ctx.reply(f'Unexpected error: {error}')


if __name__ == '__main__':
    client.run(TOKEN)
