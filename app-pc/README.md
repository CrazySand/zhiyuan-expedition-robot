# TTS API 接口文档

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

## 接口列表

### 1. TTS 播报

**接口描述**：播放 TTS 语音文本

**请求信息**：
- **方法**: `POST`
- **路径**: `/api/play_tts`
- **认证**: 需要

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 | 限制 |
|--------|------|------|------|------|
| text | string | 是 | 播报文本内容 | 长度：1-200 个字符 |

**请求示例**：

```bash
curl -X POST "http://localhost:8000/api/play_tts" \
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
- **路径**: `/api/stop_tts`
- **认证**: 需要

**请求参数**：无

**请求示例**：

```bash
curl -X POST "http://localhost:8000/api/stop_tts" \
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
- **路径**: `/api/get_audio_status`
- **认证**: 需要

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 | 限制 |
|--------|------|------|------|------|
| trace_id | string | 是 | 播报 ID（从 play_tts 接口返回） | 长度：1-100 个字符 |

**请求示例**：

```bash
curl -X GET "http://localhost:8000/api/get_audio_status?trace_id=hafhjkqwjwefk_60R9ZJSvWEJM38q279Ef3N4" \
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
- **路径**: `/api/get_audio_volume`
- **认证**: 需要

**请求参数**：无

**请求示例**：

```bash
curl -X GET "http://localhost:8000/api/get_audio_volume" \
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
- **路径**: `/api/set_audio_volume`
- **认证**: 需要

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 | 限制 |
|--------|------|------|------|------|
| audio_volume | integer | 是 | 音量大小 | 范围：0-70 |

**请求示例**：

```bash
curl -X POST "http://localhost:8000/api/set_audio_volume" \
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
    f"{BASE_URL}/api/play_tts",
    headers=HEADERS,
    json={"text": "你好，世界"}
)
result = response.json()
trace_id = result["data"]["trace_id"]
print(f"播报 ID: {trace_id}")

# 2. 查询播报状态
response = requests.get(
    f"{BASE_URL}/api/get_audio_status",
    headers=HEADERS,
    params={"trace_id": trace_id}
)
status = response.json()["data"]["tts_status"]
print(f"播报状态: {status}")

# 3. 打断播报
response = requests.post(
    f"{BASE_URL}/api/stop_tts",
    headers=HEADERS
)

# 4. 获取音量
response = requests.get(
    f"{BASE_URL}/api/get_audio_volume",
    headers=HEADERS
)
volume = response.json()["data"]["audio_volume"]
print(f"当前音量: {volume}")

# 5. 设置音量
response = requests.post(
    f"{BASE_URL}/api/set_audio_volume",
    headers=HEADERS,
    json={"audio_volume": 50}
)
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
  const response = await fetch(`${BASE_URL}/api/play_tts`, {
    method: 'POST',
    headers: headers,
    body: JSON.stringify({ text })
  });
  const result = await response.json();
  return result.data.trace_id;
}

// 2. 查询播报状态
async function getAudioStatus(traceId) {
  const response = await fetch(`${BASE_URL}/api/get_audio_status?trace_id=${traceId}`, {
    method: 'GET',
    headers: headers
  });
  const result = await response.json();
  return result.data.tts_status;
}

// 使用示例
(async () => {
  const traceId = await playTTS('你好，世界');
  console.log('播报 ID:', traceId);
  
  setTimeout(async () => {
    const status = await getAudioStatus(traceId);
    console.log('播报状态:', status);
  }, 1000);
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

---

## 更新日志

- 初始版本：包含 TTS 播报、状态查询、音量控制等基础功能
