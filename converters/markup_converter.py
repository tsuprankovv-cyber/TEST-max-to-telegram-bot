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
    markup = filter_overlapping_same_type(markup)

    corrected_markup = []
    for entity in markup:
        entity = entity.copy()
        max_offset = entity.get('from', 0)
        max_length = entity.get('length', 0)
        python_offset, python_length = normalize_max_offset(text, max_offset, max_length)
        entity['from'] = python_offset
        entity['length'] = python_length
        corrected_markup.append(entity)

    sorted_markup = sorted(corrected_markup, key=lambda m: (m.get('from', 0), -m.get('length', 0)))

    # Строим карту: позиция -> список (действие, тег)
    # действие: +1 открыть, -1 закрыть
    events = []  # (pos, tag_name, url, action) action=1 open, -1 close
    for entity in sorted_markup:
        offset = entity.get('from', 0)
        length = entity.get('length', 0)
        etype = entity.get('type', '')
        if etype not in MAX_TAG_MAP:
            continue
        tag_name = MAX_TAG_MAP[etype]
        url = entity.get('url', '') if etype in ('link', 'text_link', 'url') else ''
        events.append((offset, tag_name, url, 1))  # open
        events.append((offset + length, tag_name, url, -1))  # close

    # Сортируем: сначала по позиции, потом закрытие перед открытием, потом по приоритету тегов
    def event_sort_key(e):
        pos, tag_name, url, action = e
        # Закрывающие перед открывающими на одной позиции
        action_priority = 0 if action == -1 else 1
        # Приоритет тега (для открывающих)
        tag_priority = TAG_ORDER.get(tag_name, 99)
        return (pos, action_priority, tag_priority if action == 1 else -tag_priority)

    events.sort(key=event_sort_key)

    result = []
    pos = 0

    # Стек открытых тегов: каждый элемент (tag_name, url)
    open_stack = []

    for event_pos, tag_name, url, action in events:
        # Добавляем текст до текущей позиции
        if event_pos > pos:
            result.append(text[pos:event_pos])
            pos = event_pos

        if action == 1:  # Открываем тег
            if url:
                open_tag = f'<{tag_name} href="{url}">'
            else:
                open_tag = f'<{tag_name}>'
            result.append(open_tag)
            open_stack.append((tag_name, url))
        else:  # Закрываем тег
            # Ищем в стеке и закрываем в правильном порядке (LIFO для того же тега)
            close_tag = f'</{tag_name}>'
            # Находим позицию тега в стеке (ищем с конца)
            found_idx = -1
            for i in range(len(open_stack) - 1, -1, -1):
                if open_stack[i][0] == tag_name and open_stack[i][1] == url:
                    found_idx = i
                    break

            if found_idx >= 0:
                # Закрываем все теги от вершины стека до найденного
                to_close = []
                for i in range(len(open_stack) - 1, found_idx - 1, -1):
                    close_t = f'</{open_stack[i][0]}>'
                    result.append(close_t)
                    to_close.append(i)
                # Удаляем из стека
                for i in sorted(to_close, reverse=True):
                    open_stack.pop(i)
                # Открываем обратно те, что были выше найденного
                for i in range(found_idx, len(open_stack)):
                    t_name, t_url = open_stack[i]
                    if t_url:
                        result.append(f'<{t_name} href="{t_url}">')
                    else:
                        result.append(f'<{t_name}>')

    # Добавляем оставшийся текст
    if pos < len(text):
        result.append(text[pos:])

    # Закрываем оставшиеся открытые теги
    for tag_name, url in reversed(open_stack):
        result.append(f'</{tag_name}>')

    final_text = ''.join(result)
    logger.info(f"Output length: {len(final_text)}")
    return final_text
