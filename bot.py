from pyrogram import Client
from plugins.config import cfg

class Bot(Client):

    def __init__(self):
        super().__init__(
        "KM Auto Accept Bot",
         api_id=cfg.API_ID,
         api_hash=cfg.API_HASH,
         bot_token=cfg.BOT_TOKEN,
         plugins=dict(root="plugins"),
         workers=50,
         sleep_threshold=10
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        self.username = '@' + me.username
        print('Bot Started.')
        await set_auto_menu(self)

    async def stop(self, *args):
        await super().stop()
        print('Bot Stopped Bye')

Bot().run()
