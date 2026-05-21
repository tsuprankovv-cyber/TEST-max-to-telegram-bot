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
        return web.Response(status=405)

    try:
        body = await request.json()
        update_type = body.get('update_type', 'unknown')
        logger.info(f"Webhook: update_type={update_type}")

        if update_type == 'message_created' and (msg := body.get('message')):
            text = msg.get('body', {}).get('text', '')

            if text and text.strip().startswith('/logs'):
                logger.info("Detected /logs command in MAX")
                if ADMIN_TG_ID:
                    asyncio.create_task(handle_logs_command(ADMIN_TG_ID))
                return web.Response(status=200)

            if text and text.strip().startswith('/status'):
                logger.info("Detected /status command in MAX")
                if ADMIN_TG_ID:
                    asyncio.create_task(handle_status_command(ADMIN_TG_ID))
                return web.Response(status=200)

            asyncio.create_task(handle_max_message(msg))

        elif update_type == 'callback_query':
            callback = body.get('callback_query', body)
            asyncio.create_task(handle_logs_callback(callback))

        return web.Response(status=200)

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        return web.Response(status=400)
    except Exception as e:
        logger.error(f"Exception: {e}", exc_info=True)
        return web.Response(status=500)

async def health_handler(request):
    return web.json_response({'ok': True, 'version': 'modular-v1'})

async def create_app():
    app = web.Application()
    app.router.add_post('/webhook', webhook_handler)
    app.router.add_get('/health', health_handler)
    return app
