import asyncio
import os
import re
from dataclasses import dataclass, field

import discord
import yt_dlp
from dotenv import load_dotenv


load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

TIKTOK_REGEX = re.compile(r"(https?://(?:www\.|vm\.|vt\.)?tiktok\.com/[^\s]+)", re.IGNORECASE)
X_REGEX = re.compile(r"(https?://(?:www\.)?(?:twitter\.com|x\.com)/[^\s]+)", re.IGNORECASE)
YOUTUBE_REGEX = re.compile(
    r"(https?://(?:www\.|m\.)?(?:youtube\.com|youtu\.be|music\.youtube\.com)/[^\s]+)",
    re.IGNORECASE,
)

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",
}

FFMPEG_BEFORE_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
FFMPEG_OPTIONS = "-vn"


@dataclass
class Track:
    title: str
    stream_url: str
    page_url: str
    requested_by: str
    text_channel_id: int


@dataclass
class GuildMusicState:
    queue: list[Track] = field(default_factory=list)
    current: Track | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class TikTokLinkConverter(discord.Client):
    def __init__(self, *, intents: discord.Intents) -> None:
        super().__init__(intents=intents)
        self.music_states: dict[int, GuildMusicState] = {}

    async def on_ready(self) -> None:
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        fixed_url = self.convert_social_link(message.content)
        if fixed_url is not None:
            await self.reply_with_fixed_link(message, fixed_url)

        youtube_match = YOUTUBE_REGEX.search(message.content)
        if youtube_match:
            await self.enqueue_youtube_link(message, youtube_match.group(0))

    def music_state(self, guild_id: int) -> GuildMusicState:
        state = self.music_states.get(guild_id)
        if state is None:
            state = GuildMusicState()
            self.music_states[guild_id] = state
        return state

    def convert_social_link(self, content: str) -> str | None:
        tiktok_match = TIKTOK_REGEX.search(content)
        if tiktok_match:
            return tiktok_match.group(0).replace("tiktok.com", "kktiktok.com")

        x_match = X_REGEX.search(content)
        if x_match:
            original_url = x_match.group(0)
            if "twitter.com" in original_url.lower():
                return re.sub("twitter\\.com", "fxtwitter.com", original_url, flags=re.IGNORECASE)
            return re.sub("x\\.com", "fixupx.com", original_url, flags=re.IGNORECASE)

        return None

    async def reply_with_fixed_link(self, message: discord.Message, fixed_url: str) -> None:
        try:
            await message.reply(f"[Embed Fix]({fixed_url})", mention_author=False)
            try:
                await message.edit(suppress=True)
            except discord.Forbidden:
                print("Could not suppress embed: Missing 'Manage Messages' permission.")
            except Exception as exc:
                print(f"Error suppressing embed: {exc}")
        except Exception as exc:
            print(f"Error processing social link: {exc}")

    async def enqueue_youtube_link(self, message: discord.Message, url: str) -> None:
        if message.guild is None:
            await message.reply("YouTube playback only works inside a server.", mention_author=False)
            return

        voice_state = getattr(message.author, "voice", None)
        if voice_state is None or voice_state.channel is None:
            await message.reply("Join a voice channel first, then post the YouTube link.", mention_author=False)
            return

        voice_client = message.guild.voice_client
        if voice_client is None:
            voice_client = await voice_state.channel.connect()
        elif voice_client.channel != voice_state.channel:
            await voice_client.move_to(voice_state.channel)

        await message.channel.send("Loading YouTube audio...")

        try:
            title, stream_url, page_url = await self.extract_audio(url)
        except Exception as exc:
            await message.channel.send(f"Could not load that YouTube link: `{exc}`")
            return

        state = self.music_state(message.guild.id)
        track = Track(
            title=title,
            stream_url=stream_url,
            page_url=page_url,
            requested_by=message.author.display_name,
            text_channel_id=message.channel.id,
        )
        state.queue.append(track)

        if voice_client.is_playing() or voice_client.is_paused() or state.current is not None:
            await message.channel.send(f"Queued: **{track.title}**")
            return

        await self.play_next(message.guild)

    async def extract_audio(self, url: str) -> tuple[str, str, str]:
        loop = asyncio.get_running_loop()

        def extract() -> tuple[str, str, str]:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(url, download=False)

            if "entries" in info:
                info = next(entry for entry in info["entries"] if entry)

            stream_url = info.get("url")
            if not stream_url:
                raise RuntimeError("yt-dlp did not return an audio stream URL")

            title = info.get("title") or "YouTube audio"
            page_url = info.get("webpage_url") or url
            return title, stream_url, page_url

        return await loop.run_in_executor(None, extract)

    async def play_next(self, guild: discord.Guild) -> None:
        state = self.music_state(guild.id)
        voice_client = guild.voice_client
        if voice_client is None:
            state.current = None
            return

        async with state.lock:
            if voice_client.is_playing() or voice_client.is_paused():
                return

            if not state.queue:
                state.current = None
                return

            state.current = state.queue.pop(0)
            source = discord.FFmpegPCMAudio(
                state.current.stream_url,
                before_options=FFMPEG_BEFORE_OPTIONS,
                options=FFMPEG_OPTIONS,
            )

            def after_playback(error: Exception | None) -> None:
                if error:
                    print(f"Playback error in guild {guild.id}: {error}")
                self.loop.call_soon_threadsafe(lambda: asyncio.create_task(self.after_track(guild.id)))

            voice_client.play(source, after=after_playback)

            channel = self.get_channel(state.current.text_channel_id)
            if channel is not None:
                await channel.send(f"Now playing: **{state.current.title}**")

    async def after_track(self, guild_id: int) -> None:
        guild = self.get_guild(guild_id)
        if guild is None:
            return

        self.music_state(guild_id).current = None
        await self.play_next(guild)


intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

client = TikTokLinkConverter(intents=intents)

if TOKEN:
    client.run(TOKEN)
else:
    print("Error: DISCORD_BOT_TOKEN not found in .env file.")
