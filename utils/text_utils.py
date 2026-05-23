import re
from typing import List, Tuple
from config.logging_config import get_logger

logger = get_logger(__name__)

# === HTML utils for safe splitting ===

def _get_open_tags(text: str) -> List[str]:
    """Возвращает список имён открытых тегов в порядке открытия."""
    tags = []
    for match in re.finditer(r'<([a-zA-Z]+)[^>/]*>', text):
        tags.append(match.group(1))
    return tags

def _get_close_tags(text: str) -> List[str]:
    """Возвращает список имён закрытых тегов."""
    tags = []
    for match in re.finditer(r'</([a-zA-Z]+)>', text):
        tags.append(match.group(1))
    return tags

def _get_unclosed_tags(text: str) -> List[str]:
    """Возвращает стек незакрытых тегов (LIFO)."""
    stack = []
    # Находим все теги по порядку
    for match in re.finditer(r'</?([a-zA-Z]+)[^>]*>', text):
        full_tag = match.group(0)
        tag_name = match.group(1)
        if full_tag.startswith('</'):
            # Закрывающий — убираем из стека
            if stack and stack[-1] == tag_name:
                stack.pop()
        else:
            # Открывающий
            stack.append(tag_name)
    return stack

def _close_tags(text: str, unclosed: List[str]) -> str:
    """Добавляет закрывающие теги в правильном порядке (LIFO)."""
    for tag in reversed(unclosed):
        text += f'</{tag}>'
    return text

def _open_tags(text: str, unclosed: List[str]) -> str:
    """Добавляет открывающие теги в начале текста."""
    for tag in unclosed:
        text = f'<{tag}>' + text
    return text

def _strip_orphan_close_tags(text: str) -> str:
    """Убирает закрывающие теги без открывающих в начале текста."""
    # Находим все закрывающие теги в начале
    changed = True
    while changed:
        changed = False
        match = re.match(r'^(</[a-zA-Z]+>)+', text)
        if match:
            # Проверяем, есть ли для них открывающие дальше
            prefix = match.group(0)
            rest = text[len(prefix):]
            # Убираем только если это явные сироты
            text = rest.lstrip()
            changed = True
    return text


def split_smart_text(text: str, max_len: int = 1000) -> List[str]:
    """
    Разделяет длинный текст на части, сохраняя целостность HTML-тегов.
    - Не разрезает посередине тега
    - Если абзац содержит незакрытые теги, переносит его целиком в новую часть
    - При разбивке внутри абзаца корректно закрывает/открывает теги
    """
    if len(text) <= max_len:
        return [text]

    logger.info(f"Splitting {len(text)} chars (max={max_len})")

    parts = []
    paragraphs = text.split('\n\n')

    current = ""
    current_unclosed = []  # Стек незакрытых тегов в current

    for para in paragraphs:
        para = para.strip('\n')
        if not para:
            continue

        para_len = len(para)
        para_unclosed = _get_unclosed_tags(para)

        # Если абзац помещается в текущую часть
        if len(current) + para_len + 2 <= max_len:
            if current:
                current += '\n\n' + para
            else:
                current = para
            # Обновляем стек незакрытых тегов
            current_unclosed = _get_unclosed_tags(current)

        else:
            # Сохраняем текущую часть
            if current:
                # Закрываем все незакрытые теги перед разделением
                if current_unclosed:
                    current = _close_tags(current, current_unclosed)
                parts.append(current)

            # Если абзац сам по себе длинный — режем по предложениям
            if para_len > max_len:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                current = ""
                current_unclosed = []
                for sent in sentences:
                    sent = sent.strip()
                    if not sent:
                        continue
                    sent_len = len(sent)
                    if len(current) + sent_len + 1 <= max_len:
                        if current:
                            current += ' ' + sent
                        else:
                            current = sent
                    else:
                        if current:
                            # Закрываем теги перед сохранением
                            unclosed = _get_unclosed_tags(current)
                            if unclosed:
                                current = _close_tags(current, unclosed)
                            parts.append(current)
                        # Новый кусок — открываем теги, которые были активны
                        unclosed = _get_unclosed_tags(current) if current else []
                        current = sent
                        if unclosed:
                            current = _open_tags(current, unclosed)
                current_unclosed = _get_unclosed_tags(current) if current else []
            else:
                # Абзац короткий, но не влезает — начинаем новую часть
                current = para
                current_unclosed = para_unclosed

    # Последняя часть
    if current:
        parts.append(current)

    # Убираем сиротские закрывающие теги в начале каждой части
    parts = [_strip_orphan_close_tags(p) for p in parts if p.strip()]

    logger.info(f"Split into {len(parts)} parts")
    for i, part in enumerate(parts):
        logger.info(f"Part {i+1}: {len(part)} chars")

    return parts


def normalize_max_offset(text: str, max_offset: int, max_length: int = None) -> Tuple[int, int]:
    python_offset = 0
    utf16_pos = 0
    for i, char in enumerate(text):
        if utf16_pos >= max_offset:
            python_offset = i
            break
        utf16_pos += len(char.encode('utf-16-le')) // 2
    else:
        python_offset = len(text)

    if max_length is not None:
        python_length = 0
        utf16_end = max_offset + max_length
        utf16_pos = max_offset
        for i in range(python_offset, len(text)):
            if utf16_pos >= utf16_end:
                break
            utf16_pos += len(text[i].encode('utf-16-le')) // 2
            python_length += 1
        if python_offset != max_offset or python_length != max_length:
            logger.warning(f"Offset corrected: MAX=[{max_offset}:{max_offset+max_length}] -> Python=[{python_offset}:{python_offset+python_length}]")
        return python_offset, python_length
    return python_offset, max_length


def filter_overlapping_same_type(markup: List[dict]) -> List[dict]:
    if not markup:
        return markup
    filtered = []
    for i, entity in enumerate(markup):
        etype = entity.get('type', '')
        offset = entity.get('from', 0)
        length = entity.get('length', 0)
        end = offset + length
        is_nested = False
        for j, other in enumerate(markup):
            if i == j:
                continue
            if other.get('type') != etype:
                continue
            other_offset = other.get('from', 0)
            other_end = other_offset + other.get('length', 0)
            if other_offset <= offset and other_end >= end and (other_offset < offset or other_end > end):
                is_nested = True
                break
        if not is_nested:
            filtered.append(entity)
    return filtered
