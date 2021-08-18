async def get_member(guild, member_id):
    member_id = int(member_id)

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


async def confirmation(client, ctx, confirm_string='confirm'):
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
