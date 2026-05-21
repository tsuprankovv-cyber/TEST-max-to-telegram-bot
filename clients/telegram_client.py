import json
import time
import asyncio
import os
import aiohttp
from typing import Dict, Optional, List
from config.settings import TG_TOKEN, TG_CHAT
from config.logging_config import get_logger, LOG_RAW_TG
from utils.html_utils import fix_broken_html
from utils.transliterator import safe_filename

logger = get_logger(__name__)

class TelegramClient:
    def __init__(self):
        self.token = TG_TOKEN
        self.chat_id = TG_CHAT
        self.base = f"https://api.telegram.org/bot{self.token}"
        self.session = None
        logger.info(f"Initialized: chat_id={self.chat_id}")

    async def init(self):
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120))

    async def _request(self, method: str, **kw) -> Optional[Dict]:
        await self.init()
        logger.info(f"▶️ {method}")
        if LOG_RAW_TG:
            logger.debug(f"Request: {json.dumps(kw, default=str, ensure_ascii=False)[:500]}")

        start_time = time.time()
        try:
            async with self.session.post(f"{self.base}/{method}", **kw) as r:
                txt = await r.text()
                elapsed = time.time() - start_time
                logger.info(f"Status: {r.status} in {elapsed:.2f}s")
                logger.info(f"Response: {txt[:500]}")

                resp = json.loads(txt)
                if r.status == 200 and resp.get('ok'):
                    return resp
                elif r.status == 429:
                    wait = resp.get('parameters', {}).get('retry_after', 10)
                    logger.warning(f"Rate limit, waiting {wait}s")
                    await asyncio.sleep(wait)
                    return await self._request(method, **kw)
                else:
                    logger.error(f"Error: {resp.get('description')}")
                    return resp
        except Exception as e:
            logger.error(f"Exception: {e}")
            return None

    async def send_message(self, chat_id: str, text: str, reply_markup: Optional[Dict] = None) -> bool:
        if not text:
            return True
        text = fix_broken_html(text)
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': False
        }
        if reply_markup:
            payload['reply_markup'] = reply_markup
        resp = await self._request('sendMessage', json=payload)
        return resp and resp.get('ok', False)

    async def send_document(self, chat_id: str, file_path: str) -> bool:
        logger.info(f"Sending document: {file_path}")
        form = aiohttp.FormData()
        form.add_field('chat_id', chat_id)
        
        # Читаем файл в память перед отправкой, чтобы избежать "I/O operation on closed file"
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        filename = os.path.basename(file_path)
        form.add_field('document', file_data, filename=filename)
        resp = await self._request('sendDocument', data=form)
        return resp and resp.get('ok', False)

    async def send_media(self, media_type: str, media_data, caption="", filename="", is_url=False, reply_markup=None, **extra) -> bool:
        method_map = {
            'photo': 'sendPhoto', 'video': 'sendVideo',
            'audio': 'sendAudio', 'voice': 'sendVoice',
            'document': 'sendDocument'
        }
        method = method_map.get(media_type, 'sendDocument')
        field = media_type if media_type != 'document' else 'document'

        form = aiohttp.FormData()
        form.add_field('chat_id', self.chat_id)

        if is_url:
            form.add_field(field, media_data)
        else:
            fname = safe_filename(filename) if filename else f"{media_type}.file"
            form.add_field(field, media_data, filename=fname)

        if caption:
            caption = fix_broken_html(caption)
            form.add_field('caption', caption)
            form.add_field('parse_mode', 'HTML')

        if reply_markup and caption and media_type in ('photo', 'video'):
            form.add_field('reply_markup', json.dumps(reply_markup))

        if media_type == 'audio':
            if extra.get('performer'):
                form.add_field('performer', extra['performer'][:64])
            if extra.get('title'):
                form.add_field('title', extra['title'][:64])
            if extra.get('duration'):
                form.add_field('duration', str(extra['duration']))
        if media_type == 'voice' and extra.get('duration'):
            form.add_field('duration', str(extra['duration']))

        resp = await self._request(method, data=form)
        return resp and resp.get('ok', False)

    async def answer_callback(self, callback_id: str, text: str = "") -> bool:
        resp = await self._request('answerCallbackQuery', json={
            'callback_query_id': callback_id,
            'text': text
        })
        return resp and resp.get('ok', False)
