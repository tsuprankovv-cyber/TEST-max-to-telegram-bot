import re
from typing import List, Tuple
from config.logging_config import get_logger

logger = get_logger(__name__)

# Регулярка для поиска HTML-тегов (открывающих, закрывающих, самозакрывающихся)
TAG_RE = re.compile(r'</?[a-zA-Z][^>]*>')

def _count_open_tags(text: str) -> int:
    """Считает баланс открытых/закрытых HTML-тегов."""
    open_count = len(re.findall(r'<[a-zA-Z][^>/][^>]*>', text))
    close_count = len(re.findall(r'</[a-zA-Z][^>]*>', text))
    return open_count - close_count

def _close_open_tags(text: str, balance: int) -> str:
    """Закрывает открытые теги в конце текста."""
    # Находим все открытые теги в тексте
    open_tags = re.findall(r'<([a-zA-Z]+)[^>/]*>', text)
    # Добавляем закрывающие в обратном порядке
    for tag in reversed(open_tags[-balance:]):
        text += f'</{tag}>'
    return text

def _fix_split_point(text: str) -> str:
    """Убирает висящие закрывающие теги в начале текста."""
    # Находим закрывающие теги без открывающих в начале
    result = text
    # Простая эвристика: если текст начинается с </...> — это остаток от разбивки
    while result.startswith('</'):
        end_pos = result.find('>') + 1
        if end_pos > 0:
            result = result[end_pos:].strip()
        else:
            break
    return result


def split_smart_text(text: str, max_len: int = 1000) -> List[str]:
    """Разделяет текст, сохраняя целостность HTML-тегов."""
    if len(text) <= max_len:
        return [text]

    logger.info(f"Splitting {len(text)} chars (max={max_len})")

    parts = []
    paragraphs = text.split('\n\n')

    current = ""
    current_balance = 0  # баланс тегов в current

    for para in paragraphs:
        para_len = len(para)
        para_balance = _count_open_tags(para)

        # Если абзац помещается целиком
        if len(current) + para_len + 2 <= max_len:
            current = (current + '\n\n' + para) if current else para
            current_balance += para_balance
        else:
            # Сохраняем текущую часть
            if current:
                if current_balance > 0:
                    current = _close_open_tags(current, current_balance)
                parts.append(current)

            # Если абзац сам по себе длинный — режем по предложениям
            if para_len > max_len:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                current = ""
                current_balance = 0
                for sent in sentences:
                    sent_balance = _count_open_tags(sent)
                    if len(current) + len(sent) + 1 <= max_len:
                        current = (current + ' ' + sent) if current else sent
                        current_balance += sent_balance
                    else:
                        if current:
                            if current_balance > 0:
                                current = _close_open_tags(current, current_balance)
                            parts.append(current)
                        current = sent
                        current_balance = sent_balance
            else:
                current = para
                current_balance = para_balance

    # Последняя часть
    if current:
        if current_balance > 0:
            current = _close_open_tags(current, current_balance)
        parts.append(current)

    # Убираем висящие закрывающие теги в начале каждой части
    parts = [_fix_split_point(p) for p in parts]

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
