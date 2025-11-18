import traceback, asyncio, re, time as pytime
from datetime import datetime, timedelta
from pyrogram import *
from pyrogram.types import *
from pyrogram.errors import *
from pyrogram.errors.exceptions.bad_request_400 import *
from plugins.config import *
from plugins.database import *
from plugins.helper import *

USED_TXNS = set()
LAST_PAYMENT_CHECK = 0
PAYMENT_CACHE = {}

USER_LINKS = {}

LOG_TEXT = """<b><u>#NewUser</u></b>
    
Id - <code>{}</code>

Name - {}

Username - {}"""

broadcast_cancel = False

START_TIME = pytime.time()

PLAN_CATEGORY_MAP = {
    "y1": "Mixed Collection",
    "y2": "CP/RP Collection",
    "y3": "Mega Collection"
}

PLAN_CHANNEL_MAP = {
    # Desi/Onlyfans
    "y1p1": -1002745649036,
    "y1p2": -1002745649036,
    "y1p3": -1002745649036,
    "y1p4": -1002745649036,

    # Cp/Rp
    "y2p1": -1003264225931,
    "y2p2": -1003264225931,
    "y2p3": -1003264225931,
    "y2p4": -1003264225931,

    # Mega Collection
    "y3p1": -1003212677737,
    "y3p2": -1003212677737,
    "y3p3": -1003212677737,
    "y3p4": -1003212677737,
}

@Client.on_message(filters.command("start") & filters.private)
async def start(client, message):
    try:
        user_id = message.from_user.id
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        mention = message.from_user.mention
        username = message.from_user.username

        username_text = f"@{username}" if username else "None"

        if not await db.is_user_exist(user_id):
            await db.add_user(user_id, first_name)
            await safe_action(
                client.send_message,
                LOG_CHANNEL,
                LOG_TEXT.format(user_id, mention, username_text)
            )

        buttons = [
            [InlineKeyboardButton("🌟 Our Premium Plans", callback_data="x1")],
            #[InlineKeyboardButton("📊 Check Your Subscription", callback_data="x2")],
            #[InlineKeyboardButton("♈ How To Buy Premium", url="https://t.me/Open_Shorten_Link_Tutorial/13")],
            [InlineKeyboardButton("🆘 Help & Support", callback_data="x3")]
        ]

        return await safe_action(
            message.reply_text,
            text=(
                "Hello👋 Members"
                "\n\n🎖️ Welcome To The Premium Channel Subscription Bot"
                "\n\nHere you can buy premium channels through our bot and get exclusive content instantly!"
                "\n\n💳 Make payment and get your premium link right now in seconds."
                "\n\n👇🏻 Please choose an option below:"
            ),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await safe_action(
            client.send_message,
            LOG_CHANNEL,
            f"⚠️ Start Handler Error:\n\n<code>{e}</code>\n\nTraceback:\n<code>{traceback.format_exc()}</code>."
        )
        print(f"⚠️ Start Handler Error: {e}")
        print(traceback.format_exc())

@Client.on_message(filters.command("resendlinks") & filters.private & filters.user(ADMINS))
async def resend_links_command(client, message):
    try:
        parts = message.text.split()
        if len(parts) < 3:
            return await message.reply_text(
                "⚙️ Usage:\n`/resendlinks <plan_prefix> <new_channel_id>`\n\nExample:\n`/resendlinks y1 -1002123456789`",
                parse_mode=enums.ParseMode.MARKDOWN
            )

        plan_prefix = parts[1].strip()  # e.g. y1
        new_channel_id = int(parts[2].strip())

        await message.reply_text(
            f"🔁 Starting resend process for **{plan_prefix}** plans...\n"
            f"📢 Updating to new channel ID: `{new_channel_id}`",
            parse_mode=enums.ParseMode.MARKDOWN
        )

        for sub_plan in ["p1", "p2", "p3", "p4"]:
            plan_key = f"{plan_prefix}{sub_plan}"
            await db.update_plan_channel(plan_key, new_channel_id)

        active_users = await db.get_active_users_by_category(plan_prefix)
        now = datetime.utcnow()
        sent, skipped, failed = 0, 0, 0

        for user in active_users:
            try:
                expiry = datetime.fromisoformat(user["expiry"])
                if expiry <= now:
                    skipped += 1
                    continue

                user_id = user["id"]

                invite = await client.create_chat_invite_link(
                    chat_id=new_channel_id,
                    name=f"Backup link for {user_id}",
                    member_limit=1
                )

                USER_LINKS[user_id] = {
                    "chat_id": new_channel_id,
                    "invite_link": invite.invite_link
                }

                remaining = (expiry - now).days

                await client.send_message(
                    user_id,
                    f"📢 <b>Channel Updated!</b>\n\n"
                    f"Your premium access has been moved to a new channel.\n"
                    f"🔗 <b>Join here:</b> {invite.invite_link}\n\n"
                    f"⏳ Your access remains valid for <b>{remaining}</b> more days.\n"
                    f"⚠️ Link expires in 1 hour, please join immediately.",
                    parse_mode=enums.ParseMode.HTML
                )
                sent += 1
                await asyncio.sleep(1)

            except Exception as e:
                print(f"❌ Failed for {user.get('id')}: {e}")
                failed += 1

        await message.reply_text(
            f"✅ <b>Resend Completed!</b>\n\n"
            f"📦 Plan Category: <code>{plan_prefix}</code>\n"
            f"📨 Sent: <b>{sent}</b>\n"
            f"⏸ Skipped Expired: <b>{skipped}</b>\n"
            f"⚠️ Failed: <b>{failed}</b>\n"
            f"💾 Future users will now get the new channel automatically.",
            parse_mode=enums.ParseMode.HTML
        )

    except Exception as e:
        await safe_action(
            client.send_message,
            LOG_CHANNEL,
            f"⚠️ Resend Link Handler Error:\n\n<code>{e}</code>\n\nTraceback:\n<code>{traceback.format_exc()}</code>."
        )
        print(f"⚠️ Resend Link Handler Error: {e}")
        print(traceback.format_exc())

@Client.on_message(filters.command("broadcast") & filters.private & filters.user(ADMINS))
async def broadcast(client, message):
    global broadcast_cancel
    broadcast_cancel = False
    try:
        if message.reply_to_message:
            b_msg = message.reply_to_message
        else:
            b_msg = await safe_action(client.ask,
                message.chat.id,
                "📩 Send the message to broadcast\n\n/cancel to stop.",
            )

            if b_msg.text and b_msg.text.lower() == "/cancel":
                return await safe_action(message.reply_text, "🚫 Broadcast cancelled.")

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Cancel Broadcast", callback_data="cancel_broadcast")]]
        )

        sts = await safe_action(message.reply_text,
            "⏳ Broadcast starting...",
            reply_markup=keyboard,
        )
        start_time = pytime.time()
        total_users = await db.total_users_count()

        done = blocked = deleted = failed = success = 0

        users = await db.get_all_users()
        async for user in users:
            if broadcast_cancel:
                await safe_action(sts.edit_text, "🚫 Broadcast cancelled by admin.")
                print("🛑 Broadcast cancelled mid-way.")
                return
            try:
                if "id" in user:
                    pti, sh = await broadcast_messagesx(int(user["id"]), b_msg)
                    if pti:
                        success += 1
                    else:
                        if sh == "Blocked":
                            blocked += 1
                        elif sh == "Deleted":
                            deleted += 1
                        else:
                            failed += 1
                    done += 1

                    if done % 10 == 0 or done == total_users:
                        progress = broadcast_progress_bar(done, total_users)
                        percent = (done / total_users) * 100
                        elapsed = pytime.time() - start_time
                        speed = done / elapsed if elapsed > 0 else 0
                        remaining = total_users - done
                        eta = timedelta(seconds=int(remaining / speed)) if speed > 0 else "∞"

                        try:
                            await safe_action(sts.edit, f"""
📢 <b>Broadcast in Progress...</b>

{progress}

👥 Total Users: {total_users}
✅ Success: {success}
🚫 Blocked: {blocked}
❌ Deleted: {deleted}
⚠️ Failed: {failed}

⏳ ETA: {eta}
⚡ Speed: {speed:.2f} users/sec
""", reply_markup=keyboard)
                        except:
                            pass
                else:
                    done += 1
                    failed += 1
            except Exception:
                failed += 1
                done += 1
                continue

        time_taken = timedelta(seconds=int(pytime.time() - start_time))
        final_progress = broadcast_progress_bar(total_users, total_users)
        final_text = f"""
✅ <b>Broadcast Completed</b> ✅

⏱ Duration: {time_taken}
👥 Total Users: {total_users}

📊 Results:
✅ Success: {success} ({(success/total_users)*100:.1f}%)
🚫 Blocked: {blocked} ({(blocked/total_users)*100:.1f}%)
❌ Deleted: {deleted} ({(deleted/total_users)*100:.1f}%)
⚠️ Failed: {failed} ({(failed/total_users)*100:.1f}%)

━━━━━━━━━━━━━━━━━━━━━━
{final_progress} 100%
━━━━━━━━━━━━━━━━━━━━━━

⚡ Speed: {speed:.2f} users/sec
"""
        await safe_action(sts.edit, final_text)
    except Exception as e:
        await safe_action(client.send_message,
            LOG_CHANNEL,
            f"⚠️ Broadcast Error:\n\n<code>{e}</code>\n\nTraceback:\n<code>{traceback.format_exc()}</code>."
        )
        print(f"⚠️ Broadcast Error: {e}")
        print(traceback.format_exc())

@Client.on_message(filters.command("stats") & filters.private & filters.user(ADMINS))
async def stats(client, message):
    try:
        me = await get_me_safe(client)
        if not me:
            return

        username = me.username
        users_count = await db.total_users_count()

        uptime = str(timedelta(seconds=int(pytime.time() - START_TIME)))

        await safe_action(message.reply_text,
            f"📊 Status for @{username}\n\n"
            f"👤 Users: {users_count}\n"
            f"⏱ Uptime: {uptime}\n",
        )
    except Exception as e:
        await safe_action(client.send_message,
            LOG_CHANNEL,
            f"⚠️ Stats Error:\n\n<code>{e}</code>\n\nTraceback:\n<code>{traceback.format_exc()}</code>."
        )
        print(f"⚠️ Stats Error: {e}")
        print(traceback.format_exc())

@Client.on_message(filters.command("premiumstats") & filters.private & filters.user(ADMINS))
async def premium_stats(client, message):
    try:
        now = datetime.utcnow()

        cursor = db.col.find({})
        active_counts = {k: 0 for k in PLAN_CATEGORY_MAP.keys()}
        expired_counts = {k: 0 for k in PLAN_CATEGORY_MAP.keys()}
        total_active = 0
        total_expired = 0

        async for user in cursor:
            plan_key = user.get("plan_key")
            expiry_str = user.get("expiry")
            active = user.get("active", False)

            if not plan_key:
                continue

            category = plan_key[:2]
            expiry = datetime.fromisoformat(expiry_str) if expiry_str else None

            if expiry and expiry > now and active:
                active_counts[category] += 1
                total_active += 1
            else:
                expired_counts[category] += 1
                total_expired += 1

        text = "📊 <b>Premium Stats</b>\n\n"
        text += f"👥 <b>Total Active:</b> {total_active}\n"
        text += f"💤 <b>Total Expired:</b> {total_expired}\n\n"

        for key, name in PLAN_CATEGORY_MAP.items():
            act = active_counts[key]
            exp = expired_counts[key]
            text += f"• <b>{name}</b> → {act} active / {exp} expired\n"

        await message.reply_text(text, parse_mode=enums.ParseMode.HTML)

    except Exception as e:
        await safe_action(client.send_message,
            LOG_CHANNEL,
            f"⚠️ Premium Stats Error:\n\n<code>{e}</code>\n\nTraceback:\n<code>{traceback.format_exc()}</code>."
        )
        print(f"⚠️ Premium Stats Error: {e}")
        print(traceback.format_exc())

@Client.on_callback_query()
async def callback(client, query):
    try:
        me = await get_me_safe(client)
        if not me:
            return

        user_id = query.from_user.id
        data = query.data

        global LAST_PAYMENT_CHECK, PAYMENT_CACHE

        # Start
        if data == "x0":
            buttons = [
                [InlineKeyboardButton("🌟 Our Premium Plans", callback_data="x1")],
                #[InlineKeyboardButton("📊 Check Your Subscription", callback_data="x2")],
                #[InlineKeyboardButton("♈ How To Buy Premium", url="https://t.me/Open_Shorten_Link_Tutorial/13")],
                [InlineKeyboardButton("🆘 Help & Support", callback_data="x3")]
            ]
            await safe_action(
                query.message.edit_text,
                text=(
                    "Hello👋 Members"
                    "\n\n🎖️ Welcome To The Premium Channel Subscription Bot"
                    "\n\nHere you can buy premium channels through our bot and get exclusive content instantly!"
                    "\n\n💳 Make payment and get your premium link right now in seconds."
                    "\n\n👇🏻 Please choose an option below:"
                ),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            await safe_action(query.answer)

        # Plans
        elif data == "x1":
            buttons = [
                [InlineKeyboardButton("🎬 Mixed Collection", callback_data="y1")],
                [InlineKeyboardButton("🕵️‍♂️ Cp/Rp Collection", callback_data="y2")],
                [InlineKeyboardButton("🚀 Mega Collection", callback_data="y3")],
                [InlineKeyboardButton("🔙 Back", callback_data="x0")]
            ]
            await safe_action(
                query.message.edit_text,
                text=(
                    "📋 Choose a plan below:"
                    "\n\n🔽 Select which premium channel plan you want to buy:"
                ),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            await safe_action(query.answer)

        # Demo & Price
        elif data == "y1":
            buttons = [
                [InlineKeyboardButton("🔥 Preview", url="https://t.me/XclusivePreviewBot?start=BATCH-NjhmZDFjZTczMjdkMTAyNjk2YjIxNzAz")],
                [InlineKeyboardButton("💰 ₹100 - 1️⃣ Month", callback_data="y1p1")],
                [InlineKeyboardButton("💰 ₹200 - 3️⃣ Month", callback_data="y1p2")],
                [InlineKeyboardButton("💰 ₹300 - 6️⃣ Month", callback_data="y1p3")],
                [InlineKeyboardButton("💰 ₹500 - Lifetime", callback_data="y1p4")],
                [InlineKeyboardButton("🔙 Back", callback_data="x1")]
            ]
            await safe_action(
                query.message.edit_text,
                text=(
                    "Available Plans👇🏻"
                    "\n•1 Month: ₹100"
                    "\n•3 Months: ₹200"
                    "\n•6 Months: ₹300"
                    "\n•Lifetime: ₹500"
                    "\n\nSelect A Plan To Subscribe Or Click 'Demo' To See A Preview📌"
                ),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            await safe_action(query.answer)

        # Payment menu when a price is selected
        elif data.startswith("y1p"):
            price_map = {
                "y1p1": ("₹100", "1️⃣ Month"),
                "y1p2": ("₹200", "3️⃣ Month"),
                "y1p3": ("₹300", "6️⃣ Month"),
                "y1p4": ("₹500", "Lifetime")
            }

            price, duration = price_map[data]

            buttons = [
                [InlineKeyboardButton("✅ Payment Done", callback_data=f"paid1_{data}")],
                [InlineKeyboardButton("🔙 Back", callback_data="y1")]
            ]

            upi_id = "krishxmehta@fam"
            upi_name = "KM Membership Bot"
            qr_image = generate_upi_qr(upi_id, upi_name, price)

            caption = (
                f"🎬 Mixed Collection\n\n"
                f"Selected Plan: {duration}\n"
                f"Price: {price}\n"
                f"UPI ID: `{upi_id}` \n\n"
                f"Once you pay, click ✅ Payment Done."
            )

            await safe_action(query.message.delete)

            await safe_action(
                client.send_photo,
                chat_id=query.message.chat.id,
                photo=qr_image,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.MARKDOWN
            )
            await safe_action(query.answer)

        # User clicked Payment Done
        elif data.startswith("paid1_"):
            plan_key = data.replace("paid1_", "")
            plan_map = {
                "y1p1": ("₹100", "1️⃣ Month"),
                "y1p2": ("₹200", "3️⃣ Month"),
                "y1p3": ("₹300", "6️⃣ Month"),
                "y1p4": ("₹500", "Lifetime")
            }

            if plan_key not in plan_map:
                return await query.message.edit_text("⚠️ Invalid plan key.")

            price, duration = plan_map[plan_key]
            amount_expected = int(price.replace("₹", ""))

            await safe_action(
                query.message.edit_text,
                text=(
                    f"🔍 Checking payment status...\n\n"
                    f"🎫 Plan: 🎬 Mixed Collection\n"
                    f"🕒 Duration: {duration}\n"
                    f"💰 Amount: ₹{amount_expected}\n"
                    f"⚡ Please wait while we verify your transaction."
                ),
                parse_mode=enums.ParseMode.MARKDOWN
            )

            now = datetime.now(pytz.UTC)

            # Fetch new TXNs every 30 seconds
            global LAST_PAYMENT_CHECK
            if (now.timestamp() - LAST_PAYMENT_CHECK) > 30:
                new_txns = await fetch_fampay_payments()
                for txn in new_txns:
                    if txn.get("time") and txn["time"].tzinfo is None:
                        txn["time"] = pytz.UTC.localize(txn["time"])
                    PAYMENT_CACHE[txn["txn_id"]] = txn
                LAST_PAYMENT_CHECK = now.timestamp()

            # -----------------------
            # FIND MATCHING TXN
            # -----------------------
            matched_txn = None
            for txn in sorted(PAYMENT_CACHE.values(), key=lambda x: x["time"], reverse=True):
                txn_id = txn["txn_id"]

                # 🚫 Already used → skip
                if txn_id in USED_TXNS:
                    continue

                txn_time = txn["time"].astimezone(pytz.UTC)
                txn_age = now - txn_time

                # Match valid same-amount, recent transaction
                if txn["amount"] == amount_expected and txn_age < timedelta(minutes=10):
                    matched_txn = txn
                    break

            # -----------------------
            # NO PAYMENT FOUND
            # -----------------------
            if not matched_txn:
                return await safe_action(
                    query.message.edit_text,
                    f"❌ No recent payment found for ₹{amount_expected}.\n\n"
                    "Please wait 1 minute and press **Payment Done** again.",
                    parse_mode=enums.ParseMode.MARKDOWN
                )

            # -----------------------
            # PAYMENT VERIFIED
            # -----------------------
            txn_id = matched_txn["txn_id"]

            # 🔒 Mark as USED (forever)
            USED_TXNS.add(txn_id)
            await db.save_used_txn(txn_id)

            channel_id = await db.get_plan_channel(plan_key)
            if not channel_id:
                channel_id = PLAN_CHANNEL_MAP.get(plan_key)
                if not channel_id:
                    return await safe_action(
                        query.message.edit_text,
                "⚠️ No channel assigned for this plan. Contact admin."
                    )

            user = query.from_user

            invite = await client.create_chat_invite_link(
                chat_id=channel_id,
                name=f"Access for {user.first_name}",
                member_limit=1
            )

            USER_LINKS[user.id] = {
                "chat_id": channel_id,
                "invite_link": invite.invite_link
            }

            # Admin alerts
            for admin_id in ADMINS:
                await safe_action(
                    client.send_message,
                    admin_id,
                    f"📢 <b>New Payment Verified</b>\n\n"
                    f"👤 <b>User:</b> {user.mention} (<code>{user.id}</code>)\n"
                    f"💬 <b>Username:</b> @{user.username or 'None'}\n"
                    f"🎫 <b>Plan:</b> 🎬 Mixed Collection\n"
                    f"🕒 <b>Duration:</b> {duration}\n"
                    f"💰 <b>Amount:</b> ₹{amount_expected}\n"
                    f"🧾 <b>Txn ID:</b> <code>{txn_id}</code>\n"
                    f"⏰ <b>Time:</b> {matched_txn['time']}\n"
                    f"🔗 <b>Invite Link:</b> {invite.invite_link}",
                    parse_mode=enums.ParseMode.HTML
                )

            # User message
            await safe_action(
                query.message.edit_text,
                f"✅ <b>Payment Verified!</b>\n\n"
                f"👤 User: {user.mention} (<code>{user.id}</code>)\n"
                f"🎫 Plan: 🎬 Mixed Collection\n"
                f"🕒 Duration: {duration}\n"
                f"💰 Amount: ₹{amount_expected}\n"
                f"🧾 Txn ID: <code>{txn_id}</code>\n"
                f"⏰ Time: {matched_txn['time']}\n\n"
                f"🎟️ Your Access Link:\n{invite.invite_link}\n\n"
                f"⚠️ Link expires after joining.",
                parse_mode=enums.ParseMode.HTML
            )

            # Handle expiry
            expiry_date = None
            if "1" in duration:
                expiry_date = datetime.utcnow() + timedelta(days=30)
            elif "3" in duration:
                expiry_date = datetime.utcnow() + timedelta(days=90)
            elif "6" in duration:
                expiry_date = datetime.utcnow() + timedelta(days=180)

            if expiry_date:
                await db.update_subscription(user.id, plan_key, channel_id, expiry_date)

                async def auto_kick_user():
                    await asyncio.sleep((expiry_date - datetime.utcnow()).total_seconds())
                    try:
                        await client.ban_chat_member(channel_id, user.id)
                        await client.unban_chat_member(channel_id, user.id)
                        await db.deactivate_subscription(user.id)
                        await client.send_message(
                            user.id,
                            f"⏰ Your {duration} premium has expired.\n"
                            "You’ve been removed from the channel.\n"
                        )
                    except Exception as e:
                        print(f"Failed to kick {user.id}: {e}")

                asyncio.create_task(auto_kick_user())

            await safe_action(query.answer)

        # Demo & Price
        elif data == "y2":
            buttons = [
                [InlineKeyboardButton("🔥 Preview", url="https://t.me/XclusivePreviewBot?start=BATCH-NjhmZDFlMjgzMjdkMTAyNjk2YjIxNzE4")],
                [InlineKeyboardButton("💰 ₹200 - 1️⃣ Month", callback_data="y2p1")],
                [InlineKeyboardButton("💰 ₹400 - 3️⃣ Months", callback_data="y2p2")],
                [InlineKeyboardButton("💰 ₹600 - 6️⃣ Months", callback_data="y2p3")],
                [InlineKeyboardButton("💰 ₹1000 - Lifetimes", callback_data="y2p4")],
                [InlineKeyboardButton("🔙 Back", callback_data="x1")]
            ]
            await safe_action(
                query.message.edit_text,
                text=(
                    "Available Plans👇🏻"
                    "\n•1 Month: ₹200"
                    "\n•3 Months: ₹400"
                    "\n•6 Months: ₹600"
                    "\n•Lifetime: ₹1000"
                    "\n\nSelect A Plan To Subscribe Or Click 'Demo' To See A Preview📌"
                ),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            await safe_action(query.answer)

        # Payment menu when a price is selected
        elif data.startswith("y2p"):
            price_map = {
                "y2p1": ("₹200", "1️⃣ Month"),
                "y2p2": ("₹400", "3️⃣ Month"),
                "y2p3": ("₹600", "6️⃣ Month"),
                "y2p4": ("₹1000", "Lifetime")
            }

            price, duration = price_map[data]

            buttons = [
                [InlineKeyboardButton("✅ Payment Done", callback_data=f"paid2_{data}")],
                [InlineKeyboardButton("🔙 Back", callback_data="y2")]
            ]

            upi_id = "krishxmehta@fam"
            upi_name = "KM Membership Bot"
            qr_image = generate_upi_qr(upi_id, upi_name, price)

            caption = (
                f"🕵️‍♂️ Cp/Rp Collection\n\n"
                f"Selected Plan: {duration}\n"
                f"Price: {price}\n"
                f"UPI ID: `{upi_id}` \n\n"
                f"Once you pay, click ✅ Payment Done."
            )

            await safe_action(query.message.delete)

            await safe_action(
                client.send_photo,
                chat_id=query.message.chat.id,
                photo=qr_image,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.MARKDOWN
            )
            await safe_action(query.answer)

        # User clicked Payment Done
        elif data.startswith("paid2_"):
            plan_key = data.replace("paid2_", "")
            plan_map = {
                "y2p1": ("₹200", "1️⃣ Month"),
                "y2p2": ("₹400", "3️⃣ Month"),
                "y2p3": ("₹600", "6️⃣ Month"),
                "y2p4": ("₹1000", "Lifetime")
            }

            if plan_key not in plan_map:
                return await query.message.edit_text("⚠️ Invalid plan key.")

            price, duration = plan_map[plan_key]
            amount_expected = int(price.replace("₹", ""))

            await safe_action(
                query.message.edit_text,
                text=(
                    f"🔍 Checking payment status...\n\n"
                    f"🎫 Plan: 🕵️‍♂️ Cp/Rp Collection\n"
                    f"🕒 Duration: {duration}\n"
                    f"💰 Amount: ₹{amount_expected}\n"
                    f"⚡ Please wait while we verify your transaction."
                ),
                parse_mode=enums.ParseMode.MARKDOWN
            )

            now = datetime.now(pytz.UTC)

            if (now.timestamp() - LAST_PAYMENT_CHECK) > 30:
                new_txns = await fetch_fampay_payments()
                for txn in new_txns:
                    if txn.get("time") and txn["time"].tzinfo is None:
                        txn["time"] = pytz.UTC.localize(txn["time"])
                    PAYMENT_CACHE[txn["txn_id"]] = txn
                LAST_PAYMENT_CHECK = now.timestamp()

            matched_txn = None
            for txn in sorted(PAYMENT_CACHE.values(), key=lambda x: x["time"], reverse=True):
                txn_time = txn["time"].astimezone(pytz.UTC)
                txn_age = now - txn_time
                if txn["amount"] == amount_expected and txn_age < timedelta(minutes=10):
                    matched_txn = txn
                    break

            if matched_txn:
                channel_id = await db.get_plan_channel(plan_key)
                if not channel_id:
                    channel_id = PLAN_CHANNEL_MAP.get(plan_key)
                    if not channel_id:
                        await safe_action(
                            query.message.edit_text,
                            "⚠️ No channel assigned for this plan. Contact admin."
                        )
                        return

                user = query.from_user

                invite = await client.create_chat_invite_link(
                    chat_id=channel_id,
                    name=f"Access for {user.first_name}",
                    member_limit=1
                )

                USER_LINKS[user.id] = {
                    "chat_id": channel_id,
                    "invite_link": invite.invite_link
                }

                for admin_id in ADMINS:
                    await safe_action(
                        client.send_message,
                        admin_id,
                        f"📢 <b>New Payment Verified</b>\n\n"
                        f"👤 <b>User:</b> {user.mention} (<code>{user.id}</code>)\n"
                        f"💬 <b>Username:</b> @{user.username or 'None'}\n"
                        f"🎫 <b>Plan:</b> 🕵️‍♂️ Cp/Rp Collection\n"
                        f"🕒 <b>Duration:</b> {duration}\n"
                        f"💰 <b>Amount:</b> ₹{amount_expected}\n"
                        f"🧾 <b>Txn ID:</b> <code>{matched_txn['txn_id']}</code>\n"
                        f"⏰ <b>Time:</b> {matched_txn['time']}"
                        f"🔗 <b>Invite Link:</b> {invite.invite_link}",
                        parse_mode=enums.ParseMode.HTML
                    )

                await safe_action(
                    query.message.edit_text,
                    f"✅ Payment verified!\n\n"
                    f"👤 User: {user.mention} (<code>{user.id}</code>)\n"
                    f"💬 Username: @{user.username or 'None'}\n"
                    f"🎫 Plan: 🕵️‍♂️ Cp/Rp Collection\n"
                    f"🕒 Duration: {duration}\n"
                    f"💰 Amount: ₹{amount_expected}\n"
                    f"🧾 Txn ID: <code>{matched_txn['txn_id']}</code>\n"
                    f"⏰ Time: {matched_txn['time']}"
                    f"🎟️ Your personal access link:\n{invite.invite_link}\n\n"
                    f"⚠️ This link will expire automatically after you join.",
                    parse_mode=enums.ParseMode.HTML
                )

                expiry_date = None
                if "1" in duration:
                    expiry_date = datetime.utcnow() + timedelta(days=30)
                elif "3" in duration:
                    expiry_date = datetime.utcnow() + timedelta(days=90)
                elif "6" in duration:
                    expiry_date = datetime.utcnow() + timedelta(days=180)
                elif "Life" in duration or "life" in duration:
                    expiry_date = None

                if expiry_date:
                    await db.update_subscription(user.id, plan_key, channel_id, expiry_date)

                    async def auto_kick_user():
                        await asyncio.sleep((expiry_date - datetime.utcnow()).total_seconds())
                        try:
                            await client.ban_chat_member(channel_id, user.id)
                            await client.unban_chat_member(channel_id, user.id)
                            await db.deactivate_subscription(user.id)
                            await client.send_message(
                                user.id,
                                f"⏰ Your {duration} premium access has expired.\n"
                                "You’ve been removed from the premium channel.\n\n"
                                "To renew, please purchase again.",
                                parse_mode=enums.ParseMode.HTML
                            )
                        except Exception as e:
                            print(f"Failed to kick {user.id}: {e}")

                    asyncio.create_task(auto_kick_user())
            else:
                await safe_action(
                    query.message.edit_text,
                    f"❌ No recent payment found for ₹{amount_expected}.\n\n"
                    f"Please wait 1 minute and click **Payment Done** again.",
                    parse_mode=enums.ParseMode.MARKDOWN
                )
            await safe_action(query.answer)

        # Demo & Price
        elif data == "y3":
            buttons = [
                [InlineKeyboardButton("🔥 Preview", url="https://t.me/XclusivePreviewBot?start=BATCH-NjhmZDFlZDIzMjdkMTAyNjk2YjIxNzI0")],
                [InlineKeyboardButton("💰 ₹200 - 1️⃣ Month", callback_data="y3p1")],
                [InlineKeyboardButton("💰 ₹400 - 3️⃣ Month", callback_data="y3p2")],
                [InlineKeyboardButton("💰 ₹600 - 6️⃣ Month", callback_data="y3p3")],
                [InlineKeyboardButton("💰 ₹1000 - Lifetime", callback_data="y3p4")],
                [InlineKeyboardButton("🔙 Back", callback_data="x1")]
            ]
            await safe_action(
                query.message.edit_text,
                text=(
                    "Available Plans👇🏻"
                    "\n•1 Month: ₹200"
                    "\n•3 Months: ₹400"
                    "\n•6 Months: ₹600"
                    "\n•Lifetime: ₹1000"
                    "\n\nSelect A Plan To Subscribe Or Click 'Demo' To See A Preview📌"
                ),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            await safe_action(query.answer)

        # Payment menu when a price is selected
        elif data.startswith("y3p"):
            price_map = {
                "y3p1": ("₹200", "1️⃣ Month"),
                "y3p2": ("₹400", "3️⃣ Month"),
                "y3p3": ("₹600", "6️⃣ Month"),
                "y3p4": ("₹1000", "Lifetime")
            }

            price, duration = price_map[data]

            buttons = [
                [InlineKeyboardButton("✅ Payment Done", callback_data=f"paid3_{data}")],
                [InlineKeyboardButton("🔙 Back", callback_data="y3")]
            ]

            upi_id = "krishxmehta@fam"
            upi_name = "KM Membership Bot"
            qr_image = generate_upi_qr(upi_id, upi_name, price)

            caption = (
                f"🚀 Mega Collection\n\n"
                f"Selected Plan: {duration}\n"
                f"Price: {price}\n"
                f"UPI ID: `{upi_id}` \n\n"
                f"Once you pay, click ✅ Payment Done."
            )

            await safe_action(query.message.delete)

            await safe_action(
                client.send_photo,
                chat_id=query.message.chat.id,
                photo=qr_image,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.MARKDOWN
            )
            await safe_action(query.answer)

        # User clicked Payment Done
        elif data.startswith("paid3_"):
            plan_key = data.replace("paid3_", "")
            plan_map = {
                "y3p1": ("₹200", "1️⃣ Month"),
                "y3p2": ("₹400", "3️⃣ Month"),
                "y3p3": ("₹600", "6️⃣ Month"),
                "y3p4": ("₹1000", "Lifetime")
            }

            if plan_key not in plan_map:
                return await query.message.edit_text("⚠️ Invalid plan key.")

            price, duration = plan_map[plan_key]
            amount_expected = int(price.replace("₹", ""))

            await safe_action(
                query.message.edit_text,
                text=(
                    f"🔍 Checking payment status...\n\n"
                    f"🎫 Plan: 🚀 Mega Collection\n"
                    f"🕒 Duration: {duration}\n"
                    f"💰 Amount: ₹{amount_expected}\n"
                    f"⚡ Please wait while we verify your transaction."
                ),
                parse_mode=enums.ParseMode.MARKDOWN
            )

            now = datetime.now(pytz.UTC)

            if (now.timestamp() - LAST_PAYMENT_CHECK) > 30:
                new_txns = await fetch_fampay_payments()
                for txn in new_txns:
                    if txn.get("time") and txn["time"].tzinfo is None:
                        txn["time"] = pytz.UTC.localize(txn["time"])
                    PAYMENT_CACHE[txn["txn_id"]] = txn
                LAST_PAYMENT_CHECK = now.timestamp()

            matched_txn = None
            for txn in sorted(PAYMENT_CACHE.values(), key=lambda x: x["time"], reverse=True):
                txn_time = txn["time"].astimezone(pytz.UTC)
                txn_age = now - txn_time
                if txn["amount"] == amount_expected and txn_age < timedelta(minutes=10):
                    matched_txn = txn
                    break

            if matched_txn:
                channel_id = await db.get_plan_channel(plan_key)
                if not channel_id:
                    channel_id = PLAN_CHANNEL_MAP.get(plan_key)
                    if not channel_id:
                        await safe_action(
                            query.message.edit_text,
                            "⚠️ No channel assigned for this plan. Contact admin."
                        )
                        return

                user = query.from_user

                invite = await client.create_chat_invite_link(
                    chat_id=channel_id,
                    name=f"Access for {user.first_name}",
                    member_limit=1
                )

                USER_LINKS[user.id] = {
                    "chat_id": channel_id,
                    "invite_link": invite.invite_link
                }

                for admin_id in ADMINS:
                    await safe_action(
                        client.send_message,
                        admin_id,
                        f"📢 <b>New Payment Verified</b>\n\n"
                        f"👤 <b>User:</b> {user.mention} (<code>{user.id}</code>)\n"
                        f"💬 <b>Username:</b> @{user.username or 'None'}\n"
                        f"🎫 <b>Plan:</b> 🚀 Mega Collection\n"
                        f"🕒 <b>Duration:</b> {duration}\n"
                        f"💰 <b>Amount:</b> ₹{amount_expected}\n"
                        f"🧾 <b>Txn ID:</b> <code>{matched_txn['txn_id']}</code>\n"
                        f"⏰ <b>Time:</b> {matched_txn['time']}"
                        f"🔗 <b>Invite Link:</b> {invite.invite_link}",
                        parse_mode=enums.ParseMode.HTML
                    )

                await safe_action(
                    query.message.edit_text,
                    f"✅ Payment verified!\n\n"
                    f"👤 User: {user.mention} (<code>{user.id}</code>)\n"
                    f"💬 Username: @{user.username or 'None'}\n"
                    f"🎫 Plan: 🚀 Mega Collection\n"
                    f"🕒 Duration: {duration}\n"
                    f"💰 Amount: ₹{amount_expected}\n"
                    f"🧾 Txn ID: <code>{matched_txn['txn_id']}</code>\n"
                    f"⏰ Time: {matched_txn['time']}"
                    f"🎟️ Your personal access link:\n{invite.invite_link}\n\n"
                    f"⚠️ This link will expire automatically after you join.",
                    parse_mode=enums.ParseMode.HTML
                )

                expiry_date = None
                if "1" in duration:
                    expiry_date = datetime.utcnow() + timedelta(days=30)
                elif "3" in duration:
                    expiry_date = datetime.utcnow() + timedelta(days=90)
                elif "6" in duration:
                    expiry_date = datetime.utcnow() + timedelta(days=180)
                elif "Life" in duration or "life" in duration:
                    expiry_date = None

                if expiry_date:
                    await db.update_subscription(user.id, plan_key, channel_id, expiry_date)

                    async def auto_kick_user():
                        await asyncio.sleep((expiry_date - datetime.utcnow()).total_seconds())
                        try:
                            await client.ban_chat_member(channel_id, user.id)
                            await client.unban_chat_member(channel_id, user.id)
                            await db.deactivate_subscription(user.id)
                            await client.send_message(
                                user.id,
                                f"⏰ Your {duration} premium access has expired.\n"
                                "You’ve been removed from the premium channel.\n\n"
                                "To renew, please purchase again.",
                                parse_mode=enums.ParseMode.HTML
                            )
                        except Exception as e:
                            print(f"Failed to kick {user.id}: {e}")

                    asyncio.create_task(auto_kick_user())
            else:
                await safe_action(
                    query.message.edit_text,
                    f"❌ No recent payment found for ₹{amount_expected}.\n\n"
                    f"Please wait 1 minute and click **Payment Done** again.",
                    parse_mode=enums.ParseMode.MARKDOWN
                )
            await safe_action(query.answer)

        # Help
        elif data == "x3":
            buttons = [
                [InlineKeyboardButton("📞 Contact Admin", url="https://t.me/PookieManagerBot")],
                [InlineKeyboardButton("🔙 Back", callback_data="x0")]
            ]
            await safe_action(
                query.message.edit_text,
                text=(
                    "💡 Help & Support"
                    "\n\nIf you have any questions or need assistance with your subscription, please contact our admin."
                    "\n\nFor common questions:"
                    "- To Subscribe: Select 'Our Premium Plans' from the main menu"
                    "- To Check Your Subscriptions: Select 'My Paid Subscriptions' from the main menu"
                    "- Payment Issues: Contact our admin directly"
                    "- Access Problems: Contact admin with your subscription details"
                    "- If You Need More Premium: Talk to our support admin"
                    "\n\nOur Support Admin: @admin"
                ),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            await safe_action(query.answer)

        else:
            await safe_action(
                client.send_message,
                LOG_CHANNEL,
                f"⚠️ Unknown Callback Data Received:\n\n{data}\n\nUser: {query.from_user.id}\n\nTraceback:\n<code>{traceback.format_exc()}</code>."
            )
            await safe_action(query.answer, "⚠️ Unknown action.", show_alert=True)
    except Exception as e:
        await safe_action(
            client.send_message,
            LOG_CHANNEL,
            f"⚠️ Callback Handler Error:\n\n<code>{e}</code>\n\nTraceback:\n<code>{traceback.format_exc()}</code>."
        )
        print(f"⚠️ Callback Handler Error: {e}")
        print(traceback.format_exc())
        await safe_action(query.answer, "❌ An error occurred. The admin has been notified.", show_alert=True)

@Client.on_chat_member_updated()
async def handle_member_join(client, event):
    try:
        if event.new_chat_member and event.new_chat_member.status == enums.ChatMemberStatus.MEMBER:
            user_id = event.new_chat_member.user.id
            chat_id = event.chat.id

            if user_id in USER_LINKS:
                info = USER_LINKS[user_id]
                link = info["invite_link"]

                try:
                    await client.revoke_chat_invite_link(chat_id, link)
                except Exception as e:
                    pass

                del USER_LINKS[user_id]
    except Exception as e:
        await safe_action(
            client.send_message,
            LOG_CHANNEL,
            f"⚠️ handle_member_join Error:\n\n<code>{e}</code>\n\nTraceback:\n<code>{traceback.format_exc()}</code>."
        )
        print(f"⚠️ handle_member_join Error: {e}")
        print(traceback.format_exc())