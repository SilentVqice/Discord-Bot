from __future__ import annotations

from typing import Optional
import discord

from utils.log_config import LOG_CHANNELS


class LogHelper:
    def __init__(self, bot):
        self.bot = bot

    async def send_log(
        self,
        category: str,
        title: str,
        description: str,
        colour: discord.Colour = discord.Color.blurple(),
        thumbnail: Optional[str] = None,
    ) -> None:
        channel_id = LOG_CHANNELS.get(category)
        if not channel_id:
            return

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return

        if not isinstance(channel, discord.abc.Messageable):
            return

        embed = discord.Embed(
            title=title,
            description=description,
            colour=colour,
            timestamp=discord.utils.utcnow(),
        )

        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        try:
            await channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            pass