import tempfile
import subprocess
import os
from typing import Dict, Any, Optional
from mutagen import File as MutagenFile
from config.logging_config import get_logger
from utils.transliterator import safe_filename

logger = get_logger(__name__)

def get_audio_duration(file_path: str) -> int:
    try:
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return int(float(result.stdout.strip()))
    except:
        pass
    return 0

def extract_audio_tags(file_data: bytes, filename: str) -> Dict[str, Any]:
    logger.info(f"Extracting tags from: {filename}")
    performer, title, duration = '', '', 0
    with tempfile.NamedTemporaryFile(suffix='.tmp', delete=False) as tmp:
        tmp.write(file_data)
        tmp_path = tmp.name
    try:
        audio = MutagenFile(tmp_path)
        if audio and hasattr(audio, 'info') and audio.info:
            duration = int(audio.info.length or 0)
        if audio and hasattr(audio, 'tags') and audio.tags:
            tags = audio.tags
            performer = str(tags.get('TPE1', tags.get('©ART', '')))
            title = str(tags.get('TIT2', tags.get('©nam', '')))
    except:
        pass
    if not duration:
        duration = get_audio_duration(tmp_path)
    os.unlink(tmp_path)
    base_name = safe_filename(filename).rsplit('.', 1)[0]
    final_performer, final_title = base_name, ''
    if performer and title:
        final_title = f"{title} ({performer})"
    elif performer:
        final_title = performer
    elif title:
        final_title = title
    logger.info(f"Final: performer='{final_performer}', title='{final_title}', duration={duration}s")
    return {'performer': final_performer[:64], 'title': final_title[:64], 'duration': duration}

def convert_to_voice(file_data: bytes) -> Optional[bytes]:
    logger.info("Converting audio to voice...")
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except:
        logger.error("FFmpeg not available")
        return None
    with tempfile.NamedTemporaryFile(suffix='.tmp', delete=False) as tmp_in, \
         tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp_out:
        tmp_in.write(file_data)
        tmp_in_path, tmp_out_path = tmp_in.name, tmp_out.name
    cmd = ['ffmpeg', '-i', tmp_in_path, '-ac', '1', '-ar', '16000', '-c:a', 'libopus', '-b:a', '16k', '-vbr', 'on', '-application', 'voip', '-y', tmp_out_path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        logger.error(f"FFmpeg error: {result.stderr[:200]}")
        os.unlink(tmp_in_path)
        return None
    with open(tmp_out_path, 'rb') as f:
        ogg_data = f.read()
    os.unlink(tmp_in_path)
    os.unlink(tmp_out_path)
    logger.info(f"Converted: {len(file_data)} -> {len(ogg_data)} bytes")
    return ogg_data
