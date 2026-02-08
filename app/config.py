SECRET_KEY = "NZGNJZMSDZJD"

SERVER_HOST = "0.0.0.0"

# 云平台事件回调地址，用于主动/定时上报机器人状态 (POST, action + params)
CLOUD_EVENT_CALLBACK_URL = "http://192.168.10.100:8890/robot/api/event"

# 定时推送到中控的间隔（秒），默认 5 分钟
CLOUD_PUSH_INTERVAL = 300

SERVER_PORT = 8000

RELOAD = True

FUN_ASR_MODEL = "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"