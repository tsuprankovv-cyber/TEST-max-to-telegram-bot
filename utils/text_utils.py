import re
from typing import List, Tuple
from config.logging_config import get_logger

logger = get_logger(__name__)

def split_smart_text(text: str, max_len: int = 1000) -> List[str]:
    if len(text) <= max_len:
        return [text]
    
    logger.info(f"Splitting {len(text)} chars (max={max_len})")
    parts = []
    current = ""
    paragraphs = text.split('\n\n')
    
    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_len:
            current = (current + '\n\n' + para) if current else para
        else:
            if current:
                parts.append(current)
            if len(para) > max_len:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                current = ""
                for sent in sentences:
                    if len(current) + len(sent) + 1 <= max_len:
                        current = (current + ' ' + sent) if current else sent
                    else:
                        if current:
                            parts.append(current)
                        current = sent
            else:
                current = para
    
    if current:
        parts.append(current)
    
    logger.info(f"Split into {len(parts)} parts")
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
    if not markup: return markup
    filtered = []
    for i, entity in enumerate(markup):
        etype = entity.get('type', '')
        offset = entity.get('from', 0)
        length = entity.get('length', 0)
        end = offset + length
        is_nested = False
        for j, other in enumerate(markup):
            if i == j: continue
            if other.get('type') != etype: continue
            other_offset = other.get('from', 0)
            other_end = other_offset + other.get('length', 0)
            if other_offset <= offset and other_end >= end and (other_offset < offset or other_end > end):
                is_nested = True
                break
        if not is_nested:
            filtered.append(entity)
    return filtered
