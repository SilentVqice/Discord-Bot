import discord
from discord.ext import commands
import ollama


class AIChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.chat_memory: dict[tuple[int, int], list[dict[str, str]]] = {}

        self.system_prompt = (
            "You are a helpful Discord bot assistant. "
            "Reply clearly, naturally, and keep answers suitable for Discord. "
            "Keep replies concise unless the user asks for detail."
        )

    @commands.hybrid_command(name="ai", description="Talk to the AI")
    @commands.cooldown(2, 10, commands.BucketType.user)
    async def ai(self, ctx: commands.Context, *, prompt: str):
        memory_key = (ctx.channel.id, ctx.author.id)

        history = self.chat_memory.get(memory_key, [])
        messages = [{"role": "system", "content": self.system_prompt}, *history]
        messages.append({"role": "user", "content": prompt})

        async with ctx.typing():
            try:
                response = ollama.chat(
                    model="gemma3",
                    messages=messages
                )

                reply_text = response["message"]["content"].strip()

                if not reply_text:
                    await ctx.send("I didn't get a usable reply from the AI.")
                    return

                history.append({"role": "user", "content": prompt})
                history.append({"role": "assistant", "content": reply_text})
                self.chat_memory[memory_key] = history[-12:]

                if len(reply_text) <= 2000:
                    await ctx.send(reply_text)
                else:
                    for i in range(0, len(reply_text), 1900):
                        await ctx.send(reply_text[i:i + 1900])

            except Exception as e:
                await ctx.send(f"Local AI error: `{e}`")

    @commands.hybrid_command(name="aireset", description="Reset AI memory")
    async def aireset(self, ctx: commands.Context):
        memory_key = (ctx.channel.id, ctx.author.id)

        if memory_key in self.chat_memory:
            del self.chat_memory[memory_key]
            await ctx.send("AI memory reset for this channel.")
        else:
            await ctx.send("There was no saved AI memory for this channel.")


async def setup(bot: commands.Bot):
    await bot.add_cog(AIChat(bot))