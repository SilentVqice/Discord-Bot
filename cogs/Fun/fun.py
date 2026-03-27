import random
import discord
from discord.ext import commands
from .helpers import make_embed, add_requester_footer

EIGHTBALL_RESPONSES = [
    "Yes.",
    "No.",
    "Maybe.",
    "Definitely.",
    "Absolutely not.",
    "It is certain.",
    "Very doubtful.",
    "Ask again later.",
    "Without a doubt.",
    "Signs point to yes.",
]

class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

########################################################################################################################
# COINFLIP
########################################################################################################################

    @commands.hybrid_command(name="coinflip", description="Flips a coin.")
    async def coinflip(self, ctx: commands.Context):
        result = random.choice(["Heads", "Tails"])
        embed = make_embed("Coinflip", f"🪙 **{result}**", discord.Color.gold())
        add_requester_footer(embed, ctx.author)
        await ctx.send(embed=embed)

########################################################################################################################
# ROLL THE DICE
########################################################################################################################

    @commands.hybrid_command(name="roll", description="Roll a die with a chosen number of sides.")
    async def roll(self, ctx: commands.Context, sides: int = 6):
        if sides < 2:
            embed = make_embed("Roll", "The die needs at least 2 sides.", discord.Color.red())
            return await ctx.send(embed=embed)

        result = random.randint(1, sides)
        embed = make_embed(
            "Dice Roll",
            f"🎲 You rolled **{result}** out of **{sides}**.",
            discord.Color.blurple()
        )
        add_requester_footer(embed, ctx.author)
        await ctx.send(embed=embed)

########################################################################################################################
# EIGHTBALL
########################################################################################################################

    @commands.hybrid_command(name="eightball", description="Ask the magic 8-ball a question.")
    async def eightball(self, ctx: commands.Context, *, question: str = None):
        if not question:
            embed = make_embed("Magic 8-Ball", "Ask a question.", discord.Color.red())
            return await ctx.send(embed=embed)

        embed = make_embed("Magic 8-Ball", colour=discord.Color.dark_purple())
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=f"🎱 {random.choice(EIGHTBALL_RESPONSES)}", inline=False)
        add_requester_footer(embed, ctx.author)
        await ctx.send(embed=embed)

########################################################################################################################
# CHOOSE
########################################################################################################################

    @commands.hybrid_command(name="choose", description="Choose between multiple choices.")
    async def choose(self, ctx: commands.Context, *, choices: str = None):
        if not choices:
            embed = make_embed(
                "Choose",
                "Give me some choices separated by commas.",
                discord.Color.red()
            )
            return await ctx.send(embed=embed)

        options = [choice.strip() for choice in choices.split(",") if choice.strip()]
        if len(options) < 2:
            embed = make_embed("Choose", "Give me at least 2 choices.", discord.Color.red())
            return await ctx.send(embed=embed)

        chosen = random.choice(options)
        embed = make_embed("Choice Made", f"🤔 I choose: **{chosen}**", discord.Color.green())
        add_requester_footer(embed, ctx.author)
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))