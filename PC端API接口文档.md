# PC 端 API 接口文档

## 基础信息

- **Base URL**: `http://localhost:8000`
- **协议**: HTTP/HTTPS
- **数据格式**: JSON
- **字符编码**: UTF-8

## 认证方式

所有接口都需要在请求头中携带认证信息：

```
Authorization: Bearer your-secret-key-here
```

**注意**：
- Token 格式必须为 `Bearer {token}`
- Token 值需要与服务端配置的 `SECRET_KEY` 一致
- 认证失败将返回 `code: 401`

## 统一响应格式

### 成功响应

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    // 具体数据
  }
}
```

### 错误响应

```json
{
  "code": 400,  // 错误码：400-参数验证失败, 401-认证失败, 500-服务器错误
  "msg": "错误描述信息",
  "data": null  // 或错误详情数组
}
```

**错误码说明**：
- `400`: 请求参数验证失败
- `401`: 认证失败（Token 无效或缺失）
- `500`: 服务器内部错误

---

## TTS 接口

### 1. TTS 播报

**接口描述**：播放 TTS 语音文本

**请求信息**：
- **方法**: `POST`
- **路径**: `/api/tts/play-tts`
- **认证**: 需要

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 | 限制 |
|--------|------|------|------|------|
| text | string | 是 | 播报文本内容 | 长度：1-200 个字符 |

**请求示例**：

```bash
curl -X POST "http://localhost:8000/api/tts/play-tts" \
  -H "Authorization: Bearer your-secret-key-here" \
  -H "Content-Type: application/json" \
  -d '{"text": "你好，世界"}'
```

**响应示例**：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "trace_id": "hafhjkqwjwefk_60R9ZJSvWEJM38q279Ef3N4"
  }
}
```

**响应字段说明**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| trace_id | string | 播报 ID，用于查询播报状态或打断播报 |

**注意事项**：
- 只支持短文本请求，最高只支持 1024 字节，约 200 个中文/英文
- 麦克风优先级是最高的，如果麦克风有播报，TTS 会被加入队列
- 文本长度超过限制将返回参数验证错误

---

### 2. TTS 打断

**接口描述**：打断当前正在播放的 TTS

**请求信息**：
- **方法**: `POST`
- **路径**: `/api/tts/stop-tts`
- **认证**: 需要

**请求参数**：无

**请求示例**：

```bash
curl -X POST "http://localhost:8000/api/tts/stop-tts" \
  -H "Authorization: Bearer your-secret-key-here"
```

**响应示例**：

```json
{
  "code": 0,
  "msg": "success",
  "data": null
}
```

**注意事项**：
- 会打断默认 trace_id 对应的播放任务
- 无论播放任务当前状态如何（正在播放或在队列中），都可以被打断

---

### 3. TTS 播报状态查询

**接口描述**：查询指定 trace_id 的 TTS 播报状态

**请求信息**：
- **方法**: `GET`
- **路径**: `/api/tts/get-audio-status`
- **认证**: 需要

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 | 限制 |
|--------|------|------|------|------|
| trace_id | string | 是 | 播报 ID（从 play_tts 接口返回） | 长度：1-100 个字符 |

**请求示例**：

```bash
curl -X GET "http://localhost:8000/api/tts/get-audio-status?trace_id=hafhjkqwjwefk_60R9ZJSvWEJM38q279Ef3N4" \
  -H "Authorization: Bearer your-secret-key-here"
```

**响应示例**：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "tts_status": "TTSStatusType_Playing"
  }
}
```

**状态值说明**：

| 状态值 | 说明 |
|--------|------|
| `TTSStatusType_Playing` | 播报中 |
| `TTSStatusType_NOTInQue` | 播报队列无此文本，也不在播报，播报结束后会进入此状态 |
| `TTSStatusType_InQue` | 在播报队列中，尚未开始播报 |
| `TTSStatusType_Stop` | 暂停播报/取消播报/中断播报 |
| `TTSStatusType_Error` | 播报失败 |
| `TTSStatusType_Begin` | 开始播报（短暂，一般查询不到） |
| `TTSStatusType_End` | 播报结束（短暂，一般查询不到） |
| `TTSConfigStatusType_Unknown` | 未知状态 |

**注意事项**：
- 实际上大多情况下只能获取到 `TTSStatusType_Playing` 和 `TTSStatusType_NOTInQue` 这两种状态

---

### 4. 获取当前音量大小

**接口描述**：获取机器人当前音量设置

**请求信息**：
- **方法**: `GET`
- **路径**: `/api/tts/get-audio-volume`
- **认证**: 需要

**请求参数**：无

**请求示例**：

```bash
curl -X GET "http://localhost:8000/api/tts/get-audio-volume" \
  -H "Authorization: Bearer your-secret-key-here"
```

**响应示例**：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "audio_volume": 50
  }
}
```

**响应字段说明**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| audio_volume | integer | 音量大小，范围：0-100 |

---

### 5. 设置音量大小

**接口描述**：设置机器人音量大小

**请求信息**：
- **方法**: `POST`
- **路径**: `/api/tts/set-audio-volume`
- **认证**: 需要

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 | 限制 |
|--------|------|------|------|------|
| audio_volume | integer | 是 | 音量大小 | 范围：0-70 |

**请求示例**：

```bash
curl -X POST "http://localhost:8000/api/tts/set-audio-volume" \
  -H "Authorization: Bearer your-secret-key-here" \
  -H "Content-Type: application/json" \
  -d '{"audio_volume": 50}'
```

**响应示例**：

```json
{
  "code": 0,
  "msg": "success",
  "data": null
}
```

**注意事项**：
- ⚠️ **重要**：注意不要调节音量超过 70，音量超出此范围扬声器经功放放大后会超额定工作，造成扬声器损坏
- 如需静音，请将 `audio_volume` 设为 0

---

## Agent Control 接口

### 6. 设置交互运行模式

**接口描述**：设置机器人交互运行模式

**请求信息**：
- **方法**: `POST`
- **路径**: `/api/agent-control/set-agent-properties`
- **认证**: 需要

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 | 限制 |
|--------|------|------|------|------|
| mode | string | 是 | 交互运行模式 | 枚举值：`only_voice`、`voice_face`、`normal` |

**模式说明**：

| 模式值 | 说明 |
|--------|------|
| `only_voice` | 仅输出降噪麦克音频 `/agent/process_audio_output`，后续链路全部断开 |
| `voice_face` | 输出降噪麦克音频 `/agent/process_audio_output` 和人脸识别结果 `/agent/vision/face_id`，后续链路全部断开 |
| `normal` | 常规运行模式，交互正常运行 |

**请求示例**：

```bash
curl -X POST "http://localhost:8000/api/agent-control/set-agent-properties" \
  -H "Authorization: Bearer your-secret-key-here" \
  -H "Content-Type: application/json" \
  -d '{"mode": "only_voice"}'
```

**响应示例**：

```json
{
  "code": 0,
  "msg": "success",
  "data": null
}
```

**注意事项**：
- ⚠️ **重要**：调用后需要重启 agent 或重启机器人方可生效
- 调用后会自动重启 agent 模块
- 调用后返回值为 `CommonState_UNKNOWN` 是正常现象，可以调用 `get-agent-properties` 接口，查看交互运行模式是否切换成功

---

### 7. 查询交互运行模式

**接口描述**：查询机器人当前交互运行模式

**请求信息**：
- **方法**: `GET`
- **路径**: `/api/agent-control/get-agent-properties`
- **认证**: 需要

**请求参数**：无

**请求示例**：

```bash
curl -X GET "http://localhost:8000/api/agent-control/get-agent-properties" \
  -H "Authorization: Bearer your-secret-key-here"
```

**响应示例**：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "mode": "only_voice"
  }
}
```

**响应字段说明**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| mode | string | 当前交互运行模式，枚举值：`only_voice`、`voice_face`、`normal` |

---

## Face 接口

### 8. 人脸识别结果回调

**接口描述**：接收机器人端 FaceID 识别结果回调（由机器人端主动调用）

**请求信息**：
- **方法**: `POST`
- **路径**: `/api/face/face-recognition-callback`
- **认证**: 需要

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| timestamp | string | 是 | 时间戳 |
| face_id | string | 是 | 人脸 ID |
| confidence | number | 是 | 识别置信度（0-1） |

**请求示例**：

```bash
curl -X POST "http://localhost:8000/api/face/face-recognition-callback" \
  -H "Authorization: Bearer your-secret-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "1764829536028",
    "face_id": "A210041B50001917648293023663264",
    "confidence": 0.9811308
  }'
```

**响应示例**：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "face_id": "A210041B50001917648293023663264"
  }
}
```

**注意事项**：
- 此接口由机器人端主动调用
- 用于接收机器人端的人脸识别结果
- **重要**：PC 端接收到人脸识别结果后，需要将 `timestamp`、`face_id`、`confidence` 三个字段发送到中控端提供的接口
- 中控端需要提供相应的接口来接收这些数据

---

### 9. 获取云端人脸数据库信息

**接口描述**：获取云端人脸数据库信息

**请求信息**：
- **方法**: `GET`
- **路径**: `/api/face/cloud-face-db-info`
- **认证**: 需要

**请求参数**：无

**请求示例**：

```bash
curl -X GET "http://localhost:8000/api/face/cloud-face-db-info" \
  -H "Authorization: Bearer your-secret-key-here"
```

**响应示例**：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    // 云端人脸数据库信息
  }
}
```

---

### 10. 启动人脸识别程序

**接口描述**：启动人脸识别 Python 程序

**请求信息**：
- **方法**: `POST`
- **路径**: `/api/face/start-face-recognition`
- **认证**: 需要

**请求参数**：无

**请求示例**：

```bash
curl -X POST "http://localhost:8000/api/face/start-face-recognition" \
  -H "Authorization: Bearer your-secret-key-here"
```

**响应示例**：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "pid": 12345,
    "status": "started"
  }
}
```

**响应字段说明**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| pid | integer | 进程 ID |
| status | string | 状态，值为 `started` |

**注意事项**：
- 如果程序已在运行中，将返回错误 `code: 400`，错误信息为"人脸识别程序已在运行中"
- 启动时会自动执行必要的环境设置（ROS、虚拟环境等）

---

### 11. 停止人脸识别程序

**接口描述**：停止人脸识别 Python 程序

**请求信息**：
- **方法**: `POST`
- **路径**: `/api/face/stop-face-recognition`
- **认证**: 需要

**请求参数**：无

**请求示例**：

```bash
curl -X POST "http://localhost:8000/api/face/stop-face-recognition" \
  -H "Authorization: Bearer your-secret-key-here"
```

**响应示例**：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "status": "stopped"
  }
}
```

**响应字段说明**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| status | string | 状态，值为 `stopped` |

**注意事项**：
- 如果程序未运行，将返回错误 `code: 400`，错误信息为"人脸识别程序未运行"
- 停止时会终止整个进程组，包括所有子进程

---

### 12. 获取人脸识别进程状态

**接口描述**：获取人脸识别进程状态

**请求信息**：
- **方法**: `GET`
- **路径**: `/api/face/face-recognition-status`
- **认证**: 需要

**请求参数**：无

**请求示例**：

```bash
curl -X GET "http://localhost:8000/api/face/face-recognition-status" \
  -H "Authorization: Bearer your-secret-key-here"
```

**响应示例**：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "is_running": true,
    "status": "running",
    "pid": 12345
  }
}
```

**响应字段说明**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| is_running | boolean | 是否正在运行 |
| status | string | 状态，值为 `running` 或 `stopped` |
| pid | integer | 进程 ID（仅在运行中时返回） |
| return_code | integer | 退出码（仅在进程已退出时返回） |

**状态说明**：

| 状态值 | 说明 |
|--------|------|
| `running` | 程序正在运行 |
| `stopped` | 程序已停止 |

**注意事项**：
- 如果进程意外退出，状态会自动更新为 `stopped`

---

## 错误处理

### 参数验证错误（400）

当请求参数不符合要求时，返回：

```json
{
  "code": 400,
  "msg": "数据验证失败",
  "data": [
    {
      "loc": ["body", "text"],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

### 认证失败（401）

当 Token 无效或缺失时，返回：

```json
{
  "code": 401,
  "msg": "认证失败",
  "data": null
}
```

### 服务器错误（500）

当服务器内部发生错误时，返回：

```json
{
  "code": 500,
  "msg": "错误信息",
  "data": null
}
```

---

## 使用示例

### Python 示例

```python
import requests

BASE_URL = "http://localhost:8000"
TOKEN = "your-secret-key-here"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# 1. TTS 播报
response = requests.post(
    f"{BASE_URL}/api/tts/play-tts",
    headers=HEADERS,
    json={"text": "你好，世界"}
)
result = response.json()
trace_id = result["data"]["trace_id"]
print(f"播报 ID: {trace_id}")

# 2. 查询播报状态
response = requests.get(
    f"{BASE_URL}/api/tts/get-audio-status",
    headers=HEADERS,
    params={"trace_id": trace_id}
)
status = response.json()["data"]["tts_status"]
print(f"播报状态: {status}")

# 3. 打断播报
response = requests.post(
    f"{BASE_URL}/api/tts/stop-tts",
    headers=HEADERS
)

# 4. 获取音量
response = requests.get(
    f"{BASE_URL}/api/tts/get-audio-volume",
    headers=HEADERS
)
volume = response.json()["data"]["audio_volume"]
print(f"当前音量: {volume}")

# 5. 设置音量
response = requests.post(
    f"{BASE_URL}/api/tts/set-audio-volume",
    headers=HEADERS,
    json={"audio_volume": 50}
)

# 6. 设置交互运行模式
response = requests.post(
    f"{BASE_URL}/api/agent-control/set-agent-properties",
    headers=HEADERS,
    json={"mode": "only_voice"}
)
print("设置交互运行模式成功")

# 7. 查询交互运行模式
response = requests.get(
    f"{BASE_URL}/api/agent-control/get-agent-properties",
    headers=HEADERS
)
mode = response.json()["data"]["mode"]
print(f"当前交互运行模式: {mode}")

# 8. 启动人脸识别程序
response = requests.post(
    f"{BASE_URL}/api/face/start-face-recognition",
    headers=HEADERS
)
result = response.json()
if result["code"] == 0:
    print(f"人脸识别程序已启动，PID: {result['data']['pid']}")

# 9. 查询人脸识别进程状态
response = requests.get(
    f"{BASE_URL}/api/face/face-recognition-status",
    headers=HEADERS
)
status = response.json()["data"]
print(f"人脸识别进程状态: {status['status']}")

# 10. 停止人脸识别程序
response = requests.post(
    f"{BASE_URL}/api/face/stop-face-recognition",
    headers=HEADERS
)
print("人脸识别程序已停止")

# 11. 获取云端人脸数据库信息
response = requests.get(
    f"{BASE_URL}/api/face/cloud-face-db-info",
    headers=HEADERS
)
face_db_info = response.json()["data"]
print(f"云端人脸数据库信息: {face_db_info}")
```

### JavaScript 示例

```javascript
const BASE_URL = 'http://localhost:8000';
const TOKEN = 'your-secret-key-here';

const headers = {
  'Authorization': `Bearer ${TOKEN}`,
  'Content-Type': 'application/json'
};

// 1. TTS 播报
async function playTTS(text) {
  const response = await fetch(`${BASE_URL}/api/tts/play-tts`, {
    method: 'POST',
    headers: headers,
    body: JSON.stringify({ text })
  });
  const result = await response.json();
  return result.data.trace_id;
}

// 2. 查询播报状态
async function getAudioStatus(traceId) {
  const response = await fetch(`${BASE_URL}/api/tts/get-audio-status?trace_id=${traceId}`, {
    method: 'GET',
    headers: headers
  });
  const result = await response.json();
  return result.data.tts_status;
}

// 3. 设置交互运行模式
async function setAgentMode(mode) {
  const response = await fetch(`${BASE_URL}/api/agent-control/set-agent-properties`, {
    method: 'POST',
    headers: headers,
    body: JSON.stringify({ mode })
  });
  return await response.json();
}

// 4. 启动人脸识别程序
async function startFaceRecognition() {
  const response = await fetch(`${BASE_URL}/api/face/start-face-recognition`, {
    method: 'POST',
    headers: headers
  });
  return await response.json();
}

// 5. 查询人脸识别进程状态
async function getFaceRecognitionStatus() {
  const response = await fetch(`${BASE_URL}/api/face/face-recognition-status`, {
    method: 'GET',
    headers: headers
  });
  return await response.json();
}

// 使用示例
(async () => {
  const traceId = await playTTS('你好，世界');
  console.log('播报 ID:', traceId);
  
  setTimeout(async () => {
    const status = await getAudioStatus(traceId);
    console.log('播报状态:', status);
  }, 1000);
  
  // 设置交互运行模式
  await setAgentMode('only_voice');
  console.log('交互运行模式已设置');
  
  // 启动人脸识别程序
  const startResult = await startFaceRecognition();
  if (startResult.code === 0) {
    console.log('人脸识别程序已启动，PID:', startResult.data.pid);
  }
  
  // 查询人脸识别进程状态
  const statusResult = await getFaceRecognitionStatus();
  console.log('人脸识别进程状态:', statusResult.data);
})();
```

---

## 注意事项

1. **文本长度限制**：TTS 播报接口只支持 1-200 个字符的文本
2. **音量限制**：设置音量时不要超过 70，以免损坏扬声器
3. **认证要求**：所有接口都需要在请求头中携带有效的 Bearer Token
4. **状态查询**：大多数情况下只能查询到 `Playing` 和 `NOTInQue` 两种状态
5. **麦克风优先级**：麦克风播报优先级最高，会打断 TTS 播报
6. **CORS 支持**：API 支持跨域请求（CORS）
7. **交互运行模式**：设置交互运行模式后需要重启 agent 或重启机器人方可生效，接口会自动重启 agent 模块
8. **人脸识别进程**：启动人脸识别程序时会自动执行必要的环境设置（ROS、虚拟环境等），停止时会终止整个进程组

---

## 更新日志

- **v1.0**（初始版本）：包含 TTS 播报、状态查询、音量控制等基础功能
- **v1.1**：新增 Agent Control 接口（设置/查询交互运行模式）
- **v1.2**：新增 Face 接口（人脸识别回调、云端人脸数据库信息、人脸识别进程控制）
