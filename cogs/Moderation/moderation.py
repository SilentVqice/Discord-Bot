import asyncio
import json
import os
import discord
from discord.ext import commands
from typing import Optional

class Moderation(commands.Cog):
    WARNS_FILE = "warns.json"

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

    def load_warns(self):
        if not os.path.exists(self.WARNS_FILE):
            return {}

        with open(self.WARNS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}

    def save_warns(self, data):
        with open(self.WARNS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @commands.hybrid_command(name="purge", description="Deletes a number of messages from the channel.")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, amount: int):
        if amount < 1:
            return await ctx.send("Amount must be at least 1.")

        deleted = await ctx.channel.purge(limit=amount + (0 if ctx.interaction else 1))
        deleted_count = len(deleted) if ctx.interaction else max(len(deleted) - 1, 0)
        await ctx.send(f"Deleted {deleted_count} messages.", delete_after=5)

    @commands.hybrid_command(name="kick", description="Kicks a member from the server.")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
        if member == ctx.author:
            return await ctx.send("You cannot use this command on yourself.")

        if member == self.bot.user:
            return await ctx.send("You cannot use this command on me.")

        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("You cannot kick someone with an equal or higher role than you.")

        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send("I cannot kick that member because their role is higher than or equal to mine.")

        try:
            await member.kick(reason=reason)
            await ctx.send(f"{member.mention} has been kicked. Reason: {reason or 'No reason provided.'}")
        except discord.Forbidden:
            await ctx.send("I do not have permission to kick this user.")

    @commands.hybrid_command(name="ban", description="Bans a member from the server.")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
        if member == ctx.author:
            return await ctx.send("You cannot use this command on yourself.")

        if member == self.bot.user:
            return await ctx.send("You cannot use this command on me.")

        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("You cannot ban someone with an equal or higher role than you.")

        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send("I cannot ban that member because their role is higher than or equal to mine.")

        try:
            await member.ban(reason=reason)
            await ctx.send(f"{member.mention} has been banned. Reason: {reason or 'No reason provided.'}")
        except discord.Forbidden:
            await ctx.send("I do not have permission to ban this user.")

    @commands.hybrid_command(name="unban", description="Unbans a member by their Discord user ID.")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: int, *, reason: Optional[str] = None):
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=reason)
            await ctx.send(f"{user} has been unbanned. Reason: {reason or 'No reason provided.'}")
        except discord.NotFound:
            await ctx.send("This user is not banned.")
        except discord.Forbidden:
            await ctx.send("I do not have permission to unban this user.")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

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
            return await ctx.send("You cannot use this command on yourself.")

        if member == self.bot.user:
            return await ctx.send("You cannot use this command on me.")

        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("You cannot mute someone with an equal or higher role than you.")

        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send("I cannot mute that member because their role is higher than or equal to mine.")

        role = ctx.guild.get_role(self.muted_role_id)
        if role is None:
            return await ctx.send("Muted role was not found.")

        if role in member.roles:
            return await ctx.send(f"{member.mention} is already muted.")

        seconds = None
        if duration:
            seconds = self.parse_duration(duration)
            if seconds is None:
                return await ctx.send("Invalid duration. Use formats like 10s, 5m, 2h, 1d.")

        await member.add_roles(role, reason=reason)

        msg = f"{member.mention} has been muted."
        if reason:
            msg += f" Reason: {reason}"
        if duration:
            msg += f" Duration: {duration}"

        await ctx.send(msg)

        if seconds is not None:
            await asyncio.sleep(seconds)

            member = ctx.guild.get_member(member.id)
            if member and role in member.roles:
                await member.remove_roles(role, reason="Temporary mute expired")
                await ctx.send(f"{member.mention} has been automatically unmuted after {duration}.")

    @commands.hybrid_command(name="unmute", description="Unmutes a member.")
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
        if member == ctx.author:
            return await ctx.send("You cannot use this command on yourself.")

        if member == self.bot.user:
            return await ctx.send("You cannot use this command on me.")

        role = ctx.guild.get_role(self.muted_role_id)
        if role is None:
            return await ctx.send("Muted role was not found.")

        if role not in member.roles:
            return await ctx.send(f"{member.mention} is not muted.")

        try:
            await member.remove_roles(role, reason=reason)
            await ctx.send(f"{member.mention} has been unmuted.")
        except discord.Forbidden:
            await ctx.send("I do not have permission to unmute this user.")

    @commands.hybrid_command(name="warn", description="Warns a member.")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided."):
        if ctx.interaction:
            await ctx.defer(ephemeral=True)

        if member == ctx.author:
            return await ctx.send("You cannot warn yourself.", ephemeral=True)

        if member == self.bot.user:
            return await ctx.send("You cannot warn me.", ephemeral=True)

        if member == ctx.guild.owner:
            return await ctx.send("You cannot warn the server owner.", ephemeral=True)

        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("You cannot warn someone with an equal or higher role than you.", ephemeral=True)

        me = ctx.guild.me or ctx.guild.get_member(self.bot.user.id)
        if me is None:
            return await ctx.send("I could not verify my server permissions.", ephemeral=True)

        if member.top_role >= me.top_role:
            return await ctx.send("I cannot warn that member because their role is higher than or equal to mine.", ephemeral=True)

        warns = self.load_warns()

        guild_id = str(ctx.guild.id)
        user_id = str(member.id)

        if guild_id not in warns:
            warns[guild_id] = {}

        if user_id not in warns[guild_id]:
            warns[guild_id][user_id] = []

        warns[guild_id][user_id].append({
            "moderator": ctx.author.id,
            "reason": reason
        })

        self.save_warns(warns)

        warn_count = len(warns[guild_id][user_id])

        dm_embed = discord.Embed(
            title="You have been warned!",
            colour=discord.Color.orange()
        )
        dm_embed.add_field(name="Server", value=ctx.guild.name, inline=False)
        dm_embed.add_field(name="Warned by", value=f"{ctx.author} ({ctx.author.id})", inline=False)
        dm_embed.add_field(name="Reason", value=reason, inline=False)
        dm_embed.set_footer(text=f"Total warnings: {warn_count}")

        try:
            await member.send(embed=dm_embed)
            dm_status = "User notified in DMs."
        except discord.Forbidden:
            dm_status = "Could not DM the user."

        embed = discord.Embed(
            title="Member Warned",
            colour=discord.Color.orange()
        )
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Total Warnings", value=str(warn_count), inline=True)
        embed.set_footer(text=dm_status)

        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="warnings", description="Shows a member's warnings.")
    @commands.has_permissions(manage_messages=True)
    async def warnings(self, ctx: commands.Context, member: discord.Member):
        warns = self.load_warns()
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)

        user_warns = warns.get(guild_id, {}).get(user_id, [])

        if not user_warns:
            return await ctx.send(f"{member.mention} has no warnings.")

        embed = discord.Embed(
            title=f"Warnings for {member}",
            colour=discord.Color.orange()
        )

        for i, warn in enumerate(user_warns[:10], start=1):
            moderator = ctx.guild.get_member(warn["moderator"])
            moderator_name = moderator.mention if moderator else f"ID: {warn['moderator']}"
            embed.add_field(
                name=f"Warning #{i}",
                value=f"**Reason:** {warn['reason']}\n**Moderator:** {moderator_name}",
                inline=False
            )

        embed.set_footer(text=f"Total warnings: {len(user_warns)}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="delwarn", description="Removes a specific warning from a member.")
    @commands.has_permissions(manage_messages=True)
    async def delwarn(self, ctx: commands.Context, member: discord.Member, warn_number: int):
        if ctx.interaction:
            await ctx.defer(ephemeral=True)

        warns = self.load_warns()
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)

        user_warns = warns.get(guild_id, {}).get(user_id, [])

        if not user_warns:
            if ctx.interaction:
                return await ctx.interaction.followup.send(f"{member.mention} has no warnings.", ephemeral=True)
            return await ctx.send(f"{member.mention} has no warnings.", delete_after=3)

        if warn_number < 1 or warn_number > len(user_warns):
            if ctx.interaction:
                return await ctx.interaction.followup.send(
                    f"Invalid warning number. Choose between 1 and {len(user_warns)}.",
                    ephemeral=True
                )
            return await ctx.send(
                f"Invalid warning number. Choose between 1 and {len(user_warns)}.",
                delete_after=3
            )

        removed_warn = user_warns.pop(warn_number - 1)

        if user_warns:
            warns[guild_id][user_id] = user_warns
        else:
            del warns[guild_id][user_id]
            if not warns[guild_id]:
                del warns[guild_id]

        self.save_warns(warns)

        moderator = ctx.guild.get_member(removed_warn["moderator"])
        moderator_name = moderator.mention if moderator else f"ID: {removed_warn['moderator']}"

        embed = discord.Embed(
            title="Warning Removed",
            colour=discord.Color.green()
        )
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Removed Warning #", value=str(warn_number), inline=True)
        embed.add_field(name="Original Moderator", value=moderator_name, inline=False)
        embed.add_field(name="Reason", value=removed_warn["reason"], inline=False)

        remaining = len(warns.get(guild_id, {}).get(user_id, []))
        embed.set_footer(text=f"Remaining warnings: {remaining}")

        if ctx.interaction:
            await ctx.interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await ctx.send(embed=embed, delete_after=5)

    @delwarn.error
    async def delwarn_error(self, ctx: commands.Context, error):
        print(f"[REMOVEWARN ERROR] {repr(error)}")

        message = "An unexpected error occurred."

        if isinstance(error, commands.MissingPermissions):
            message = "You do not have permission to use this command."
        elif isinstance(error, commands.MissingRequiredArgument):
            message = "Usage: `;removewarn @member warning_number`"
        elif isinstance(error, commands.MemberNotFound):
            message = "That member could not be found."
        elif isinstance(error, commands.BadArgument):
            message = "Invalid argument provided."

        try:
            if ctx.interaction and not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(message, ephemeral=True)
            elif ctx.interaction:
                await ctx.interaction.followup.send(message, ephemeral=True)
            else:
                await ctx.send(message, delete_after=5)
        except Exception as e:
            print(f"[REMOVEWARN ERROR HANDLER FAILED] {repr(e)}")

    @commands.hybrid_command(name="clearwarns", description="Clears all warnings for a member.")
    @commands.has_permissions(manage_messages=True)
    async def clearwarns(self, ctx: commands.Context, member: discord.Member):
        warns = self.load_warns()
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)

        if guild_id in warns and user_id in warns[guild_id]:
            del warns[guild_id][user_id]
            self.save_warns(warns)
            await ctx.send(f"Cleared all warnings for {member.mention}.")
        else:
            await ctx.send(f"{member.mention} has no warnings.")

    @warn.error
    async def warn_error(self, ctx: commands.Context, error):
        print(f"[WARN ERROR] {repr(error)}")

        message = "An unexpected error occurred."

        if isinstance(error, commands.MissingPermissions):
            message = "You do not have permission to use this command."
        elif isinstance(error, commands.MissingRequiredArgument):
            message = "Usage: `;warn @member reason`"
        elif isinstance(error, commands.MemberNotFound):
            message = "That member could not be found."
        elif isinstance(error, commands.BadArgument):
            message = "Invalid argument provided."

        try:
            if ctx.interaction and not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(message, ephemeral=True)
            elif ctx.interaction:
                await ctx.interaction.followup.send(message, ephemeral=True)
            else:
                await ctx.send(message, delete_after=5)
        except Exception as e:
            print(f"[WARN ERROR HANDLER FAILED] {repr(e)}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))