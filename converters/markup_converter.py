import re
from typing import List, Dict
from config.logging_config import get_logger
from utils.text_utils import normalize_max_offset, filter_overlapping_same_type

logger = get_logger(__name__)

MAX_TAG_MAP = {
    "strong": "b", "bold": "b", "b": "b",
    "emphasized": "i", "italic": "i", "em": "i", "i": "i",
    "underline": "u", "u": "u", "ins": "u",
    "strikethrough": "s", "strike": "s", "s": "s", "del": "s",
    "code": "code", "inline-code": "code", "pre": "pre",
    "spoiler": "tg-spoiler",
    "link": "a", "text_link": "a", "url": "a",
}

TAG_ORDER = {'a': 1, 'u': 2, 's': 3, 'b': 4, 'i': 5, 'code': 6, 'pre': 7, 'tg-spoiler': 8}

def parse_markdown_to_html(text: str) -> str:
    if not text:
        return text
    logger.info("Parsing markdown")
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'\+\+(.+?)\+\+', r'<u>\1</u>', text)
    text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text)
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
    return text


def apply_markup(text: str, markup: List[Dict]) -> str:
    if not markup or not text:
        return text

    logger.info(f"Applying markup: text_len={len(text)}, entities={len(markup)}")

    # Фильтруем вложенные сущности одного типа
    markup = filter_overlapping_same_type(markup)

    # Корректируем смещения (UTF-16 → Python)
    corrected_markup = []
    for entity in markup:
        entity = entity.copy()
        max_offset = entity.get('from', 0)
        max_length = entity.get('length', 0)
        python_offset, python_length = normalize_max_offset(text, max_offset, max_length)
        entity['from'] = python_offset
        entity['length'] = python_length
        corrected_markup.append(entity)

    # Создаём события: (позиция, тип_тега, url, действие)
    # действие: +1 = открыть, -1 = закрыть
    events = []
    for entity in corrected_markup:
        offset = entity.get('from', 0)
        length = entity.get('length', 0)
        etype = entity.get('type', '')
        if etype not in MAX_TAG_MAP:
            continue
        tag_name = MAX_TAG_MAP[etype]
        url = entity.get('url', '') if etype in ('link', 'text_link', 'url') else None
        if etype in ('link', 'text_link', 'url') and url:
            url = url.replace('"', '&quot;')
        events.append((offset, tag_name, url, 1))   # открытие
        events.append((offset + length, tag_name, url, -1))  # закрытие

    # Сортируем события:
    # 1. По позиции
    # 2. На одной позиции: закрытие перед открытием
    # 3. Открытие: по приоритету тега (a > u > s > b > i)
    # 4. Закрытие: обратный порядок
    def event_sort_key(e):
        pos, tag_name, url, action = e
        if action == -1:  # закрытие
            return (pos, 0, 0, 0)
        else:  # открытие
            tag_priority = TAG_ORDER.get(tag_name, 99)
            return (pos, 1, tag_priority, 0)

    events.sort(key=event_sort_key)

    result = []
    pos = 0
    open_tags = []  # стек: [(tag_name, url, unique_id)]

    for evt in events:
        evt_pos, tag_name, url, action = evt

        # Добавляем текст до события
        if evt_pos > pos:
            result.append(text[pos:evt_pos])
            pos = evt_pos

        if action == 1:  # Открытие
            if url:
                result.append(f'<{tag_name} href="{url}">')
            else:
                result.append(f'<{tag_name}>')
            open_tags.append(tag_name)

        else:  # Закрытие
            # Закрываем все теги от вершины стека до нашего тега (LIFO)
            temp_closed = []
            found = False
            while open_tags:
                top = open_tags.pop()
                result.append(f'</{top}>')
                temp_closed.append(top)
                if top == tag_name:
                    found = True
                    break

            if not found:
                # Тег не найден в стеке — значит уже был закрыт, игнорируем
                logger.warning(f"Tag </{tag_name}> not found in stack, skipping")

            # Открываем обратно те, что закрыли, но не являются целевым
            for t in reversed(temp_closed[:-1]):  # кроме последнего (целевого)
                if t in MAX_TAG_MAP.values():
                    result.append(f'<{t}>')
                    open_tags.append(t)

    # Добавляем остаток текста
    if pos < len(text):
        result.append(text[pos:])

    # Закрываем все оставшиеся открытые теги
    for t in reversed(open_tags):
        result.append(f'</{t}>')

    final_text = ''.join(result)
    logger.info(f"Output length: {len(final_text)}")
    logger.debug(f"Output preview: {final_text[:300]}")
    return final_text
