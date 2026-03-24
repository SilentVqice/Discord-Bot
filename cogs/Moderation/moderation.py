import asyncio
import discord
from discord.ext import commands


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.muted_role_id = 1483291125778354176

    def parse_duration(self, duration: str):
        """Converts a string like '10s', '5m', '2h', '1d' into seconds."""
        try:
            unit = duration[-1].lower()
            amount = int(duration[:-1])

            if unit == "s":
                return amount
            elif unit == "m":
                return amount * 60
            elif unit == "h":
                return amount * 3600
            elif unit == "d":
                return amount * 86400

            return None
        except (ValueError, IndexError):
            return None

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, amount: int):
        """Deletes a number of messages from the channel."""
        if amount < 1:
            return

        deleted = await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f"Deleted {len(deleted) - 1} messages.", delete_after=5)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason=None):
        """Kicks a member from the server."""

        if member == ctx.author:
            await ctx.send("You cannot use this command on yourself.", delete_after=5)
            return

        if member == self.bot.user:
            await ctx.send("You cannot use this command on me.", delete_after=5)
            return

        try:
            await member.kick(reason=reason)
            await ctx.send(
                f"{member.mention} has been kicked. Reason: {reason}",
                delete_after=5
            )
        except discord.Forbidden:
            await ctx.send(
                "I do not have permission to kick this user!",
                delete_after=5
            )

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason=None):
        """Bans a member from the server."""

        if member == ctx.author:
            await ctx.send("You cannot use this command on yourself.", delete_after=5)
            return

        if member == self.bot.user:
            await ctx.send("You cannot use this command on me.", delete_after=5)
            return

        try:
            await member.ban(reason=reason)
            await ctx.send(
                f"{member.mention} has been banned. Reason: {reason}",
                delete_after=5
            )
        except discord.Forbidden:
            await ctx.send(
                "I do not have permission to ban this user!",
                delete_after=5
            )

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: int, *, reason=None):
        """
        Unbans a member by their Discord user ID.
        Usage: ;unban 123456789012345678
        """
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=reason)
            await ctx.send(
                f"{user} has been unbanned. Reason: {reason}",
                delete_after=5
            )
        except discord.NotFound:
            await ctx.send("This user is not banned.", delete_after=5)
        except discord.Forbidden:
            await ctx.send(
                "I do not have permission to unban this user!",
                delete_after=5
            )
        except Exception as e:
            await ctx.send(f"An error occurred: {e}", delete_after=5)

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx: commands.Context, member: discord.Member, duration: str = None, *, reason=None):
        """Mutes a member, optionally for a set time."""

        if member == ctx.author:
            await ctx.send("You cannot use this command on yourself.", delete_after=5)
            return

        if member == self.bot.user:
            await ctx.send("You cannot use this command on me.", delete_after=5)
            return

        role = ctx.guild.get_role(self.muted_role_id)
        if role is None:
            await ctx.send("Muted role was not found.", delete_after=5)
            return

        if role in member.roles:
            await ctx.send(f"{member.mention} is already muted.", delete_after=5)
            return

        seconds = None
        if duration:
            seconds = self.parse_duration(duration)
            if seconds is None:
                await ctx.send(
                    "Invalid duration. Use formats like 10s, 5m, 2h, 1d.",
                    delete_after=5
                )
                return

        await member.add_roles(role, reason=reason)

        msg = f"{member.mention} has been muted."
        if reason:
            msg += f" Reason: {reason}"
        if duration:
            msg += f" Duration: {duration}"

        await ctx.send(msg, delete_after=5)

        if seconds is not None:
            await asyncio.sleep(seconds)

            if role in member.roles:
                await member.remove_roles(role, reason="Temporary mute expired")
                await ctx.send(
                    f"{member.mention} has been automatically unmuted after {duration}.",
                    delete_after=5
                )

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member, *, reason=None):
        """Unmutes a member by removing the Muted role."""

        if member == ctx.author:
            await ctx.send("You cannot use this command on yourself.", delete_after=5)
            return

        if member == self.bot.user:
            await ctx.send("You cannot use this command on me.", delete_after=5)
            return

        role = ctx.guild.get_role(self.muted_role_id)
        if role is None:
            await ctx.send("Muted role was not found.", delete_after=5)
            return

        if role not in member.roles:
            await ctx.send(f"{member.mention} is not muted.", delete_after=5)
            return

        try:
            await member.remove_roles(role, reason=reason)
            await ctx.send(f"{member.mention} has been unmuted.", delete_after=5)
        except discord.Forbidden:
            await ctx.send(
                "I do not have permission to unmute this user!",
                delete_after=5
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))