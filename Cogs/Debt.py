from time import sleep

from discord.ext import commands


def setup(bot):
    bot.add_cog(Debt(bot))


class Debt(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # @commands.command(help='`/clear AMOUNT` to clear AMOUNT messages\n`/clear all` to clear all messages from this channel')
    # @commands.has_permissions(administrator=True)
    # async def clear(self, ctx, amount=''):
    #     if amount == 'all':
    #         if not await confirmation(self.bot, ctx):
    #             return
    #         await ctx.send(f'Clearing all messages from this channel')
    #         await log(self.bot, f'{ctx.author} cleared {amount} messages from #{ctx.channel}')
    #         amount = 999999999999999999999999999999999999999999
    #     elif amount == '':
    #         await ctx.send(f'No args passed. Use `/clear AMOUNT` to clear AMOUNT messages. Use `/clear all` to clear all messages from this channel')
    #         await log(self.bot, f'{ctx.author} attempted to clear messages from #{ctx.channel}, but it failed because parameter "amount" was not passed')
    #         return
    #     else:
    #         amount = int(amount)
    #         if amount >= 10 and not await confirmation(self.bot, ctx):
    #             return
    #         await ctx.send(f'Clearing {amount} messages from this channel')
    #         await log(self.bot, f'{ctx.author} cleared {amount} messages from #{ctx.channel}')
    #     sleep(1)
    #     await ctx.channel.purge(limit=int(float(amount)) + 2)

    # @client.command()
    # async def owe(ctx, target=None, amount=None):
    #     # Get objects for ctx.author, target, and amount
    #     user = ctx.author
    #     if target is not None:
    #         target = re.sub('\\D', '', target)
    #         target = await get_member_by_id(target)
    #     if amount is not None:
    #         amount = round(float(amount), 2)
    #         if amount <= 0:
    #             amount = None

    #     if target is not None and amount is not None:
    #         await debt_utility(ctx, user, target, amount)

    # @client.command()
    # async def pay(ctx, target=None, amount=None):
    #     # Get objects for ctx.author, target, and amount
    #     user = ctx.author
    #     if target is not None:
    #         target = re.sub('\\D', '', target)
    #         target = await get_member_by_id(target)
    #     if amount is not None:
    #         amount = round(float(amount), 2)
    #         if amount <= 0:
    #             amount = None

    #     if target is not None and amount is not None:
    #         await debt_utility(ctx, target, user, amount)

    # @client.command()
    # async def debt(ctx, target=None, amount=None):
    #     # Get objects for ctx.author, target, and amount
    #     user = ctx.author
    #     if target is not None:
    #         target = re.sub('\\D', '', target)
    #         target = await get_member_by_id(target)
    #     if amount is not None:
    #         amount = round(float(amount), 2)
    #         if amount <= 0:
    #             amount = None

    #     # Target owes ctx.author amount
    #     if target is not None and amount is not None:
    #         await debt_utility(ctx, target, user, amount)

    #     # Print how much ctx.author owes target, or vice versa
    #     elif target is not None and amount is None:
    #         # Read from csv and append to message
    #         with open('debt_data.csv') as f:
    #             csv_reader = csv.reader(f, delimiter=',')
    #             data = []
    #             for row in csv_reader:
    #                 data.append(row)
    #             await print_debt(ctx, data, member_id=target.id)

    #     # Print every debt
    #     elif target is None and amount is None:
    #         # # Read from csv and append to message
    #         with open('debt_data.csv') as f:
    #             csv_reader = csv.reader(f, delimiter=',')
    #             data = []
    #             for row in csv_reader:
    #                 data.append(row)
    #             await print_debt(ctx, data)

    #     else:
    #         pass
