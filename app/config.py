# 服务器密钥
SECRET_KEY = "NZGNJZMSDZJD"

# 服务器主机
SERVER_HOST = "0.0.0.0"

# 服务器端口
SERVER_PORT = 8000

# 云平台事件回调地址，用于主动/定时上报机器人状态 (POST, action + params)
CLOUD_EVENT_CALLBACK_URL = "http://192.168.10.100:8890/robot/api/event"

# 定时推送到中控的间隔（秒），默认 5 分钟
CLOUD_PUSH_INTERVAL = 300

# 是否启用云平台事件回调
ENABLE_CLOUD_EVENT_CALLBACK = False

# 是否启用热重载（开发环境使用）
RELOAD = True

# FunASR 模型路径
FUN_ASR_MODEL = "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"

# TTS 播报完成回调：按字数估算时长（秒/字），用于 sleep 后回调中控
TTS_SECONDS_PER_CHAR = 0.23

# 展厅 PC 本地人脸图片文件夹（灵心平台上传的人脸），与机器人 cloud-db 合并后供中控同步；启动时若不存在则程序终止
FACE_IMAGES_FOLDER = ""