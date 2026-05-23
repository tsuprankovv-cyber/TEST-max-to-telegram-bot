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

# Приоритет тегов: чем МЕНЬШЕ число, тем ВЫШЕ приоритет (внешний тег)
TAG_PRIORITY = {'a': 1, 'u': 2, 's': 3, 'b': 4, 'i': 5, 'code': 6, 'pre': 7, 'tg-spoiler': 8}


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
    """
    Конвертирует разметку MAX в HTML Telegram.
    
    Алгоритм:
    1. Собираем все границы (точки, где меняется набор активных тегов)
    2. Разбиваем текст на сегменты по этим границам
    3. Для каждого сегмента определяем активные теги
    4. Оборачиваем сегмент в теги, сортируя по приоритету (внешние → внутренние)
    """
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
        if max_length <= 0:
            continue
        python_offset, python_length = normalize_max_offset(text, max_offset, max_length)
        entity['from'] = python_offset
        entity['length'] = python_length
        corrected_markup.append(entity)

    if not corrected_markup:
        return text

    # === Шаг 1: Собираем все границы ===
    boundaries = set()
    boundaries.add(0)
    boundaries.add(len(text))

    for entity in corrected_markup:
        boundaries.add(entity['from'])
        boundaries.add(entity['from'] + entity['length'])

    boundaries = sorted(boundaries)

    # === Шаг 2: Для каждого сегмента определяем активные теги ===
    segments = []  # [(start, end, [tags])]
    
    for i in range(len(boundaries) - 1):
        seg_start = boundaries[i]
        seg_end = boundaries[i + 1]
        mid_point = (seg_start + seg_end) // 2  # любая точка внутри сегмента
        
        active_tags = []
        for entity in corrected_markup:
            ent_start = entity['from']
            ent_end = entity['from'] + entity['length']
            if ent_start <= mid_point < ent_end:
                etype = entity.get('type', '')
                if etype in MAX_TAG_MAP:
                    tag_name = MAX_TAG_MAP[etype]
                    url = entity.get('url', '') if etype in ('link', 'text_link', 'url') else None
                    active_tags.append((tag_name, url, TAG_PRIORITY.get(tag_name, 99)))
        
        # Сортируем по приоритету (внешние → внутренние)
        active_tags.sort(key=lambda x: x[2])
        
        if seg_end > seg_start:
            segments.append((seg_start, seg_end, active_tags))

    # === Шаг 3: Собираем результат ===
    result = []
    
    for seg_start, seg_end, tags in segments:
        segment_text = text[seg_start:seg_end]
        if not segment_text:
            continue
        
        # Открываем теги (внешние → внутренние)
        for tag_name, url, _ in tags:
            if tag_name == 'a' and url:
                result.append(f'<a href="{url}">')
            else:
                result.append(f'<{tag_name}>')
        
        # Текст сегмента
        result.append(segment_text)
        
        # Закрываем теги (внутренние → внешние = обратный порядок)
        for tag_name, url, _ in reversed(tags):
            result.append(f'</{tag_name}>')

    final_text = ''.join(result)
    logger.info(f"Output length: {len(final_text)}")
    logger.debug(f"Output preview: {final_text[:300]}")
    return final_text
