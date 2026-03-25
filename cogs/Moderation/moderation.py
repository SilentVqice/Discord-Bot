import asyncio
from typing import Optional

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

    @commands.hybrid_command(name="purge", description="Deletes a number of messages from the channel.")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, amount: int):
        if amount < 1:
            return await ctx.send("Amount must be at least 1.", ephemeral=True)

        deleted = await ctx.channel.purge(limit=amount + (0 if ctx.interaction else 1))
        await ctx.send(f"Deleted {len(deleted) - 1} messages.", delete_after=5)

    @commands.hybrid_command(name="kick", description="Kicks a member from the server.")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
        if member == ctx.author:
            return await ctx.send("You cannot use this command on yourself.", ephemeral=True)

        if member == self.bot.user:
            return await ctx.send("You cannot use this command on me.", ephemeral=True)

        try:
            await member.kick(reason=reason)
            await ctx.send(f"{member.mention} has been kicked. Reason: {reason or 'No reason provided.'}")
        except discord.Forbidden:
            await ctx.send("I do not have permission to kick this user.", ephemeral=True)

    @commands.hybrid_command(name="ban", description="Bans a member from the server.")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
        if member == ctx.author:
            return await ctx.send("You cannot use this command on yourself.", ephemeral=True)

        if member == self.bot.user:
            return await ctx.send("You cannot use this command on me.", ephemeral=True)

        try:
            await member.ban(reason=reason)
            await ctx.send(f"{member.mention} has been banned. Reason: {reason or 'No reason provided.'}")
        except discord.Forbidden:
            await ctx.send("I do not have permission to ban this user.", ephemeral=True)

    @commands.hybrid_command(name="unban", description="Unbans a member by their Discord user ID.")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: int, *, reason: Optional[str] = None):
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=reason)
            await ctx.send(f"{user} has been unbanned. Reason: {reason or 'No reason provided.'}")
        except discord.NotFound:
            await ctx.send("This user is not banned.", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("I do not have permission to unban this user.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"An error occurred: {e}", ephemeral=True)

    @commands.hybrid_command(name="mute", description="Mutes a member, optionally for a set time.")
    @commands.has_permissions(manage_roles=True)
    async def mute(
        self,
        ctx: commands.Context,
        member: discord.Member,
        duration: Optional[str] = None,
        *,
        reason: Optional[str] = None
    ):
        if member == ctx.author:
            return await ctx.send("You cannot use this command on yourself.", ephemeral=True)

        if member == self.bot.user:
            return await ctx.send("You cannot use this command on me.", ephemeral=True)

        role = ctx.guild.get_role(self.muted_role_id)
        if role is None:
            return await ctx.send("Muted role was not found.", ephemeral=True)

        if role in member.roles:
            return await ctx.send(f"{member.mention} is already muted.", ephemeral=True)

        seconds = None
        if duration:
            seconds = self.parse_duration(duration)
            if seconds is None:
                return await ctx.send(
                    "Invalid duration. Use formats like 10s, 5m, 2h, 1d.",
                    ephemeral=True
                )

        await member.add_roles(role, reason=reason)

        msg = f"{member.mention} has been muted."
        if reason:
            msg += f" Reason: {reason}"
        if duration:
            msg += f" Duration: {duration}"

        await ctx.send(msg)

        if seconds is not None:
            await asyncio.sleep(seconds)

            if role in member.roles:
                await member.remove_roles(role, reason="Temporary mute expired")
                await ctx.send(f"{member.mention} has been automatically unmuted after {duration}.")

    @commands.hybrid_command(name="unmute", description="Unmutes a member.")
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
        if member == ctx.author:
            return await ctx.send("You cannot use this command on yourself.", ephemeral=True)

        if member == self.bot.user:
            return await ctx.send("You cannot use this command on me.", ephemeral=True)

        role = ctx.guild.get_role(self.muted_role_id)
        if role is None:
            return await ctx.send("Muted role was not found.", ephemeral=True)

        if role not in member.roles:
            return await ctx.send(f"{member.mention} is not muted.", ephemeral=True)

        try:
            await member.remove_roles(role, reason=reason)
            await ctx.send(f"{member.mention} has been unmuted.")
        except discord.Forbidden:
            await ctx.send("I do not have permission to unmute this user.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))