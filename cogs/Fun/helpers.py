from typing import Optional
import discord


def make_embed(
    title: str,
    description: Optional[str] = None,
    colour: discord.Colour = discord.Color.blurple(),
) -> discord.Embed:
    return discord.Embed(title=title, description=description, colour=colour)


def add_requester_footer(embed: discord.Embed, user: discord.abc.User) -> discord.Embed:
    embed.set_footer(text=f"Requested by {user}", icon_url=user.display_avatar.url)
    return embed