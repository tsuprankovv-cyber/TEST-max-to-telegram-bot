import json
import time
import asyncio
import tempfile
import os
from typing import Dict, List
from config.logging_config import get_logger, LOG_RAW_MAX
from config.settings import TG_CHAT
from clients.telegram_client import TelegramClient
from converters.markup_converter import apply_markup, parse_markdown_to_html
from converters.button_converter import convert_max_buttons, extract_keyboard_from_attachments
from converters.media_converter import MediaProcessor
from utils.text_utils import split_smart_text
from utils.audio_utils import extract_audio_tags, convert_to_voice, get_audio_duration
from utils.transliterator import safe_filename

logger = get_logger(__name__)

tg = TelegramClient()
media_proc = MediaProcessor()

async def download_from_url(url: str):
    if not url:
        logger.warning("[DOWNLOAD] Empty URL")
        return None
    logger.info(f"[DOWNLOAD] Starting: {url[:100]}...")
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=300)) as r:
                logger.info(f"[DOWNLOAD] Status: {r.status}")
                if r.status == 200:
                    data = await r.read()
                    logger.info(f"[DOWNLOAD] ✅ {len(data)} bytes")
                    return data
                logger.error(f"[DOWNLOAD] ❌ HTTP {r.status}")
                return None
    except Exception as e:
        logger.error(f"[DOWNLOAD] ❌ Exception: {e}")
        return None

async def process_attachment(att: Dict, caption: str = "", reply_markup=None) -> bool:
    start_time = time.time()
    logger.info(f"[ATT] Processing: caption_len={len(caption)}, has_reply_markup={reply_markup is not None}")
    
    if not isinstance(att, dict):
        logger.warning("[ATT] ❌ Not a dict, skipping")
        return False

    tg_type, meta = media_proc.determine(att)
    logger.info(f"[ATT] Type: {tg_type}, filename: {meta.get('filename')}, size: {meta.get('size')}")

    if tg_type == 'keyboard':
        logger.info("[ATT] ⏭ Skipping keyboard")
        return True

    direct_url = meta.get('url') or att.get('payload', {}).get('url')
    if not direct_url:
        logger.error("[ATT] ❌ No URL")
        return False

    if tg_type in ('photo', 'video') and direct_url:
        logger.info(f"[ATT] 📤 Sending {tg_type} via URL")
        result = await tg.send_media(tg_type, direct_url, caption, meta.get('filename', ''), is_url=True, reply_markup=reply_markup)
        elapsed = time.time() - start_time
        logger.info(f"[ATT] {'✅' if result else '❌'} Completed in {elapsed:.2f}s")
        return result

    file_data = await download_from_url(direct_url)
    if not file_data:
        logger.error("[ATT] ❌ Download failed")
        return False

    extra = {}
    if meta.get('original_type') == 'voice' and media_proc.ffmpeg_ok:
        voice_data = convert_to_voice(file_data)
        if voice_data:
            tg_type, file_data = 'voice', voice_data
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
                tmp.write(voice_data)
                extra['duration'] = get_audio_duration(tmp.name)
                os.unlink(tmp.name)
            logger.info(f"[ATT] ✅ Converted to voice, duration={extra['duration']}s")

    if tg_type == 'audio':
        extra.update(extract_audio_tags(file_data, meta.get('filename', '')))

    logger.info(f"[ATT] 📤 Sending {tg_type} to Telegram...")
    result = await tg.send_media(tg_type, file_data, caption, meta.get('filename', ''), False, **extra)
    elapsed = time.time() - start_time
    logger.info(f"[ATT] {'✅' if result else '❌'} Completed in {elapsed:.2f}s")
    return result

async def send_media_group(media_items: List[Dict], caption: str = "") -> bool:
    logger.info(f"[MEDIA-GROUP] Processing {len(media_items)} items, caption_len={len(caption)}")
    downloaded = []
    for item in media_items:
        url = item['meta'].get('url')
        if not url:
            continue
        data = await download_from_url(url)
        if data:
            downloaded.append({
                'type': item['type'],
                'data': data,
                'filename': safe_filename(item['meta'].get('filename', ''))
            })

    if not downloaded:
        logger.warning("[MEDIA-GROUP] No items downloaded")
        return False

    for i, item in enumerate(downloaded):
        await tg.send_media(item['type'], item['data'], caption=caption if i == 0 else "", filename=item['filename'])
        await asyncio.sleep(0.3)
    return True

def extract_message_data(msg: Dict) -> Dict:
    link = msg.get('link', {})
    is_forward = isinstance(link, dict) and link.get('type') == 'forward' and 'message' in link
    inner = link['message'] if is_forward else msg

    body = inner.get('body', {})
    text = body.get('text', '') or inner.get('text', '')
    markup = body.get('markup', []) or inner.get('markup', [])
    attachments = [a for a in (body.get('attachments') or inner.get('attachments') or []) if isinstance(a, dict)]
    reply_markup = inner.get('reply_markup') or msg.get('reply_markup')

    logger.info(f"[EXTRACT] text_len={len(text)}, markup={len(markup)}, attachments={len(attachments)}, is_forward={is_forward}")
    if LOG_RAW_MAX:
        for i, att in enumerate(attachments):
            logger.info(f"[EXTRACT] Attachment {i+1}: type={att.get('type')}, has_payload={'payload' in att}")
    
    return {
        "mid": body.get('mid', ''),
        "text": text,
        "markup": markup,
        "attachments": attachments,
        "is_forward": is_forward,
        "reply_markup": reply_markup
    }

async def handle_max_message(msg: Dict):
    start_time = time.time()
    logger.info("=" * 80)
    logger.info(f"[HANDLE] 🚀 Processing MAX message")

    if LOG_RAW_MAX:
        logger.debug(f"[HANDLE] Raw: {json.dumps(msg, ensure_ascii=False)[:2000]}")

    data = extract_message_data(msg)

    if not data['text'] and not data['attachments']:
        logger.info("[HANDLE] ⏭ Empty message, skipping")
        return

    text = data['text']
    logger.info(f"[HANDLE] Raw text length: {len(text)}")

    if data['markup']:
        logger.info(f"[HANDLE] Applying markup ({len(data['markup'])} entities)")
        text = apply_markup(text, data['markup'])
    elif text and ('*' in text or '_' in text or '[' in text):
        logger.info("[HANDLE] Using markdown parser")
        text = parse_markdown_to_html(text)

    logger.info(f"[HANDLE] Final text length: {len(text)}")

    # Разделяем вложения
    media_items, other = [], []
    for att in data['attachments']:
        if att.get('type') == 'inline_keyboard':
            continue
        t, m = media_proc.determine(att)
        item = {'type': t, 'attachment': att, 'meta': m}
        if t in ('photo', 'video'):
            media_items.append(item)
        else:
            other.append(item)

    logger.info(f"[HANDLE] Media: {len(media_items)} photo/video, Other: {len(other)} docs/audio")

    # Кнопки
    reply_markup = convert_max_buttons(data.get('reply_markup', {}))
    if not reply_markup:
        reply_markup = extract_keyboard_from_attachments(data['attachments'])
    logger.info(f"[HANDLE] Reply markup: {'✅' if reply_markup else '❌ None'}")

    if media_items:
        logger.info(f"[HANDLE] Processing {len(media_items)} media items")
        text_parts = split_smart_text(text, max_len=1000) if text else [""]
        caption = text_parts[0] if text_parts[0] else ""
        logger.info(f"[HANDLE] Text parts: {len(text_parts)}, caption_len={len(caption)}")

        first_reply_markup = reply_markup if len(text_parts) == 1 and caption else None
        logger.info(f"[HANDLE] First reply_markup: {'✅' if first_reply_markup else '❌ None'}")

        if len(media_items) == 1:
            logger.info("[HANDLE] 📷 Single media")
            await process_attachment(media_items[0]['attachment'], caption, reply_markup=first_reply_markup)
        else:
            logger.info(f"[HANDLE] 📸 Media group: {len(media_items)} items")
            await send_media_group(media_items, caption)

        remaining_parts = text_parts[1:]
        for i, part in enumerate(remaining_parts):
            is_last = (i == len(remaining_parts) - 1)
            logger.info(f"[HANDLE] 📝 Text part {i+2}/{len(text_parts)} with markup: {is_last}")
            await tg.send_message(TG_CHAT, part, reply_markup=reply_markup if is_last else None)

    elif text:
        logger.info("[HANDLE] 📝 Text only (no media)")
        text_parts = split_smart_text(text, max_len=4000) if len(text) > 4000 else [text]
        for i, part in enumerate(text_parts):
            is_last = (i == len(text_parts) - 1)
            await tg.send_message(TG_CHAT, part, reply_markup=reply_markup if is_last else None)

    for i, item in enumerate(other):
        logger.info(f"[HANDLE] 📎 Other attachment {i+1}/{len(other)}")
        await process_attachment(item['attachment'], "")
        await asyncio.sleep(0.5)

    elapsed = time.time() - start_time
    logger.info(f"[HANDLE] ✅ Complete in {elapsed:.2f}s")
    logger.info("=" * 80)
