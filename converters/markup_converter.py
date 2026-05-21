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

    sorted_markup = sorted(corrected_markup, key=lambda m: (m.get('from', 0), m.get('length', 0)))
    tag_starts = {}
    tag_ends = {}

    for entity in sorted_markup:
        offset = entity.get('from', 0)
        length = entity.get('length', 0)
        etype = entity.get('type', '')
        if etype not in MAX_TAG_MAP:
            continue
        tag_name = MAX_TAG_MAP[etype]
        if etype in ('link', 'text_link', 'url'):
            url = entity.get('url', '').replace('"', '&quot;')
            open_tag = f'<{tag_name} href="{url}">' if url else f'<{tag_name}>'
        else:
            open_tag = f'<{tag_name}>'
        tag_starts.setdefault(offset, []).append(open_tag)
        tag_ends.setdefault(offset + length, []).append(open_tag)

    result = []
    open_tags = []
    for i, char in enumerate(text):
        if i in tag_ends:
            for open_tag in reversed(open_tags):
                if open_tag in tag_ends[i]:
                    open_tags.remove(open_tag)
                    close_tag = f'</{open_tag.split()[0].strip("<>")}>'
                    result.append(close_tag)
        if i in tag_starts:
            sorted_tags = sorted(tag_starts[i], key=lambda t: TAG_ORDER.get(t.split()[0].strip('<>'), 99))
            for open_tag in sorted_tags:
                open_tags.append(open_tag)
                result.append(open_tag)
        result.append(char)
    for open_tag in reversed(open_tags):
        result.append(f'</{open_tag.split()[0].strip("<>")}>')

    final_text = ''.join(result)
    logger.info(f"Output length: {len(final_text)}")
    return final_text
