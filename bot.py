import os
import asyncio
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.presences = True

bot = commands.Bot(command_prefix=";", intents=intents, help_command=None)

async def load_extensions():
    await bot.load_extension("cogs.Music.music")
    await bot.load_extension("cogs.Utility.utility")
    await bot.load_extension("cogs.Moderation.moderation")
    await bot.load_extension("cogs.Fun.fun")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(token)

asyncio.run(main())