from os import path, getenv

API_ID = int(getenv("API_ID", "15479023"))
API_HASH = getenv("API_HASH", "f8f6cf547822449c29fc60dae3b31dd4")
BOT_TOKEN = getenv("BOT_TOKEN", "8060569801:AAEk1tmmpaUfIyydSe20TASfscafotRbqKA")

# Your Force Subscribe Channel Id Below 
CHANNEL = int(getenv("CHANNEL", "-1002829948273")) # Make Bot Admin In This Channel

# Admin Or Owner Id Below
ADMIN = list(map(int, getenv("ADMIN", "1512442581").split()))

MONGO_URI = getenv("MONGO_URI", "mongodb+srv://KM-AutoAccept:KM-AutoAccept123@km-autoaccept.restswy.mongodb.net/?retryWrites=true&w=majority&appName=KM-AutoAccept")
