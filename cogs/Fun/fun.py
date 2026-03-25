import asyncio
import html
import random
from typing import Optional

import aiohttp
import discord
from discord.ext import commands

RPS_EMOJIS = {
    "rock": "🪨",
    "paper": "📄",
    "scissors": "✂️",
}

TTT_WIN_COMBINATIONS = [
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
]

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

def make_embed(
    title: str,
    description: Optional[str] = None,
    colour: discord.Colour = discord.Color.blurple(),
) -> discord.Embed:
    return discord.Embed(title=title, description=description, colour=colour)


def add_requester_footer(embed: discord.Embed, user: discord.abc.User) -> discord.Embed:
    embed.set_footer(text=f"Requested by {user}", icon_url=user.display_avatar.url)
    return embed


def build_ttt_embed(status: str, player_x: discord.abc.User, player_o: discord.abc.User) -> discord.Embed:
    embed = discord.Embed(
        title="❌⭕ Tic Tac Toe",
        description=status,
        colour=discord.Color.blurple()
    )
    embed.add_field(name="❌ Player X", value=player_x.mention, inline=True)
    embed.add_field(name="⭕ Player O", value=player_o.mention, inline=True)
    embed.set_footer(text="Press a square to make your move.")
    return embed

########################################################################################################################
# ROCK PAPER SCISSORS UI
########################################################################################################################

class RPSButton(discord.ui.Button):
    def __init__(self, label: str, view_ref: "RPSView"):
        super().__init__(
            label=f"{RPS_EMOJIS[label.lower()]} {label}",
            style=discord.ButtonStyle.primary
        )
        self.choice_lower = label.lower()
        self.choice_label = label
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        if self.view_ref.pve:
            if interaction.user != self.view_ref.player1:
                return await interaction.response.send_message(
                    "This button isn’t for you!",
                    ephemeral=True
                )
            player = self.view_ref.player1
        else:
            if interaction.user not in [self.view_ref.player1, self.view_ref.opponent]:
                return await interaction.response.send_message(
                    "This button isn’t for you!",
                    ephemeral=True
                )
            player = interaction.user

        if player in self.view_ref.choices:
            return await interaction.response.send_message(
                "You already chose!",
                ephemeral=True
            )

        self.view_ref.choices[player] = (self.choice_lower, self.choice_label)

        await interaction.response.send_message(
            f"You chose {RPS_EMOJIS[self.choice_lower]} **{self.choice_label}**!",
            ephemeral=True
        )

        if self.view_ref.pve:
            bot_choice = random.choice(["rock", "paper", "scissors"])
            self.view_ref.choices[self.view_ref.opponent] = (
                bot_choice,
                bot_choice.capitalize()
            )
            await self.view_ref.resolve(interaction)
        elif len(self.view_ref.choices) == 2:
            await self.view_ref.resolve(interaction)


class RPSView(discord.ui.View):
    def __init__(self, bot: commands.Bot, player1: discord.Member, opponent: Optional[discord.Member] = None):
        super().__init__(timeout=60)
        self.bot = bot
        self.player1 = player1
        self.opponent = opponent or bot.user
        self.choices = {}
        self.pve = opponent is None or opponent.bot

        for label in ["Rock", "Paper", "Scissors"]:
            self.add_item(RPSButton(label, self))

    async def resolve(self, interaction: discord.Interaction):
        p1, p2 = self.player1, self.opponent
        c1_lower, c1_label = self.choices[p1]
        c2_lower, c2_label = self.choices[p2]

        c1_emoji = RPS_EMOJIS[c1_lower]
        c2_emoji = RPS_EMOJIS[c2_lower]

        if c1_lower == c2_lower:
            result = "🤝 It's a tie!"
        elif (
            (c1_lower == "rock" and c2_lower == "scissors")
            or (c1_lower == "paper" and c2_lower == "rock")
            or (c1_lower == "scissors" and c2_lower == "paper")
        ):
            result = f"✅ {p1.mention} wins!"
        else:
            result = f"❌ {p2.mention} wins!"

        for item in self.children:
            item.disabled = True

        embed = discord.Embed(
            title="Rock, Paper, Scissors",
            description=(
                f"{p1.mention} chose {c1_emoji} **{c1_label}**\n"
                f"{p2.mention} chose {c2_emoji} **{c2_label}**\n"
                f"{result}"
            ),
            colour=discord.Color.blurple()
        )

        await interaction.message.edit(embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

########################################################################################################################
# TIC TAC TOE UI
########################################################################################################################

class TicTacToeButton(discord.ui.Button):
    def __init__(self, position: int):
        super().__init__(
            label="\u200b",
            style=discord.ButtonStyle.secondary,
            row=position // 3
        )
        self.position = position

    async def callback(self, interaction: discord.Interaction):
        view: "TicTacToeView" = self.view

        if interaction.user not in (view.player_x, view.player_o):
            return await interaction.response.send_message(
                "You are not part of this game.",
                ephemeral=True
            )

        if interaction.user != view.current_player:
            return await interaction.response.send_message(
                "It is not your turn.",
                ephemeral=True
            )

        if view.board[self.position] is not None:
            return await interaction.response.send_message(
                "That spot is already taken.",
                ephemeral=True
            )

        await view.make_move(interaction, self.position, interaction.user)


class TicTacToeView(discord.ui.View):
    def __init__(self, player_x: discord.Member, player_o: discord.abc.User, bot_player: bool = False):
        super().__init__(timeout=120)
        self.player_x = player_x
        self.player_o = player_o
        self.current_player = player_x
        self.board = [None] * 9
        self.bot_player = bot_player
        self.message: Optional[discord.Message] = None

        for i in range(9):
            self.add_item(TicTacToeButton(i))

    def get_button(self, position: int) -> Optional[TicTacToeButton]:
        for item in self.children:
            if isinstance(item, TicTacToeButton) and item.position == position:
                return item
        return None

    def check_winner(self) -> Optional[str]:
        for a, b, c in TTT_WIN_COMBINATIONS:
            if self.board[a] and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]
        return None

    def is_draw(self) -> bool:
        return all(cell is not None for cell in self.board)

    def disable_all_buttons(self):
        for item in self.children:
            item.disabled = True

    def available_moves(self) -> list[int]:
        return [i for i, cell in enumerate(self.board) if cell is None]

    def choose_bot_move(self) -> int:
        for move in self.available_moves():
            self.board[move] = "O"
            if self.check_winner() == "O":
                self.board[move] = None
                return move
            self.board[move] = None

        for move in self.available_moves():
            self.board[move] = "X"
            if self.check_winner() == "X":
                self.board[move] = None
                return move
            self.board[move] = None

        if 4 in self.available_moves():
            return 4

        corners = [i for i in [0, 2, 6, 8] if i in self.available_moves()]
        if corners:
            return random.choice(corners)

        return random.choice(self.available_moves())

    async def make_move(self, interaction: discord.Interaction, position: int, player: discord.abc.User):
        symbol = "X" if player == self.player_x else "O"
        self.board[position] = symbol

        button = self.get_button(position)
        if button is not None:
            button.label = symbol
            button.disabled = True
            button.style = discord.ButtonStyle.danger if symbol == "X" else discord.ButtonStyle.success

        winner = self.check_winner()
        if winner:
            self.disable_all_buttons()
            await interaction.response.edit_message(
                embed=build_ttt_embed(f"🎉 {player.mention} wins!", self.player_x, self.player_o),
                view=self,
                content=None
            )
            self.stop()
            return

        if self.is_draw():
            self.disable_all_buttons()
            await interaction.response.edit_message(
                embed=build_ttt_embed("It is a draw.", self.player_x, self.player_o),
                view=self,
                content=None
            )
            self.stop()
            return

        self.current_player = self.player_o if self.current_player == self.player_x else self.player_x
        current_symbol = "X" if self.current_player == self.player_x else "O"

        await interaction.response.edit_message(
            embed=build_ttt_embed(
                f"It is now {self.current_player.mention}'s turn ({current_symbol}).",
                self.player_x,
                self.player_o
            ),
            view=self,
            content=None
        )

        if self.bot_player and self.current_player == self.player_o and self.message:
            await self.handle_bot_turn()

    async def handle_bot_turn(self):
        await asyncio.sleep(1)

        move = self.choose_bot_move()
        self.board[move] = "O"

        button = self.get_button(move)
        if button is not None:
            button.label = "O"
            button.disabled = True
            button.style = discord.ButtonStyle.success

        winner = self.check_winner()
        if winner:
            self.disable_all_buttons()
            await self.message.edit(
                embed=build_ttt_embed(f"🎉 {self.player_o.mention} wins!", self.player_x, self.player_o),
                view=self,
                content=None
            )
            self.stop()
            return

        if self.is_draw():
            self.disable_all_buttons()
            await self.message.edit(
                embed=build_ttt_embed("It is a draw.", self.player_x, self.player_o),
                view=self,
                content=None
            )
            self.stop()
            return

        self.current_player = self.player_x
        await self.message.edit(
            embed=build_ttt_embed(
                f"It is now {self.player_x.mention}'s turn (X).",
                self.player_x,
                self.player_o
            ),
            view=self,
            content=None
        )

    async def on_timeout(self):
        self.disable_all_buttons()
        if self.message:
            try:
                await self.message.edit(
                    embed=build_ttt_embed("Game timed out.", self.player_x, self.player_o),
                    view=self,
                    content=None
                )
            except Exception:
                pass

########################################################################################################################
# CONNECT 4 UI
########################################################################################################################

class Connect4Button(discord.ui.Button):
    def __init__(self, column: int, row: int):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=str(column + 1),
            row=row
        )
        self.column = column

    async def callback(self, interaction: discord.Interaction):
        await self.view.play_turn(interaction, self.column)


class Connect4View(discord.ui.View):
    ROWS = 6
    COLS = 7

    def __init__(self, bot: commands.Bot, author: discord.Member, opponent: discord.Member):
        super().__init__(timeout=180)
        self.bot = bot
        self.author = author
        self.opponent = opponent
        self.players = {1: author, 2: opponent}
        self.is_bot_game = opponent.id == bot.user.id
        self.current = 1
        self.board = [[0 for _ in range(self.COLS)] for _ in range(self.ROWS)]
        self.message: Optional[discord.Message] = None
        self.lock = asyncio.Lock()

        for col in range(self.COLS):
            button_row = 0 if col < 5 else 1
            self.add_item(Connect4Button(col, button_row))

    def render_board(self) -> str:
        pieces = {0: "⚫", 1: "🔴", 2: "🟡"}
        lines = ["".join(pieces[cell] for cell in row) for row in self.board]
        lines.append("1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣")
        return "\n".join(lines)

    def get_embed(self, title: str = "Connect 4", description: Optional[str] = None) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description if description else self.render_board(),
            colour=discord.Color.red() if self.current == 1 else discord.Color.gold()
        )
        if not description:
            current_player = self.players[self.current]
            piece = "🔴" if self.current == 1 else "🟡"
            embed.add_field(name="Turn", value=f"{current_player.mention} {piece}", inline=False)
            embed.add_field(
                name="Players",
                value=f"🔴 {self.author.mention} vs 🟡 {self.opponent.mention}",
                inline=False
            )
        return embed

    def available_columns(self) -> list[int]:
        return [c for c in range(self.COLS) if self.board[0][c] == 0]

    def drop_piece(self, col: int, player: int) -> Optional[int]:
        for row in range(self.ROWS - 1, -1, -1):
            if self.board[row][col] == 0:
                self.board[row][col] = player
                return row
        return None

    def check_winner(self, row: int, col: int, player: int) -> bool:
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
        for dr, dc in directions:
            count = 1
            for direction in (1, -1):
                r = row + dr * direction
                c = col + dc * direction
                while 0 <= r < self.ROWS and 0 <= c < self.COLS and self.board[r][c] == player:
                    count += 1
                    r += dr * direction
                    c += dc * direction
            if count >= 4:
                return True
        return False

    def disable_all(self):
        for child in self.children:
            child.disabled = True

    async def finish_game(self, winner: Optional[discord.abc.User] = None):
        self.disable_all()
        if winner is None:
            title = "Connect 4 - Draw"
            desc = f"{self.render_board()}\n\nIt's a draw!"
        else:
            title = "Connect 4 - Winner"
            desc = f"{self.render_board()}\n\n{winner.mention} wins!"

        await self.message.edit(embed=self.get_embed(title=title, description=desc), view=self)
        self.stop()

    async def bot_turn(self):
        await asyncio.sleep(1)
        valid = self.available_columns()
        if not valid:
            await self.finish_game()
            return

        col = random.choice(valid)
        row = self.drop_piece(col, 2)

        if self.check_winner(row, col, 2):
            await self.finish_game(winner=self.opponent)
            return

        if not self.available_columns():
            await self.finish_game()
            return

        self.current = 1
        await self.message.edit(embed=self.get_embed(), view=self)

    async def play_turn(self, interaction: discord.Interaction, column: int):
        async with self.lock:
            if interaction.user.id not in (self.author.id, self.opponent.id):
                return await interaction.response.send_message(
                    "This game is not yours.",
                    ephemeral=True
                )

            if interaction.user.id != self.players[self.current].id:
                return await interaction.response.send_message(
                    "It's not your turn.",
                    ephemeral=True
                )

            row = self.drop_piece(column, self.current)
            if row is None:
                return await interaction.response.send_message(
                    "That column is full.",
                    ephemeral=True
                )

            if self.check_winner(row, column, self.current):
                await interaction.response.defer()
                await self.finish_game(winner=self.players[self.current])
                return

            if not self.available_columns():
                await interaction.response.defer()
                await self.finish_game()
                return

            self.current = 2 if self.current == 1 else 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

            if self.is_bot_game and self.current == 2:
                await self.bot_turn()

    async def on_timeout(self):
        self.disable_all()
        if self.message:
            try:
                timeout_embed = self.get_embed(
                    title="Connect 4 - Timed Out",
                    description=f"{self.render_board()}\n\nGame ended due to inactivity."
                )
                await self.message.edit(embed=timeout_embed, view=self)
            except Exception:
                pass

class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

########################################################################################################################
# KITTY
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
# BUNNY
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
# ROLL
########################################################################################################################

    @commands.hybrid_command(name="roll", description="Rolls a die.")
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

########################################################################################################################
# SAY
########################################################################################################################

    @commands.command()
    async def say(self, ctx: commands.Context, *, text: str = None):
        if not text:
            embed = make_embed("Say", "Give me something to say.", discord.Color.red())
            return await ctx.send(embed=embed)

        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.HTTPException):
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

        result = data["results"][0]
        gif_url = result.get("url")
        anime_name = result.get("anime_name", "Unknown")

        embed = make_embed(
            "Hug",
            f"🤗 {ctx.author.mention} hugs {member.mention}!",
            discord.Color.pink()
        )
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

        result = data["results"][0]
        gif_url = result.get("url")
        anime_name = result.get("anime_name", "Unknown")

        embed = make_embed(
            "Slap",
            f"🖐️ {ctx.author.mention} slapped {member.mention}!",
            discord.Color.red()
        )
        embed.set_image(url=gif_url)
        embed.set_footer(
            text=f"Anime: {anime_name} • Requested by {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )
        await ctx.send(embed=embed)

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
                data = await resp.json()

        question_data = data["results"][0]
        question = html.unescape(question_data["question"])
        correct = html.unescape(question_data["correct_answer"])
        incorrect = [html.unescape(i) for i in question_data["incorrect_answers"]]

        answers = incorrect + [correct]
        random.shuffle(answers)

        letters = ["A", "B", "C", "D"]
        answer_map = dict(zip(letters, answers))

        description = "\n".join(f"**{letter}**. {answer}" for letter, answer in answer_map.items())

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
# FLAG
########################################################################################################################

    @commands.hybrid_command(name="flag", description="Starts a country flag guessing game.")
    async def flag(self, ctx: commands.Context):
        if ctx.interaction:
            await ctx.defer()

        try:
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

        except Exception as e:
            await ctx.send(f"Error: {e}")

########################################################################################################################
# ROCK PAPER SCISSORS
########################################################################################################################

    @commands.hybrid_command(name="rps", description="Starts a rock paper scissors game.")
    async def rps(self, ctx: commands.Context, opponent: discord.Member = None):
        if opponent == ctx.author:
            return await ctx.send("You can't play against yourself!")

        view = RPSView(self.bot, ctx.author, opponent)

        embed = make_embed(
            "Rock, Paper, Scissors",
            f"{ctx.author.mention} vs {'🤖 Bot' if view.pve else opponent.mention}\nChoose your move below!",
            discord.Color.blurple()
        )
        message = await ctx.send(embed=embed, view=view)
        view.message = message

########################################################################################################################
# TIC TAC TOE
########################################################################################################################

    @commands.hybrid_command(name="ttt", description="Play Tic Tac Toe.")
    async def ttt(self, ctx: commands.Context, opponent: discord.Member = None):
        if opponent is None:
            view = TicTacToeView(ctx.author, ctx.me, bot_player=True)
            message = await ctx.send(
                embed=build_ttt_embed(
                    f"It is now {ctx.author.mention}'s turn (X).",
                    ctx.author,
                    ctx.me
                ),
                view=view
            )
            view.message = message
            return

        if opponent.bot:
            return await ctx.send("You cannot use `;ttt @bot`. Use `;ttt` to play against me.")

        if opponent == ctx.author:
            return await ctx.send("You cannot play against yourself.")

        view = TicTacToeView(ctx.author, opponent, bot_player=False)
        message = await ctx.send(
            embed=build_ttt_embed(
                f"It is now {ctx.author.mention}'s turn (X).",
                ctx.author,
                opponent
            ),
            view=view
        )
        view.message = message

########################################################################################################################
# CONNECT 4
########################################################################################################################

    @commands.hybrid_command(name="connect4", aliases=["c4"], description="Play Connect 4.")
    async def connect4(self, ctx: commands.Context, opponent: discord.Member = None):
        if opponent is None:
            opponent = ctx.me

        if opponent == ctx.author:
            return await ctx.send("You cannot play against yourself.")

        if opponent.bot and opponent != ctx.me:
            return await ctx.send("You can only play against me, not another bot.")

        view = Connect4View(self.bot, ctx.author, opponent)
        message = await ctx.send(embed=view.get_embed(), view=view)
        view.message = message


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))