
import os
import logging
import re
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from dotenv import load_dotenv

# Load token from .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Setup logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Store banned users and warnings
banned_users = set()
user_warnings = {}
bad_words = {"madarchod", "behenchod", "chutiya", "bitch", "fuck", "bc", "mc"}  # Custom bad words

# Group rules
GROUP_RULES = """
📜 গ্রুপ নিয়মাবলী:
1. স্প্যাম করা যাবে না
2. অন্যদের সম্মান করুন
3. খারাপ ভাষা ব্যবহার করবেন না
4. অ্যাডমিন নির্দেশনা মেনে চলুন
5. কোন বিজ্ঞাপন বা সেলফ-প্রমোশন নয়
6. লিংক শেয়ার করা যাবে না
"""

# Spam check function
async def check_spam(user_id: int, message_time: float) -> bool:
    if user_id not in user_warnings:
        user_warnings[user_id] = {"count": 0, "messages": [message_time]}
        return False
    
    # Remove messages older than 5 seconds
    user_warnings[user_id]["messages"] = [
        time for time in user_warnings[user_id]["messages"]
        if message_time - time < 5
    ]
    
    user_warnings[user_id]["messages"].append(message_time)
    return len(user_warnings[user_id]["messages"]) > 5

# Rules command
@dp.message(lambda msg: msg.text == "/rules")
async def show_rules(message: types.Message):
    await message.reply(GROUP_RULES)

@dp.message(lambda msg: msg.text and msg.text.startswith('/setrules'))
async def set_rules(message: types.Message):
    if not message.from_user.id == message.chat.owner_id:
        await message.reply("Only group owner can change rules.")
        return
    try:
        new_rules = message.text.replace('/setrules', '').strip()
        if new_rules:
            global GROUP_RULES
            GROUP_RULES = new_rules
            await message.reply("Rules updated successfully!")
        else:
            await message.reply("Please provide rules: /setrules [new rules]")
    except Exception as e:
        await message.reply("Error updating rules. Try again.")

@dp.message(lambda msg: msg.text and msg.text.startswith('/setbadwords'))
async def set_bad_words(message: types.Message):
    if not message.from_user.id == message.chat.owner_id:
        await message.reply("Only group owner can change bad words.")
        return
    try:
        words = message.text.replace('/setbadwords', '').strip()
        if words:
            global bad_words
            bad_words = set(words.split())
            await message.reply("Bad words list updated!")
        else:
            await message.reply("Please provide words: /setbadwords [word1 word2 ...]")
    except Exception as e:
        await message.reply("Error updating bad words. Try again.")

# Welcome new members
@dp.chat_member()
async def welcome_new_member(event: types.ChatMemberUpdated):
    if event.new_chat_member.status == "member":
        welcome_text = f"👋 Welcome {event.new_chat_member.user.mention_html()}! Thank you for joining our group."
        await event.bot.send_message(event.chat.id, welcome_text, parse_mode=ParseMode.HTML)

# Start command handler
@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    await message.reply("👋 হ্যালো! আমি আপনার টেলিগ্রাম বট।\nType /help to see available commands.")

@dp.message(lambda msg: msg.text == "/help" or msg.text == "/menu")
async def show_help(message: types.Message):
    chat_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    is_admin = chat_member.status in ["creator", "administrator"]
    
    basic_commands = """
📜 Available Commands:
➖➖➖➖➖➖➖➖➖
/start - Start the bot
/rules - Show group rules
/help - Show this menu
"""
    
    admin_commands = """
👑 Admin Commands:
➖➖➖➖➖➖➖➖➖
/setrules [text] - Set new group rules
/setbadwords [words] - Update bad words list
/unban @username - Unban a user

🛡️ Auto Moderation:
• Anti-spam system (3 warnings)
• Bad words filter
• Link protection
• Welcome messages
"""
    
    if is_admin:
        await message.reply(basic_commands + admin_commands)
    else:
        await message.reply(basic_commands)

# Unban command handler
@dp.message(lambda msg: msg.text and msg.text.startswith('/unban'))
async def unban_user(message: types.Message):
    try:
        # Get username from command
        username = message.text.split()[1].replace('@', '')
        # Find user ID from message that triggered the ban
        for user_id in banned_users:
            chat_member = await bot.get_chat_member(message.chat.id, user_id)
            if chat_member.user.username and chat_member.user.username.lower() == username.lower():
                banned_users.remove(user_id)
                await message.reply(f"User @{username} has been unbanned.")
                return
        await message.reply("This user is not banned or not found.")
    except (IndexError, ValueError):
        await message.reply("Please provide a username: /unban @username")

# Message handler for all messages
@dp.message()
async def handle_messages(message: types.Message):
    if message.from_user.id in banned_users:
        await message.delete()
        return
        
    # Check if message is a command
    if message.text and message.text.startswith('/'):
        chat_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status not in ["creator", "administrator"]:
            await message.delete()
            await message.answer("Commands are restricted to admins only.")
            return
    
    # If not a command, check for spam and bad words
    if not message.text.startswith('/'):
        await message.delete()
        return

    # Check for spam
    if await check_spam(message.from_user.id, message.date.timestamp()):
        await message.delete()
        user_warnings[message.from_user.id]["count"] += 1
        warning_count = user_warnings[message.from_user.id]["count"]
        
        if warning_count >= 3:
            banned_users.add(message.from_user.id)
            await message.answer(f"User {message.from_user.full_name} has been banned for multiple violations.")
        else:
            await message.answer(f"⚠️ Warning {warning_count}/3 for {message.from_user.full_name}: Spamming detected!")
        return

    # Check for bad words
    if message.text and any(word.lower() in message.text.lower() for word in bad_words):
        await message.delete()
        user_warnings[message.from_user.id]["count"] += 1
        warning_count = user_warnings[message.from_user.id]["count"]
        
        if warning_count >= 3:
            banned_users.add(message.from_user.id)
            await message.answer(f"User {message.from_user.full_name} has been banned for multiple violations.")
        else:
            await message.answer(f"⚠️ Warning {warning_count}/3 for {message.from_user.full_name}: Bad language detected!")
        return

    # URL detection pattern
    url_pattern = re.compile(
        r'(?:(?:https?|ftp):\/\/|t\.me\/|telegram\.me\/|www\.)(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s,]*'
    )
    
    if url_pattern.search(message.text or ''):
        try:
            # Delete the message
            await message.delete()
            
            # Ban the user
            banned_users.add(message.from_user.id)
            
            # Notify about the ban
            await message.answer(
                f"User {message.from_user.full_name} has been banned for sending links."
            )
        except Exception as e:
            logging.error(f"Error handling message: {e}")

# Run the bot
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
