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
TWITCH_CLIP_REGEX = re.compile(
    r"https?://(?:www\.)?twitch\.tv/[A-Za-z0-9_]+/clip/([A-Za-z0-9_-]+)"
    r"|https?://clips\.twitch\.tv/([A-Za-z0-9_]+)/clip/([A-Za-z0-9_-]+)"
    r"|https?://clips\.twitch\.tv/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
YOUTUBE_REGEX = re.compile(
    r"(https?://(?:www\.|m\.)?(?:youtube\.com|youtu\.be|music\.youtube\.com)/[^\s]+)",
    re.IGNORECASE,
)
COMMAND_PREFIX = "!"

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
MAX_TRACK_DURATION_SECONDS = 2 * 60 * 60


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

        if await self.handle_music_command(message):
            return

        fixed_url = self.convert_social_link(message.content)
        if fixed_url is not None:
            await self.reply_with_fixed_link(message, fixed_url)

    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member.bot or member.guild.voice_client is None:
            return

        voice_client = member.guild.voice_client
        if before.channel != voice_client.channel and after.channel != voice_client.channel:
            return

        await self.disconnect_if_alone(member.guild)

    async def handle_music_command(self, message: discord.Message) -> bool:
        content = message.content.strip()
        if not content.startswith(COMMAND_PREFIX):
            return False

        command, _, rest = content[1:].partition(" ")
        command = command.lower()
        rest = rest.strip()

        if command in {"play", "p"}:
            youtube_match = YOUTUBE_REGEX.search(rest)
            if not youtube_match:
                await message.reply("Use `!play <youtube link>`.", mention_author=False)
                return True

            await self.enqueue_youtube_link(message, youtube_match.group(0))
            return True

        if command in {"stop", "leave", "disconnect"}:
            await self.stop_music(message)
            return True

        if command == "skip":
            await self.skip_track(message)
            return True

        if command in {"queue", "q"}:
            await self.show_queue(message)
            return True

        if command in {"musichelp", "commands"}:
            await message.reply(
                "Music commands: `!play <youtube link>`, `!skip`, `!stop`, `!queue`.",
                mention_author=False,
            )
            return True

        return False

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

        twitch_match = TWITCH_CLIP_REGEX.search(content)
        if twitch_match:
            author = twitch_match.group(2)
            slug = twitch_match.group(1) or twitch_match.group(3) or twitch_match.group(4)
            if author:
                return f"https://fxtwitch.seria.moe/{author}/clip/{slug}"
            return f"https://fxtwitch.seria.moe/clip/{slug}"

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

        if not self.voice_has_listeners(voice_client):
            await voice_client.disconnect()
            await message.reply("I left because nobody is in the voice channel.", mention_author=False)
            return

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

    async def stop_music(self, message: discord.Message) -> None:
        if message.guild is None:
            return

        state = self.music_state(message.guild.id)
        state.queue.clear()
        state.current = None

        voice_client = message.guild.voice_client
        if voice_client is None:
            await message.reply("I am not in a voice channel.", mention_author=False)
            return

        await voice_client.disconnect()
        await message.reply("Stopped playback and left the voice channel.", mention_author=False)

    async def skip_track(self, message: discord.Message) -> None:
        if message.guild is None:
            return

        voice_client = message.guild.voice_client
        if voice_client is None or not voice_client.is_connected():
            await message.reply("I am not playing anything.", mention_author=False)
            return

        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()
            await message.reply("Skipped.", mention_author=False)
            return

        await message.reply("I am not playing anything.", mention_author=False)

    async def show_queue(self, message: discord.Message) -> None:
        if message.guild is None:
            return

        state = self.music_state(message.guild.id)
        lines = []
        if state.current is not None:
            lines.append(f"Now playing: **{state.current.title}**")

        if state.queue:
            queued = "\n".join(f"{index}. {track.title}" for index, track in enumerate(state.queue, start=1))
            lines.append(f"Queued:\n{queued}")

        if not lines:
            lines.append("The music queue is empty.")

        await message.reply("\n".join(lines), mention_author=False)

    def voice_has_listeners(self, voice_client: discord.VoiceClient) -> bool:
        channel = voice_client.channel
        return any(not member.bot for member in channel.members)

    async def disconnect_if_alone(self, guild: discord.Guild) -> None:
        voice_client = guild.voice_client
        if voice_client is None or not voice_client.is_connected():
            return

        if self.voice_has_listeners(voice_client):
            return

        state = self.music_state(guild.id)
        state.queue.clear()
        state.current = None

        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()

        await voice_client.disconnect()

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
            duration = info.get("duration")
            if duration is not None and duration > MAX_TRACK_DURATION_SECONDS:
                raise RuntimeError(
                    f"{title} is longer than the 2 hour music limit "
                    f"({self.format_duration(duration)})."
                )

            page_url = info.get("webpage_url") or url
            return title, stream_url, page_url

        return await loop.run_in_executor(None, extract)

    def format_duration(self, seconds: int | float) -> str:
        seconds = int(seconds)
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes}m"
        if minutes:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

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
                await voice_client.disconnect()
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
