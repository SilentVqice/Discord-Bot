import random

import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands import Context

class Connect4():
    def __init__(self, players) -> None:
        self.players = players
        self.turn = 0
        self.board = [[] for _ in range(0, 7)]
        self.emoji = ["⚫", "🟣", "🟠"]
        self.winner = None

    def in_bounds(self, x: int, y: int) -> bool:
        return (x in range(0, 7)) and (y in range(0, 6))

    def get_cell(self, x: int, y: int) -> int:
        if self.in_bounds(x, y):
            try:
                return self.board[y][x]
            except IndexError:
                return 0
        else:
            return 0

    def get_board(self) -> discord.Embed:
        board = "```"
        for row in range(6, 0, -1):
            for column in self.board:
                cell = column[row - 1] if len(column) >= row else 0
                board += self.emoji[cell]
            board += '\n'
        board += "1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣```"
        player = f"\nCurrent turn: {self.players[self.turn % 2].display_name}"
        embed = discord.Embed(title = "Connect 4", description = board, color = 0xedb8cc)
        embed.set_footer(text = player)
        return embed

    def get_winner(self) -> discord.Embed:
        embed = self.get_board()
        embed.remove_footer()
        if self.winner == 0:
            embed.add_field(name = "Stalemate", value = ":(")
        else:
            embed.add_field(name = "Winner", value = self.players[self.winner - 1].display_name)
        return embed

    def check_win(self) -> int:
        def vertical(x: int, y: int):
            counts = [0] * 3
            for yo in range(0, 4):
                counts[self.get_cell(x, y + yo)] += 1 
            most = max(counts)
            if most == 4:
                return counts.index(most)

        def horizontal(x: int, y: int):
            counts = [0] * 3
            for xo in range(0, 4):
                counts[self.get_cell(x + xo, y)] += 1 
            most = max(counts)
            if most == 4:
                return counts.index(most)

        def diagonal_right(x: int, y: int):
            counts = [0] * 3
            for o in range(0, 4):
                counts[self.get_cell(x + o, y + o)] += 1 
            most = max(counts)
            if most == 4:
                return counts.index(most)

        def diagonal_left(x: int, y: int):
            counts = [0] * 3
            for o in range(0, 4):
                counts[self.get_cell(x - o, y + o)] += 1 
            most = max(counts)
            if most == 4:
                return counts.index(most)

        for x in range(0, 7):
            for y in range(0, 6):
                winner = vertical(x, y) or horizontal(x, y) or diagonal_left(x, y) or diagonal_right(x, y)
                if winner != None and winner != 0:
                    return winner
        for x in range(0, 7):
            for y in range(0, 6):
                if self.get_cell(x, y) == 0:
                    return None
        return 0


    def step(self, column: int) -> bool:
        if len(self.board[column]) >= 6:
            return False

        self.board[column].append(self.turn % 2 + 1)

        return True

    async def interact(self, interaction: discord.Interaction, column: int) -> None:
        if not any([p.id == interaction.user.id for p in self.players]):
            await interaction.response.send_message("You aren't a part of the game.", ephemeral = True)
            return
        if self.players[self.turn % 2].id != interaction.user.id:
            await interaction.response.send_message("It's not your turn.", ephemeral = True)
            return

        if self.step(column):
            self.turn += 1

        self.winner = self.check_win()

        if self.winner != None:
            await interaction.response.edit_message(
                embed = self.get_winner(),
                view = None
            )
        else:
            await interaction.response.edit_message(
                embed = self.get_board()
            )

class Connect4View(discord.ui.View):
    def __init__(self, players) -> None:
        super().__init__()
        self.game = Connect4(players)
        self.value = None

    @discord.ui.button(label="1", style=discord.ButtonStyle.blurple)
    async def one(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.game.interact(interaction, 0)

    @discord.ui.button(label="2", style=discord.ButtonStyle.blurple)
    async def two(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.game.interact(interaction, 1)

    @discord.ui.button(label="3", style=discord.ButtonStyle.blurple)
    async def three(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.game.interact(interaction, 2)

    @discord.ui.button(label="4", style=discord.ButtonStyle.blurple)
    async def four(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.game.interact(interaction, 3)

    @discord.ui.button(label="5", style=discord.ButtonStyle.blurple)
    async def five(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.game.interact(interaction, 4)

    @discord.ui.button(label="6", style=discord.ButtonStyle.blurple)
    async def six(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.game.interact(interaction, 5)

    @discord.ui.button(label="7", style=discord.ButtonStyle.blurple)
    async def seven(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.game.interact(interaction, 6)

class Connectfour(commands.Cog, name="connectfour"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="connect4", description=":3", aliases = ["Connect4", "C4", "c4", "connect4"]
    )
    async def connect4(self, context: Context, opponent: discord.Member) -> None:
        players = [context.author, opponent]
        view = Connect4View(players)
        embed = view.game.get_board()
        await context.send(embed = embed, view = view)

async def setup(bot) -> None:
    await bot.add_cog(Connectfour(bot))