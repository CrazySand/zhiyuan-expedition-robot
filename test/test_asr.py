import shutil

if not shutil.which("ffmpeg"):
    raise Exception("未检测到 ffmpeg")

from funasr import AutoModel

model = AutoModel(
    model="iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
    disable_update=True,
    disable_pbar=True,
)

audio_path = r"E:\zhiyuan-expedition-robot\test.pcm"

result = model.generate(input=audio_path)

print(result)
