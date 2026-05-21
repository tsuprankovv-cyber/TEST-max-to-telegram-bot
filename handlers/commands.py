import asyncio
from config.logging_config import get_logger
from config.settings import ADMIN_TG_ID
from clients.telegram_client import TelegramClient
from utils.log_filter import filter_logs, get_period_from_preset, get_log_file_for_period

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
    logger.info(f"Logs command from chat_id={chat_id}")

    if not ADMIN_TG_ID:
        await tg.send_message(chat_id, "❌ ADMIN_TG_ID не настроен. Логи недоступны.")
        return

    await tg.send_message(
        chat_id,
        "📊 <b>Выберите период для логов:</b>",
        reply_markup=LOG_PERIOD_BUTTONS
    )

async def handle_logs_callback(callback_query: dict):
    callback_id = callback_query.get('id')
    data = callback_query.get('data', '')
    message = callback_query.get('message', {})
    chat_id = str(message.get('chat', {}).get('id', ''))

    logger.info(f"Logs callback: data={data}, chat_id={chat_id}")

    if not data.startswith('logs:'):
        return

    preset = data.split(':', 1)[1]
    start_date, end_date, max_lines = get_period_from_preset(preset)

    await tg.answer_callback(callback_id, "⏳ Формирую логи...")

    content = filter_logs(start_date, end_date, max_lines)

    if content.startswith("Нет логов") or content.startswith("Лог-файл"):
        await tg.send_message(chat_id, f"⚠️ {content}")
        return

    filename = f"logs_{preset}.log"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

    await tg.send_document(chat_id, filename)

    import os
    os.unlink(filename)
    logger.info(f"Logs sent: {filename}")

async def handle_status_command(chat_id: str):
    logger.info(f"Status command from chat_id={chat_id}")

    status_text = "📊 <b>Статус бота:</b>\n\n"
    status_text += "✅ Бот активен\n"

    from config.settings import MAX_CHAN, TG_CHAT
    status_text += f"📡 MAX канал: <code>{MAX_CHAN}</code>\n"
    status_text += f"📥 TG чат: <code>{TG_CHAT}</code>\n"

    await tg.send_message(chat_id, status_text)
