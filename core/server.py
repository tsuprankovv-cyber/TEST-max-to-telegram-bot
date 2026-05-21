import json
import asyncio
from aiohttp import web
from config.logging_config import get_logger
from handlers.message_handler import handle_max_message

logger = get_logger(__name__)

async def webhook_handler(request):
    if request.method != 'POST':
        logger.warning(f"[WEBHOOK] Invalid method: {request.method}")
        return web.Response(status=405)

    try:
        body = await request.json()
        update_type = body.get('update_type', 'unknown')
        logger.info(f"[WEBHOOK] 📨 Update type: {update_type}")
        logger.info(f"[WEBHOOK] Body: {json.dumps(body, ensure_ascii=False)[:300]}")

        if update_type == 'message_created' and (msg := body.get('message')):
            text = msg.get('body', {}).get('text', '')
            logger.info(f"[WEBHOOK] Message: {text[:80] if text else '(empty)'}")
            asyncio.create_task(handle_max_message(msg))

        return web.Response(status=200)

    except json.JSONDecodeError as e:
        logger.error(f"[WEBHOOK] ❌ Invalid JSON: {e}")
        return web.Response(status=400)
    except Exception as e:
        logger.error(f"[WEBHOOK] ❌ Exception: {e}", exc_info=True)
        return web.Response(status=500)

async def health_handler(request):
    from config.settings import ADMIN_TG_ID
    return web.json_response({
        'ok': True,
        'version': 'modular-v3',
        'admin_tg_id_set': bool(ADMIN_TG_ID)
    })

async def create_app():
    app = web.Application()
    app.router.add_post('/webhook', webhook_handler)
    app.router.add_get('/health', health_handler)
    logger.info("[SERVER] Routes: POST /webhook, GET /health")
    return app
