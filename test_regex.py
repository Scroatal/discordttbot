import re

TIKTOK_REGEX = r'(https?://(?:www\.|vm\.|vt\.)?tiktok\.com/[^\s]+)'

test_cases = [
    "https://www.tiktok.com/@user/video/1234567890",
    "https://tiktok.com/@user/video/1234567890",
    "https://vm.tiktok.com/ZM8C9J/",
    "https://vt.tiktok.com/ZSJ4/",
    "Check this out: https://www.tiktok.com/@user/video/1234567890 wow",
    "http://tiktok.com/video/123"
]

print("Running Regex Tests...")
for url in test_cases:
    match = re.search(TIKTOK_REGEX, url)
    if match:
        original = match.group(0)
        fixed = original.replace("tiktok.com", "kktiktok.com")
        print(f"[PASS] Matched: {original} -> Fixed: {fixed}")
    else:
        print(f"[FAIL] Did not match: {url}")
