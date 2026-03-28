import asyncio
import json
import os
from typing import Optional

import discord
from discord.ext import commands

from utils.config import (
    PURGE_ALLOWED_ROLES,
    KICK_ALLOWED_ROLES,
    BAN_ALLOWED_ROLES,
    UNBAN_ALLOWED_ROLES,
    MUTE_ALLOWED_ROLES,
    UNMUTE_ALLOWED_ROLES,
    WARN_ALLOWED_ROLES,
    WARNINGS_ALLOWED_ROLES,
    DELWARN_ALLOWED_ROLES,
    CLEARWARNS_ALLOWED_ROLES,
)

class Moderation(commands.Cog):
    WARNS_FILE = "warns.json"

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.muted_role_id = 1483291125778354176

####################################################################################################################
# HELPERS
####################################################################################################################

    def parse_duration(self, duration: str) -> Optional[int]:
        """Convert strings like 10s, 5m, 2h, 1d into seconds."""
        try:
            unit = duration[-1].lower()
            amount = int(duration[:-1])

            if amount <= 0:
                return None

            if unit == "s":
                return amount
            if unit == "m":
                return amount * 60
            if unit == "h":
                return amount * 3600
            if unit == "d":
                return amount * 86400

            return None
        except (ValueError, IndexError):
            return None

    def load_warns(self) -> dict:
        if not os.path.exists(self.WARNS_FILE):
            return {}

        with open(self.WARNS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}

    def save_warns(self, data: dict) -> None:
        with open(self.WARNS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def user_has_allowed_role(self, member: discord.Member, allowed_role_ids: set[int]) -> bool:
        return any(role.id in allowed_role_ids for role in member.roles)

    async def send_command_response(
        self,
        ctx: commands.Context,
        message: Optional[str] = None,
        *,
        embed: Optional[discord.Embed] = None,
        ephemeral: bool = False,
        delete_after: Optional[float] = None,
    ):
        if ctx.interaction:
            if not ctx.interaction.response.is_done():
                return await ctx.interaction.response.send_message(
                    content=message,
                    embed=embed,
                    ephemeral=ephemeral,
                )
            return await ctx.interaction.followup.send(
                content=message,
                embed=embed,
                ephemeral=ephemeral,
            )

        return await ctx.send(message, embed=embed, delete_after=delete_after)

    async def check_role_access(
        self,
        ctx: commands.Context,
        allowed_roles: set[int],
    ) -> bool:
        if ctx.guild is None or not isinstance(ctx.author, discord.Member):
            return False

        if ctx.author == ctx.guild.owner:
            return True

        if self.user_has_allowed_role(ctx.author, allowed_roles):
            return True

        embed = self.make_error_embed(
            "You do not have the required role to use this command.",
            title="Access Denied",
            footer="Contact a staff member if you think this is a mistake.",
        )

        await self.send_command_response(
            ctx,
            embed=embed,
            ephemeral=True if ctx.interaction else False,
            delete_after=5 if not ctx.interaction else None,
        )
        return False

    async def can_moderate_target(
        self,
        ctx: commands.Context,
        member: discord.Member,
        action_name: str,
        *,
        check_bot_hierarchy: bool = True,
    ) -> bool:
        if ctx.guild is None or not isinstance(ctx.author, discord.Member):
            return False

        if member == ctx.author:
            await self.send_command_response(
                ctx,
                embed=self.make_error_embed(f"You cannot {action_name} yourself.", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )
            return False

        if member == self.bot.user:
            await self.send_command_response(
                ctx,
                embed=self.make_error_embed(f"You cannot {action_name} me.", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )
            return False

        if member == ctx.guild.owner:
            await self.send_command_response(
                ctx,
                embed=self.make_error_embed(f"You cannot {action_name} the server owner.", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )
            return False

        if ctx.author != ctx.guild.owner and member.top_role >= ctx.author.top_role:
            await self.send_command_response(
                ctx,
                embed=self.make_error_embed(
                    f"You cannot {action_name} someone with an equal or higher role than you.",
                    ctx=ctx
                ),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )
            return False

        if check_bot_hierarchy:
            me = ctx.guild.me or ctx.guild.get_member(self.bot.user.id)
            if me is None:
                await self.send_command_response(
                    ctx,
                    embed=self.make_error_embed("I could not verify my server permissions.", ctx=ctx),
                    ephemeral=True if ctx.interaction else False,
                    delete_after=5 if not ctx.interaction else None,
                )
                return False

            if member.top_role >= me.top_role:
                await self.send_command_response(
                    ctx,
                    embed=self.make_error_embed(
                        f"I cannot {action_name} that member because their role is higher than or equal to mine.",
                        ctx=ctx
                    ),
                    ephemeral=True if ctx.interaction else False,
                    delete_after=5 if not ctx.interaction else None,
                )
                return False

        return True

    async def temporary_unmute_task(
        self,
        guild_id: int,
        member_id: int,
        role_id: int,
        seconds: int,
        duration_text: str,
    ):
        await asyncio.sleep(seconds)

        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return

        member = guild.get_member(member_id)
        role = guild.get_role(role_id)

        if member is None or role is None:
            return

        if role not in member.roles:
            return

        try:
            await member.remove_roles(role, reason="Temporary mute expired")
        except discord.Forbidden:
            return

    def make_error_embed(
            self,
            description: str,
            *,
            title: str = "Action Denied",
            ctx: Optional[commands.Context] = None,
            footer: Optional[str] = None,
    ) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description,
            colour=discord.Color.red(),
        )

        if footer is not None:
            embed.set_footer(text=footer)
        elif ctx is not None and getattr(ctx, "author", None):
            embed.set_footer(
                text=f"Requested by {ctx.author}",
                icon_url=ctx.author.display_avatar.url,
            )
        else:
            embed.set_footer(text="Please check your permissions and role hierarchy.")

        return embed

    def make_usage_embed(
            self,
            usage: str,
            *,
            ctx: Optional[commands.Context] = None,
    ) -> discord.Embed:
        embed = discord.Embed(
            title="Missing Arguments",
            description=f"Usage: `{usage}`",
            colour=discord.Color.red(),
        )

        if ctx is not None and getattr(ctx, "author", None):
            embed.set_footer(
                text=f"Requested by {ctx.author}",
                icon_url=ctx.author.display_avatar.url,
            )
        else:
            embed.set_footer(text="Please provide the required arguments.")

        return embed

    def make_success_embed(
        self,
        description: str,
        *,
        title: str = "Success",
        ctx: Optional[commands.Context] = None,
        footer: Optional[str] = None,
    ) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description,
            colour=discord.Color.green(),
        )

        if footer is not None:
            embed.set_footer(text=footer)
        elif ctx is not None and getattr(ctx, "author", None):
            embed.set_footer(
                text=f"Requested by {ctx.author}",
                icon_url=ctx.author.display_avatar.url,
            )
        else:
            embed.set_footer(text="Action completed successfully.")

        return embed

####################################################################################################################
# PURGE
####################################################################################################################

    @commands.hybrid_command(name="purge", description="Deletes a number of messages from the channel.")
    async def purge(self, ctx: commands.Context, amount: Optional[int] = None):
        if amount is None:
            return await self.send_command_response(
                ctx,
                embed=self.make_usage_embed(";purge <amount>", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

        if not await self.check_role_access(ctx, PURGE_ALLOWED_ROLES):
            return

        if amount < 1:
            return await self.send_command_response(
                ctx,
                embed=self.make_error_embed("Amount must be at least 1.", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

        deleted = await ctx.channel.purge(limit=amount + (0 if ctx.interaction else 1))
        deleted_count = len(deleted) if ctx.interaction else max(len(deleted) - 1, 0)

        await self.send_command_response(
            ctx,
            embed=self.make_success_embed(
                f"Deleted **{deleted_count}** messages.",
                title="Messages Purged",
                ctx=ctx,
            ),
            ephemeral=True if ctx.interaction else False,
            delete_after=5 if not ctx.interaction else None,
        )

####################################################################################################################
# KICK
####################################################################################################################

    @commands.hybrid_command(name="kick", description="Kicks a member from the server.")
    async def kick(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None,
        *,
        reason: Optional[str] = None,
    ):
        if member is None:
            return await self.send_command_response(
                ctx,
                embed=self.make_usage_embed(";kick @member [reason]", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

        if not await self.check_role_access(ctx, KICK_ALLOWED_ROLES):
            return

        if not await self.can_moderate_target(ctx, member, "kick"):
            return

        try:
            await member.kick(reason=reason or "No reason provided.")
            await self.send_command_response(
                ctx,
                embed=self.make_success_embed(
                    f"{member.mention} has been kicked.\n**Reason:** {reason or 'No reason provided.'}",
                    title="Member Kicked",
                    ctx=ctx,
                ),
            )
        except discord.Forbidden:
            await self.send_command_response(
                ctx,
                embed=self.make_error_embed("I do not have permission to kick that member.", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

####################################################################################################################
# BAN
####################################################################################################################

    @commands.hybrid_command(name="ban", description="Bans a member from the server.")
    async def ban(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None,
        *,
        reason: Optional[str] = None,
    ):
        if member is None:
            return await self.send_command_response(
                ctx,
                embed=self.make_usage_embed(";ban @member [reason]", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

        if not await self.check_role_access(ctx, BAN_ALLOWED_ROLES):
            return

        if not await self.can_moderate_target(ctx, member, "ban"):
            return

        try:
            await member.ban(reason=reason or "No reason provided.")
            await self.send_command_response(
                ctx,
                embed=self.make_success_embed(
                    f"{member.mention} has been banned.\n**Reason:** {reason or 'No reason provided.'}",
                    title="Member Banned",
                    ctx=ctx,
                ),
            )
        except discord.Forbidden:
            await self.send_command_response(
                ctx,
                embed=self.make_error_embed("I do not have permission to ban that member.", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

####################################################################################################################
# UNBAN
####################################################################################################################

    @commands.hybrid_command(name="unban", description="Unbans a member by their Discord user ID.")
    async def unban(
        self,
        ctx: commands.Context,
        user_id: Optional[int] = None,
        *,
        reason: Optional[str] = None,
    ):
        if user_id is None:
            return await self.send_command_response(
                ctx,
                embed=self.make_usage_embed(";unban <user_id> [reason]", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

        if not await self.check_role_access(ctx, UNBAN_ALLOWED_ROLES):
            return

        if ctx.guild is None:
            return

        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=reason or "No reason provided.")
            await self.send_command_response(
                ctx,
                embed=self.make_success_embed(
                    f"**{user}** has been unbanned.\n**Reason:** {reason or 'No reason provided.'}",
                    title="Member Unbanned",
                    ctx=ctx,
                ),
            )
        except discord.NotFound:
            await self.send_command_response(
                ctx,
                embed=self.make_error_embed("This user is not banned.", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )
        except discord.Forbidden:
            await self.send_command_response(
                ctx,
                embed=self.make_error_embed("I do not have permission to unban this user.", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )
        except Exception as e:
            await self.send_command_response(
                ctx,
                embed=self.make_error_embed(f"An error occurred: {e}", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

####################################################################################################################
# MUTE
####################################################################################################################

    @commands.hybrid_command(name="mute", description="Mutes a member, optionally for a set time.")
    async def mute(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None,
        duration: Optional[str] = None,
        *,
        reason: Optional[str] = None,
    ):
        if member is None:
            return await self.send_command_response(
                ctx,
                embed=self.make_usage_embed(";mute @member [duration] [reason]", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

        if not await self.check_role_access(ctx, MUTE_ALLOWED_ROLES):
            return

        if not await self.can_moderate_target(ctx, member, "mute"):
            return

        if ctx.guild is None:
            return

        role = ctx.guild.get_role(self.muted_role_id)
        if role is None:
            return await self.send_command_response(
                ctx,
                embed=self.make_error_embed("Muted role was not found.", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

        if role in member.roles:
            return await self.send_command_response(
                ctx,
                embed=self.make_error_embed(f"{member.mention} is already muted.", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

        seconds = None
        if duration:
            seconds = self.parse_duration(duration)
            if seconds is None:
                return await self.send_command_response(
                    ctx,
                    embed=self.make_error_embed("Invalid duration. Use formats like 10s, 5m, 2h, 1d.", ctx=ctx),
                    ephemeral=True if ctx.interaction else False,
                    delete_after=5 if not ctx.interaction else None,
                )

        try:
            await member.add_roles(role, reason=reason or "No reason provided.")
        except discord.Forbidden:
            return await self.send_command_response(
                ctx,
                embed=self.make_error_embed("I do not have permission to mute this user.", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

        description = f"{member.mention} has been muted.\n**Reason:** {reason or 'No reason provided.'}"
        if duration:
            description += f"\n**Duration:** {duration}"

        await self.send_command_response(
            ctx,
            embed=self.make_success_embed(
                description,
                title="Member Muted",
                ctx=ctx,
            ),
        )

        if seconds is not None:
            self.bot.loop.create_task(
                self.temporary_unmute_task(
                    ctx.guild.id,
                    member.id,
                    role.id,
                    seconds,
                    duration,
                )
            )

####################################################################################################################
# UNMUTE
####################################################################################################################

    @commands.hybrid_command(name="unmute", description="Unmutes a member.")
    async def unmute(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None,
        *,
        reason: Optional[str] = None,
    ):
        if member is None:
            return await self.send_command_response(
                ctx,
                embed=self.make_usage_embed(";unmute @member [reason]", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

        if not await self.check_role_access(ctx, UNMUTE_ALLOWED_ROLES):
            return

        if ctx.guild is None:
            return

        if member == ctx.author:
            return await self.send_command_response(
                ctx,
                embed=self.make_error_embed("You cannot unmute yourself.", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

        if member == self.bot.user:
            return await self.send_command_response(
                ctx,
                embed=self.make_error_embed("You cannot unmute me.", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

        role = ctx.guild.get_role(self.muted_role_id)
        if role is None:
            return await self.send_command_response(
                ctx,
                embed=self.make_error_embed("Muted role was not found.", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

        if role not in member.roles:
            return await self.send_command_response(
                ctx,
                embed=self.make_error_embed(f"{member.mention} is not muted.", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

        try:
            await member.remove_roles(role, reason=reason or "No reason provided.")
            await self.send_command_response(
                ctx,
                embed=self.make_success_embed(
                    f"{member.mention} has been unmuted.",
                    title="Member Unmuted",
                    ctx=ctx,
                ),
            )
        except discord.Forbidden:
            await self.send_command_response(
                ctx,
                embed=self.make_error_embed("I do not have permission to unmute this user.", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

####################################################################################################################
# WARN
####################################################################################################################

    @commands.hybrid_command(name="warn", description="Warns a member.")
    async def warn(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None,
        *,
        reason: Optional[str] = None,
    ):
        if member is None:
            return await self.send_command_response(
                ctx,
                embed=self.make_usage_embed(";warn @member [reason]", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

        if not await self.check_role_access(ctx, WARN_ALLOWED_ROLES):
            return

        if not await self.can_moderate_target(ctx, member, "warn"):
            return

        if ctx.guild is None or not isinstance(ctx.author, discord.Member):
            return

        warns = self.load_warns()

        guild_id = str(ctx.guild.id)
        user_id = str(member.id)

        if guild_id not in warns:
            warns[guild_id] = {}

        if user_id not in warns[guild_id]:
            warns[guild_id][user_id] = []

        final_reason = reason or "No reason provided."

        warns[guild_id][user_id].append({
            "moderator": ctx.author.id,
            "reason": final_reason
        })

        self.save_warns(warns)

        warn_count = len(warns[guild_id][user_id])

        dm_embed = discord.Embed(
            title="You have been warned!",
            colour=discord.Color.orange()
        )
        dm_embed.add_field(name="Server", value=ctx.guild.name, inline=False)
        dm_embed.add_field(name="Warned by", value=f"{ctx.author} ({ctx.author.id})", inline=False)
        dm_embed.add_field(name="Reason", value=final_reason, inline=False)
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
        embed.add_field(name="Reason", value=final_reason, inline=False)
        embed.add_field(name="Total Warnings", value=str(warn_count), inline=True)
        embed.set_footer(text=dm_status)

        await self.send_command_response(
            ctx,
            embed=embed,
            ephemeral=True if ctx.interaction else False,
        )

####################################################################################################################
# WARNINGS
####################################################################################################################

    @commands.hybrid_command(name="warnings", description="Shows a member's warnings.")
    async def warnings(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        if member is None:
            return await self.send_command_response(
                ctx,
                embed=self.make_usage_embed(";warnings @member", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

        if not await self.check_role_access(ctx, WARNINGS_ALLOWED_ROLES):
            return

        if ctx.guild is None:
            return

        warns = self.load_warns()
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)

        user_warns = warns.get(guild_id, {}).get(user_id, [])

        if not user_warns:
            return await self.send_command_response(
                ctx,
                embed=self.make_error_embed(f"{member.mention} has no warnings.", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

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

        await self.send_command_response(
            ctx,
            embed=embed,
            ephemeral=True if ctx.interaction else False,
        )

####################################################################################################################
# DELWARN
####################################################################################################################

    @commands.hybrid_command(name="delwarn", description="Removes a specific warning from a member.")
    async def delwarn(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None,
        warn_number: Optional[int] = None,
    ):
        if member is None or warn_number is None:
            return await self.send_command_response(
                ctx,
                embed=self.make_usage_embed(";delwarn @member <warning_number>", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

        if not await self.check_role_access(ctx, DELWARN_ALLOWED_ROLES):
            return

        if ctx.guild is None:
            return

        warns = self.load_warns()
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)

        user_warns = warns.get(guild_id, {}).get(user_id, [])

        if not user_warns:
            return await self.send_command_response(
                ctx,
                embed=self.make_error_embed(f"{member.mention} has no warnings.", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

        if warn_number < 1 or warn_number > len(user_warns):
            return await self.send_command_response(
                ctx,
                embed=self.make_error_embed(f"Invalid warning number. Choose between 1 and {len(user_warns)}.", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
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

        await self.send_command_response(
            ctx,
            embed=embed,
            ephemeral=True if ctx.interaction else False,
            delete_after=5 if not ctx.interaction else None,
        )

####################################################################################################################
# CLEARWARNS
####################################################################################################################

    @commands.hybrid_command(name="clearwarns", description="Clears all warnings for a member.")
    async def clearwarns(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        if member is None:
            return await self.send_command_response(
                ctx,
                embed=self.make_usage_embed(";clearwarns @member", ctx=ctx),
                ephemeral=True if ctx.interaction else False,
                delete_after=5 if not ctx.interaction else None,
            )

        if not await self.check_role_access(ctx, CLEARWARNS_ALLOWED_ROLES):
            return

        if ctx.guild is None:
            return

        warns = self.load_warns()
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)

        if guild_id in warns and user_id in warns[guild_id]:
            del warns[guild_id][user_id]
            if not warns[guild_id]:
                del warns[guild_id]

            self.save_warns(warns)

            return await self.send_command_response(
                ctx,
                embed=self.make_success_embed(
                    f"All warnings for {member.mention} have been cleared.",
                    title="Warnings Cleared",
                    ctx=ctx,
                ),
                ephemeral=True if ctx.interaction else False,
            )

        await self.send_command_response(
            ctx,
            embed=self.make_error_embed(f"{member.mention} has no warnings.", ctx=ctx),
            ephemeral=True if ctx.interaction else False,
            delete_after=5 if not ctx.interaction else None,
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))