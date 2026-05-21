import os
from datetime import datetime, timedelta
from config.logging_config import get_logger

logger = get_logger(__name__)

LOG_FILE = 'bot_debug.log'

def filter_logs(
    start_date: str = None,
    end_date: str = None,
    max_lines: int = None
) -> str:
    if not os.path.exists(LOG_FILE):
        logger.warning(f"Log file {LOG_FILE} not found")
        return "Лог-файл не найден."

    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if not lines:
        return "Лог-файл пуст."

    if start_date:
        lines = [l for l in lines if l[:10] >= start_date]
    if end_date:
        lines = [l for l in lines if l[:10] <= end_date]
    if max_lines:
        lines = lines[-max_lines:]

    if not lines:
        return "Нет логов за выбранный период."

    logger.info(f"Filtered {len(lines)} log lines")
    return ''.join(lines)

def get_log_file_for_period(start_date: str, end_date: str) -> str:
    content = filter_logs(start_date, end_date)
    filename = f"logs_{start_date}_{end_date}.log"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    return filename

def get_period_from_preset(preset: str) -> tuple:
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    presets = {
        '1h': (None, None, None),  # особый случай - фильтр по времени
        'today': (today, today, None),
        'yesterday': (yesterday, yesterday, None),
        '3d': ((datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'), today, None),
        '100': (None, None, 100),
    }

    return presets.get(preset, (today, today, None))
