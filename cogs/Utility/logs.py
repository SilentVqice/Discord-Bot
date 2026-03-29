from __future__ import annotations
import discord
from discord.ext import commands
from utils.logger import LogHelper
from utils.emojis import EMOJIS

class Logs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = LogHelper(bot)

####################################################################################################################
# HELPERS
####################################################################################################################

    @staticmethod
    def clean_log_text(text: str, limit: int = 1000) -> str:
        if not text:
            return "No text content."

        text = text.replace("```", "`\u200b``")
        return text[:limit]

    def format_dt(self, dt) -> str:
        return dt.strftime("%d %b %Y %H:%M")

    def format_role_colour(self, role: discord.Role) -> str:
        if role.colour == discord.Colour.default():
            return "Default"
        return str(role.colour)

    def format_permissions(self, perms: discord.Permissions) -> str:
        enabled = [name.replace("_", " ").title() for name, value in perms if value]

        if not enabled:
            return "None"

        return "\n".join(f"• {perm}" for perm in enabled)

    def get_permission_changes(
        self,
        before_perms: discord.Permissions,
        after_perms: discord.Permissions
    ) -> tuple[list[str], list[str]]:
        added = []
        removed = []

        for perm_name, after_value in after_perms:
            before_value = getattr(before_perms, perm_name, False)

            if not before_value and after_value:
                added.append(perm_name.replace("_", " ").title())
            elif before_value and not after_value:
                removed.append(perm_name.replace("_", " ").title())

        return added, removed

####################################################################################################################
# MEMBER LOGS
####################################################################################################################

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.logger.send_log(
            category="member",
            title="Member Joined",
            description=(
                f"**User:** {member.mention} (`{member.id}`)\n"
                f"**Account created:** {member.created_at.strftime('%d %b %Y %H:%M UTC')}"
            ),
            colour=discord.Color.green(),
            thumbnail=member.display_avatar.url,
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self.logger.send_log(
            category="member",
            title="Member Left",
            description=(
                f"**User:** {member} (`{member.id}`)\n"
                f"**Mention:** {member.mention}"
            ),
            colour=discord.Color.red(),
            thumbnail=member.display_avatar.url,
        )

####################################################################################################################
# MESSAGE LOGS
####################################################################################################################

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        content = self.clean_log_text(message.content, 1500)

        await self.logger.send_log(
            category="message",
            title="Message Deleted",
            description=(
                f"**Author:** {message.author.mention} (`{message.author.id}`)\n"
                f"**Channel:** {message.channel.mention}\n\n"
                f"**Content:**\n```txt\n{content}\n```"
            ),
            colour=discord.Color.red(),
            thumbnail=message.author.display_avatar.url,
        )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not before.guild or before.author.bot:
            return

        if before.content == after.content:
            return

        old_content = self.clean_log_text(before.content, 1000)
        new_content = self.clean_log_text(after.content, 1000)

        await self.logger.send_log(
            category="message",
            title="Message Edited",
            description=(
                f"**Author:** {before.author.mention} (`{before.author.id}`)\n"
                f"**Channel:** {before.channel.mention} | [Jump]({after.jump_url})\n\n"
                f"**Before:**\n```txt\n{old_content}\n```\n"
                f"**After:**\n```txt\n{new_content}\n```\n"
            ),
            colour=discord.Color.orange(),
            thumbnail=before.author.display_avatar.url,
        )

####################################################################################################################
# VOICE LOGS
####################################################################################################################

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.bot:
            return

        if before.channel == after.channel:
            return

        if before.channel is None and after.channel is not None:
            await self.logger.send_log(
                category="voice",
                title="Voice Join",
                description=(
                    f"**User:** {member.mention} (`{member.id}`)\n"
                    f"**Channel:** {after.channel.mention}"
                ),
                colour=discord.Color.green(),
                thumbnail=member.display_avatar.url,
            )

        elif before.channel is not None and after.channel is None:
            await self.logger.send_log(
                category="voice",
                title="Voice Leave",
                description=(
                    f"**User:** {member.mention} (`{member.id}`)\n"
                    f"**Channel:** {before.channel.mention}"
                ),
                colour=discord.Color.red(),
                thumbnail=member.display_avatar.url,
            )

        elif before.channel != after.channel:
            await self.logger.send_log(
                category="voice",
                title="Voice Move",
                description=(
                    f"**User:** {member.mention} (`{member.id}`)\n"
                    f"**From:** {before.channel.mention}\n"
                    f"**To:** {after.channel.mention}"
                ),
                colour=discord.Color.blurple(),
                thumbnail=member.display_avatar.url,
            )

####################################################################################################################
# SERVER LOGS
####################################################################################################################

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        await self.logger.send_log(
            category="server",
            title="Channel Created",
            description=(
                f"**Name:** {channel.name}\n"
                f"**ID:** `{channel.id}`\n"
                f"**Type:** `{channel.type}`"
            ),
            colour=discord.Color.green(),
        )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        await self.logger.send_log(
            category="server",
            title="Channel Deleted",
            description=(
                f"**Name:** {channel.name}\n"
                f"**ID:** `{channel.id}`\n"
                f"**Type:** `{channel.type}`"
            ),
            colour=discord.Color.red(),
        )

    async def get_role_audit_user(
        self,
        guild: discord.Guild,
        action: discord.AuditLogAction,
        role_id: int,
    ):
        async for entry in guild.audit_logs(limit=10, action=action):
            if entry.target and entry.target.id == role_id:
                return entry.user
        return None

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        user = await self.get_role_audit_user(
            role.guild,
            discord.AuditLogAction.role_create,
            role.id
        )

        embed_description = (
            f"**Role:** {role.mention}\n"
            f"**Name:** {role.name}\n"
            f"**Role ID:** `{role.id}`\n"
            f"**Colour:** `{self.format_role_colour(role)}`\n"
            f"**Created at:** {self.format_dt(role.created_at)}\n"
            f"**Created by:** {user.mention if user else '`Unknown`'}\n\n"
            f"**Permissions:**\n{self.format_permissions(role.permissions)}"
        )

        await self.logger.send_log(
            category="server",
            title="Role Created",
            description=embed_description,
            colour=role.colour if role.colour != discord.Colour.default() else discord.Color.green(),
        )

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        user = await self.get_role_audit_user(
            role.guild,
            discord.AuditLogAction.role_delete,
            role.id
        )

        embed_description = (
            f"**Name:** {role.name}\n"
            f"**Role ID:** `{role.id}`\n"
            f"**Colour:** `{self.format_role_colour(role)}`\n"
            f"**Created at:** {self.format_dt(role.created_at)}\n"
            f"**Deleted by:** {user.mention if user else '`Unknown`'}\n\n"
            f"**Permissions:**\n{self.format_permissions(role.permissions)}"
        )

        await self.logger.send_log(
            category="server",
            title="Role Deleted",
            description=embed_description,
            colour=role.colour if role.colour != discord.Colour.default() else discord.Color.red(),
        )

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        changes = []

        if before.name != after.name:
            changes.append(f"**Name:** `{before.name}` → `{after.name}`")

        if before.colour != after.colour:
            changes.append(
                f"**Colour:** `{self.format_role_colour(before)}` → `{self.format_role_colour(after)}`"
            )

        if before.mentionable != after.mentionable:
            changes.append(
                f"**Mentionable:** `{'Yes' if before.mentionable else 'No'}` → `{'Yes' if after.mentionable else 'No'}`"
            )

        if before.hoist != after.hoist:
            changes.append(
                f"**Displayed Separately:** `{'Yes' if before.hoist else 'No'}` → `{'Yes' if after.hoist else 'No'}`"
            )

        added_perms, removed_perms = self.get_permission_changes(before.permissions, after.permissions)

        if added_perms:
            changes.append(
                f"{EMOJIS['success']} **Permissions Added:**\n" + "\n".join(f"• {perm}" for perm in added_perms)
            )

        if removed_perms:
            changes.append(
                f"\n{EMOJIS['error']} **Permissions Removed:**\n" + "\n".join(f"• {perm}" for perm in removed_perms)
            )

        if not changes:
            return

        user = await self.get_role_audit_user(
            after.guild,
            discord.AuditLogAction.role_update,
            after.id
        )

        embed_description = (
            f"**Role:** {after.mention}\n"
            f"**Role ID:** `{after.id}`\n"
            f"**Updated by:** {user.mention if user else '`Unknown`'}\n\n"
            + "\n".join(changes)
        )

        await self.logger.send_log(
            category="server",
            title="Role Updated",
            description=embed_description,
            colour=after.colour if after.colour != discord.Colour.default() else discord.Color.orange(),
        )

####################################################################################################################
# ERROR LOGS
####################################################################################################################

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        if hasattr(ctx.command, "on_error"):
            return

        ignored = (
            commands.CommandNotFound,
        )
        if isinstance(error, ignored):
            return

        command_text = getattr(ctx.message, "content", "Unknown command")
        command_text = self.clean_log_text(command_text, 1000)

        await self.logger.send_log(
            category="error",
            title="Command Error",
            description=(
                f"**User:** {ctx.author.mention} (`{ctx.author.id}`)\n"
                f"**Channel:** {ctx.channel.mention}\n"
                f"**Command:**\n```txt\n{command_text}\n```\n"
                f"**Error:** `{type(error).__name__}: {error}`"
            ),
            colour=discord.Color.red(),
            thumbnail=ctx.author.display_avatar.url,
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Logs(bot))