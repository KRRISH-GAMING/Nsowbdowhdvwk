import motor.motor_asyncio
from plugins.config import *
from datetime import datetime

class Database:

    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users

    def new_user(self, id, name):
        return dict(id=id, name=name)

    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await self.col.insert_one(user)

    async def is_user_exist(self, id):
        user = await self.col.find_one({"id": int(id)})
        return bool(user)

    async def total_users_count(self):
        return await self.col.count_documents({})

    async def get_all_users(self):
        return self.col.find({})

    async def delete_user(self, user_id):
        await self.col.delete_many({"id": int(user_id)})

    async def update_subscription(self, user_id, plan_key, channel_id, expiry):
        await self.col.update_one(
            {"id": int(user_id)},
            {
                "$set": {
                    "plan_key": plan_key,
                    "channel_id": channel_id,
                    "expiry": expiry.isoformat(),
                    "active": True
                }
            },
            upsert=True
        )

    async def get_active_subscriptions(self):
        now = datetime.utcnow().isoformat()
        return self.col.find({
            "active": True,
            "expiry": {"$gt": now}
        })

    async def deactivate_subscription(self, user_id):
        await self.col.update_one(
            {"id": int(user_id)},
            {"$set": {"active": False}}
        )

    async def get_user_subscription(self, user_id):
        return await self.col.find_one({"id": int(user_id)})

    async def get_active_users_by_category(self, category_prefix):
        now = datetime.utcnow().isoformat()
        cursor = self.col.find({
            "active": True,
            "expiry": {"$gt": now},
            "plan_key": {"$regex": f"^{category_prefix}"}
        })
        return [user async for user in cursor]

    async def update_plan_channel(self, plan_key, new_channel_id):
        await self.db.plan_channels.update_one(
            {"plan_key": plan_key},
            {"$set": {"channel_id": int(new_channel_id)}},
            upsert=True
        )

    async def get_plan_channel(self, plan_key):
        doc = await self.db.plan_channels.find_one({"plan_key": plan_key})
        return int(doc["channel_id"]) if doc and "channel_id" in doc else None

    async def save_used_txn(self, txn_id: str):
        await self.db.used_txns.update_one(
            {"txn_id": txn_id},
            {"$set": {"txn_id": txn_id}},
            upsert=True
        )

    async def is_txn_used(self, txn_id: str) -> bool:
        data = await self.db.used_txns.find_one({"txn_id": txn_id})
        return data is not None

    async def load_all_used_txns(self):
        cursor = self.db.used_txns.find({})
        return {doc["txn_id"] async for doc in cursor}

db = Database(DB_URI, DB_NAME)
