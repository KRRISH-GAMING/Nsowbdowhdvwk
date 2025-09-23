import asyncio
from pyrogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat, Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram import filters, Client, errors, enums
from pyrogram.errors import (UserNotParticipant, ApiIdInvalid, PhoneNumberInvalid, PhoneCodeInvalid, PhoneCodeExpired, SessionPasswordNeeded, PasswordHashInvalid)
from pyrogram.errors.exceptions.flood_420 import FloodWait
from plugins.database import *
from plugins.config import cfg

SESSION_STRING_SIZE = 351

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

        for admin_id in cfg.SUDO:
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
        await client.send_message(kk.id, "**Hello {}!\nWelcome To {}\n\n__Powerd By : @DeadxNone __**".format(message.from_user.mention, message.chat.title))
        add_user(kk.id)
    except errors.PeerIdInvalid as e:
        print("user isn't start bot(means group)")
    except Exception as err:
        print(str(err))

@Client.on_message(filters.private & filters.command("start"))
async def start(client, message):
    try:
        await client.get_chat_member(cfg.CHID, message.from_user.id)
    except:
        try:
            invite_link = await client.create_chat_invite_link(int(cfg.CHID))
        except:
            await message.reply("**Make Sure I Am Admin In Your Channel**")
            return 
        key = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("🍿 Join Update Channel 🍿", url=invite_link.invite_link),
                InlineKeyboardButton("🍀 Check Again 🍀", callback_data="chk")
            ]]
        ) 
        await message.reply_text("**⚠️Access Denied!⚠️\n\nPlease Join My Update Channel To Use Me.If You Joined The Channel Then Click On Check Again Button To Confirm.**", reply_markup=key)
        return 
    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🗯 Channel", url="https://t.me/+YczdaoCKP-AxMWFl"),
            InlineKeyboardButton("💬 Support", url="https://t.me/+8E9nKxs8Y-Y2OGRl")
        ]]
    )
    add_user(message.from_user.id)
    await message.reply_text("**🦊 Hello {}!\nI'm an auto approve [Admin Join Requests]({}) Bot.\nI can approve users in Groups/Channels.Add me to your chat and promote me to admin with add members permission.\n\n__Powered By : @DeadxNone __**".format(message.from_user.mention, "https://t.me/telegram/153"), reply_markup=keyboard)

@Client.on_message(filters.private & ~filters.forwarded & filters.command(["login"]))
async def login(client, message):
    user_data = get_session(message.from_user.id)
    if user_data is not None:
        await message.reply("**Your Are Already Logged In. First /logout Your Old Session. Then Do Login.**")
        return 
    
    user_id = int(message.from_user.id)
    phone_number_msg = await client.ask(chat_id=user_id, text="<b>Please send your phone number which includes country code</b>\n<b>Example:</b> <code>+13124562345, +9171828181889</code>")
    if phone_number_msg.text=='/cancel':
        return await phone_number_msg.reply('<b>process cancelled !</b>')
    
    phone_number = phone_number_msg.text
    client = Client(":memory:", cfg.API_ID, cfg.API_HASH)
    await client.connect()
    await phone_number_msg.reply("Sending OTP...")
    
    try:
        code = await client.send_code(phone_number)
        phone_code_msg = await client.ask(user_id, "Please check for an OTP in official telegram account. If you got it, send OTP here after reading the below format. \n\nIf OTP is `12345`, **please send it as** `1 2 3 4 5`.\n\n**Enter /cancel to cancel The Procces**", filters=filters.text, timeout=600)
    except PhoneNumberInvalid:
        await phone_number_msg.reply('`PHONE_NUMBER` **is invalid.**')
        return
    
    if phone_code_msg.text=='/cancel':
        return await phone_code_msg.reply('<b>process cancelled !</b>')
    
    try:
        phone_code = phone_code_msg.text.replace(" ", "")
        await client.sign_in(phone_number, code.phone_code_hash, phone_code)
    except PhoneCodeInvalid:
        await phone_code_msg.reply('**OTP is invalid.**')
        return
    except PhoneCodeExpired:
        await phone_code_msg.reply('**OTP is expired.**')
        return
    except SessionPasswordNeeded:
        two_step_msg = await client.ask(user_id, '**Your account has enabled two-step verification. Please provide the password.\n\nEnter /cancel to cancel The Procces**', filters=filters.text, timeout=300)
        if two_step_msg.text=='/cancel':
            return await two_step_msg.reply('<b>process cancelled !</b>')
        
        try:
            password = two_step_msg.text
            await client.check_password(password=password)
        except PasswordHashInvalid:
            await two_step_msg.reply('**Invalid Password Provided**')
            return
    
    string_session = await client.export_session_string()
    await client.disconnect()
    if len(string_session) < SESSION_STRING_SIZE:
        return await message.reply('<b>invalid session sring</b>')
    
    try:
        user_data = get_session(message.from_user.id)
        if user_data is None:
            uclient = Client(":memory:", session_string=string_session, api_id=API_ID, api_hash=API_HASH)
            await uclient.connect()
            set_session(message.from_user.id, session=string_session)
    except Exception as e:
        return await message.reply_text(f"<b>ERROR IN LOGIN:</b> `{e}`")
    
    await client.send_message(message.from_user.id, "<b>Account Login Successfully.\n\nIf You Get Any Error Related To AUTH KEY Then /logout first and /login again</b>")

@Client.on_message(filters.private & ~filters.forwarded & filters.command(["logout"]))
async def logout(client, message):
    user_data = get_session(message.from_user.id)  
    if user_data is None:
        return await message.reply("❌ You are not logged in.")
    
    set_session(message.from_user.id, session=None)  
    await message.reply("**Logout Successfully** ♦")

@Client.on_message(filters.command('accept') & filters.private)
async def accept(client, message):
    show = await message.reply("**Please Wait.....**")
    
    user_data = get_session(message.from_user.id)
    if user_data is None:
        await show.edit("**For Accepte Pending Request You Have To /login First.**")
        return
    
    try:
        acc = Client("joinrequest", session_string=user_data, api_hash=API_HASH, api_id=API_ID)
        await acc.connect()
    except:
        return await show.edit("**Your Login Session Expired. So /logout First Then Login Again By - /login**")
    
    show = await show.edit("**Now Forward A Message From Your Channel Or Group With Forward Tag\n\nMake Sure Your Logged In Account Is Admin In That Channel Or Group With Full Rights.**")
    vj = await client.listen(message.chat.id)
    if vj.forward_from_chat and not vj.forward_from_chat.type in [enums.ChatType.PRIVATE, enums.ChatType.BOT]:
        chat_id = vj.forward_from_chat.id
        try:
            info = await acc.get_chat(chat_id)
        except:
            await show.edit("**Error - Make Sure Your Logged In Account Is Admin In This Channel Or Group With Rights.**")
    else:
        return await message.reply("**Message Not Forwarded From Channel Or Group.**")
    await vj.delete()
    
    msg = await show.edit("**Accepting all join requests... Please wait until it's completed.**")
    try:
        while True:
            await acc.approve_all_chat_join_requests(chat_id)
            await asyncio.sleep(1)
            join_requests = [request async for request in acc.get_chat_join_requests(chat_id)]
            if not join_requests:
                break
        
        await msg.edit("**Successfully accepted all join requests.**")
    except Exception as e:
        await msg.edit(f"**An error occurred:** {str(e)}")

@Client.on_message(filters.command("bcast") & filters.user(cfg.SUDO))
async def bcast(client, message):
    allusers = users
    lel = await message.reply_text("`⚡️ Processing...`")
    success = 0
    failed = 0
    deactivated = 0
    blocked = 0
    for usrs in allusers.find():
        try:
            userid = usrs["user_id"]
            #print(int(userid))
            if message.command[0] == "bcast":
                await message.reply_to_message.copy(int(userid))
            success +=1
        except FloodWait as ex:
            await asyncio.sleep(ex.value)
            if message.command[0] == "bcast":
                await message.reply_to_message.copy(int(userid))
        except errors.InputUserDeactivated:
            deactivated +=1
            remove_user(userid)
        except errors.UserIsBlocked:
            blocked +=1
        except Exception as e:
            print(e)
            failed +=1

    await lel.edit(f"✅Successfull to `{success}` users.\n❌ Faild to `{failed}` users.\n👾 Found `{blocked}` Blocked users \n👻 Found `{deactivated}` Deactivated users.")

@Client.on_message(filters.command("fcast") & filters.user(cfg.SUDO))
async def fcast(client, message):
    allusers = users
    lel = await message.reply_text("`⚡️ Processing...`")
    success = 0
    failed = 0
    deactivated = 0
    blocked = 0
    for usrs in allusers.find():
        try:
            userid = usrs["user_id"]
            #print(int(userid))
            if message.command[0] == "fcast":
                await message.reply_to_message.forward(int(userid))
            success +=1
        except FloodWait as ex:
            await asyncio.sleep(ex.value)
            if message.command[0] == "fcast":
                await message.reply_to_message.forward(int(userid))
        except errors.InputUserDeactivated:
            deactivated +=1
            remove_user(userid)
        except errors.UserIsBlocked:
            blocked +=1
        except Exception as e:
            print(e)
            failed +=1

    await lel.edit(f"✅Successfull to `{success}` users.\n❌ Faild to `{failed}` users.\n👾 Found `{blocked}` Blocked users \n👻 Found `{deactivated}` Deactivated users.")

@Client.on_message(filters.command("users") & filters.user(cfg.SUDO))
async def users(client, message):
    xx = all_users()
    x = all_groups()
    tot = int(xx + x)
    await message.reply_text(text=f"""
🍀 Chats Stats 🍀
🙋‍♂️ Users : `{xx}`
👥 Groups : `{x}`
🚧 Total users & groups : `{tot}` """)

@Client.on_callback_query(filters.regex("chk"))
async def chk(_, cb : CallbackQuery):
    try:
        await client.get_chat_member(cfg.CHID, cb.from_user.id)
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
    await cb.message.edit_text(text="**🦊 Hello {}!\nI'm an auto approve [Admin Join Requests]({}) Bot.\nI can approve users in Groups/Channels.Add me to your chat and promote me to admin with add members permission.\n\n__Powered By : @DeadxNone __**".format(cb.from_user.mention, "https://t.me/telegram/153"), reply_markup=keyboard)
