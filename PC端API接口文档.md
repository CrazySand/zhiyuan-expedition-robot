# PC 端 API 接口文档

## 基础信息

- **Base URL**: `http://localhost:8000`（或配置的 `SERVER_HOST:SERVER_PORT`）
- **协议**: HTTP/HTTPS
- **数据格式**: JSON
- **字符编码**: UTF-8
- **接口风格**: RESTful（同一资源路径，用 HTTP 方法区分操作）

## 认证方式

所有接口需在请求头中携带：

```
X-API-KEY: <SECRET_KEY>
```

- 与服务端 `config.SECRET_KEY` 一致
- 认证失败返回 `code: 401`

## 统一响应格式

**成功**：

```json
{
  "code": 0,
  "msg": "success",
  "data": { }
}
```

**错误**：

```json
{
  "code": 400,
  "msg": "错误描述",
  "data": null
}
```

- `400`: 参数验证失败
- `401`: 认证失败
- `500`: 服务器错误

---

## 接口总览（RESTful）

| 资源 | GET | POST | PUT | DELETE |
|------|-----|------|-----|--------|
| **/api/tts** | - | 发起播报 | - | 打断播报 |
| **/api/tts/status** | 播报状态（?trace_id=） | - | - | - |
| **/api/tts/volume** | 获取音量 | - | 设置音量 | - |
| **/api/agent-control/agent-properties** | 查询模式 | 设置模式 | - | - |
| **/api/face-recognition** | 进程状态 | 启动 | - | 停止 |
| **/api/face-recognition/cloud-db** | 云端人脸库 | - | - | - |
| **/api/asr** | 进程状态 | 启动 | - | 停止 |
| **/api/webhooks/face-recognition** | - | 人脸识别回调 | - | - |
| **/api/webhooks/asr/audio** | - | ASR 音频上传 | - | - |

---

## 1. TTS

### 1.1 发起播报

- **方法**: `POST`
- **路径**: `/api/tts`
- **请求体**: `{"text": "播报内容"}`，`text` 长度 1–200

**示例**：

```bash
curl -X POST "http://localhost:8000/api/tts" \
  -H "X-API-KEY: NZGNJZMSDZJD" \
  -H "Content-Type: application/json" \
  -d '{"text": "你好，世界"}'
```

**响应**：`data.trace_id` 用于查询状态或打断。

---

### 1.2 打断播报

- **方法**: `DELETE`
- **路径**: `/api/tts`
- **请求体**: 无

```bash
curl -X DELETE "http://localhost:8000/api/tts" \
  -H "X-API-KEY: NZGNJZMSDZJD"
```

---

### 1.3 查询播报状态

- **方法**: `GET`
- **路径**: `/api/tts/status`
- **Query**: `trace_id`（必填，1–100 字符）

```bash
curl -X GET "http://localhost:8000/api/tts/status?trace_id=xxx" \
  -H "X-API-KEY: NZGNJZMSDZJD"
```

**响应**：`data.tts_status`，如 `TTSStatusType_Playing`、`TTSStatusType_NOTInQue` 等。

---

### 1.4 获取音量

- **方法**: `GET`
- **路径**: `/api/tts/volume`

```bash
curl -X GET "http://localhost:8000/api/tts/volume" \
  -H "X-API-KEY: NZGNJZMSDZJD"
```

**响应**：`data.audio_volume`（0–100）。

---

### 1.5 设置音量

- **方法**: `PUT`
- **路径**: `/api/tts/volume`
- **请求体**: `{"audio_volume": 50}`，范围 0–70

```bash
curl -X PUT "http://localhost:8000/api/tts/volume" \
  -H "X-API-KEY: NZGNJZMSDZJD" \
  -H "Content-Type: application/json" \
  -d '{"audio_volume": 50}'
```

**注意**：音量建议不超过 70，以免损坏扬声器。

---

## 2. Agent Control

### 2.1 设置交互运行模式

- **方法**: `POST`
- **路径**: `/api/agent-control/agent-properties`
- **请求体**: `{"mode": "only_voice"|"voice_face"|"normal"}`

| mode | 说明 |
|------|------|
| `only_voice` | 仅输出降噪麦克音频，后续链路断开 |
| `voice_face` | 输出麦克音频 + 人脸识别结果，后续链路断开 |
| `normal` | 常规运行模式 |

```bash
curl -X POST "http://localhost:8000/api/agent-control/agent-properties" \
  -H "X-API-KEY: NZGNJZMSDZJD" \
  -H "Content-Type: application/json" \
  -d '{"mode": "normal"}'
```

**注意**：调用后会自动重启 agent；需重启 agent 或机器人后生效。

---

### 2.2 查询交互运行模式

- **方法**: `GET`
- **路径**: `/api/agent-control/agent-properties`

```bash
curl -X GET "http://localhost:8000/api/agent-control/agent-properties" \
  -H "X-API-KEY: NZGNJZMSDZJD"
```

**响应**：`data.mode`。

---

## 3. Face Recognition（人脸识别）

### 3.1 获取云端人脸库信息

- **方法**: `GET`
- **路径**: `/api/face-recognition/cloud-db`

```bash
curl -X GET "http://localhost:8000/api/face-recognition/cloud-db" \
  -H "X-API-KEY: NZGNJZMSDZJD"
```

---

### 3.2 启动人脸识别

- **方法**: `POST`
- **路径**: `/api/face-recognition`

```bash
curl -X POST "http://localhost:8000/api/face-recognition" \
  -H "X-API-KEY: NZGNJZMSDZJD"
```

**响应**：`data.pid`、`data.status: "started"`。已在运行则返回 400。

---

### 3.3 停止人脸识别

- **方法**: `DELETE`
- **路径**: `/api/face-recognition`

```bash
curl -X DELETE "http://localhost:8000/api/face-recognition" \
  -H "X-API-KEY: NZGNJZMSDZJD"
```

---

### 3.4 查询人脸识别进程状态

- **方法**: `GET`
- **路径**: `/api/face-recognition`

```bash
curl -X GET "http://localhost:8000/api/face-recognition" \
  -H "X-API-KEY: NZGNJZMSDZJD"
```

**响应**：`data.is_running`、`data.status`（`running`/`stopped`）、`data.pid`（可选）、`data.return_code`（可选）。

---

## 4. ASR（语音识别进程）

### 4.1 启动 ASR

- **方法**: `POST`
- **路径**: `/api/asr`

```bash
curl -X POST "http://localhost:8000/api/asr" \
  -H "X-API-KEY: NZGNJZMSDZJD"
```

**响应**：`data.pid`、`data.status: "started"`。

---

### 4.2 停止 ASR

- **方法**: `DELETE`
- **路径**: `/api/asr`

```bash
curl -X DELETE "http://localhost:8000/api/asr" \
  -H "X-API-KEY: NZGNJZMSDZJD"
```

---

### 4.3 查询 ASR 进程状态

- **方法**: `GET`
- **路径**: `/api/asr`

```bash
curl -X GET "http://localhost:8000/api/asr" \
  -H "X-API-KEY: NZGNJZMSDZJD"
```

**响应**：`data.is_running`、`data.status`、`data.pid`（可选）。

---

## 5. Webhooks（机器人回调）

以下接口由**机器人端**主动调用，PC 端接收。

### 5.1 人脸识别结果回调

- **方法**: `POST`
- **路径**: `/api/webhooks/face-recognition`
- **请求体**: `{"timestamp": 1717200000, "face_id": "xxx", "confidence": 0.95}`

机器人识别人脸后 POST 到此地址；PC 端可将结果转发中控。

---

### 5.2 ASR 音频上传

- **方法**: `POST`
- **路径**: `/api/webhooks/asr/audio`
- **Content-Type**: `multipart/form-data`
- **表单字段**: `file`（音频文件二进制）

机器人上传音频 → PC 端存临时文件 → 语音转文字 → 结果可发中控 → 返回 `data.text`。

```bash
curl -X POST "http://localhost:8000/api/webhooks/asr/audio" \
  -H "X-API-KEY: NZGNJZMSDZJD" \
  -F "file=@/path/to/audio.wav"
```

---

## 6. 错误响应示例

**400 参数错误**：

```json
{
  "code": 400,
  "msg": "数据验证失败",
  "data": [{"loc": ["body", "text"], "msg": "...", "type": "..."}]
}
```

**401 认证失败**：

```json
{
  "code": 401,
  "msg": "认证失败",
  "data": null
}
```

**500 服务器错误**：

```json
{
  "code": 500,
  "msg": "错误信息",
  "data": null
}
```

---

## 7. 使用示例（Python）

```python
import httpx

BASE_URL = "http://localhost:8000"
HEADERS = {"X-API-KEY": "NZGNJZMSDZJD"}

async def main():
    async with httpx.AsyncClient(timeout=60, headers=HEADERS) as client:
        # TTS
        r = await client.post(f"{BASE_URL}/api/tts", json={"text": "你好"})
        trace_id = r.json()["data"]["trace_id"]

        r = await client.get(f"{BASE_URL}/api/tts/status", params={"trace_id": trace_id})
        print(r.json()["data"]["tts_status"])

        await client.delete(f"{BASE_URL}/api/tts")

        # 音量
        r = await client.get(f"{BASE_URL}/api/tts/volume")
        print(r.json()["data"]["audio_volume"])
        await client.put(f"{BASE_URL}/api/tts/volume", json={"audio_volume": 50})

        # Agent 模式
        await client.post(f"{BASE_URL}/api/agent-control/agent-properties", json={"mode": "normal"})
        r = await client.get(f"{BASE_URL}/api/agent-control/agent-properties")
        print(r.json()["data"]["mode"])

        # 人脸识别
        r = await client.get(f"{BASE_URL}/api/face-recognition/cloud-db")
        await client.post(f"{BASE_URL}/api/face-recognition")
        r = await client.get(f"{BASE_URL}/api/face-recognition")
        print(r.json()["data"])
        await client.delete(f"{BASE_URL}/api/face-recognition")

        # ASR
        await client.post(f"{BASE_URL}/api/asr")
        r = await client.get(f"{BASE_URL}/api/asr")
        print(r.json()["data"])
        await client.delete(f"{BASE_URL}/api/asr")
```

---

## 8. 注意事项

1. **认证**：请求头必须带 `X-API-KEY`，与服务器 `SECRET_KEY` 一致。
2. **TTS**：文本 1–200 字符；麦克风优先级高于 TTS，会排队或被打断。
3. **音量**：设置音量建议 ≤ 70。
4. **Agent 模式**：设置后会自动重启 agent，需重启或等待后生效。
5. **人脸/ASR 进程**：同一时间只能一个实例；GET 查状态，POST 启动，DELETE 停止。
6. **Webhooks**：由机器人调用；ASR 音频为 multipart 上传，字段名 `file`。

---

## 9. 更新日志

- **v2.0**：全面改为 RESTful；TTS/Face/ASR 用 GET/POST/PUT/DELETE 同一资源路径；认证改为 `X-API-KEY`；新增 ASR、Webhooks 说明。
- **v1.2**：Face 接口（人脸识别进程、云端人脸库）。
- **v1.1**：Agent Control（设置/查询交互运行模式）。
- **v1.0**：TTS、音量、统一响应格式。
