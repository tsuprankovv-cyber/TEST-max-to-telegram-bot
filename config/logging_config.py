import os
import sys
import logging
from logging.handlers import RotatingFileHandler

LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG').upper()
LOG_RAW_MAX = os.getenv('LOG_RAW_MAX', '1') == '1'
LOG_RAW_TG = os.getenv('LOG_RAW_TG', '1') == '1'
LOG_MARKUP = os.getenv('LOG_MARKUP', '1') == '1'
LOG_MEDIA = os.getenv('LOG_MEDIA', '1') == '1'

def setup_logging():
    file_handler = RotatingFileHandler(
        'bot_debug.log',
        maxBytes=20*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        '%Y-%m-%d %H:%M:%S'
    ))

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        '%Y-%m-%d %H:%M:%S'
    ))

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.DEBUG),
        handlers=[console_handler, file_handler]
    )

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
