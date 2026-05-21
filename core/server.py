import json
import asyncio
from aiohttp import web
from config.logging_config import get_logger
from config.settings import ADMIN_TG_ID
from handlers.message_handler import handle_max_message
from handlers.commands import handle_logs_command, handle_logs_callback, handle_status_command

logger = get_logger(__name__)

async def webhook_handler(request):
    if request.method != 'POST':
        logger.warning(f"[WEBHOOK] Invalid method: {request.method}")
        return web.Response(status=405)

    try:
        body = await request.json()
        update_type = body.get('update_type', 'unknown')
        logger.info(f"[WEBHOOK] 📨 Update type: {update_type}")
        logger.info(f"[WEBHOOK] Body: {json.dumps(body, ensure_ascii=False)[:500]}")

        if update_type == 'message_created' and (msg := body.get('message')):
            text = msg.get('body', {}).get('text', '')
            logger.info(f"[WEBHOOK] Message text: {text[:100] if text else '(empty)'}")

            # Проверка команд
            if text and text.strip().startswith('/logs'):
                logger.info("[WEBHOOK] 🎯 /logs command detected")
                if ADMIN_TG_ID:
                    logger.info(f"[WEBHOOK] Sending logs menu to admin: {ADMIN_TG_ID}")
                    asyncio.create_task(handle_logs_command(ADMIN_TG_ID))
                else:
                    logger.warning("[WEBHOOK] ❌ ADMIN_TG_ID not set, cannot send logs")
                return web.Response(status=200)

            if text and text.strip().startswith('/status'):
                logger.info("[WEBHOOK] 🎯 /status command detected")
                if ADMIN_TG_ID:
                    asyncio.create_task(handle_status_command(ADMIN_TG_ID))
                return web.Response(status=200)

            # Обычное сообщение — пересылаем
            asyncio.create_task(handle_max_message(msg))

        elif update_type == 'callback_query':
            callback = body.get('callback_query', body)
            logger.info(f"[WEBHOOK] 🎯 Callback query: {callback.get('data', '')[:50]}")
            asyncio.create_task(handle_logs_callback(callback))

        else:
            logger.info(f"[WEBHOOK] ⏭ Skipping update_type={update_type}")

        return web.Response(status=200)

    except json.JSONDecodeError as e:
        logger.error(f"[WEBHOOK] ❌ Invalid JSON: {e}")
        return web.Response(status=400)
    except Exception as e:
        logger.error(f"[WEBHOOK] ❌ Exception: {e}", exc_info=True)
        return web.Response(status=500)

async def health_handler(request):
    return web.json_response({
        'ok': True,
        'version': 'modular-v2',
        'admin_tg_id_set': bool(ADMIN_TG_ID)
    })

async def create_app():
    app = web.Application()
    app.router.add_post('/webhook', webhook_handler)
    app.router.add_get('/health', health_handler)
    logger.info("[SERVER] Routes registered: POST /webhook, GET /health")
    return app
