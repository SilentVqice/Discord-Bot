import io
import json
import os
from pathlib import Path
from typing import Optional
import discord
from PIL import Image, ImageFont, ImageOps
from discord import AllowedMentions
from discord.ext import commands
from utils.emojis import EMOJIS

class AssetButtons(discord.ui.View):
    def __init__(self, urls: dict[str, str]):
        super().__init__(timeout=180)

        for label, url in urls.items():
            self.add_item(discord.ui.Button(label=label, url=url))

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

########################################################################################################################
# HELPERS
########################################################################################################################

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

########################################################################################################################
# EVENTS
########################################################################################################################

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

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
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

########################################################################################################################
# COMMANDS
########################################################################################################################

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
            icon_url=member.display_avatar.url
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Username", value=str(member), inline=True)
        embed.add_field(name="User ID", value=member.id, inline=False)
        embed.add_field(name="Account Created", value=created, inline=True)
        embed.add_field(name="Joined Server", value=joined, inline=True)
        embed.add_field(name=f"Roles [{roles_count}]", value=roles_display, inline=False)

        await ctx.send(mention_author=True, embed=embed, allowed_mentions=allowed)

    @commands.hybrid_command(name="avatar", description="Get a user's avatar.")
    async def avatar(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None
    ):
        member = member or ctx.author

        server_avatar = member.guild_avatar
        global_avatar = member.avatar or member.display_avatar

        embed = discord.Embed(colour=discord.Color.blurple())

        embed.set_author(
            name=f"{member}",
            icon_url=member.display_avatar.url
        )

        embed.title = (
            f"**Global Avatar** {EMOJIS['arrow_right']}\n"
            f"**Server Avatar** {EMOJIS['arrow_down']}"
        )

        if server_avatar:
            embed.set_image(url=server_avatar.url)
            embed.set_thumbnail(url=global_avatar.url)
        else:
            embed.set_image(url=global_avatar.url)

        embed.set_footer(
            text=f"Requested by {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )

        urls = {}

        if global_avatar.is_animated():
            urls["Global GIF"] = global_avatar.replace(format="gif", size=1024).url
        else:
            urls["Global PNG"] = global_avatar.replace(format="png", size=1024).url

        if server_avatar:
            if server_avatar.is_animated():
                urls["Server GIF"] = server_avatar.replace(format="gif", size=1024).url
            else:
                urls["Server PNG"] = server_avatar.replace(format="png", size=1024).url

        view = AssetButtons(urls)

        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="banner", description="Get a user's banner.")
    async def banner(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None
    ):
        member = member or ctx.author

        user = await self.bot.fetch_user(member.id)
        banner_asset = user.banner

        if not banner_asset:
            embed = discord.Embed(
                description=f"{member.mention} does not have a banner set.",
                colour=discord.Color.red()
            )

            if ctx.interaction:
                await ctx.interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                msg = await ctx.send(embed=embed)
                await msg.delete(delay=5)
            return

        embed = discord.Embed(colour=discord.Color.blurple())

        embed.set_author(
            name=f"{member}",
            icon_url=member.display_avatar.url
        )

        embed.title = "**Banner**"

        embed.set_image(url=banner_asset.url)

        embed.set_footer(
            text=f"Requested by {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )

        urls = {"PNG": banner_asset.replace(format="png", size=1024).url}

        if banner_asset.is_animated():
            urls["GIF"] = banner_asset.replace(format="gif", size=1024).url

        view = AssetButtons(urls)

        if ctx.interaction:
            await ctx.interaction.response.send_message(embed=embed, view=view)
        else:
            await ctx.send(embed=embed, view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))