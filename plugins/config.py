from os import path, getenv

API_ID = int(getenv("API_ID", "35384565"))
API_HASH = getenv("API_HASH", "dbba8a136120df358bd3b6e1fbc18792")
BOT_TOKEN = getenv("BOT_TOKEN", "8060569801:AAEk1tmmpaUfIyydSe20TASfscafotRbqKA")

# Your Force Subscribe Channel Id Below 
CHANNEL = int(getenv("CHANNEL", "-1002829948273")) # Make Bot Admin In This Channel

# Admin Or Owner Id Below
ADMIN = list(map(int, getenv("ADMIN", "8477930865").split()))

MONGO_URI = getenv("MONGO_URI", "mongodb+srv://KM-AutoAccept:KM-AutoAccept123@km-autoaccept.restswy.mongodb.net/?retryWrites=true&w=majority&appName=KM-AutoAccept")
