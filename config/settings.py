import os
import sys

# ===================================================================
# ОБЯЗАТЕЛЬНЫЕ ПЕРЕМЕННЫЕ
# ===================================================================
TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
TG_CHAT = os.getenv('TELEGRAM_CHAT_ID', '').strip()
MAX_TOKEN = os.getenv('MAX_TOKEN', '').strip()
MAX_CHAN = os.getenv('MAX_CHANNEL_ID', '').strip()

# ===================================================================
# ДОПОЛНИТЕЛЬНЫЕ
# ===================================================================
MAX_BASE = os.getenv('MAX_API_BASE', 'https://platform-api.max.ru').rstrip('/')
MAX_WEBHOOK_SECRET = os.getenv('MAX_WEBHOOK_SECRET', '').strip()
RENDER_EXTERNAL_URL = os.getenv('RENDER_EXTERNAL_URL', '').strip()
VERIFY_WEBHOOK_SECRET = os.getenv('VERIFY_WEBHOOK_SECRET', '1') == '1'
ADMIN_TG_ID = os.getenv('ADMIN_TG_ID', '').strip()
PORT = int(os.getenv('PORT', 8080))

# ===================================================================
# ПРОВЕРКА ОБЯЗАТЕЛЬНЫХ
# ===================================================================
if not all([TG_TOKEN, TG_CHAT, MAX_TOKEN, MAX_CHAN]):
    print("❌ FATAL: Missing required environment variables!")
    sys.exit(1)
