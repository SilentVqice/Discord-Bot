import aiohttp
import discord
from discord.ext import commands
from .helpers import make_embed

class Social(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

########################################################################################################################
# SAY
########################################################################################################################

    @commands.hybrid_command(name="say", description="Make the bot say something.")
    async def say(self, ctx: commands.Context, *, text: str = None):
        if not text:
            embed = make_embed("Say", "Give me something to say.", discord.Color.red())
            return await ctx.send(embed=embed)

        try:
            await ctx.message.delete()
        except (AttributeError, discord.Forbidden, discord.HTTPException):
            pass

        embed = discord.Embed(description=text, colour=discord.Color.blurple())
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

########################################################################################################################
# HUG
########################################################################################################################

    @commands.hybrid_command(name="hug", description="Hug someone with a random anime GIF.")
    async def hug(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            embed = make_embed("Hug", "You need to mention someone to hug.", discord.Color.red())
            return await ctx.send(embed=embed)

        if member == ctx.author:
            embed = make_embed(
                "Hug",
                f"🤗 {ctx.author.mention} hugs themselves. That is a bit sad.",
                discord.Color.pink()
            )
            return await ctx.send(embed=embed)

        url = "https://nekos.best/api/v2/hug"
        headers = {"User-Agent": "DiscordBot/1.0"}

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    embed = make_embed(
                        "Hug",
                        "Could not fetch a hug GIF right now.",
                        discord.Color.red()
                    )
                    return await ctx.send(embed=embed)

                data = await resp.json()

        results = data.get("results")
        if not results:
            return await ctx.send(embed=make_embed("Hug", "No hug GIF was returned.", discord.Color.red()))

        result = results[0]
        gif_url = result.get("url")
        anime_name = result.get("anime_name", "Unknown")

        embed = make_embed(
            "Hug",
            f"🤗 {ctx.author.mention} hugs {member.mention}!",
            discord.Color.pink()
        )
        if gif_url:
            embed.set_image(url=gif_url)
        embed.set_footer(
            text=f"Anime: {anime_name} • Requested by {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )
        await ctx.send(embed=embed)

########################################################################################################################
# SLAP
########################################################################################################################

    @commands.hybrid_command(name="slap", description="Slap someone with a random anime GIF.")
    async def slap(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            embed = make_embed("Slap", "You need to mention someone to slap.", discord.Color.red())
            return await ctx.send(embed=embed)

        if member == ctx.author:
            embed = make_embed("Slap", "🖐️ You slapped yourself. Brilliant.", discord.Color.red())
            return await ctx.send(embed=embed)

        url = "https://nekos.best/api/v2/slap"
        headers = {"User-Agent": "DiscordBot/1.0"}

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    embed = make_embed(
                        "Slap",
                        "Could not fetch a slap GIF right now.",
                        discord.Color.red()
                    )
                    return await ctx.send(embed=embed)

                data = await resp.json()

        results = data.get("results")
        if not results:
            return await ctx.send(embed=make_embed("Slap", "No slap GIF was returned.", discord.Color.red()))

        result = results[0]
        gif_url = result.get("url")
        anime_name = result.get("anime_name", "Unknown")

        embed = make_embed(
            "Slap",
            f"🖐️ {ctx.author.mention} slapped {member.mention}!",
            discord.Color.red()
        )
        if gif_url:
            embed.set_image(url=gif_url)
        embed.set_footer(
            text=f"Anime: {anime_name} • Requested by {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Social(bot))