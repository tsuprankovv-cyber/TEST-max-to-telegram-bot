import os
import sys
import asyncio
from aiohttp import web
from config.settings import RENDER_EXTERNAL_URL, PORT
from config.logging_config import setup_logging, get_logger
from clients.max_client import MaxClient
from core.server import create_app
from config.settings import MAX_WEBHOOK_SECRET

logger = get_logger(__name__)

async def main():
    setup_logging()
    logger.info("=" * 100)
    logger.info("🚀 MAX → TELEGRAM FORWARDER [MODULAR]")
    logger.info("=" * 100)

    mx = MaxClient()
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
        await mx.register_webhook(webhook_url, MAX_WEBHOOK_SECRET)

    app = await create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()

    logger.info(f"🌐 Server running on port {PORT}")
    logger.info("✅ Ready!")

    await asyncio.Event().wait()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Stopped")
    except Exception as e:
        print(f"💥 FATAL: {e}")
        sys.exit(1)
