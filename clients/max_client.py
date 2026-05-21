import aiohttp
from config.settings import MAX_TOKEN, MAX_CHAN, MAX_BASE
from config.logging_config import get_logger

logger = get_logger(__name__)

class MaxClient:
    def __init__(self):
        self.token = MAX_TOKEN
        self.cid = MAX_CHAN
        self.base = MAX_BASE
        self.session = None
        logger.info(f"Initialized: cid={self.cid}")

    async def init(self):
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60))

    async def register_webhook(self, webhook_url: str, secret: str = "") -> bool:
        await self.init()
        logger.info(f"Registering webhook for chat {self.cid}: {webhook_url}")
        body = {"url": webhook_url, "chat_id": self.cid, "update_types": ["message_created"]}
        if secret:
            body["secret"] = secret
        try:
            async with self.session.post(
                f"{self.base}/subscriptions",
                headers={'Authorization': self.token},
                json=body
            ) as r:
                text = await r.text()
                logger.info(f"Response: {r.status} - {text}")
                return r.status == 200
        except Exception as e:
            logger.error(f"Failed: {e}")
            return False
