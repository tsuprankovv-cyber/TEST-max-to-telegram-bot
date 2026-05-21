import subprocess
from typing import Tuple, Dict
from config.logging_config import get_logger

logger = get_logger(__name__)

class MediaProcessor:
    VOICE_EXTS = {'ogg', 'opus', 'oga'}
    AUDIO_EXTS = {'mp3', 'wav', 'm4a', 'flac', 'aac', 'wma', 'alac', 'aiff'}

    def __init__(self):
        self.ffmpeg_ok = self._check_ffmpeg()
        logger.info(f"FFmpeg available: {self.ffmpeg_ok}")

    def _check_ffmpeg(self) -> bool:
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except:
            return False

    def determine(self, att: Dict) -> Tuple[str, Dict]:
        atype = att.get('type', 'file')
        payload = att.get('payload', {})
        fname = payload.get('filename') or att.get('filename', '')
        ext = fname.split('.')[-1].lower() if '.' in fname else ''
        meta = {
            'filename': fname,
            'size': payload.get('size', 0),
            'url': payload.get('url'),
            'token': payload.get('token'),
            'ext': ext,
            'original_type': atype
        }

        if atype == 'voice': return 'voice', meta
        if atype == 'audio': return 'audio', meta
        if atype == 'video': return 'video', meta
        if atype in ('image', 'photo'): return 'photo', meta
        if atype == 'share': return 'document', meta
        if atype == 'inline_keyboard': return 'keyboard', meta

        if ext in self.VOICE_EXTS: return 'voice', meta
        if ext in self.AUDIO_EXTS: return 'audio', meta

        return 'document', meta
