import io
import json
import os
from pathlib import Path
import discord
from typing import Optional
from PIL import Image, ImageFont, ImageOps
from discord import AllowedMentions
from discord.ext import commands

help_data = {
    "Moderation": {
        "ban": {
            "usage": ";ban @user [reason] or /ban @user [reason]",
            "description": "Bans a member from the server.",
            "example": [";ban @user Breaking rules"]
        },
        "unban": {
            "usage": ";unban <user_id> [reason] or /unban <user_id> [reason]",
            "description": "Unbans a member by their Discord user ID.",
            "example": [";unban 123456789012345678 Appeal accepted"]
        },
        "kick": {
            "usage": ";kick @user [reason] or /kick @user [reason]",
            "description": "Kicks a member from the server.",
            "example": [";kick @user Spamming"]
        },
        "mute": {
            "usage": ";mute @user [duration] [reason] or /mute @user [duration]",
            "description": "Mutes a member, optionally for a set time.",
            "example": [";mute @user 10m Spam"]
        },
        "unmute": {
            "usage": ";unmute @user [reason] or /unmute @user [reason]",
            "description": "Unmutes a member by removing the muted role.",
            "example": [";unmute @user"]
        },
        "purge": {
            "usage": ";purge <amount> or /purge <amount>",
            "description": "Deletes a number of messages from the channel.",
            "example": [";purge 10"]
        }
    },

    "Utility": {
        "help": {
            "usage": ";help [command] or /help [command]",
            "description": "Shows all commands or detailed help for one command.",
            "example": [";help", ";help play"]
        },
        "info": {
            "usage": ";info [@user] or /info [@user]",
            "description": "Shows information about you or another user.",
            "example": [";info", ";info @Velourie"]
        }
    },
    "Fun": {
        "kitty": {
            "usage": ";kitty or /kitty",
            "description": "Sends a random cat image.",
            "example": [";kitty"]
        },
        "bunny": {
            "usage": ";bunny or /bunny",
            "description": "Sends a random bunny image.",
            "example": [";bunny"]
        },
        "coinflip": {
            "usage": ";coinflip or /coinflip",
            "description": "Flips a coin.",
            "example": [";coinflip"]
        },
        "roll": {
            "usage": ";roll [sides] or /roll [sides]",
            "description": "Rolls a die with the number of sides you choose.",
            "example": [";roll", ";roll 20"]
        },
        "eightball": {
            "usage": ";eightball <question> or /eightball <question>",
            "description": "Ask the magic 8-ball a question.",
            "example": [";eightball Will I win?"],
            "aliases": ["8ball"]
        },
        "choose": {
            "usage": ";choose <option1, option2, option3> or /choose <option1, option2, option3>",
            "description": "Chooses one option from a list.",
            "example": [";choose red, blue, green"]
        },
        "say": {
            "usage": ";say <text> or /say <text>",
            "description": "Makes the bot repeat a message in an embed.",
            "example": [";say hello"]
        },
        "hug": {
            "usage": ";hug @user or /hug @user",
            "description": "Sends a random anime hug GIF.",
            "example": [";hug @user"]
        },
        "slap": {
            "usage": ";slap @user or /slap @user",
            "description": "Sends a random anime slap GIF.",
            "example": [";slap @user"]
        },
        "trivia": {
            "usage": ";trivia or /trivia",
            "description": "Starts a trivia question.",
            "example": [";trivia"]
        },
        "flag": {
            "usage": ";flag or /flag",
            "description": "Starts a country flag guessing game.",
            "example": [";flag"]
        },
        "rps": {
            "usage": ";rps [@user] or /rps [@user]",
            "description": "Play Rock, Paper, Scissors against a user or the bot.",
            "example": [";rps", ";rps @user"]
        },
        "ttt": {
            "usage": ";ttt [@user] or /ttt [@user]",
            "description": "Play Tic Tac Toe against a user or the bot.",
            "example": [";ttt", ";ttt @user"]
        },
        "connect4": {
            "usage": ";connect4 [@user] or /connect4 [@user]",
            "description": "Play Connect 4 against a user or the bot.",
            "example": [";connect4", ";connect4 @user", ";c4 @user"],
            "aliases": ["c4"]
        },
    },
    "Music": {
        "join": {
            "usage": ";join or /join",
            "description": "Joins your current voice channel.",
            "example": [";join"]
        },
        "play": {
            "usage": ";play <song name or URL> or /play <song name or URL>",
            "description": "Adds a song to the queue or starts playback.",
            "example": [";play Despacito", ";play https://youtube.com/watch?v=..."]
        },
        "pause": {
            "usage": ";pause or /pause",
            "description": "Pauses the current song.",
            "example": [";pause"]
        },
        "resume": {
            "usage": ";resume or /resume",
            "description": "Resumes the paused song.",
            "example": [";resume"]
        },
        "skip": {
            "usage": ";skip or /skip",
            "description": "Skips the current song.",
            "example": [";skip"]
        },
        "queue": {
            "usage": ";queue or /queue",
            "description": "Shows the current queue.",
            "example": [";queue"]
        },
        "remove": {
            "usage": ";remove <number> or /remove <number>",
            "description": "Removes a song from the queue.",
            "example": [";remove 2"]
        },
        "clear": {
            "usage": ";clear or /clear",
            "description": "Clears the queue.",
            "example": [";clear"]
        },
        "leave": {
            "usage": ";leave or /leave",
            "description": "Stops playback and disconnects from voice.",
            "example": [";leave"]
        },
        "loop": {
            "usage": ";loop [on/off] or /loop [on/off]",
            "description": "Toggles looping for the current song.",
            "example": [";loop", ";loop on", ";loop off"]
        },
        "shuffle": {
            "usage": ";shuffle or /shuffle",
            "description": "Shuffles the current queue.",
            "example": [";shuffle"]
        },
        "volume": {
            "usage": ";volume <0-200> or volume <0-200>",
            "description": "Sets playback volume.",
            "example": [";volume 50", ";volume 100"]
        },
        "slowed": {
            "usage": ";slowed [on/off] or /slowed [on/off]",
            "description": "Toggles slowed mode.",
            "example": [";slowed", ";slowed on", ";slowed off"]
        },
        "sped": {
            "usage": ";sped [on/off] or /sped [on/off]",
            "description": "Toggles sped mode.",
            "example": [";sped", ";sped on", ";sped off"]
        },
        "bassboost": {
            "usage": ";bassboost [on/off] or bassboost [on/off]",
            "description": "Toggles bassboost mode.",
            "example": [";bassboost", ";bassboost on", ";bassboost off"]
        },
        "lyrics": {
            "usage": ";lyrics or /lyrics",
            "description": "Shows lyrics for the current track.",
            "example": [";lyrics"]
        }
    }
}

def find_help_entry(command_name: str):
    command_name = command_name.lower()

    for category, commands_dict in help_data.items():
        for name, info in commands_dict.items():
            aliases = [a.lower() for a in info.get("aliases", [])]
            if command_name == name.lower() or command_name in aliases:
                return category, name, info

    return None, None, None

class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.member_count_channel_id = 1483268373902000128
        self.reaction_channel_id = 1483259632385396926
        self.reaction_message_file = "reaction_message.json"

        self.default_role_id = 1483280765092630669
        self.welcome_channel_id = 1483276233818112202

        self.emoji_to_role = {
            "<:bed:1483254053227200584>": 1483256278565523608
        }

        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.assets_dir = self.base_dir / "assets"
        self.background_path = self.assets_dir / "welcome_background.png"
        self.font_path = self.assets_dir / "DejaVuSans-Bold.ttf"

        self.card_width = 1000
        self.card_height = 350

    @commands.hybrid_command(name="help", description="Shows all commands or detailed help for one command.")
    async def help_command(self, ctx: commands.Context, command_name: Optional[str] = None):
        if command_name is None:
            embed = discord.Embed(
                title="✨ Bot Help",
                description=(
                    "Here are all available commands.\n"
                    "Use `;help <command>` for detailed information."
                ),
                colour=discord.Color.blurple()
            )

            embed.set_author(
                name=self.bot.user.name,
                icon_url=self.bot.user.display_avatar.url if self.bot.user else None
            )

            category_emojis = {
                "Utility": "🛠️",
                "Moderation": "🛡️",
                "Fun": "🎮",
                "Music": "🎵"
            }

            for category, commands_dict in help_data.items():
                emoji = category_emojis.get(category, "•")
                value = "\n".join(
                    f"`;{name}` — {info['description']}"
                    for name, info in commands_dict.items()
                )
                embed.add_field(
                    name=f"{emoji} {category}",
                    value=value,
                    inline=False
                )

            embed.add_field(
                name="Made with love by",
                value=f"<@465610916873109504>",
                inline=False
            )
            embed.set_footer(text=f"Total commands: {sum(len(x) for x in help_data.values())}")
            return await ctx.send(embed=embed)

        category, name, info = find_help_entry(command_name)

        if info is None:
            return await ctx.send(f"⚠️ No help found for `{command_name}`.")

        embed = discord.Embed(
            title=f"📘 ;{name}",
            description=info["description"],
            colour=discord.Color.blue()
        )

        embed.add_field(name="Usage", value=f"`{info['usage']}`", inline=False)

        examples = "\n".join(f"`{example}`" for example in info.get("example", []))
        if examples:
            embed.add_field(name="Examples", value=examples, inline=False)

        aliases = info.get("aliases")
        if aliases:
            embed.add_field(
                name="Aliases",
                value=", ".join(f"`;{alias}`" for alias in aliases),
                inline=False
            )

        embed.add_field(name="Category", value=category, inline=True)
        embed.set_footer(text="< > = required | [ ] = optional")

        await ctx.send(embed=embed)

    async def setup_reaction_message(self):
        channel = self.bot.get_channel(self.reaction_channel_id)
        if not channel:
            return

        message_id = None
        if os.path.exists(self.reaction_message_file):
            with open(self.reaction_message_file, "r") as f:
                data = json.load(f)
                message_id = data.get("message_id")

        message = None

        if message_id:
            try:
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                message = None

        if message is None:
            embed = discord.Embed(
                title="React to get your roles!",
                description="React with <:bed:1483254053227200584> to get the **RBW** role!",
                colour=discord.Color.red()
            )
            message = await channel.send(embed=embed)
            await message.add_reaction("<:bed:1483254053227200584>")

            with open(self.reaction_message_file, "w") as f:
                json.dump({"message_id": message.id}, f)

    async def update_member_count(self, guild: discord.Guild):
        channel = guild.get_channel(self.member_count_channel_id)
        if channel:
            await channel.edit(name=f"Members: {guild.member_count}")

    def load_font(self, size: int):
        if self.font_path.exists():
            return ImageFont.truetype(str(self.font_path), size)
        return ImageFont.load_default()

    async def fetch_avatar_bytes(self, member: discord.Member) -> bytes:
        avatar_asset = member.display_avatar.replace(size=256)
        return await avatar_asset.read()

    def fit_background(self) -> Image.Image:
        background = Image.open(self.background_path).convert("RGBA")
        return ImageOps.fit(
            background,
            (self.card_width, self.card_height),
            method=Image.Resampling.LANCZOS
        )

    def build_welcome_card(self, avatar_bytes: bytes, member: discord.Member) -> io.BytesIO:
        card = self.fit_background()

        output = io.BytesIO()
        card.save(output, format="PNG")
        output.seek(0)
        return output

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.bot.user.name} is online! :3")
        for guild in self.bot.guilds:
            await self.update_member_count(guild)
        await self.setup_reaction_message()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        member = guild.get_member(payload.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.NotFound:
                return
            except discord.HTTPException:
                return

        if member.bot:
            return

        role_id = self.emoji_to_role.get(str(payload.emoji))
        if role_id is None:
            return

        role = guild.get_role(role_id)
        if role:
            await member.add_roles(role)
            print(f"Added {role.name} to {member.name}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        try:
            member = await guild.fetch_member(payload.user_id)
        except discord.NotFound:
            return
        except discord.HTTPException:
            return

        if member.bot:
            return

        role_id = self.emoji_to_role.get(str(payload.emoji))
        if role_id is None:
            return

        role = guild.get_role(role_id)
        if role:
            await member.remove_roles(role)
            print(f"Removed {role.name} from {member.name}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self.update_member_count(member.guild)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.update_member_count(member.guild)

        channel = member.guild.get_channel(self.welcome_channel_id)
        if channel is None:
            return

        if not self.background_path.exists():
            embed = discord.Embed(
                title=f"Welcome to the server, {member.display_name}!",
                description="We're very happy to have you here buh buh",
                colour=discord.Color.green(),
            )
            embed.set_footer(text="Missing welcome background image.")
            await channel.send(
                content=f"Welcome {member.mention}!",
                embed=embed
            )
        else:
            avatar_bytes = await self.fetch_avatar_bytes(member)
            welcome_image = self.build_welcome_card(avatar_bytes, member)

            file = discord.File(fp=welcome_image, filename="welcome.png")

            embed = discord.Embed(
                title=f"Welcome to the server, {member.display_name}!",
                description="buh buh buh",
                colour=discord.Color.green(),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_image(url="attachment://welcome.png")
            embed.set_footer(text="Enjoy your stay!")

            await channel.send(
                content=f"Welcome {member.mention}!",
                embed=embed,
                file=file,
            )

        role = member.guild.get_role(self.default_role_id)
        if role:
            await member.add_roles(role)
            print(f"Added {role.name} to {member.name}.")

    @commands.hybrid_command(name="info", description="Shows information about you or another user.")
    async def info(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        member = member or ctx.author

        roles = [role.mention for role in reversed(member.roles) if role.name != "@everyone"]
        roles_display = ", ".join(roles) if roles else "No roles."
        roles_count = len(roles)

        created = member.created_at.strftime("%d %b %Y %H:%M:%S")
        joined = member.joined_at.strftime("%d %b %Y %H:%M:%S")

        allowed = AllowedMentions(users=True)
        embed = discord.Embed(
            title="User info",
            colour=member.color
        )
        embed.add_field(name="Member", value=member.mention, inline=True)

        embed.set_author(
            name=str(member),
            icon_url=member.avatar.url if member.avatar else None
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        embed.add_field(name="Username", value=str(member), inline=True)
        embed.add_field(name="User ID", value=member.id, inline=False)
        embed.add_field(name="Account Created", value=created, inline=True)
        embed.add_field(name="Joined Server", value=joined, inline=True)
        embed.add_field(name=f"Roles [{roles_count}]", value=roles_display, inline=False)

        await ctx.send(mention_author=True, embed=embed, allowed_mentions=allowed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return

        special_user_responses = {
            979934316429738035: "Mwah",
            465610916873109504: "👑"
        }

        if self.bot.user in message.mentions:
            await message.channel.send("Hewwo :3")

        handled_mentions = set()
        for user in message.mentions:
            if user.id in special_user_responses and user.id not in handled_mentions:
                await message.channel.send(special_user_responses[user.id])
                handled_mentions.add(user.id)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.MissingPermissions):
            return await ctx.send("You do not have permission to use that command.", delete_after=5)

        if isinstance(error, commands.BadArgument):
            return await ctx.send("I couldn't read that user. Try `;connect4` or `;connect4 @user`.")

        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send("Missing argument for that command.")

        if isinstance(error, commands.CommandInvokeError) and isinstance(error.original, RuntimeError):
            message = str(error.original).lower()
            if "library needed" in message and "voice" in message:
                return await ctx.send(
                    "Voice support is missing. Install `PyNaCl` and `davey`, then restart the bot."
                )

        await ctx.send(f"Command error: {error}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))