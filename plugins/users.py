from pyrogram.types import Message
from pyrogram import filters, Client
from plugins.config import *
from plugins.database import *

@Client.on_message(filters.command("users") & filters.user(ADMIN))
async def users(client, message):
    xx = all_users()
    x = all_groups()
    tot = int(xx + x)
    await message.reply_text(text=f"""
🍀 Chats Stats 🍀
🙋‍♂️ Users : `{xx}`
👥 Groups : `{x}`
🚧 Total users & groups : `{tot}` """)
