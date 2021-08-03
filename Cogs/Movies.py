from datetime import datetime, timedelta
from time import time, sleep


import discord
import os
import pandas as pd
from discord.ext import commands
from discord_components import Button, ButtonStyle, InteractionType
from utils import *
import random
import requests


def setup(bot):
    bot.add_cog(Movies(bot))


class Movies(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # If the movies.csv file doesn't exist, create it and add the headers
        if not os.path.isfile('movies.csv'):
            with open('movies.csv', 'w') as f:
                f.write('Title,User,Watched\n')

        self.movie_list = pd.read_csv('movies.csv')


    async def need_movie(self, ctx, *, movie_name: str):
        # If the movie was already on the list, call a dumbass increment on the user
        if movie_name.lower() in (str(i).lower() for i in self.movie_list['Title'].values):
            old_author = ctx.author
            ctx.author = self.bot.user
            await ctx.invoke(self.bot.get_command('dinc'), member_id=str(old_author.id), reason='trying to add a movie that was already in the list')
            return

        self.movie_list = self.movie_list.append(
            {'Title': movie_name, 'User': ctx.author.name, 'Watched': False}, ignore_index=True)
        self.movie_list.to_csv('movies.csv', index=False)

        # Send a message to the channel to confirm the movie was added
        await ctx.send(f'"{movie_name}" has been added to the watch list!')


    async def list_movies(self, ctx):
        if len(self.movie_list) == 0:
            await ctx.send('No movies right now. Get to work adding some!')
            return

        movie_message = ''

        # Discord messages can't hold more than 2000 characters, so split the message into multiple messages if necessary
        for index, row in self.movie_list.iterrows():
            line = f'**{row["Title"]}**, added by {row["User"]}'

            # Strike the movie if it's been watched
            if row['Watched']:
                line = f'~~{line}~~\n'
            else:
                line += '\n'

            if len(movie_message + line) > 2000:
                await ctx.send(movie_message)
                movie_message = ''

            movie_message += line

        # Send the last message if it's not empty
        if movie_message:
            await ctx.send(movie_message)


    async def watch(self, ctx, *, movie_name: str):
        # Check to make sure that the movie exists
        if movie_name.lower() not in (str(i).lower() for i in self.movie_list['Title'].values):
            await ctx.send('That movie was not in the list, so I added it')
            self.movie_list = self.movie_list.append(
                {'Title': movie_name, 'User': ctx.author.name, 'Watched': True}, ignore_index=True)
            return

        index = self.movie_list[self.movie_list['Title'].str.contains(movie_name.lower(), na=False, case=False)].index
        self.movie_list.loc[index, 'Watched'] = True
        self.movie_list.to_csv('movies.csv', index=False)

        # Send a message to the channel to confirm the movie was watched
        await ctx.send(f'"{movie_name}" has been watched!')


    async def pick_movie(self, ctx):
        movie_list = self.movie_list.loc[self.movie_list['Watched'] == False]

        if len(movie_list) == 0:
            await ctx.send('There are no more movies to pick from :(')
            await self.throw_tomato(ctx)
            return

        movie = movie_list.sample()

        # Send a message to the channel to confirm the movie was watched
        await ctx.send(f'We\'re watching **{movie["Title"].values[0]}**!')


    async def throw_tomato(self, ctx):
        # Grab a random movie from rotten tomatoes

        data = {'movieCount': 0}

        # pick a random word from words.txt
        with open('words.txt', 'r') as f:
            words = f.readlines()
            word = random.choice(words).strip()
            word = word.replace(' ', '+')

        r = requests.get(f'https://www.rottentomatoes.com/api/private/v2.0/search/?limit=20&meterClass=rotten&q={word}')
        data = r.json()

        if data['movieCount'] == 0:
            await ctx.send(' ...I dunno. I can\'t think of any right now')
            return

        movies = data['movies']
        movie = movies[random.randint(0, len(movies) - 1)]
        movie_name = movie['name']
        movie_image = movie['image']
        movie_url = 'https://rottentomatoes.com' + movie['url']
        embed = discord.Embed(title=movie_name, url=movie_url)
        embed.set_image(url=movie_image)
        await ctx.send('I found this though!', embed=embed)


    # Command to act as a wrapper for all the movie functions
    @commands.command()
    async def movie(self, ctx, subcommand=None, *movie_name):
        if subcommand in ['need', 'add']:
            await self.need_movie(ctx, movie_name=' '.join(movie_name))
        elif subcommand == 'list':
            await self.list_movies(ctx)
        elif subcommand == 'watch':
            await self.watch(ctx, movie_name=' '.join(movie_name))
        elif subcommand in ['pick', 'random']:
            await self.pick_movie(ctx)
        elif subcommand == 'tomato':
            await self.throw_tomato(ctx)
        else:
            await ctx.send(f'**Valid Movie Commands**\n' +
                           f'`{self.bot.command_prefix}movie add [movie_name]` - Add a movie to the watch list\n' +
                           f'`{self.bot.command_prefix}movie need [movie_name]` - Same as `add`\n' +
                           f'`{self.bot.command_prefix}movie list` - List all the movies in the watch list\n' +
                           f'`{self.bot.command_prefix}movie watch [movie_name]` - Watch a movie\n' +
                           f'`{self.bot.command_prefix}movie pick` - Pick a random movie to watch\n' +
                           f'`{self.bot.command_prefix}movie random` - Same as `pick`')
