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
reaction_roles = None
reaction_message_ids = []


##### =========== #####
##### CORE EVENTS #####
##### =========== #####
@client.event
async def on_ready():
    global reaction_roles

    # Load reaction roles JSON, generate role menu
    if exists('reaction_roles.json'):
        with open('reaction_roles.json', 'r') as f:
            reaction_roles = json.loads(f.read())
        await log('Reaction roles JSON loaded')
        await create_role_menu()
    else:
        await log('No reaction roles JSON found')

    # Show the bot as online
    await client.change_presence(activity=discord.Game('Hello, sir'), status=None, afk=False)
    await log('Bot is online')


##### ================== #####
##### MEMEBER MANAGEMENT #####
##### ================== #####
@client.event
async def on_raw_reaction_add(payload):
    try:
        if payload.message_id in reaction_message_ids:
            # Get CSE guild
            guild_id = payload.guild_id
            guild = discord.utils.find(lambda g: g.id == guild_id, client.guilds)

            # Find a role corresponding to the emoji name.
            classes = []
            for menu in reaction_roles.keys():
                for class_name in reaction_roles[menu].keys():
                    if class_name not in ['channel_name', 'clear_channel']:
                        classes.append(reaction_roles[menu][class_name])
            role = None
            for _class in classes:
                emoji = f':{_class["emoji"]}:'
                if emoji in str(payload.emoji):
                    role = discord.utils.find(lambda r: r.name == _class['role'], guild.roles)

            # If role found, assign it
            if role is not None:
                member = await guild.fetch_member(payload.user_id)
                if not member.bot:  # Error suppression
                    await member.add_roles(role)
                    await dm(member, f'Welcome to {role}!')
                    await log(f'Assigned role {role} to {member}')
    except Exception:
        await log('Error suppressed, likely due to bot reacting to a role menu')


@client.event
async def on_raw_reaction_remove(payload):
    if payload.message_id in reaction_message_ids:
        # Get CSE guild
        guild_id = payload.guild_id
        guild = discord.utils.find(lambda g: g.id == guild_id, client.guilds)

        # Find a role corresponding to the emoji name.
        classes = []
        for menu in reaction_roles.keys():
            for class_name in reaction_roles[menu].keys():
                if class_name not in ['channel_name', 'clear_channel']:
                    classes.append(reaction_roles[menu][class_name])
        role = None
        for _class in classes:
            emoji = f':{_class["emoji"]}:'
            if emoji in str(payload.emoji):
                role = discord.utils.find(lambda r: r.name == _class['role'], guild.roles)

        # If role found, take it
        if role is not None:
            member = await guild.fetch_member(payload.user_id)
            await member.remove_roles(role)
            await dm(member, f'We\'ve taken you out of {role}')
            await log(f'Took role {role} from {member}')


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
async def buildserver(ctx):
    # Get confirmation before wiping
    if not await confirmation(ctx, 'build'):
        return

    if not exists('reaction_roles.json'):
        ctx.send('No reaction_roles.json found, please run again with attached JSON')
        return
    else:
        # Read JSON file attached to message, or make sure reaction roles are loaded if not attachment
        if len(ctx.message.attachments) > 0:
            try:
                os.remove('reaction_roles.json')
            except FileNotFoundError:
                pass
            await ctx.message.attachments[0].save('reaction_roles.json')
        try:
            with open('reaction_roles.json', 'r') as f:
                reaction_roles = json.loads(f.read())
        except FileNotFoundError:
            await ctx.send('Missing reaction roles JSON')
            return

        await log(f'BUILDING SERVER ({ctx.author})')
        await destroy_server(ctx.guild)
        await build_server(ctx.guild)
        await log('Recreating reaction role menus')
        await create_role_menu()


@client.command()
@commands.has_permissions(administrator=True)
async def destroyserver(ctx):
    # Get confirmation before wiping
    if not await confirmation(ctx, 'destroy'):
        return

    await log(f'DESTROYING SERVER ({ctx.author})')
    await destroy_server(ctx.guild)


@client.command()
@commands.has_permissions(administrator=True)
async def admin(ctx):
    await ctx.send(f'You\'re an admin, Harry!')


@client.command()
@commands.has_permissions(administrator=True)
async def rolemenu(ctx):
    global reaction_roles

    # Read JSON file attached to message
    if len(ctx.message.attachments) > 0:
        try:
            os.remove('reaction_roles.json')
        except FileNotFoundError:
            pass
        await ctx.message.attachments[0].save('reaction_roles.json')
    try:
        with open('reaction_roles.json', 'r') as f:
            reaction_roles = json.loads(f.read())
    except FileNotFoundError:
        await ctx.send('Missing reaction roles JSON')
        return

    # Create the role menu
    await create_role_menu()
    await log(f'{ctx.author} built a rolemenu in #{ctx.channel}. Configuration saved to reaction_roles.json')


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


async def create_role_menu():
    def get_emoji(emoji_name):
        emoji = discord.utils.get(client.emojis, name=emoji_name)
        if emoji is not None:
            return emoji
        return f':{emoji_name}:'

    # Generate list of menus to iterate through when sending messages
    menus = []
    clear_channel = False
    for key in reaction_roles.keys():
        menus.append((key, reaction_roles[key]))

    # Generate each menu independently
    for menu in menus:
        print(f'Generating menu {menu[0]} in {menu[1]["channel_name"]}')
        # Get channel object
        channel_name = menu[1]['channel_name']
        reaction_role_channel = None
        for guild in client.guilds:
            for channel in guild.channels:
                if channel.name.strip().lower() == channel_name.strip().lower():
                    reaction_role_channel = channel

        # Clear channel if necessary
        if bool(menu[1]['clear_channel']):
            await reaction_role_channel.purge(limit=99999999999999)

        # Send menus
        message = f'__**{menu[0].strip()}**__\n'
        if not bool(menu[1]['clear_channel']):
            message = f'_ _\n__**{menu[0].strip()}**__\n'
        for option_name in menu[1].keys():
            if option_name not in ['channel_name', 'clear_channel']:
                emoji = str(get_emoji(menu[1][option_name]['emoji']))
                message += f'{emoji} `{option_name}`\n'
        reaction_message = await reaction_role_channel.send(message)

        # React to menu
        for option_name in menu[1].keys():
            if option_name not in ['channel_name', 'clear_channel']:
                emoji = get_emoji(menu[1][option_name]['emoji'])
                await reaction_message.add_reaction(emoji)

            # Put reaction message ids in global list
            reaction_message_ids.append(reaction_message.id)


async def destroy_server(guild):
    # Deletes all CS/CEG/EE class channels/categories
    cse_ee_class_names = re.compile('(CS|CEG|EE) \\d{1,4}')

    # Find all matching categories in the guild
    for category in guild.categories:
        if cse_ee_class_names.match(category.name):

            # Delete all channels in the category
            await log(f'Deleting: {category.name}')
            for channel in category.channels:
                await channel.delete()

            # Delete the category itself
            await category.delete()

    # Delete class roles
    for role in guild.roles:
        if cse_ee_class_names.match(role.name):
            await role.delete()


async def build_server(guild):
    # Builds new CS/CEG/EE class channels/categories from reaction roles
    cse_ee_class_names = re.compile('(CS|CEG|EE) \\d{1,4}')

    # Iterate through all menus in reaction roles
    for menu in reaction_roles:
        # Iterate through all classes in each menu
        for _class in reaction_roles[menu]:
            # Ignore menu properties
            if cse_ee_class_names.match(_class):
                await log(f'Building: {_class}')

                # Create class role
                permissions = discord.Permissions(read_messages=True, send_messages=True, embed_links=True, attach_files=True, read_message_history=True, add_reactions=True, connect=True, speak=True, stream=True, use_voice_activation=True, change_nickname=True, mention_everyone=False)
                await guild.create_role(name=_class, permissions=permissions)

                # Create category
                category = await guild.create_category(_class)
                await category.set_permissions(guild.default_role, read_messages=False)
                for role in guild.roles:
                    if role.name == _class:
                        await category.set_permissions(role, read_messages=True)
                        break

                # Create channels
                await category.create_text_channel(_class.replace(' ', ''))
                await category.create_voice_channel('Student Voice')
                await category.create_voice_channel('TA Voice', user_limit=2)


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
