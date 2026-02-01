import shutil

if not shutil.which("ffmpeg"):
    raise Exception("未检测到 ffmpeg")
    
from funasr import AutoModel
from app.config import FUN_ASR_MODEL


model = AutoModel(
    model=FUN_ASR_MODEL,
    disable_update=True,
    disable_pbar=True,
)


def recognize_audio(audio_path: str) -> str:
    result = model.generate(input=audio_path)
    return result[0].get("text", "") if result else ""
