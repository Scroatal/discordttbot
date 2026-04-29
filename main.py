import discord
import re
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Define the Regex pattern for TikTok links
# Matches: https://tiktok.com, https://www.tiktok.com, https://vm.tiktok.com, https://vt.tiktok.com
# Also handles query parameters and trailing slashes
TIKTOK_REGEX = r'(https?://(?:www\.|vm\.|vt\.)?tiktok\.com/[^\s]+)'
FIXER_DOMAIN = "kktiktok.com"

class TikTokFixerClient(discord.Client):
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

    async def on_message(self, message):
        # Ignore messages from the bot itself to prevent infinite loops
        if message.author == self.user:
            return

        # Search for TikTok links in the message content
        match = re.search(TIKTOK_REGEX, message.content)
        
        if match:
            original_url = match.group(0)
            print(f"Detected TikTok link: {original_url}")

            # Replace only the TikTok domain token so short links keep their subdomain.
            # Example: vm.tiktok.com/... -> vm.kktiktok.com/...
            new_url = original_url.replace("tiktok.com", FIXER_DOMAIN)
            
            try:
                # Reply to the user with the fixed link
                # mention_author=False keeps it cleaner
                await message.reply(f"[TikTok Embed Fix]({new_url})", mention_author=False)
                
                # Attempt to suppress the original embed to avoid clutter
                # This requires 'Manage Messages' permission
                try:
                    await message.edit(suppress=True)
                except discord.Forbidden:
                    print("Could not suppress embed: Missing 'Manage Messages' permission.")
                except Exception as e:
                    print(f"Error suppressing embed: {e}")

            except Exception as e:
                print(f"Error processing message: {e}")

# IMPORTANT: Message Content Intent must be enabled in the Discord Developer Portal
intents = discord.Intents.default()
intents.message_content = True

client = TikTokFixerClient(intents=intents)

if TOKEN:
    client.run(TOKEN)
else:
    print("Error: DISCORD_BOT_TOKEN not found in .env file.")
