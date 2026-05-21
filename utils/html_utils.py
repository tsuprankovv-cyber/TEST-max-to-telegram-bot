import re
from config.logging_config import get_logger

logger = get_logger(__name__)

def remove_empty_tags(text: str) -> str:
    if not text: return text
    for tag in ['b', 'i', 'u', 's', 'code', 'pre', 'a', 'tg-spoiler']:
        text = re.sub(f'<{tag}></{tag}>', '', text)
        text = re.sub(f'<{tag} [^>]*></{tag}>', '', text)
    return text

def fix_broken_html(text: str) -> str:
    if not text: return text
    tags = ['b', 'i', 'u', 's', 'code', 'pre', 'a', 'tg-spoiler']
    for tag in tags:
        open_count = text.count(f'<{tag}>') + len(re.findall(f'<{tag} [^>]*>', text))
        close_count = text.count(f'</{tag}>')
        if open_count > close_count:
            text += f'</{tag}>' * (open_count - close_count)
            logger.warning(f"Added {open_count - close_count} </{tag}>")
    text = remove_empty_tags(text)
    return text
