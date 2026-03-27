import aiohttp
import discord
from discord.ext import commands
from .helpers import make_embed, add_requester_footer

class Images(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

########################################################################################################################
# KITTY IMAGES
########################################################################################################################

    @commands.hybrid_command(name="kitty", description="Sends a random cat image.")
    async def kitty(self, ctx: commands.Context):
        if ctx.interaction:
            await ctx.defer()

        url = "https://api.thecatapi.com/v1/images/search"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    embed = make_embed(
                        "Kitty",
                        "Could not fetch a cat image right now.. Sorry! 😿",
                        discord.Color.red()
                    )
                    return await ctx.send(embed=embed)

                data = await resp.json()
                image_url = data[0]["url"]

        embed = make_embed("Kitty!", colour=discord.Color.pink())
        embed.set_image(url=image_url)
        add_requester_footer(embed, ctx.author)
        await ctx.send(embed=embed)

########################################################################################################################
# BUNNY IMAGES
########################################################################################################################

    @commands.hybrid_command(name="bunny", description="Sends a random bunny image.")
    async def bunny(self, ctx: commands.Context):
        if ctx.interaction:
            await ctx.defer()

        url = "https://rabbit-api-two.vercel.app/api/random"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    embed = make_embed(
                        "Bunny",
                        "Could not fetch a bunny right now 🐰",
                        discord.Color.red()
                    )
                    return await ctx.send(embed=embed)

                data = await resp.json()

        image_url = None
        possible = [
            data.get("image"),
            data.get("url"),
            data.get("link"),
            data.get("src"),
            data.get("image_url"),
        ]

        for p in possible:
            if isinstance(p, str) and p.startswith("http"):
                image_url = p
                break

        if not image_url:
            embed = make_embed(
                "Bunny",
                "No valid bunny image found in API response 😢",
                discord.Color.red()
            )
            return await ctx.send(embed=embed)

        embed = make_embed("Bunny!", colour=discord.Color.pink())
        embed.set_image(url=image_url)
        add_requester_footer(embed, ctx.author)
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Images(bot))