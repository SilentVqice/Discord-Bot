from __future__ import annotations
from typing import Optional
import discord
from discord.ext import commands

help_data = {
    "Moderation": {
        "purge": {
            "usage": ";purge <amount> or /purge <amount>",
            "description": "Deletes a number of messages from the channel.",
            "example": [";purge 10"]
        },
        "ban": {
            "usage": ";ban <@user> [reason] or /ban <@user> [reason]",
            "description": "Bans a member from the server.",
            "example": [";ban @user Breaking rules"]
        },
        "unban": {
            "usage": ";unban <user_id> [reason] or /unban <user_id> [reason]",
            "description": "Unbans a member by their Discord user ID.",
            "example": [";unban 123456789012345678 Appeal accepted"]
        },
        "kick": {
            "usage": ";kick <@user> [reason] or /kick <@user> [reason]",
            "description": "Kicks a member from the server.",
            "example": [";kick @user Spamming"]
        },
        "mute": {
            "usage": ";mute <@user> [duration] [reason] or /mute <@user> [duration]",
            "description": "Mutes a member, optionally for a set time.",
            "example": [";mute @user 10m Spam"]
        },
        "unmute": {
            "usage": ";unmute <@user> [reason] or /unmute <@user> [reason]",
            "description": "Unmutes a member by removing the muted role.",
            "example": [";unmute @user"]
        },
        "warn": {
            "usage": ";warn <@user> [reason] or /warn <@user> [reason]",
            "description": "Warns a user, optionally for a specified reason.",
            "example": [";warn @user Ignoring staff"]
        },
        "warnings": {
            "usage": ";warnings <@user> or /warnings <@user>",
            "description": "Shows a user's warnings.",
            "example": [";warnings @user"]
        },
        "delwarn": {
            "usage": ";delwarn <@user> <warn_number>",
            "description": "Deletes a specific warning from a user.",
            "example": [";delwarn @user 2"]
        },
        "clearwarns": {
            "usage": ";clearwarns <@user>",
            "description": "Deletes all warns from a user",
            "example": [";clearwarns @user"]
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
        },
        "ticketpanel": {
            "usage": ";ticketpanel or /ticketpanel",
            "description": "Creates a ticket panel for opening tickets.",
            "example": [";ticketpanel"]
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
            "usage": ";hug <@user> or /hug <@user>",
            "description": "Sends a random anime hug GIF.",
            "example": [";hug @user"]
        },
        "slap": {
            "usage": ";slap <@user> or /slap <@user>",
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
            "example": [";connect4", ";connect4 @user", ";c4 @user"]
        },
        "ai": {
            "usage": ";ai <text> or /ai <text>",
            "description": "Talk with the AI.",
            "example": [";ai Hello, can you help me with something?"]
        }
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
        "add": {
            "usage": ";add <song name or URL> or /add <song name or URL>",
            "description": "Adds a song to the queue",
            "example": [";add Despacito", ";add https://youtube.com/watch?v=..."]
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
        "queue loop": {
            "usage": ";queue loop or /queue loop",
            "description": "Loop the current queue.",
            "example": [";queue loop"]
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
            "usage": ";volume <0-200> or /volume <0-200>",
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
            "usage": ";bassboost [on/off] or /bassboost [on/off]",
            "description": "Toggles bassboost mode.",
            "example": [";bassboost", ";bassboost on", ";bassboost off"]
        },
        "autoplay": {
            "usage": ";autoplay [on/off] or /autoplay [on/off]",
            "description": "Toggles autoplay mode.",
            "example": [";autoplay", ";autoplay on", ";autoplay off"]
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

CATEGORY_ORDER = ["Moderation", "Utility", "Fun", "Music"]

CATEGORY_EMOJIS = {
    "Moderation": "🛡️",
    "Utility": "🛠️",
    "Fun": "🎮",
    "Music": "🎵"
}

class HelpPaginator(discord.ui.View):
    def __init__(self, cog: "Help", author_id: int):
        super().__init__(timeout=180)
        self.cog = cog
        self.author_id = author_id
        self.page_index = 0
        self.max_pages = len(CATEGORY_ORDER)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "You cannot use someone else's help menu.",
                ephemeral=True
            )
            return False
        return True

    def update_buttons(self):
        self.previous_button.disabled = self.page_index == 0
        self.next_button.disabled = self.page_index == self.max_pages - 1

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page_index > 0:
            self.page_index -= 1

        self.update_buttons()
        embed = self.cog.build_help_page_embed(self.page_index)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page_index < self.max_pages - 1:
            self.page_index += 1

        self.update_buttons()
        embed = self.cog.build_help_page_embed(self.page_index)
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def build_help_page_embed(self, page_index: int) -> discord.Embed:
        category = CATEGORY_ORDER[page_index]
        commands_dict = help_data[category]
        emoji = CATEGORY_EMOJIS.get(category, "•")

        embed = discord.Embed(
            title=f"{emoji} {category} Commands",
            description="Use `;help <command>` for detailed information about one command.",
            colour=discord.Color.blurple()
        )

        if self.bot.user:
            embed.set_author(
                name=self.bot.user.name,
                icon_url=self.bot.user.display_avatar.url
            )

        lines = []
        for name, info in commands_dict.items():
            lines.append(f"`;{name}` — {info['description']}")

        embed.add_field(
            name="Commands",
            value="\n".join(lines),
            inline=False
        )

        embed.add_field(
            name="Made with love by",
            value="<@465610916873109504>",
            inline=False
        )

        embed.set_footer(
            text=f"Page {page_index + 1}/{len(CATEGORY_ORDER)} • Total commands: {sum(len(x) for x in help_data.values())}"
        )

        return embed

    @commands.hybrid_command(name="help", description="Shows all commands or detailed help for one command.")
    async def help_command(self, ctx: commands.Context, command_name: Optional[str] = None):
        if command_name is None:
            view = HelpPaginator(self, ctx.author.id)
            view.update_buttons()
            embed = self.build_help_page_embed(0)
            await ctx.send(embed=embed, view=view)
            return

        category, name, info = find_help_entry(command_name)

        if info is None:
            await ctx.send(f"⚠No help found for `{command_name}`.")
            return

        embed = discord.Embed(
            title=f";{name}",
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


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))