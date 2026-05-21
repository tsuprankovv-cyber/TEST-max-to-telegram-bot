import os
import asyncio
from config.logging_config import get_logger
from config.settings import ADMIN_TG_ID
from clients.telegram_client import TelegramClient
from utils.log_filter import filter_logs, get_period_from_preset

logger = get_logger(__name__)

tg = TelegramClient()

LOG_PERIOD_BUTTONS = {
    'inline_keyboard': [
        [{'text': '📅 За сегодня', 'callback_data': 'logs:today'}],
        [{'text': '📅 За вчера', 'callback_data': 'logs:yesterday'}],
        [{'text': '📅 За 3 дня', 'callback_data': 'logs:3d'}],
        [{'text': '📝 Последние 100 строк', 'callback_data': 'logs:100'}],
        [{'text': '🕐 За последний час', 'callback_data': 'logs:1h'}],
    ]
}

async def handle_logs_command(chat_id: str):
    logger.info(f"[LOGS] 📊 Logs requested from chat_id={chat_id}")

    if not ADMIN_TG_ID:
        logger.error("[LOGS] ❌ ADMIN_TG_ID not set")
        await tg.send_message(chat_id, "❌ ADMIN_TG_ID не настроен.")
        return

    await tg.send_message(
        chat_id,
        "📊 <b>Выберите период для логов:</b>",
        reply_markup=LOG_PERIOD_BUTTONS
    )
    logger.info("[LOGS] ✅ Menu sent")

async def handle_logs_callback(callback_query: dict):
    callback_id = callback_query.get('id')
    data = callback_query.get('data', '')
    message = callback_query.get('message', {})
    chat_id = str(message.get('chat', {}).get('id', ''))

    logger.info(f"[LOGS] 📊 Callback: data={data}, chat_id={chat_id}")

    if not data.startswith('logs:'):
        logger.warning(f"[LOGS] ⚠️ Unknown callback data: {data}")
        return

    preset = data.split(':', 1)[1]
    logger.info(f"[LOGS] Preset: {preset}")

    start_date, end_date, max_lines = get_period_from_preset(preset)
    logger.info(f"[LOGS] Filter: start={start_date}, end={end_date}, max_lines={max_lines}")

    await tg.answer_callback(callback_id, "⏳ Формирую логи...")

    content = filter_logs(start_date, end_date, max_lines)
    logger.info(f"[LOGS] Filtered content: {len(content)} chars")

    if content.startswith("Нет логов") or content.startswith("Лог-файл"):
        logger.warning(f"[LOGS] ⚠️ {content}")
        await tg.send_message(chat_id, f"⚠️ {content}")
        return

    filename = f"logs_{preset}.log"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    logger.info(f"[LOGS] 📄 File created: {filename} ({len(content)} bytes)")

    success = await tg.send_document(chat_id, filename)
    logger.info(f"[LOGS] 📤 File sent: {'✅' if success else '❌'}")

    if os.path.exists(filename):
        os.unlink(filename)
        logger.info(f"[LOGS] 🗑️ Temp file deleted: {filename}")

async def handle_status_command(chat_id: str):
    logger.info(f"[STATUS] 📊 Status requested from chat_id={chat_id}")

    from config.settings import MAX_CHAN, TG_CHAT
    status_text = "📊 <b>Статус бота:</b>\n\n"
    status_text += "✅ Бот активен\n"
    status_text += "🧩 Версия: modular-v2\n"
    status_text += f"📡 MAX канал: <code>{MAX_CHAN}</code>\n"
    status_text += f"📥 TG чат: <code>{TG_CHAT}</code>\n"
    status_text += f"👤 Admin ID: {ADMIN_TG_ID if ADMIN_TG_ID else '❌ не задан'}\n"

    await tg.send_message(chat_id, status_text)
    logger.info("[STATUS] ✅ Status sent")
