from discord.ext import commands
import discord

def has_allowed_roles(role_ids: set[int]):
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.guild is None:
            raise commands.NoPrivateMessage("This command can only be used in a server.")

        if not isinstance(ctx.author, discord.Member):
            raise commands.CheckFailure("Could not verify your member roles.")

        if ctx.author == ctx.guild.owner:
            return True

        user_role_ids = {role.id for role in ctx.author.roles}
        if user_role_ids & role_ids:
            return True

        raise commands.CheckFailure("You do not have the required role to use this command.")

    return commands.check(predicate)