import re

TIKTOK_REGEX = re.compile(r"(https?://(?:www\.|vm\.|vt\.)?tiktok\.com/[^\s]+)", re.IGNORECASE)
TWITTER_REGEX = re.compile(r"(https?://(?:www\.)?(?:twitter\.com|x\.com)/[^\s]+)", re.IGNORECASE)
TWITCH_CLIP_REGEX = re.compile(
    r"https?://(?:www\.)?twitch\.tv/[A-Za-z0-9_]+/clip/([A-Za-z0-9_-]+)"
    r"|https?://clips\.twitch\.tv/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
YOUTUBE_REGEX = re.compile(
    r"(https?://(?:www\.|m\.)?(?:youtube\.com|youtu\.be|music\.youtube\.com)/[^\s]+)",
    re.IGNORECASE,
)


def convert_social_link(content):
    tiktok_match = TIKTOK_REGEX.search(content)
    if tiktok_match:
        return tiktok_match.group(0).replace("tiktok.com", "kktiktok.com")

    twitter_match = TWITTER_REGEX.search(content)
    if twitter_match:
        original = twitter_match.group(0)
        if "twitter.com" in original.lower():
            return re.sub("twitter\\.com", "fxtwitter.com", original, flags=re.IGNORECASE)
        return re.sub("x\\.com", "fixupx.com", original, flags=re.IGNORECASE)

    twitch_match = TWITCH_CLIP_REGEX.search(content)
    if twitch_match:
        slug = twitch_match.group(1) or twitch_match.group(2)
        return f"https://fxtwitch.seria.moe/clip/{slug}"

    return None

test_cases = [
    ("https://www.tiktok.com/@user/video/1234567890", "https://www.kktiktok.com/@user/video/1234567890"),
    ("https://tiktok.com/@user/video/1234567890", "https://kktiktok.com/@user/video/1234567890"),
    ("https://vm.tiktok.com/ZM8C9J/", "https://vm.kktiktok.com/ZM8C9J/"),
    ("https://vt.tiktok.com/ZSJ4/", "https://vt.kktiktok.com/ZSJ4/"),
    (
        "Check this out: https://www.tiktok.com/@user/video/1234567890 wow",
        "https://www.kktiktok.com/@user/video/1234567890",
    ),
    ("http://tiktok.com/video/123", "http://kktiktok.com/video/123"),
]

print("Running TikTok Regex Tests...")
for content, expected in test_cases:
    fixed = convert_social_link(content)
    if fixed == expected:
        print(f"[PASS] Fixed: {fixed}")
    else:
        raise AssertionError(f"Expected {expected}, got {fixed}")

twitter_test_cases = [
    ("https://twitter.com/user/status/1234567890", "https://fxtwitter.com/user/status/1234567890"),
    ("https://www.twitter.com/user/status/1234567890", "https://www.fxtwitter.com/user/status/1234567890"),
    ("https://x.com/user/status/1234567890", "https://fixupx.com/user/status/1234567890"),
    ("https://www.x.com/user/status/1234567890", "https://www.fixupx.com/user/status/1234567890"),
    ("Check out this tweet: https://twitter.com/user/status/123 wow", "https://fxtwitter.com/user/status/123"),
    ("http://x.com/abc", "http://fixupx.com/abc"),
]

print("\nRunning Twitter/X Regex Tests...")
for content, expected in twitter_test_cases:
    fixed = convert_social_link(content)
    if fixed == expected:
        print(f"[PASS] Fixed: {fixed}")
    else:
        raise AssertionError(f"Expected {expected}, got {fixed}")

twitch_test_cases = [
    (
        "https://www.twitch.tv/dekel/clip/CrunchySolidLaptopOSfrog-Ql8CoQ4ICFT5pu6s",
        "https://fxtwitch.seria.moe/clip/CrunchySolidLaptopOSfrog-Ql8CoQ4ICFT5pu6s",
    ),
    (
        "https://twitch.tv/dekel/clip/CrunchySolidLaptopOSfrog-Ql8CoQ4ICFT5pu6s",
        "https://fxtwitch.seria.moe/clip/CrunchySolidLaptopOSfrog-Ql8CoQ4ICFT5pu6s",
    ),
    (
        "https://clips.twitch.tv/CrunchySolidLaptopOSfrog-Ql8CoQ4ICFT5pu6s",
        "https://fxtwitch.seria.moe/clip/CrunchySolidLaptopOSfrog-Ql8CoQ4ICFT5pu6s",
    ),
]

print("\nRunning Twitch Clip Regex Tests...")
for content, expected in twitch_test_cases:
    fixed = convert_social_link(content)
    if fixed == expected:
        print(f"[PASS] Fixed: {fixed}")
    else:
        raise AssertionError(f"Expected {expected}, got {fixed}")

youtube_test_cases = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtu.be/dQw4w9WgXcQ",
    "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
]

print("\nRunning YouTube Regex Tests...")
for content in youtube_test_cases:
    if YOUTUBE_REGEX.search(content):
        print(f"[PASS] Matched: {content}")
    else:
        raise AssertionError(f"Did not match YouTube URL: {content}")
