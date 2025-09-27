import asyncio
from pyrogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat, Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram import filters, Client, errors, enums
from plugins.database import *
from plugins.config import *

async def set_auto_menu(client):
    try:
        owner_cmds = [
            BotCommand("start", "Check I am alive"),
            BotCommand("login", "Login session"),
            BotCommand("logout", "Logout session"),
            BotCommand("accept", "Accept all pending requests"),
            BotCommand("bcast", "Broadcast a message to users"),
            BotCommand("fcast", "Forward a message to users"),
            BotCommand("users", "View bot users"),
        ]

        for admin_id in SUDO:
            await client.set_bot_commands(owner_cmds, scope=BotCommandScopeChat(chat_id=admin_id))

        default_cmds = [
            BotCommand("start", "Check I am alive"),
            BotCommand("login", "Login session"),
            BotCommand("logout", "Logout session"),
            BotCommand("accept", "Accept all pending requests"),
        ]

        await client.set_bot_commands(default_cmds, scope=BotCommandScopeDefault())
        
        print("✅ Main Bot Menu Commands Set!")
    except Exception as e:
        print(f"⚠️ Set Menu Error: {e}")

@Client.on_chat_join_request(filters.group | filters.channel)
async def approve(client, message):
    op = message.chat
    kk = message.from_user
    try:
        add_group(message.chat.id)
        await client.approve_chat_join_request(op.id, kk.id)
        await client.send_message(kk.id, "Hello {}!\nWelcome To {}\n\n__Powerd By : @DeadxNone __".format(message.from_user.mention, message.chat.title))
        add_user(kk.id)
    except errors.PeerIdInvalid as e:
        print("user isn't start bot(means group)")
    except Exception as err:
        print(str(err))

@Client.on_message(filters.private & filters.command("start"))
async def start(client, message):
    try:
        await client.get_chat_member(CHID, message.from_user.id)
    except:
        try:
            invite_link = await client.create_chat_invite_link(int(CHID), creates_join_request=True)
        except:
            await message.reply("Make Sure I Am Admin In Your Channel")
            return 
        key = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("🍿 Join Update Channel 🍿", url=invite_link.invite_link),
                InlineKeyboardButton("🍀 Check Again 🍀", callback_data="chk")
            ]]
        ) 
        await message.reply_text("⚠️Access Denied!⚠️\n\nPlease Join My Update Channel To Use Me.If You Joined The Channel Then Click On Check Again Button To Confirm.", reply_markup=key)
        return 
    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🗯 Channel", url="https://t.me/+YczdaoCKP-AxMWFl"),
            InlineKeyboardButton("💬 Support", url="https://t.me/+8E9nKxs8Y-Y2OGRl")
        ]]
    )
    add_user(message.from_user.id)
    await message.reply_text("🦊 Hello {}!\nI'm an auto approve [Admin Join Requests]({}) Bot.\nI can approve users in Groups/Channels.Add me to your chat and promote me to admin with add members permission.\n\n__Powered By : @DeadxNone __".format(message.from_user.mention, "https://t.me/telegram/153"), reply_markup=keyboard)

@Client.on_message(filters.command('accept') & filters.private)
async def accept(client, message):
    show = await message.reply("Please Wait.....")
    
    user_data = get_session(message.from_user.id)
    if user_data is None:
        await show.edit("For Accepte Pending Request You Have To /login First.")
        return
    
    try:
        acc = Client("joinrequest", session_string=user_data, api_hash=API_HASH, api_id=API_ID)
        await acc.connect()
    except:
        return await show.edit("Your Login Session Expired. So /logout First Then Login Again By - /login")
    
    show = await show.edit("Now Forward A Message From Your Channel Or Group With Forward Tag\n\nMake Sure Your Logged In Account Is Admin In That Channel Or Group With Full Rights.")
    vj = await client.listen(message.chat.id)
    if vj.forward_from_chat and not vj.forward_from_chat.type in [enums.ChatType.PRIVATE, enums.ChatType.BOT]:
        chat_id = vj.forward_from_chat.id
        try:
            info = await acc.get_chat(chat_id)
        except:
            await show.edit("Error - Make Sure Your Logged In Account Is Admin In This Channel Or Group With Rights.")
    else:
        return await message.reply("Message Not Forwarded From Channel Or Group.")
    await vj.delete()
    
    msg = await show.edit("Accepting all join requests... Please wait until it's completed.")
    try:
        while True:
            await acc.approve_all_chat_join_requests(chat_id)
            await asyncio.sleep(1)
            join_requests = [request async for request in acc.get_chat_join_requests(chat_id)]
            if not join_requests:
                break
        
        await msg.edit("Successfully accepted all join requests.")
    except Exception as e:
        await msg.edit(f"An error occurred: {str(e)}")

@Client.on_callback_query(filters.regex("chk"))
async def chk(_, cb : CallbackQuery):
    try:
        await client.get_chat_member(CHID, cb.from_user.id)
    except:
        await cb.answer("🙅‍♂️ You are not joined my channel first join channel then check again. 🙅‍♂️", show_alert=True)
        return 
    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🗯 Channel", url="https://t.me/+YczdaoCKP-AxMWFl"),
            InlineKeyboardButton("💬 Support", url="https://t.me/+8E9nKxs8Y-Y2OGRl")
        ]]
    )
    add_user(cb.from_user.id)
    await cb.message.edit_text(text="🦊 Hello {}!\nI'm an auto approve [Admin Join Requests]({}) Bot.\nI can approve users in Groups/Channels.Add me to your chat and promote me to admin with add members permission.\n\n__Powered By : @DeadxNone __".format(cb.from_user.mention, "https://t.me/telegram/153"), reply_markup=keyboard)
