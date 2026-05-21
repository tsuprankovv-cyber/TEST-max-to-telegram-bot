import os
import sys
import asyncio
from aiohttp import web
from config.settings import RENDER_EXTERNAL_URL, PORT, TG_CHAT, MAX_CHAN
from config.logging_config import setup_logging, get_logger, LOG_LEVEL, LOG_RAW_MAX, LOG_RAW_TG, LOG_MARKUP, LOG_MEDIA
from clients.max_client import MaxClient
from core.server import create_app
from config.settings import MAX_WEBHOOK_SECRET, ADMIN_TG_ID

logger = get_logger(__name__)

def log_structure():
    """Логирует структуру модулей для самопроверки."""
    logger.info("=" * 80)
    logger.info("📦 MODULE STRUCTURE CHECK")
    logger.info("=" * 80)
    
    modules = [
        ("config.settings", "config/settings.py"),
        ("config.logging_config", "config/logging_config.py"),
        ("utils.html_utils", "utils/html_utils.py"),
        ("utils.transliterator", "utils/transliterator.py"),
        ("utils.text_utils", "utils/text_utils.py"),
        ("utils.audio_utils", "utils/audio_utils.py"),
        ("utils.log_filter", "utils/log_filter.py"),
        ("clients.telegram_client", "clients/telegram_client.py"),
        ("clients.max_client", "clients/max_client.py"),
        ("converters.markup_converter", "converters/markup_converter.py"),
        ("converters.button_converter", "converters/button_converter.py"),
        ("converters.media_converter", "converters/media_converter.py"),
        ("handlers.message_handler", "handlers/message_handler.py"),
        ("handlers.commands", "handlers/commands.py"),
        ("core.server", "core/server.py"),
    ]
    
    for module_name, file_path in modules:
        try:
            __import__(module_name)
            logger.info(f"✅ {file_path} — loaded")
        except Exception as e:
            logger.error(f"❌ {file_path} — FAILED: {e}")
    
    logger.info("=" * 80)

async def main():
    setup_logging()
    
    logger.info("=" * 100)
    logger.info("🚀 MAX → TELEGRAM FORWARDER [MODULAR]")
    logger.info("=" * 100)
    logger.info(f"📡 MAX Channel: {MAX_CHAN}")
    logger.info(f"📥 Telegram Chat: {TG_CHAT}")
    logger.info(f"👤 Admin TG ID: {ADMIN_TG_ID}")
    logger.info(f"📊 LOG_LEVEL: {LOG_LEVEL}")
    logger.info(f"📊 LOG_RAW_MAX: {LOG_RAW_MAX}")
    logger.info(f"📊 LOG_RAW_TG: {LOG_RAW_TG}")
    logger.info(f"📊 LOG_MARKUP: {LOG_MARKUP}")
    logger.info(f"📊 LOG_MEDIA: {LOG_MEDIA}")
    logger.info(f"🔗 Webhook URL: {RENDER_EXTERNAL_URL}/webhook" if RENDER_EXTERNAL_URL else "⚠️ RENDER_EXTERNAL_URL not set")
    logger.info("=" * 100)
    
    # Проверка структуры модулей
    log_structure()

    mx = MaxClient()
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
        success = await mx.register_webhook(webhook_url, MAX_WEBHOOK_SECRET)
        logger.info(f"📡 Webhook registration: {'✅ OK' if success else '❌ FAILED'}")

    app = await create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()

    logger.info(f"🌐 Server running on port {PORT}")
    logger.info("✅ Ready to receive messages!")
    logger.info("=" * 100)

    await asyncio.Event().wait()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Stopped")
    except Exception as e:
        print(f"💥 FATAL: {e}")
        sys.exit(1)
