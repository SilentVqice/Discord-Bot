import os
import logging
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.presences = True

test_guild_id = 1483248089757388861


class MyBot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension("cogs.Music.music")
        await self.load_extension("cogs.Utility.utility")
        await self.load_extension("cogs.Utility.tickets")
        await self.load_extension("cogs.Utility.logs")
        await self.load_extension("cogs.Moderation.moderation")
        await self.load_extension("cogs.Fun.games")
        await self.load_extension("cogs.Fun.quiz")
        await self.load_extension("cogs.Fun.images")
        await self.load_extension("cogs.Fun.social")
        await self.load_extension("cogs.Fun.fun")

        guild = discord.Object(id=test_guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

        print("Commands synced.")

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.MemberNotFound):
            return await ctx.send("That member could not be found.", delete_after=5)

        if isinstance(error, commands.BadArgument):
            return await ctx.send("Invalid argument provided.", delete_after=5)

        if isinstance(error, commands.BadUnionArgument):
            return await ctx.send("Invalid value provided.", delete_after=5)

        print(f"[GLOBAL COMMAND ERROR] {repr(error)}")

    async def on_ready(self):
        print(f"Logged in as {self.user} ({self.user.id})")


bot = MyBot(
    command_prefix=";",
    intents=intents,
    help_command=None,
)

bot.run(token, log_handler=handler, log_level=logging.INFO)