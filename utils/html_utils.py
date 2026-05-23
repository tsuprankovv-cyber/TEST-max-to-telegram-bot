import re
from config.logging_config import get_logger

logger = get_logger(__name__)

def remove_empty_tags(text: str) -> str:
    """Удаляет пустые HTML-теги."""
    if not text:
        return text
    for tag in ['b', 'i', 'u', 's', 'code', 'pre', 'a', 'tg-spoiler']:
        text = re.sub(f'<{tag}></{tag}>', '', text)
        text = re.sub(f'<{tag} [^>]*></{tag}>', '', text)
    return text


def fix_broken_html(text: str) -> str:
    """
    Исправляет битый HTML: добавляет недостающие закрывающие теги
    в правильном порядке (LIFO — последний открытый закрывается первым).
    """
    if not text:
        return text

    logger.debug(f"HTML-FIX input: {len(text)} chars")

    # Находим все открывающие и закрывающие теги
    open_tags = re.findall(r'<([a-zA-Z]+)[^>/]*>', text)  # только имя тега
    close_tags = re.findall(r'</([a-zA-Z]+)>', text)

    # Стек: симулируем открытие/закрытие
    stack = []
    # Разбираем текст последовательно
    pos = 0
    result_parts = [text]

    # Считаем баланс
    tag_balance = {}
    for tag in set(open_tags + close_tags):
        tag_balance[tag] = open_tags.count(tag) - close_tags.count(tag)

    # Добавляем недостающие закрывающие теги в порядке LIFO
    # Берём порядок открытия из оригинального текста
    open_order = []
    for match in re.finditer(r'<([a-zA-Z]+)[^>/]*>', text):
        tag = match.group(1)
        if tag not in open_order:
            open_order.append(tag)

    # Закрываем в обратном порядке
    suffix = ''
    for tag in reversed(open_order):
        if tag_balance.get(tag, 0) > 0:
            suffix += f'</{tag}>'
            tag_balance[tag] -= 1
            logger.warning(f"HTML-FIX: Added </{tag}>")

    if suffix:
        text = text + suffix

    # Удаляем пустые теги
    text = remove_empty_tags(text)

    logger.debug(f"HTML-FIX output: {len(text)} chars")
    return text
