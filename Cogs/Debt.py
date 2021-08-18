import pandas as pd
from discord.ext import commands
from utils import *


def setup(bot):
    bot.add_cog(Debt(bot))


class Debt(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def owe(self, ctx, target, amount):
        assert float(amount) > 0, 'Amount must be positive'
        assert float(amount) < 420, 'Amount must be less than $420'
        await self.debt_utility(ctx, ctx.author, target, amount)
        await self.print_debt(ctx, target=ctx.author)

    @commands.command()
    async def pay(self, ctx, target=None, amount=None):
        assert float(amount) > 0, 'Amount must be positive'
        assert float(amount) < 420, 'Amount must be less than $420'
        await self.debt_utility(ctx, target, ctx.author, amount)
        await self.print_debt(ctx, target=ctx.author)

    @commands.command()
    async def debt(self, ctx, target=None, amount=None):
        # If no amount passed, print debts
        if amount is None:
            await self.print_debt(ctx, target)

        # If amount passed, target owes user
        else:
            assert float(amount) > 0, 'Amount must be positive'
            assert float(amount) < 420, 'Amount must be less than $420'
            await self.debt_utility(ctx, target, ctx.author, amount)
            await self.print_debt(ctx, target=ctx.author)

    @commands.command()
    async def groceries(self, ctx):
        try:
            data = pd.read_csv('debt_data.csv', header=None, dtype=str)

            debts = {}
            for _, row in data.iterrows():
                debtor = await get_member(ctx.guild, row[0])
                amount = float(row[2])
                if debtor not in debts:
                    debts[debtor] = amount
                else:
                    debts[debtor] += amount

            sorted_debts = sorted(debts.items(), key=lambda x: x[1])
            sorted_debts.reverse()

            message = ''
            for member in sorted_debts:
                message = message + member[0].mention + ': ${:,.2f}'.format(float(member[1])) + '\n'
            await ctx.send(message)

        except pd.errors.EmptyDataError:
            await ctx.send('No one owes anyone anything')

    async def debt_utility(self, ctx, target, user, amount):
        '''Target owes user amount'''
        try:
            data = pd.read_csv('debt_data.csv', header=None, dtype=str)
            data = data.values.tolist()
        except pd.errors.EmptyDataError:
            data = []

        # Get member objects
        if type(target) == str:
            target = await get_member(ctx.guild, ''.join(c for c in target if c.isdigit()))
        if type(user) == str:
            user = await get_member(ctx.guild, ''.join(c for c in user if c.isdigit()))
        assert target != user, 'Stop it, idiot'

        # Find out if debt already exists between debtor and debtee
        existing_debt_row = -1
        for i, row in enumerate(data):
            debtor = await get_member(ctx.guild, row[0])
            debtee = await get_member(ctx.guild, row[1])

            if (debtor == target and debtee == user) or (debtor == user and debtee == target):
                existing_debt_row = i
                break

        # If debt already exists
        if existing_debt_row >= 0:
            row = data[existing_debt_row]
            # If adding to existing debt
            if debtor == target and debtee == user:
                row[2] = float(row[2]) + float(amount)

            # If subtracting from existing debt
            if debtor == user and debtee == target:
                row[2] = float(row[2]) - float(amount)

                # If new debt is negative, flip debtor and debtee
                if row[2] < 0:
                    row[0], row[1] = row[1], row[0]
                    row[2] = abs(row[2])

        # If debt does not exist, create row
        else:
            data.append([target.id, user.id, amount])

        # Remove 0 debt rows
        i, stop = 0, len(data)
        while i < stop:
            if round(float(data[i][2]), 2) == 0:
                data.pop(i)
                i -= 1
                stop = len(data)
            i += 1

        data = pd.DataFrame(data)
        data.to_csv('debt_data.csv', header=False, index=False)

    async def print_debt(self, ctx, target=None):
        try:
            data = pd.read_csv('debt_data.csv', header=None, dtype=str)
            message = ''

            # If target passed, print debts for target
            if target is not None:
                if type(target) == str:
                    target_id = ''.join(c for c in target if c.isdigit())
                    target = await get_member(ctx.guild, target_id)
                for _, row in data.iterrows():
                    debtor = await get_member(ctx.guild, row[0])
                    debtee = await get_member(ctx.guild, row[1])
                    if target in {debtor, debtee}:
                        message = message + debtor.mention + ' owes ' + debtee.mention + ' ${:,.2f}'.format(float(row[2])) + '\n'
                if len(message.strip()) == 0:
                    message = f'{target.mention} has no debts and no one owes them'

            # If target not passed, print all debts
            else:
                for _, row in data.iterrows():
                    debtor = await get_member(ctx.guild, row[0])
                    debtee = await get_member(ctx.guild, row[1])
                    message = message + debtor.mention + ' owes ' + debtee.mention + ' ${:,.2f}'.format(float(row[2])) + '\n'

            await ctx.send(message)

        except pd.errors.EmptyDataError:
            await ctx.send('No one owes anyone anything')
