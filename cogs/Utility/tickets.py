import asyncio
import io
import discord
from discord.ext import commands
from datetime import datetime

ticket_category_id = 1486944969074802758
staff_role_id = 1483933455334248538
transcript_log_channel_id = 1486948183887052963


def make_embed(
    title: str,
    description: str | None = None,
    colour: discord.Colour = discord.Color.blurple(),
) -> discord.Embed:
    return discord.Embed(title=title, description=description, colour=colour)

def escape_text(text: str) -> str:
    return text.replace("\r", "").strip()

async def build_transcript(channel: discord.TextChannel) -> discord.File:
    lines = []

    async for message in channel.history(limit=None, oldest_first=True):
        created = message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        author = f"{message.author} ({message.author.id})"

        content = escape_text(message.content) if message.content else ""

        if not content:
            content = "[no text content]"

        lines.append(f"[{created}] {author}: {content}")

        if message.attachments:
            for attachment in message.attachments:
                lines.append(f"     Attachment: {attachment.url}")

        if message.embeds:
            lines.append(f"     Embeds: {len(message.embeds)}")

        if message.stickers:
            lines.append(f"     Stickers: {len(message.stickers)}")

    transcript_text = "\n".join(lines) if lines else "No messages in this ticket."

    buffer = io.BytesIO(transcript_text.encode("utf-8"))
    filename = f"{channel.name}-transcript.txt"
    return discord.File(buffer, filename=filename)

async def send_transcript_and_close(
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        closing_staff: discord.Member,
        close_reason: str | None = None,
):
    guild = interaction.guild
    if guild is None:
        await channel.delete(reason=f"Ticket closed by {closing_staff}")
        return

    log_channel = guild.get_channel(transcript_log_channel_id)
    transcript_file = await build_transcript(channel)

    owner_id = None
    claimed_by_id = None

    if channel.topic:
        for part in channel.topic.split(";"):
            if part.startswith("ticket-owner:"):
                try:
                    owner_id = int(part.split(":", 1)[1])
                except ValueError:
                    owner_id = None
            elif part.startswith("claimed-by:"):
                try:
                    claimed_by_id = int(part.split(":", 1)[1])
                except ValueError:
                    claimed_by_id = None

    owner_mention = f"<@{owner_id}>" if owner_id else "Unknown"
    claimed_by_mention = f"<@{claimed_by_id}>" if claimed_by_id else "Not claimed"

    opened_ts = int(channel.created_at.timestamp())
    closed_ts = int(discord.utils.utcnow().timestamp())

    embed = discord.Embed(
        title="Ticket Closed",
        colour=discord.Color.red(),
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(name="🆔 Ticket ID", value=str(channel.id), inline=True)
    embed.add_field(name="🟢 Opened By", value=owner_mention, inline=True)
    embed.add_field(name="🔴 Closed By", value=closing_staff.mention, inline=True)

    embed.add_field(
        name="⏰ Opened",
        value=f"<t:{opened_ts}:F>",
        inline=True
    )
    embed.add_field(
        name="🙋 Claimed By",
        value=claimed_by_mention,
        inline=True
    )
    embed.add_field(
        name="",
        value="",
        inline=True
    )

    embed.add_field(
        name="📍 Reason",
        value=close_reason or "No reason specified",
        inline=False
    )

    if isinstance(log_channel, discord.TextChannel):
        await log_channel.send(embed=embed, file=transcript_file)

    await channel.delete(
        reason=f"Ticket closed by {closing_staff} | Reason: {close_reason or 'No reason provided.'}"
    )

class TicketReasonModal(discord.ui.Modal, title="Open a Ticket"):
    reason = discord.ui.TextInput(
        label="What do you need help with?",
        style=discord.TextStyle.paragraph,
        placeholder="Describe your issue here...",
        required=True,
        max_length=500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        if guild is None:
            return await interaction.response.send_message(
                "This can only be used in a server.",
                ephemeral=True
            )

        category = guild.get_channel(ticket_category_id)
        staff_role = guild.get_role(staff_role_id)
        bot_member = guild.me

        if category is None:
            return await interaction.response.send_message(
                "Ticket category was not found. Make sure you copied the category ID, not a channel ID.",
                ephemeral=True
            )

        if not isinstance(category, discord.CategoryChannel):
            return await interaction.response.send_message(
                "The ID you provided is not a category. Copy the ID of the Tickets category itself.",
                ephemeral=True
            )

        if staff_role is None:
            return await interaction.response.send_message(
                "Staff role not found. Check your staff role ID.",
                ephemeral=True
            )

        if bot_member is None:
            return await interaction.response.send_message(
                "Bot member could not be found in this guild.",
                ephemeral=True
            )

        existing = discord.utils.find(
            lambda c: (
                isinstance(c, discord.TextChannel)
                and c.category_id == category.id
                and c.topic is not None
                and f"ticket-owner:{user.id}" in c.topic
            ),
            guild.channels,
        )

        if existing:
            return await interaction.response.send_message(
                f"You already have an open ticket: {existing.mention}",
                ephemeral=True
            )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            ),
            staff_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
            ),
            bot_member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                read_message_history=True,
            ),
        }

        safe_name = "".join(
            ch for ch in user.name.lower().replace(" ", "-")
            if ch.isalnum() or ch == "-"
        ).strip("-")

        if not safe_name:
            safe_name = f"user-{user.id}"

        channel_name = f"ticket-{safe_name}-{user.id}"

        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"ticket-owner:{user.id}",
            reason=f"Ticket opened by {user}",
        )

        embed = make_embed(
            title="📩 Support Ticket",
            description=(
                f"{user.mention}, thank you for contacting support.\nSomeone will be with you shortly.\n\n"
                f"**Reason:**\n{self.reason.value}"
            ),
            colour=discord.Color.green(),
        )
        embed.set_footer(text=f"User ID: {user.id}")

        await channel.send(
            content=f"||{user.mention}|| ||{staff_role.mention}||",
            embed=embed,
            view=TicketManageView()
        )

        await interaction.response.send_message(
            f"Your ticket has been created: {channel.mention}",
            ephemeral=True
        )

class CloseReasonModal(discord.ui.Modal, title="Close Ticket With Reason"):
    reason = discord.ui.TextInput(
        label="Reason for closing",
        style=discord.TextStyle.paragraph,
        placeholder="Write the reason for closing this ticket...",
        required=True,
        max_length=500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.channel
        guild = interaction.guild

        if guild is None or channel is None or not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message(
                "This can only be used inside a server ticket.",
                ephemeral=True
            )

        staff_role = guild.get_role(staff_role_id)
        if staff_role is None:
            return await interaction.response.send_message(
                "Staff role not found.",
                ephemeral=True
            )

        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "Could not verify your server permissions.",
                ephemeral=True
            )

        if staff_role not in interaction.user.roles:
            return await interaction.response.send_message(
                "Only staff can close tickets.",
                ephemeral=True
            )

        embed = make_embed(
            title="Ticket Closing",
            description=(
                f"This ticket will be closed by {interaction.user.mention} in 5 seconds.\n\n"
                f"**Reason:**\n{self.reason.value}"
            ),
            colour=discord.Color.red(),
        )

        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(5)
        await send_transcript_and_close(
            interaction=interaction,
            channel=channel,
            closing_staff=interaction.user,
            close_reason=self.reason.value,
        )

class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Open Ticket",
        style=discord.ButtonStyle.green,
        emoji="📩",
        custom_id="ticket_open_button"
    )
    async def open_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(TicketReasonModal())


class TicketManageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @staticmethod
    def get_claimed_by(topic: str | None) -> int | None:
        if not topic:
            return None

        parts = topic.split(";")
        for part in parts:
            if part.startswith("claimed-by:"):
                try:
                    return int(part.split(":", 1)[1])
                except ValueError:
                    return None
        return None

    @staticmethod
    def set_claimed_by(topic: str | None, staff_id: int) -> str:
        base_parts = []

        if topic:
            for part in topic.split(";"):
                if not part.startswith("claimed-by:"):
                    base_parts.append(part)

        base_parts.append(f"claimed-by:{staff_id}")
        return ";".join(base_parts)

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.red,
        emoji="🔒",
        custom_id="ticket_close_button"
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        channel = interaction.channel
        guild = interaction.guild

        if guild is None or channel is None or not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message(
                "This can only be used inside a server ticket.",
                ephemeral=True
            )

        staff_role = guild.get_role(staff_role_id)

        if staff_role is None:
            return await interaction.response.send_message(
                "Staff role not found.",
                ephemeral=True
            )

        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "Could not verify your server permissions.",
                ephemeral=True
            )

        if staff_role not in interaction.user.roles:
            return await interaction.response.send_message(
                "Only staff can close tickets.",
                ephemeral=True
            )

        await interaction.response.send_message("Closing ticket in 5 seconds and saving transcript...")
        await asyncio.sleep(5)
        await send_transcript_and_close(
            interaction=interaction,
            channel=channel,
            closing_staff=interaction.user,
            close_reason=None
        )

    @discord.ui.button(
        label="Close with Reason",
        style=discord.ButtonStyle.danger,
        emoji="📝",
        custom_id="ticket_close_reason_button"
    )
    async def close_with_reason(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        guild = interaction.guild

        if guild is None:
            return await interaction.response.send_message(
                "This can only be used inside a server ticket.",
                ephemeral=True
            )

        staff_role = guild.get_role(staff_role_id)

        if staff_role is None:
            return await interaction.response.send_message(
                "Staff role not found.",
                ephemeral=True
            )

        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "Could not verify your server permissions.",
                ephemeral=True
            )

        if staff_role not in interaction.user.roles:
            return await interaction.response.send_message(
                "Only staff can close tickets with a reason.",
                ephemeral=True
            )

        await interaction.response.send_modal(CloseReasonModal())

    @discord.ui.button(
        label="Claim",
        style=discord.ButtonStyle.success,
        emoji="🙋",
        custom_id="ticket_claim_button"
    )
    async def claim_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        channel = interaction.channel
        guild = interaction.guild

        if guild is None or channel is None or not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message(
                "This can only be used inside a server ticket.",
                ephemeral=True
            )

        staff_role = guild.get_role(staff_role_id)
        if staff_role is None:
            return await interaction.response.send_message(
                "Staff role not found.",
                ephemeral=True
            )

        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "Could not verify your server permissions.",
                ephemeral=True
            )

        if staff_role not in interaction.user.roles:
            return await interaction.response.send_message(
                "Only staff can claim tickets.",
                ephemeral=True
            )

        claimed_by = self.get_claimed_by(channel.topic)

        if claimed_by is not None:
            if claimed_by == interaction.user.id:
                return await interaction.response.send_message(
                    "You already claimed this ticket.",
                    ephemeral=True
                )

            existing_staff = guild.get_member(claimed_by)
            existing_name = existing_staff.mention if existing_staff else f"<@{claimed_by}>"

            return await interaction.response.send_message(
                f"This ticket has already been claimed by {existing_name}.",
                ephemeral=True
            )

        new_topic = self.set_claimed_by(channel.topic, interaction.user.id)
        await channel.edit(topic=new_topic)

        embed = make_embed(
            title="Ticket Claimed",
            description=f"This ticket has been claimed by {interaction.user.mention}.",
            colour=discord.Color.blurple(),
        )

        await interaction.response.send_message(embed=embed)

class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(TicketPanelView())
        self.bot.add_view(TicketManageView())

    @commands.hybrid_command(name="ticketpanel", description="Send the ticket panel")
    @commands.has_permissions(manage_channels=True)
    @commands.guild_only()
    async def ticket_panel(self, ctx: commands.Context):
        embed = make_embed(
            title="Support Tickets",
            description="Press the button below to open a private support ticket.",
            colour=discord.Color.blurple(),
        )
        await ctx.send(embed=embed, view=TicketPanelView())

async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))