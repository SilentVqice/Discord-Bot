import discord
import time
import asyncio
import yt_dlp as youtube_dl
import yt_dlp.utils as ytdlp_utils
import re
import aiohttp
import os
import base64
from typing import Any, cast, Optional
from discord.ext import commands
from dotenv import load_dotenv
load_dotenv()

ytdlp_utils.bug_reports_message = lambda *args, **kwargs: ""

ytdl_format_options: dict[str, Any] = {
    "format": "bestaudio[acodec=opus]/bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "auto",
    "js_runtimes": {
        "node": {
            "path": r"C:\Program Files\nodejs\node.exe"
        }
    },
}

ffmpeg_options = {
    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_on_network_error 1 "
        "-reconnect_on_http_error 4xx,5xx "
        "-reconnect_delay_max 10"
    ),
    "options": "-vn"
}

ytdl = youtube_dl.YoutubeDL(cast(Any, ytdl_format_options))

spotify_track_url_re = re.compile(
    r"(?:https?://)?open\.spotify\.com/track/([A-Za-z0-9]+)(?:\?.*)?$"
)

spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

class GuildMusicState:
    def __init__(self):
        self.song_queue = []
        self.loop_song = False
        self.current_song = None
        self.skip_once = False
        self.now_playing_message = None
        self.now_playing_updater = None
        self.slowed_mode = False
        self.sped_mode = False
        self.bassboost_mode = False
        self.play_started_at = None
        self.paused_at = None
        self.autoplay_mode = False
        self.current_volume = 1.0
        self.paused_total = 0.0

class MusicControls(discord.ui.View):
    def __init__(self, cog, guild_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild_id = guild_id
        self.message = None
        self.refresh_button_labels()

    def get_state(self):
        return self.cog.get_state(self.guild_id)

    def get_loop_button_text(self) -> str:
        state = self.get_state()
        return f"Loop: {'On' if state.loop_song else 'Off'}"

    def get_mode_button_text(self) -> str:
        state = self.get_state()
        if state.slowed_mode:
            mode = "Slowed"
        elif state.sped_mode:
            mode = "Sped"
        else:
            mode = "Normal"
        return f"Mode: {mode}"

    def get_bassboost_button_text(self) -> str:
        state = self.get_state()
        return f"Bassboost: {'On' if state.bassboost_mode else 'Off'}"

    def get_autoplay_button_text(self) -> str:
        state = self.get_state()
        return f"Autoplay: {'On' if state.autoplay_mode else 'Off'}"

    def refresh_button_labels(self):
        self.loop_button.label = self.get_loop_button_text()
        self.mode_button.label = self.get_mode_button_text()
        self.bassboost_button.label = self.get_bassboost_button_text()
        self.autoplay_button.label = self.get_autoplay_button_text()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        vc = interaction.guild.voice_client if interaction.guild else None

        if not vc or not vc.channel:
            await interaction.response.send_message(
                embed=self.cog.warning_embed("I'm not in a voice channel.", title="Not Connected"),
                ephemeral=True
            )
            return False

        if not interaction.user.voice or interaction.user.voice.channel != vc.channel:
            await interaction.response.send_message(
                embed=self.cog.warning_embed(
                    "You must be in my voice channel to use these controls.",
                    title="Access Denied"
                ),
                ephemeral=True
            )
            return False

        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        self.refresh_button_labels()

        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

    @discord.ui.button(label="Pause/Resume", emoji="▶️", style=discord.ButtonStyle.primary, row=0)
    async def pause_resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.get_state()
        vc = interaction.guild.voice_client

        if not vc:
            return await interaction.response.send_message(
                embed=self.cog.warning_embed("Nothing is playing.", title="Nothing Playing"),
                ephemeral=True
            )

        if vc.is_paused():
            vc.resume()
            if state.paused_at is not None:
                state.paused_total += time.monotonic() - state.paused_at
                state.paused_at = None

        elif vc.is_playing():
            vc.pause()
            state.paused_at = time.monotonic()

        else:
            return await interaction.response.send_message(
                embed=self.cog.warning_embed("Nothing is playing.", title="Nothing Playing"),
                ephemeral=True
            )

        self.refresh_button_labels()
        await interaction.response.edit_message(
            embed=self.cog.build_now_playing_embed(state),
            view=self
        )

    @discord.ui.button(label="Skip", emoji="⏭️", style=discord.ButtonStyle.primary, row=0)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.get_state()
        vc = interaction.guild.voice_client

        if not vc or not (vc.is_playing() or vc.is_paused()):
            return await interaction.response.send_message(
                embed=self.cog.warning_embed("Nothing is playing.", title="Nothing Playing"),
                ephemeral=True
            )

        state.skip_once = True
        await interaction.response.defer()
        vc.stop()

    @discord.ui.button(label="Mode: Normal", emoji="⚙️", style=discord.ButtonStyle.primary, row=0)
    async def mode_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.get_state()
        vc = interaction.guild.voice_client

        if vc is None or state.current_song is None:
            return await interaction.response.send_message(
                embed=self.cog.warning_embed("Nothing is playing.", title="Nothing Playing"),
                ephemeral=True
            )

        if not state.slowed_mode and not state.sped_mode:
            state.slowed_mode = True
            state.sped_mode = False
        elif state.slowed_mode:
            state.slowed_mode = False
            state.sped_mode = True
        else:
            state.slowed_mode = False
            state.sped_mode = False

        ok, error = await self.cog.apply_current_mode_from_interaction(interaction)
        if not ok:
            return await interaction.response.send_message(
                embed=self.cog.error_embed(
                    error or "Couldn't change mode.",
                    title="Mode Change Failed"
                ),
                ephemeral=True
            )

        self.refresh_button_labels()
        await interaction.response.edit_message(
            embed=self.cog.build_now_playing_embed(state),
            view=self
        )

    @discord.ui.button(label="Loop: Off", emoji="🔁", style=discord.ButtonStyle.success, row=0)
    async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.get_state()
        state.loop_song = not state.loop_song

        self.refresh_button_labels()
        await interaction.response.edit_message(
            embed=self.cog.build_now_playing_embed(state),
            view=self
        )

    @discord.ui.button(label="Stop", emoji="⏹️", style=discord.ButtonStyle.danger, row=0)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.get_state()
        vc = interaction.guild.voice_client

        if not vc:
            return await interaction.response.send_message(
                embed=self.cog.warning_embed("Nothing is playing.", title="Nothing Playing"),
                ephemeral=True
            )

        if state.now_playing_updater:
            state.now_playing_updater.cancel()
            state.now_playing_updater = None

        state.now_playing_message = None
        state.song_queue.clear()
        state.current_song = None
        state.skip_once = False
        state.loop_song = False
        state.autoplay_mode = False
        state.slowed_mode = False
        state.sped_mode = False
        state.bassboost_mode = False
        state.current_volume = 1.0
        state.play_started_at = None
        state.paused_at = None
        state.paused_total = 0.0

        for item in self.children:
            item.disabled = True

        self.refresh_button_labels()
        await interaction.response.edit_message(
            embed=self.cog.info_embed("Playback stopped.", title="Stopped"),
            view=self
        )

        vc.stop()

        try:
            await vc.disconnect()
        except Exception:
            pass

    @discord.ui.button(label="Autoplay: Off", emoji="♾️", style=discord.ButtonStyle.primary, row=1)
    async def autoplay_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.get_state()
        state.autoplay_mode = not state.autoplay_mode

        self.refresh_button_labels()
        await interaction.response.edit_message(
            embed=self.cog.build_now_playing_embed(state),
            view=self
        )

    @discord.ui.button(label="Bassboost: Off", emoji="🔊", style=discord.ButtonStyle.primary, row=1)
    async def bassboost_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.get_state()
        vc = interaction.guild.voice_client

        if vc is None or state.current_song is None:
            return await interaction.response.send_message(
                embed=self.cog.warning_embed("Nothing is playing.", title="Nothing Playing"),
                ephemeral=True
            )

        state.bassboost_mode = not state.bassboost_mode

        ok, error = await self.cog.apply_current_mode_from_interaction(interaction)
        if not ok:
            return await interaction.response.send_message(
                embed=self.cog.error_embed(
                    error or "Couldn't change bassboost mode.",
                    title="Mode Change Failed"
                ),
                ephemeral=True
            )

        self.refresh_button_labels()
        await interaction.response.edit_message(
            embed=self.cog.build_now_playing_embed(state),
            view=self
        )

    @discord.ui.button(label="Queue", emoji="📂", style=discord.ButtonStyle.primary, row=1)
    async def queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.get_state()

        if not state.current_song and not state.song_queue:
            return await interaction.response.send_message(
                embed=self.cog.warning_embed("Queue is empty!", title="Empty Queue"),
                ephemeral=True
            )

        lines = []

        if state.current_song:
            lines.append(
                f"**Now Playing:**\n🎶 **[{state.current_song['title']}]({state.current_song['webpage_url']})**"
            )

        if state.song_queue:
            queue_text = "\n".join(
                f"`{i}.` **[{song['title']}]({song['webpage_url']})**"
                for i, song in enumerate(state.song_queue[:15], start=1)
            )
            if len(state.song_queue) > 15:
                queue_text += f"\n...and **{len(state.song_queue) - 15}** more."
            lines.append(f"**Up Next:**\n{queue_text}")
        else:
            lines.append("**Up Next:**\nNo songs queued.")

        embed = discord.Embed(
            title="🎼 Music Queue",
            description="\n\n".join(lines),
            colour=discord.Color.blurple()
        )
        embed.set_footer(
            text=f"Total queued: {len(state.song_queue)} | Loop: {'On' if state.loop_song else 'Off'}"
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Lyrics", emoji="🎤", style=discord.ButtonStyle.primary, row=1)
    async def lyrics_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.get_state()

        if state.current_song is None:
            return await interaction.response.send_message(
                embed=self.cog.warning_embed("Nothing is playing!", title="Lyrics Unavailable"),
                ephemeral=True
            )

        data = await self.cog.fetch_lyrics_data(state.current_song)
        if data is None:
            return await interaction.response.send_message(
                embed=self.cog.warning_embed(
                    "Couldn't find lyrics for the current track.",
                    title="Lyrics Not Found"
                ),
                ephemeral=True
            )

        await interaction.response.send_message(
            embed=self.cog.build_lyrics_embed(data),
            ephemeral=True
        )

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_states = {}

    def make_embed(self, description: str, colour: discord.Color, *, title: str | None = None) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description,
            colour=colour
        )
        embed.timestamp = discord.utils.utcnow()
        return embed

    def success_embed(self, description: str, *, title: str = "Success") -> discord.Embed:
        return self.make_embed(f"✅ {description}", discord.Color.green(), title=title)

    def error_embed(self, description: str, *, title: str = "Error") -> discord.Embed:
        return self.make_embed(f"❌ {description}", discord.Color.red(), title=title)

    def warning_embed(self, description: str, *, title: str = "Warning") -> discord.Embed:
        return self.make_embed(f"⚠️ {description}", discord.Color.orange(), title=title)

    def info_embed(self, description: str, *, title: str = "Info") -> discord.Embed:
        return self.make_embed(f"ℹ️ {description}", discord.Color.blurple(), title=title)

    def get_state(self, guild_id: int) -> GuildMusicState:
        if guild_id not in self.guild_states:
            self.guild_states[guild_id] = GuildMusicState()
        return self.guild_states[guild_id]

    async def apply_current_mode_from_interaction(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild.id)
        vc = interaction.guild.voice_client if interaction.guild else None

        if vc is None or state.current_song is None:
            return False, "Nothing is playing."

        if not (vc.is_playing() or vc.is_paused()):
            return False, "Nothing is playing."

        try:
            fresh_song = await self.get_song_info(state.current_song["url"])
        except Exception as e:
            return False, f"Couldn't reload the current track: {e}"

        audio_url = fresh_song.get("audio_url")
        if not audio_url:
            return False, "Couldn't rebuild the current stream."

        position = self.get_current_playback_position(state)
        was_paused = vc.is_paused()

        if was_paused:
            vc.resume()
            if state.paused_at is not None:
                state.paused_total += time.monotonic() - state.paused_at
                state.paused_at = None

        new_source = self.make_audio_source(
            audio_url,
            start_at=position,
            slowed=state.slowed_mode,
            sped=state.sped_mode,
            bassboost=state.bassboost_mode,
            volume=state.current_volume
        )

        vc.source = new_source

        state.play_started_at = time.monotonic() - position
        state.paused_at = None

        if was_paused:
            vc.pause()
            state.paused_at = time.monotonic()

        return True, None

    def is_spotify_track_url(self, query: str) -> bool:
        return bool(spotify_track_url_re.search(query.strip()))

    def extract_spotify_track_id(self, url: str) -> str | None:
        match = spotify_track_url_re.search(url.strip())
        if not match:
            return None
        return match.group(1)

    async def get_spotify_access_token(self) -> str:
        if not spotify_client_id or not spotify_client_secret:
            raise RuntimeError(
                "Spotify credentials are missing. Add SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET to your .env file."
            )

        auth_string = f"{spotify_client_id}:{spotify_client_secret}"
        encoded_auth = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "grant_type": "client_credentials"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://accounts.spotify.com/api/token",
                headers=headers,
                data=data
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"Spotify auth failed: {resp.status} - {error_text}")

                payload = await resp.json()
                token = payload.get("access_token")
                if not token:
                    raise RuntimeError(f"Spotify did not return an access token.")

                return token

    async def get_spotify_track_info(self, spotify_url: str) -> dict[str, Any]:
        track_id = self.extract_spotify_track_id(spotify_url)
        if not track_id:
            raise RuntimeError("Invalid Spotify track URL.")

        access_token = await self.get_spotify_access_token()

        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(f"https://api.spotify.com/v1/tracks/{track_id}") as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"Spotify track lookup failed: {resp.status} - {error_text}")

                data = await resp.json()

        artists = data.get("artists", [])
        artist_names = [artist.get("name") for artist in artists if artist.get("name")]
        artist_text = ", ".join(artist_names) if artist_names else "Unknown"

        album = data.get("album", {})
        images = album.get("images", [])
        thumbnail = images[0].get("url") if images else None

        duration_ms = data.get("duration_ms") or 0
        duration_seconds = int(duration_ms / 1000)

        return {
            "spotify_url": spotify_url,
            "title": data.get("name", "Unknown"),
            "artists": artist_names,
            "artist_text": artist_text,
            "duration": duration_seconds,
            "thumbnail": thumbnail,
            "search_query": f"{artist_text} - {data.get('name', 'Unknown')} audio",
        }

    async def resolve_spotify_to_youtube(self, spotify_url: str) -> dict[str, Any]:
        spotify_track = await self.get_spotify_track_info(spotify_url)
        youtube_song = await self.get_song_info(spotify_track["search_query"])

        youtube_url = youtube_song.get("webpage_url") or youtube_song.get("url")
        if not youtube_url:
            raise RuntimeError("Couldn't resolve the Spotify track to a playable YouTube result.")

        return {
            "query": spotify_url,
            "url": youtube_url,
            "title": spotify_track["title"],
            "webpage_url": youtube_url,
            "audio_url": youtube_song.get("audio_url"),
            "duration": spotify_track["duration"] or youtube_song.get("duration", 0),
            "thumbnail": spotify_track.get("thumbnail") or youtube_song.get("thumbnail"),
            "uploader": spotify_track["artist_text"],
            "views": youtube_song.get("views"),
            "likes": youtube_song.get("likes"),
            "spotify_url": spotify_url,
            "source_platform": "spotify",
        }

    async def get_song_info(self, query):
        loop = asyncio.get_running_loop()

        info = await loop.run_in_executor(
            None,
            lambda: ytdl.extract_info(query, download=False)
        )

        info = cast(dict[str, Any], info)

        entries = info.get("entries")
        if isinstance(entries, list) and entries:
            first = entries[0]
            if isinstance(first, dict):
                info = cast(dict[str, Any], first)

        webpage_url = info.get("webpage_url") or info.get("original_url") or query

        return {
            "query": query,
            "url": webpage_url,
            "title": info.get("title", "Unknown"),
            "webpage_url": webpage_url,
            "audio_url": info.get("url"),
            "duration": info.get("duration") or 0,
            "thumbnail": info.get("thumbnail"),
            "uploader": info.get("uploader") or info.get("channel") or "Unknown",
            "views": info.get("view_count"),
            "likes": info.get("like_count"),
        }

    async def get_autoplay_song(
        self,
        state: GuildMusicState,
        seed_song: dict[str, Any],
        requester=None
    ) -> dict[str, Any] | None:
        title = seed_song.get("title") or ""
        uploader = seed_song.get("uploader") or ""

        search_query = f"{title} {uploader}".strip()
        if not search_query:
            return None

        loop = asyncio.get_running_loop()

        try:
            info = await loop.run_in_executor(
                None,
                lambda: ytdl.extract_info(
                    f"ytsearch5:{search_query}",
                    download=False
                )
            )
        except Exception:
            return None

        info = cast(dict[str, Any], info)
        entries = info.get("entries")

        if not isinstance(entries, list):
            return None

        current_url = seed_song.get("webpage_url") or seed_song.get("url")
        queued_urls = {
            song.get("webpage_url") or song.get("url")
            for song in state.song_queue
        }

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            webpage_url = entry.get("webpage_url") or entry.get("original_url")
            if not webpage_url:
                continue

            if current_url and webpage_url == current_url:
                continue

            if webpage_url in queued_urls:
                continue

            return {
                "url": webpage_url,
                "title": entry.get("title", "Unknown"),
                "webpage_url": webpage_url,
                "thumbnail": entry.get("thumbnail"),
                "duration": entry.get("duration") or 0,
                "uploader": entry.get("uploader") or entry.get("channel") or "Unknown",
                "views": entry.get("view_count"),
                "likes": entry.get("like_count"),
                "requester": requester
            }

        return None

    def format_time(self, seconds: float | int) -> str:
        seconds = max(0, int(seconds))
        minutes, secs = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def build_progress_bar(self, position: float, duration: int, length: int = 16) -> str:
        if duration <= 0:
            return "🔴 LIVE"

        position = max(0.0, min(position, float(duration)))
        ratio = position / duration if duration else 0.0
        filled = int(ratio * length)

        if filled >= length:
            filled = length - 1

        return "█" * filled + "🔘" + "─" * (length - filled - 1)

    def get_mode_text(self, state: GuildMusicState) -> str:
        parts = []

        if state.slowed_mode:
            parts.append("Slowed")
        elif state.sped_mode:
            parts.append("Sped")

        if state.bassboost_mode:
            parts.append("BassBoost")

        return " + ".join(parts) if parts else "Normal"

    def get_current_playback_position(self, state: GuildMusicState) -> float:
        if state.play_started_at is None:
            return 0.0

        if state.paused_at is not None:
            elapsed = state.paused_at - state.play_started_at - state.paused_total
        else:
            elapsed = time.monotonic() - state.play_started_at - state.paused_total

        return max(0.0, elapsed)

    def make_audio_source(
            self,
            audio_url,
            *,
            start_at=0.0,
            slowed=False,
            sped=False,
            bassboost=False,
            volume=1.0
    ):
        before = ffmpeg_options["before_options"]
        if start_at and start_at > 0:
            before = f"{before} -ss {start_at:.2f}"

        filters = []

        if slowed:
            filters.extend([
                "atempo=0.92",
                "asetrate=48000*0.92",
                "aresample=48000",
                "aecho=0.7:0.75:30:0.05",
            ])
        elif sped:
            filters.extend([
                "atempo=1.08",
                "asetrate=48000*1.08",
                "aresample=48000",
                "treble=g=1.2:f=4500:width_type=o:width=1.0:m=0.35",
            ])
        else:
            filters.append("aresample=48000")

        if bassboost:
            filters.extend([
                "bass=g=2.5:f=90:width_type=o:width=1.2:m=0.35",
                "volume=0.90"
            ])

        options = f'-vn -filter:a "{",".join(filters)}"' if filters else "-vn"

        source = discord.FFmpegPCMAudio(
            audio_url,
            before_options=before,
            options=options
        )
        return discord.PCMVolumeTransformer(source, volume=volume)

    async def apply_current_mode(self, ctx):
        state = self.get_state(ctx.guild.id)
        vc = ctx.voice_client

        if vc is None or state.current_song is None:
            return False, "Nothing is playing."

        if not (vc.is_playing() or vc.is_paused()):
            return False, "Nothing is playing."

        try:
            fresh_song = await self.get_song_info(state.current_song["url"])
        except Exception as e:
            return False, f"Couldn't reload the current track: {e}"

        audio_url = fresh_song.get("audio_url")
        if not audio_url:
            return False, "Couldn't rebuild the current stream."

        position = self.get_current_playback_position(state)
        was_paused = vc.is_paused()

        if was_paused:
            vc.resume()
            if state.paused_at is not None:
                state.paused_total += time.monotonic() - state.paused_at
                state.paused_at = None

        new_source = self.make_audio_source(
            audio_url,
            start_at=position,
            slowed=state.slowed_mode,
            sped=state.sped_mode,
            bassboost=state.bassboost_mode,
            volume=state.current_volume
        )

        vc.source = new_source

        state.play_started_at = time.monotonic() - position
        state.paused_at = None

        if was_paused:
            vc.pause()
            state.paused_at = time.monotonic()

        return True, None

    def build_now_playing_embed(self, state: GuildMusicState) -> discord.Embed:
        song = state.current_song
        if song is None:
            return discord.Embed(title="Nothing Playing", description="No active track.")

        title = song.get("title", "Unknown")
        webpage_url = song.get("webpage_url", "")
        duration = song.get("duration") or 0
        thumbnail = song.get("thumbnail")
        uploader = song.get("uploader") or "Unknown"
        views = song.get("views")
        likes = song.get("likes")
        requester = song.get("requester")
        source_platform = song.get("source_platform", "youtube")

        position = self.get_current_playback_position(state)
        progress_bar = self.build_progress_bar(position, duration)
        duration_text = self.format_time(duration) if duration > 0 else "LIVE"
        elapsed_text = self.format_time(position)

        status_text = "Paused" if state.paused_at is not None else "Playing"
        mode_text = self.get_mode_text(state)

        embed = discord.Embed(
            title="🎶 Now Playing",
            description=f"**[{title}]({webpage_url})**" if webpage_url else f"**{title}**",
            colour=discord.Colour.red(),
            url=webpage_url if webpage_url else None
        )

        embed.add_field(name="⏱️ Duration", value=duration_text, inline=True)
        embed.add_field(name="📺 Uploader", value=uploader, inline=True)
        embed.add_field(name="▶️ Status", value=status_text, inline=True)

        embed.add_field(name="🔁 Loop", value="ON" if state.loop_song else "OFF", inline=True)
        embed.add_field(name="⚙️ Mode", value=mode_text, inline=True)
        embed.add_field(name="📂 Queue", value=str(len(state.song_queue)), inline=True)

        if views is not None:
            embed.add_field(name="👀 Views", value=f"{views:,}", inline=True)

        if likes is not None:
            embed.add_field(name="👍 Likes", value=f"{likes:,}", inline=True)

        if requester is not None:
            embed.add_field(name="🙋 Requester", value=requester.mention, inline=True)

        embed.add_field(
            name="📍 Progress",
            value=f"`{elapsed_text} / {duration_text}`\n`{progress_bar}`",
            inline=True
        )

        embed.add_field(name="♾️ Autoplay", value="ON" if state.autoplay_mode else "OFF", inline=True)

        embed.add_field(name="🔊 Bassboost", value="ON" if state.bassboost_mode else "OFF", inline=True)

        if thumbnail:
            embed.set_image(url=thumbnail)

        footer_text = "Use ;queue to view upcoming songs."
        if source_platform == "spotify":
            footer_text += " • Resolved from Spotify"

        embed.set_footer(text=footer_text)

        return embed

    async def update_now_playing_embed(self, guild_id: int):
        state = self.get_state(guild_id)

        if state.now_playing_message is None or state.current_song is None:
            return

        try:
            view = MusicControls(self, guild_id)
            view.message = state.now_playing_message

            await state.now_playing_message.edit(
                embed=self.build_now_playing_embed(state),
                view=view
            )
        except Exception as e:
            print(f"Failed to update now playing embed: {e}")

    async def now_playing_progress_loop(self, guild_id: int, song_url: str):
        state = self.get_state(guild_id)

        while True:
            await asyncio.sleep(5)

            if state.now_playing_message is None or state.current_song is None:
                break

            if state.current_song.get("url") != song_url:
                break

            message = state.now_playing_message
            if message.guild is None:
                break

            vc = message.guild.voice_client
            if vc is None or not vc.is_connected():
                break

            if not (vc.is_playing() or vc.is_paused()):
                break

            try:
                await self.update_now_playing_embed(guild_id)
            except Exception:
                break

    def clean_lyrics_title(self, title: str) -> str:
        title = re.sub(
            r"\s*[\[(](?:official|lyrics?|lyric video|audio|video|visualizer|sped up|slowed|reverb|nightcore).*?[\])]",
            "",
            title,
            flags=re.IGNORECASE,
        )
        title = title.replace("|", "-")
        return " ".join(title.split()).strip(" -")

    def guess_artist_and_track(self, song: dict[str, Any]) -> tuple[str, str]:
        raw_title = self.clean_lyrics_title(song.get("title") or "")
        uploader = (song.get("uploader") or "").replace(" - Topic", "").replace("VEVO", "").strip()

        if " - " in raw_title:
            artist, track = raw_title.split(" - ", 1)
            artist = artist.strip()
            track = track.strip()
            if artist and track:
                return artist, track

        return uploader, raw_title

    async def fetch_lyrics_data(self, song: dict[str, Any]) -> dict[str, str] | None:
        artist, track = self.guess_artist_and_track(song)
        duration = int(song.get("duration") or 0)

        headers = {"User-Agent": "DiscordMusicBot/1.0"}

        async with aiohttp.ClientSession(headers=headers) as session:
            params = {"track_name": track}
            if artist:
                params["artist_name"] = artist
            if duration > 0:
                params["duration"] = duration

            async with session.get("https://lrclib.net/api/get", params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    lyrics = data.get("plainLyrics") or data.get("syncedLyrics")
                    if lyrics:
                        return {
                            "artist": data.get("artistName") or artist or "Unknown",
                            "track": data.get("trackName") or track or song.get("title", "Unknown"),
                            "lyrics": lyrics.strip(),
                        }

            search_params = {"track_name": track}
            if artist:
                search_params["artist_name"] = artist

            async with session.get("https://lrclib.net/api/search", params=search_params) as resp:
                if resp.status == 200:
                    results = await resp.json()
                    if isinstance(results, list):
                        for item in results:
                            lyrics = item.get("plainLyrics") or item.get("syncedLyrics")
                            if lyrics:
                                return {
                                    "artist": item.get("artistName") or artist or "Unknown",
                                    "track": item.get("trackName") or track or song.get("title", "Unknown"),
                                    "lyrics": lyrics.strip(),
                                }

        return None

    def trim_lyrics(self, text: str, limit: int = 3500) -> tuple[str, bool]:
        text = text.strip()
        if len(text) <= limit:
            return text, False
        return text[: limit - 3].rstrip() + "...", True

    def build_lyrics_embed(self, data: dict[str, str]) -> discord.Embed:
        lyrics_text, was_trimmed = self.trim_lyrics(data["lyrics"])

        embed = discord.Embed(
            title=f"🎤 Lyrics — {data['track']}",
            description=lyrics_text,
            colour=discord.Color.purple(),
        )
        embed.add_field(name="Artist", value=data["artist"], inline=True)

        if was_trimmed:
            embed.set_footer(text="Lyrics were truncated to fit in one message.")

        return embed

    @commands.hybrid_command(name="autoplay", description="Toggles autoplay mode.")
    async def autoplay(self, ctx: commands.Context, mode: Optional[str] = None):
        state = self.get_state(ctx.guild.id)

        if mode is None:
            state.autoplay_mode = not state.autoplay_mode
        else:
            mode = mode.lower().strip()
            if mode in ("on", "true", "yes", "1"):
                state.autoplay_mode = True
            elif mode in ("off", "false", "no", "0"):
                state.autoplay_mode = False
            else:
                return await ctx.send(embed=self.warning_embed("Use `;autoplay`, `;autoplay on`, or `;autoplay off`.", title="Invalid Usage"))

        await ctx.send(embed=self.info_embed(f"Autoplay is now **{'ON' if state.autoplay_mode else 'OFF'}**.", title="Autoplay Updated"))
        await self.update_now_playing_embed(ctx.guild.id)

    @commands.hybrid_command(name="play", description="Adds a song to the queue or starts playback.")
    async def play(self, ctx: commands.Context, *, query: str):
        if ctx.interaction:
            await ctx.defer()

        state = self.get_state(ctx.guild.id)

        if not ctx.author.voice:
            return await ctx.send(
                embed=self.warning_embed("You must be in a voice channel!", title="Voice Required")
            )

        if ctx.voice_client and ctx.voice_client.channel != ctx.author.voice.channel:
            return await ctx.send(
                embed=self.warning_embed(
                    f"I'm already being used in **{ctx.voice_client.channel}**.",
                    title="Bot Is Busy"
                )
            )

        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()
            await asyncio.sleep(0.5)

        try:
            if self.is_spotify_track_url(query):
                song = await self.resolve_spotify_to_youtube(query)
            else:
                song = await self.get_song_info(query)
        except Exception as e:
            return await ctx.send(
                embed=self.error_embed(
                    f"Couldn't load this track:\n```py\n{e}\n```",
                    title="Track Load Failed"
                )
            )

        queue_song = {
            "url": song.get("url") or song.get("webpage_url"),
            "title": song.get("title", "Unknown"),
            "webpage_url": song.get("webpage_url"),
            "thumbnail": song.get("thumbnail"),
            "duration": song.get("duration", 0),
            "uploader": song.get("uploader", "Unknown"),
            "views": song.get("views"),
            "likes": song.get("likes"),
            "requester": ctx.author,
            "spotify_url": song.get("spotify_url"),
            "source_platform": song.get("source_platform", "youtube"),
        }

        state.song_queue.append(queue_song)

        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            await ctx.send(
                embed=self.success_embed(
                    f"Added to queue: **[{song['title']}]({song['webpage_url']})**",
                    title="Queued"
                )
            )
        else:
            await self.play_next(ctx)

    async def play_next(self, ctx):
        state = self.get_state(ctx.guild.id)

        if not ctx.voice_client or not ctx.voice_client.is_connected():
            return

        if state.loop_song and state.current_song and not state.skip_once:
            queued_song = state.current_song
        else:
            state.skip_once = False

            if not state.song_queue:
                if state.autoplay_mode and state.current_song is not None:
                    auto_song = await self.get_autoplay_song(
                        state,
                        state.current_song,
                        requester=ctx.guild.me if ctx.guild else None
                    )
                    if auto_song is not None:
                        state.song_queue.append(auto_song)

                if not state.song_queue:
                    state.current_song = None

                    if state.now_playing_updater:
                        state.now_playing_updater.cancel()
                        state.now_playing_updater = None

                    state.now_playing_message = None

                    await ctx.voice_client.disconnect()
                    await ctx.channel.send(
                        embed=self.info_embed(
                            "Queue finished. Disconnected from the voice channel.",
                            title="Disconnected"
                        )
                    )
                    return

            queued_song = state.song_queue.pop(0)

        try:
            track_url = queued_song.get("url") or queued_song.get("webpage_url")

            if not track_url:
                await ctx.send(
                    embed=self.error_embed("This queued track has no playable URL.", title="Playback Failed")
                )
                return

            if self.is_spotify_track_url(track_url):
                await ctx.send(
                    embed=self.error_embed(
                        "A Spotify link was sent to the playback loader instead of a resolved YouTube link.",
                        title="Playback Failed"
                    )
                )
                return

            fresh_song = await self.get_song_info(track_url)
        except Exception as e:
            await ctx.send(embed=self.error_embed(f"Couldn't load this track:\n```py\n{e}\n```", title="Track Load Failed"))
            return

        audio_url = fresh_song.get("audio_url")
        if not audio_url:
            await ctx.send(embed=self.error_embed("Couldn't get a playable stream for this track.", title="Playback Failed"))
            return

        state.current_song = {
            "url": fresh_song.get("url", queued_song.get("url")),
            "title": fresh_song.get("title", queued_song.get("title", "Unknown")),
            "webpage_url": fresh_song.get("webpage_url", queued_song.get("webpage_url", "")),
            "thumbnail": fresh_song.get("thumbnail", queued_song.get("thumbnail")),
            "duration": fresh_song.get("duration", queued_song.get("duration", 0)),
            "uploader": fresh_song.get("uploader", queued_song.get("uploader", "Unknown")),
            "views": fresh_song.get("views", queued_song.get("views")),
            "likes": fresh_song.get("likes", queued_song.get("likes")),
            "requester": queued_song.get("requester"),
            "source_platform": queued_song.get("source_platform", "youtube"),
        }

        source = self.make_audio_source(
            audio_url,
            slowed=state.slowed_mode,
            sped=state.sped_mode,
            bassboost=state.bassboost_mode,
            volume=state.current_volume
        )

        def after_playback(error):
            if error:
                print(f"Playback error: {error}")

            if ctx.voice_client and ctx.voice_client.is_connected():
                future = asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)
                try:
                    future.result()
                except Exception as e:
                    print(f"Error in play_next: {e}")

        if not ctx.voice_client or not ctx.voice_client.is_connected():
            return

        ctx.voice_client.play(source, after=after_playback)

        state.play_started_at = time.monotonic()
        state.paused_at = None
        state.paused_total = 0.0

        if state.now_playing_updater:
            state.now_playing_updater.cancel()
            state.now_playing_updater = None

        if state.now_playing_message:
            try:
                await state.now_playing_message.delete()
            except Exception:
                pass

        view = MusicControls(self, ctx.guild.id)
        state.now_playing_message = await ctx.channel.send(
            embed=self.build_now_playing_embed(state),
            view=view
        )
        view.message = state.now_playing_message

        state.now_playing_updater = asyncio.create_task(
            self.now_playing_progress_loop(ctx.guild.id, state.current_song["url"])
        )

    @commands.hybrid_command(name="pause", description="Pauses the current song.")
    async def pause(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)

        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            state.paused_at = time.monotonic()
            await ctx.send(embed=self.info_embed("Playback has been paused.", title="Paused"))
            await self.update_now_playing_embed(ctx.guild.id)
        else:
            await ctx.send(embed=self.warning_embed("No song is playing!", title="Nothing Playing"))

    @commands.hybrid_command(name="resume", description="Resumes the paused song.")
    async def resume(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)

        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            if state.paused_at is not None:
                state.paused_total += time.monotonic() - state.paused_at
                state.paused_at = None
            await ctx.send(embed=self.success_embed("Playback has been resumed.", title="Resumed"))
            await self.update_now_playing_embed(ctx.guild.id)
        else:
            await ctx.send(embed=self.warning_embed("No song is paused!", title="Nothing Paused"))

    @commands.hybrid_command(name="skip", description="Skips the current song.")
    async def skip(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)

        if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
            state.skip_once = True
            ctx.voice_client.stop()
            await ctx.send(embed=self.info_embed("Skipped the song.", title="Skipped"))
        else:
            await ctx.send(embed=self.warning_embed("Nothing is playing!", title="Nothing Playing"))

    @commands.hybrid_command(name="queue", description="See the list of songs in the queue.")
    async def queue(self, ctx):
        state = self.get_state(ctx.guild.id)

        if not state.current_song and not state.song_queue:
            return await ctx.send(
                embed=self.warning_embed("Queue is empty!", title="Empty Queue")
            )

        lines = []

        if state.current_song:
            lines.append(
                f"**Now Playing:**\n🎶 **[{state.current_song['title']}]({state.current_song['webpage_url']})**")

        if state.song_queue:
            queue_text = "\n".join(
                f"`{i}.` **[{song['title']}]({song['webpage_url']})**"
                for i, song in enumerate(state.song_queue, start=1)
            )
            lines.append(f"**Up Next:**\n{queue_text}")
        else:
            lines.append("**Up Next:**\nNo songs queued.")

        embed = discord.Embed(
            title="🎼 Music Queue",
            description="\n\n".join(lines),
            colour=discord.Color.blurple()
        )
        embed.set_footer(text=f"Total queued: {len(state.song_queue)} | Loop: {'On' if state.loop_song else 'Off'}")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="shuffle", description="Shuffles the current queue.")
    async def shuffle(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)

        if len(state.song_queue) < 2:
            return await ctx.send(
                embed=self.warning_embed("You need at least 2 songs in the queue to shuffle it.",
                                         title="Not Enough Songs")
            )

        import random
        random.shuffle(state.song_queue)

        await ctx.send(
            embed=self.success_embed("The queue has been shuffled.", title="Queue Shuffled")
        )
        await self.update_now_playing_embed(ctx.guild.id)

    @commands.hybrid_command(name="join", description="Joins your current voice channel.")
    async def join(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send(
                embed=self.warning_embed("You must be in a voice channel!", title="Voice Required")
            )

        if ctx.voice_client:
            if ctx.voice_client.channel == ctx.author.voice.channel:
                return await ctx.send(
                    embed=self.info_embed("I'm already in your voice channel.", title="Already Connected")
                )

            await ctx.voice_client.move_to(ctx.author.voice.channel)
            return await ctx.send(
                embed=self.success_embed(f"Moved to **{ctx.author.voice.channel}**.", title="Voice Connected")
            )

        await ctx.author.voice.channel.connect()
        await ctx.send(
            embed=self.success_embed(f"Joined **{ctx.author.voice.channel}**.", title="Voice Connected")
        )

    @commands.hybrid_command(name="leave", description="Stops playback and disconnects from voice.")
    async def leave(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)

        if not ctx.voice_client or not ctx.voice_client.is_connected():
            return await ctx.send(embed=self.warning_embed("I'm not in a voice channel.", title="Not Connected"))

        if state.now_playing_updater:
            state.now_playing_updater.cancel()
            state.now_playing_updater = None

        state.now_playing_message = None
        state.song_queue.clear()
        state.current_song = None
        state.skip_once = False
        state.loop_song = False
        state.autoplay_mode = False
        state.slowed_mode = False
        state.sped_mode = False
        state.bassboost_mode = False
        state.current_volume = 1.0
        state.play_started_at = None
        state.paused_at = None
        state.paused_total = 0.0

        await ctx.voice_client.disconnect()
        await ctx.send(embed=self.info_embed("Disconnected from the voice channel.", title="Disconnected"))

    @commands.hybrid_command(name="loop", description="Toggles looping for the current song.")
    async def loop(self, ctx: commands.Context, mode: Optional[str] = None):
        state = self.get_state(ctx.guild.id)

        if mode is None:
            state.loop_song = not state.loop_song
        else:
            mode = mode.lower().strip()
            if mode in ("on", "true", "yes", "1"):
                state.loop_song = True
            elif mode in ("off", "false", "no", "0"):
                state.loop_song = False
            else:
                return await ctx.send(embed=self.warning_embed("Use `;loop`, `;loop on`, or `;loop off`.", title="Invalid Usage"))

        await ctx.send(embed=self.info_embed(f"Loop is now **{'ON' if state.loop_song else 'OFF'}**.", title="Loop Updated"))
        await self.update_now_playing_embed(ctx.guild.id)

    @commands.hybrid_command(name="volume", description="Sets playback volume.")
    async def volume(self, ctx: commands.Context, volume: int):
        state = self.get_state(ctx.guild.id)

        if volume < 0 or volume > 200:
            return await ctx.send(embed=self.warning_embed("Volume must be between `0` and `200`.", title="Invalid Volume"))

        state.current_volume = volume / 100

        if ctx.voice_client and ctx.voice_client.source:
            if isinstance(ctx.voice_client.source, discord.PCMVolumeTransformer):
                ctx.voice_client.source.volume = state.current_volume
            else:
                ctx.voice_client.source = discord.PCMVolumeTransformer(
                    ctx.voice_client.source,
                    volume=state.current_volume
                )

            await ctx.send(embed=self.success_embed(f"Volume set to {volume}%.", title="Volume Updated"))
            await self.update_now_playing_embed(ctx.guild.id)
        else:
            await ctx.send(embed=self.warning_embed("No song is playing!", title="Nothing Playing"))

    @commands.hybrid_command(name="slowed", description="Toggles slowed mode.")
    async def slowed(self, ctx: commands.Context, mode: Optional[str] = None):
        state = self.get_state(ctx.guild.id)

        if mode is None:
            state.slowed_mode = not state.slowed_mode
        else:
            mode = mode.lower().strip()
            if mode in ("on", "true", "yes", "1"):
                state.slowed_mode = True
            elif mode in ("off", "false", "no", "0"):
                state.slowed_mode = False
            else:
                return await ctx.send(
                    embed=self.warning_embed(
                        "Use `;slowed`, `;slowed on`, or `;slowed off`.",
                        title="Invalid Usage"
                    )
                )

        if state.slowed_mode:
            state.sped_mode = False

        if ctx.voice_client and state.current_song:
            ok, error = await self.apply_current_mode(ctx)
            if not ok:
                return await ctx.send(
                    embed=self.error_embed(
                        error or "Couldn't apply slowed mode.",
                        title="Mode Change Failed"
                    )
                )

        await ctx.send(
            embed=self.info_embed(
                f"Slowed mode is now **{'ON' if state.slowed_mode else 'OFF'}**.",
                title="Mode Updated"
            )
        )
        await self.update_now_playing_embed(ctx.guild.id)

    @commands.hybrid_command(name="sped", description="Toggles sped mode.")
    async def sped(self, ctx: commands.Context, mode: Optional[str] = None):
        state = self.get_state(ctx.guild.id)

        if mode is None:
            state.sped_mode = not state.sped_mode
        else:
            mode = mode.lower().strip()
            if mode in ("on", "true", "yes", "1"):
                state.sped_mode = True
            elif mode in ("off", "false", "no", "0"):
                state.sped_mode = False
            else:
                return await ctx.send(
                    embed=self.warning_embed(
                        "Use `;sped`, `;sped on`, or `;sped off`.",
                        title="Invalid Usage"
                    )
                )

        if state.sped_mode:
            state.slowed_mode = False

        if ctx.voice_client and state.current_song:
            ok, error = await self.apply_current_mode(ctx)
            if not ok:
                return await ctx.send(
                    embed=self.error_embed(
                        error or "Couldn't apply sped mode.",
                        title="Mode Change Failed"
                    )
                )

        await ctx.send(
            embed=self.info_embed(
                f"Sped mode is now **{'ON' if state.sped_mode else 'OFF'}**.",
                title="Mode Updated"
            )
        )
        await self.update_now_playing_embed(ctx.guild.id)

    @commands.hybrid_command(name="bassboost", description="Toggles bassboost mode.")
    async def bassboost(self, ctx: commands.Context, mode: Optional[str] = None):
        state = self.get_state(ctx.guild.id)

        if mode is None:
            state.bassboost_mode = not state.bassboost_mode
        else:
            mode = mode.lower().strip()
            if mode in ("on", "true", "yes", "1"):
                state.bassboost_mode = True
            elif mode in ("off", "false", "no", "0"):
                state.bassboost_mode = False
            else:
                return await ctx.send(
                    embed=self.warning_embed(
                        "Use `;bassboost`, `;bassboost on`, or `;bassboost off`.",
                        title="Invalid Usage"
                    )
                )

        if ctx.voice_client and state.current_song:
            ok, error = await self.apply_current_mode(ctx)
            if not ok:
                return await ctx.send(
                    embed=self.error_embed(
                        error or "Couldn't apply bassboost mode.",
                        title="Mode Change Failed"
                    )
                )

        await ctx.send(
            embed=self.info_embed(
                f"BassBoost mode is now **{'ON' if state.bassboost_mode else 'OFF'}**.",
                title="Mode Updated"
            )
        )
        await self.update_now_playing_embed(ctx.guild.id)

    @commands.hybrid_command(name="clear", description="Clears the queue.")
    async def clear(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)

        if not state.song_queue:
            return await ctx.send(embed=self.warning_embed("Queue is already empty!", title="Empty Queue"))

        cleared = len(state.song_queue)
        state.song_queue.clear()
        await ctx.send(embed=self.info_embed(f"Cleared **{cleared}** song(s) from the queue.", title="Queue Cleared"))
        await self.update_now_playing_embed(ctx.guild.id)

    @commands.hybrid_command(name="remove", description="Removes a song from the queue.")
    async def remove(self, ctx: commands.Context, position: int):
        state = self.get_state(ctx.guild.id)

        if not state.song_queue:
            return await ctx.send(embed=self.warning_embed("Queue is empty!", title="Empty Queue"))

        if position < 1 or position > len(state.song_queue):
            return await ctx.send(embed=self.warning_embed(f"Choose a number between `1` and `{len(state.song_queue)}`.", title="Invalid Queue Position"))

        removed_song = state.song_queue.pop(position - 1)
        await ctx.send(embed=self.info_embed(f"Removed **{removed_song['title']}** from the queue.", title="Removed"))
        await self.update_now_playing_embed(ctx.guild.id)

    @commands.hybrid_command(name="lyrics", description="Shows lyrics for the current track.")
    async def lyrics(self, ctx: commands.Context):
        if ctx.interaction:
            await ctx.defer(ephemeral=True)

        state = self.get_state(ctx.guild.id)

        if state.current_song is None:
            return await ctx.send(
                embed=self.warning_embed("Nothing is playing!", title="Lyrics Unavailable"),
                ephemeral=True
            )

        data = await self.fetch_lyrics_data(state.current_song)
        if data is None:
            return await ctx.send(
                embed=self.warning_embed(
                    "Couldn't find lyrics for the current track.",
                    title="Lyrics Not Found"
                ),
                ephemeral=True
            )

        await ctx.send(embed=self.build_lyrics_embed(data), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Music(bot))