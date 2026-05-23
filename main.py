import os
import sys
import asyncio
from aiohttp import web
from config.settings import RENDER_EXTERNAL_URL, PORT, TG_CHAT, MAX_CHAN, TG_TOKEN, ADMIN_TG_ID
from config.logging_config import setup_logging, get_logger, LOG_LEVEL, LOG_RAW_MAX, LOG_RAW_TG, LOG_MARKUP, LOG_MEDIA
from clients.max_client import MaxClient
from core.server import create_app
from config.settings import MAX_WEBHOOK_SECRET

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

async def telegram_polling():
    """Фоновый опрос Telegram API для команд."""
    from handlers.commands import (
        handle_logs_command, handle_status_command, handle_logs_callback,
        handle_start_command
    )
    import aiohttp
    
    logger.info("📡 Starting Telegram polling for commands...")
    await asyncio.sleep(2)
    
    offset = 0
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates",
                    params={"offset": offset, "timeout": 30},
                    timeout=aiohttp.ClientTimeout(total=35)
                ) as r:
                    if r.status != 200:
                        continue
                    data = await r.json()
                    if not data.get('ok'):
                        continue
                    
                    for update in data['result']:
                        offset = update['update_id'] + 1
                        
                        if 'message' in update:
                            msg = update['message']
                            chat_id = str(msg.get('chat', {}).get('id', ''))
                            text = msg.get('text', '')
                            
                            if not ADMIN_TG_ID or chat_id != ADMIN_TG_ID:
                                logger.info(f"[POLLING] ⏭ Ignored message from {chat_id} (not admin)")
                                continue
                            
                            logger.info(f"[POLLING] 📨 Command: {text}")
                            
                            if text == '/start':
                                await handle_start_command(chat_id)
                            elif text == '/logs' or text == '📊 Логи':
                                await handle_logs_command(chat_id)
                            elif text == '/status' or text == '📈 Статус':
                                await handle_status_command(chat_id)
                        
                        elif 'callback_query' in update:
                            callback = update['callback_query']
                            logger.info(f"[POLLING] 🎯 Callback: {callback.get('data', '')}")
                            await handle_logs_callback(callback)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[POLLING] Error: {e}")
            await asyncio.sleep(5)

async def main():
    setup_logging()
    
    logger.info("=" * 100)
    logger.info("🚀 MAX → TELEGRAM FORWARDER [MODULAR v4]")
    logger.info("=" * 100)
    logger.info(f"📡 MAX Channel: {MAX_CHAN}")
    logger.info(f"📥 Telegram Chat: {TG_CHAT}")
    logger.info(f"👤 Admin TG ID: {ADMIN_TG_ID}")
    logger.info(f"📊 LOG_LEVEL: {LOG_LEVEL}")
    logger.info(f"🔗 Webhook URL: {RENDER_EXTERNAL_URL}/webhook" if RENDER_EXTERNAL_URL else "⚠️ RENDER_EXTERNAL_URL not set")
    logger.info("=" * 100)
    
    log_structure()

    mx = MaxClient()
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
        success = await mx.register_webhook(webhook_url, MAX_WEBHOOK_SECRET)
        logger.info(f"📡 MAX Webhook: {'✅ OK' if success else '❌ FAILED'}")

    asyncio.create_task(telegram_polling())

    app = await create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()

    logger.info(f"🌐 Server running on port {PORT}")
    logger.info("✅ Ready!")
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
