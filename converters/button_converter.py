from typing import Dict, List, Optional
from config.logging_config import get_logger

logger = get_logger(__name__)

OLD_FORM_URL = 'https://forms.yandex.ru/cloud/680f8114505690020a036f30/'
NEW_FORM_URL = 'https://forms.yandex.ru/cloud/680f5f5ce010db158f8b7610'

def replace_button_urls(buttons: List[List[Dict]]) -> List[List[Dict]]:
    for row in buttons:
        for btn in row:
            if btn.get('url') == OLD_FORM_URL:
                btn['url'] = NEW_FORM_URL
                logger.info(f"Replaced URL in '{btn.get('text', '')}'")
    return buttons

def convert_max_buttons(reply_markup: Dict) -> Optional[Dict]:
    if not reply_markup:
        return None
    keyboard = reply_markup.get('inline_keyboard') or reply_markup.get('keyboard')
    if not keyboard or not isinstance(keyboard, list):
        return None
    telegram_keyboard = []
    for row in keyboard:
        telegram_row = []
        for button in row:
            if button.get('type') == 'url' or button.get('url'):
                url = button.get('url', '')
                if url == OLD_FORM_URL:
                    url = NEW_FORM_URL
                telegram_row.append({'text': button.get('text', 'Button'), 'url': url})
        if telegram_row:
            telegram_keyboard.append(telegram_row)
    logger.info(f"Converted {len(telegram_keyboard)} rows")
    return {'inline_keyboard': telegram_keyboard} if telegram_keyboard else None

def extract_keyboard_from_attachments(attachments: List[Dict]) -> Optional[Dict]:
    for att in attachments:
        if att.get('type') == 'inline_keyboard':
            payload = att.get('payload', {})
            buttons = payload.get('buttons', [])
            if buttons:
                buttons = replace_button_urls(buttons)
                logger.info(f"Found inline_keyboard: {len(buttons)} rows")
                return convert_max_buttons({'inline_keyboard': buttons})
    return None
