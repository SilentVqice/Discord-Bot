import asyncio
import html
import random
import aiohttp
import discord
from discord.ext import commands
from .helpers import make_embed

class Quiz(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

########################################################################################################################
# TRIVIA
########################################################################################################################

    @commands.hybrid_command(name="trivia", description="Starts a trivia question.")
    async def trivia(self, ctx: commands.Context):
        if ctx.interaction:
            await ctx.defer()

        url = "https://opentdb.com/api.php?amount=1&type=multiple"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return await ctx.send("Could not fetch a trivia question right now.")

                data = await resp.json()

        if not data.get("results"):
            return await ctx.send("No trivia question was returned.")

        question_data = data["results"][0]
        question = html.unescape(question_data["question"])
        correct = html.unescape(question_data["correct_answer"])
        incorrect = [html.unescape(i) for i in question_data["incorrect_answers"]]

        answers = incorrect + [correct]
        random.shuffle(answers)

        letters = ["A", "B", "C", "D"]
        answer_map = dict(zip(letters, answers))

        description = "\n".join(
            f"**{letter}**. {answer}" for letter, answer in answer_map.items()
        )

        embed = make_embed(
            "🧠 Trivia Question",
            f"**{question}**\n\n{description}",
            discord.Color.green()
        )
        await ctx.send(embed=embed)

        def check(m: discord.Message):
            return (
                m.author == ctx.author
                and m.channel == ctx.channel
                and m.content.upper() in letters
            )

        try:
            msg = await self.bot.wait_for("message", timeout=20, check=check)
        except asyncio.TimeoutError:
            return await ctx.send(f"⏰ Time's up! The correct answer was **{correct}**.")

        if answer_map[msg.content.upper()] == correct:
            await ctx.send("✅ Correct!")
        else:
            await ctx.send(f"❌ Wrong! The correct answer was **{correct}**.")

########################################################################################################################
# FLAG TRIVIA
########################################################################################################################

    @commands.hybrid_command(name="flag", description="Starts a country flag guessing game.")
    async def flag(self, ctx: commands.Context):
        if ctx.interaction:
            await ctx.defer()

        url = "https://restcountries.com/v3.1/all?fields=name,flags"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return await ctx.send("⚠️ API failed. Try again later.")
                data = await resp.json()

        valid = [
            c for c in data
            if "name" in c and "common" in c["name"]
            and "flags" in c and "png" in c["flags"]
        ]

        if not valid:
            return await ctx.send("⚠️ No valid countries found.")

        country = random.choice(valid)
        correct = country["name"]["common"]
        flag_url = country["flags"]["png"]

        embed = make_embed(
            "🌍 Guess the Country!",
            "What country does this flag belong to?",
            discord.Color.blue()
        )
        embed.set_image(url=flag_url)
        await ctx.send(embed=embed)

        def check(m: discord.Message):
            return m.author == ctx.author and m.channel == ctx.channel

        total_time = 25
        hint_sent = False

        async def scheduled_hint():
            nonlocal hint_sent
            await asyncio.sleep(10)
            if not hint_sent:
                hint_sent = True
                await ctx.send(f"💡 Hint: Starts with **{correct[0]}**")

        hint_task = asyncio.create_task(scheduled_hint())
        start_time = asyncio.get_running_loop().time()

        while True:
            elapsed = asyncio.get_running_loop().time() - start_time
            remaining = total_time - elapsed

            if remaining <= 0:
                if not hint_task.done():
                    hint_task.cancel()
                return await ctx.send(f"⏰ Time's up! The answer was **{correct}**.")

            try:
                msg = await self.bot.wait_for("message", timeout=remaining, check=check)
            except asyncio.TimeoutError:
                if not hint_task.done():
                    hint_task.cancel()
                return await ctx.send(f"⏰ Time's up! The answer was **{correct}**.")

            if correct.lower() in msg.content.lower():
                if not hint_task.done():
                    hint_task.cancel()
                return await ctx.send("✅ Correct!")

            await ctx.send("❌ Wrong! Try again...")

            if not hint_sent:
                await ctx.send(f"💡 Hint: Starts with **{correct[0]}**")
                hint_sent = True

async def setup(bot: commands.Bot):
    await bot.add_cog(Quiz(bot))