# PC 端 API 接口文档

PC 端 FastAPI 后端部署在 PC，对外提供统一 API，通过机器人端 SDK 与机器人交互。机器人端通过 Webhooks 向 PC 回调人脸识别、ASR 音频等结果。

---

## 1. 概述

### 1.1 基础信息

| 项目 | 说明 |
|------|------|
| 基础 URL | `http://<PC_IP>:8000`（本地开发可为 `http://localhost:8000`） |
| 路径前缀 | 所有接口均以 `/api` 开头 |
| 认证方式 | 请求头需携带 `X-API-KEY`，与后端配置的密钥一致 |
| 超时建议 | 部分接口会转发到机器人，建议客户端超时 ≥ 60s |

### 1.2 认证

每个请求需在 Header 中携带：

```
X-API-KEY: <密钥>
```

认证失败时 HTTP 状态码仍为 200，响应体为：

```json
{
  "code": 401,
  "msg": "认证失败",
  "data": null
}
```

### 1.3 统一响应格式

成功时：

```json
{
  "code": 0,
  "msg": "success",
  "data": { ... }
}
```

失败时（业务错误或参数校验失败等）：

```json
{
  "code": 400,
  "msg": "错误描述",
  "data": null
}
```

或 `data` 为错误详情（如校验失败时的字段列表）。服务端异常时 `code` 为 500。

---

## 2. TTS 播报

### 2.1 发起 TTS 播报

**POST** `/api/tts`

**请求体（JSON）**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| text | string | 是 | 播报文本，长度 1~200 |

**请求示例**

```json
{
  "text": "你好，我是远征机器人"
}
```

**响应示例**

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "trace_id": "hafhjkqwjwefkxxxx"
  }
}
```

`trace_id` 用于后续查询该次播报状态或打断播报。

---

### 2.2 打断 TTS 播报

**DELETE** `/api/tts`

无请求体。

**响应示例**

```json
{
  "code": 0,
  "msg": "success",
  "data": null
}
```

---

### 2.3 查询 TTS 播报状态

**GET** `/api/tts/status`

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| trace_id | string | 是 | 播报 id，长度 1~100 |

**响应示例**

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "tts_status": "TTSStatusType_Playing"
  }
}
```

`tts_status` 常见取值：`TTSStatusType_Playing`（播报中）、`TTSStatusType_NOTInQue`（已结束/未在队列）、`TTSStatusType_InQue`（队列中）、`TTSStatusType_Stop`（已打断）、`TTSStatusType_Error`（失败）等。

---

### 2.4 获取音量

**GET** `/api/tts/volume`

无参数。

**响应示例**

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "audio_volume": 50
  }
}
```

---

### 2.5 设置音量

**PUT** `/api/tts/volume`

**请求体（JSON）**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| audio_volume | int | 是 | 音量大小，0~70（超过 70 可能损坏扬声器） |

**请求示例**

```json
{
  "audio_volume": 40
}
```

**响应示例**

```json
{
  "code": 0,
  "msg": "success",
  "data": null
}
```

---

## 3. Agent 控制

### 3.1 设置交互运行模式

**POST** `/api/agent-control/agent-properties`

设置机器人交互模式并会触发 agent 重启以生效。

**请求体（JSON）**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| mode | string | 是 | 枚举：`only_voice` / `voice_face` / `normal` |

| mode | 说明 |
|------|------|
| only_voice | 仅输出降噪麦克音频，后续链路断开 |
| voice_face | 输出降噪麦克音频 + 人脸识别结果，后续链路断开 |
| normal | 常规交互模式，完整链路 |

**请求示例**

```json
{
  "mode": "voice_face"
}
```

**响应示例**

```json
{
  "code": 0,
  "msg": "success",
  "data": null
}
```

---

### 3.2 查询交互运行模式

**GET** `/api/agent-control/agent-properties`

无参数。

**响应示例**

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "mode": "voice_face"
  }
}
```

---

## 4. 人脸识别

### 4.1 获取云端人脸库信息

**GET** `/api/face-recognition/cloud-db`

无参数。返回机器人端云端人脸库信息（如 user_info.json 内容）。

**响应示例**

```json
{
  "code": 0,
  "msg": "success",
  "data": { ... }
}
```

---

### 4.2 启动人脸识别程序

**POST** `/api/face-recognition`

在机器人端启动人脸识别 Python 程序（如 get_face_id.py）。

**响应示例**

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

---

### 4.3 停止人脸识别程序

**DELETE** `/api/face-recognition`

**响应示例**

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "status": "stopped"
  }
}
```

---

### 4.4 获取人脸识别进程状态

**GET** `/api/face-recognition`

**响应示例**

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

或已停止时：`"is_running": false`, `"status": "stopped"`，可能带 `return_code`。

---

## 5. ASR（语音识别）

### 5.1 启动 ASR 程序

**POST** `/api/asr`

在机器人端启动 ASR 程序（get_voice.py），开始采集并上传音频到 PC 做识别。

**响应示例**

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "pid": 12346,
    "status": "started"
  }
}
```

---

### 5.2 停止 ASR 程序

**DELETE** `/api/asr`

**响应示例**

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "status": "stopped"
  }
}
```

---

### 5.3 获取 ASR 进程状态

**GET** `/api/asr`

**响应示例**

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "is_running": true,
    "status": "running",
    "pid": 12346
  }
}
```

---

## 6. Webhooks（机器人回调）

以下接口由**机器人端**主动调用，用于将人脸识别结果、ASR 音频上传到 PC。调用方需同样携带 `X-API-KEY`。  
（机器人通过 SSH 隧道访问 PC 时，通常请求 `http://127.0.0.1:8001` 对应 PC 的 8000 端口。）

### 6.1 人脸识别结果回调

**POST** `/api/webhooks/face-recognition`

**请求体（JSON）**

| 字段 | 类型 | 说明 |
|------|------|------|
| timestamp | string | 时间戳 |
| face_id | string | 人脸 ID |
| confidence | number | 置信度 |

**响应示例**

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "face_id": "A210041B50001917648293023663264"
  }
}
```

---

### 6.2 ASR 音频上传

**POST** `/api/webhooks/asr/audio`

**Content-Type**：`multipart/form-data`

**请求体**

| 字段 | 类型 | 说明 |
|------|------|------|
| file | file | 音频文件（二进制），如 PCM |

PC 端会进行语音转文字（FunASR）并返回识别文本。

**响应示例**

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "text": "识别出的文字内容"
  }
}
```

---

## 7. 通用接口

所有可编排的 REST 接口均收敛为单一入口，便于中控/前端统一调用。

### 7.1 获取支持的 action 列表

**GET** `/api/common/actions`

无参数。返回当前支持的 `action` 及参数说明。

**响应示例**

```json
{
  "code": 0,
  "msg": "success",
  "data": [
    {
      "action": "tts.play",
      "params": {"text": "string, 必填, 1~200 字"},
      "desc": "发起 TTS 播报"
    },
    {
      "action": "tts.stop",
      "params": {},
      "desc": "打断当前 TTS 播报"
    }
  ]
}
```

---

### 7.2 通用调用

**POST** `/api/common`

**请求体（JSON）**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | string | 是 | 动作标识，如 `tts.play`、`asr.start` |
| params | object | 否 | 该动作所需参数，默认 `{}` |

**请求示例 1：TTS 播报**

```json
{
  "action": "tts.play",
  "params": {
    "text": "你好"
  }
}
```

**请求示例 2：查询人脸识别状态**

```json
{
  "action": "face_recognition.status",
  "params": {}
}
```

**请求示例 3：设置音量**

```json
{
  "action": "tts.volume.set",
  "params": {
    "audio_volume": 50
  }
}
```

**响应格式**与前述接口一致，均为 `{ "code", "msg", "data" }`。例如成功时：

```json
{
  "code": 0,
  "msg": "success",
  "data": { ... }
}
```

**支持的 action 一览**

| action | params | 说明 |
|--------|--------|------|
| tts.play | `{ "text": "1~200 字" }` | 发起 TTS 播报 |
| tts.stop | `{}` | 打断 TTS 播报 |
| tts.status | `{ "trace_id": "string" }` | 查询 TTS 播报状态 |
| tts.volume.get | `{}` | 获取音量 |
| tts.volume.set | `{ "audio_volume": 0~70 }` | 设置音量 |
| agent.properties.set | `{ "mode": "only_voice\|voice_face\|normal" }` | 设置交互模式并重启 agent |
| agent.properties.get | `{}` | 查询交互模式 |
| face_recognition.cloud_db | `{}` | 获取云端人脸库信息 |
| face_recognition.start | `{}` | 启动人脸识别程序 |
| face_recognition.stop | `{}` | 停止人脸识别程序 |
| face_recognition.status | `{}` | 获取人脸识别进程状态 |
| asr.start | `{}` | 启动 ASR 程序 |
| asr.stop | `{}` | 停止 ASR 程序 |
| asr.status | `{}` | 获取 ASR 进程状态 |

若传入不支持的 `action`，返回 `code: 400`，提示可调用 `GET /api/common/actions` 查看列表。

---

## 8. 接口总览

| 分类 | 方法 | 路径 | 说明 |
|------|------|------|------|
| TTS | POST | /api/tts | 发起播报 |
| TTS | DELETE | /api/tts | 打断播报 |
| TTS | GET | /api/tts/status | 查询播报状态 |
| TTS | GET | /api/tts/volume | 获取音量 |
| TTS | PUT | /api/tts/volume | 设置音量 |
| Agent | POST | /api/agent-control/agent-properties | 设置交互模式 |
| Agent | GET | /api/agent-control/agent-properties | 查询交互模式 |
| 人脸 | GET | /api/face-recognition/cloud-db | 云端人脸库信息 |
| 人脸 | POST | /api/face-recognition | 启动人脸识别 |
| 人脸 | DELETE | /api/face-recognition | 停止人脸识别 |
| 人脸 | GET | /api/face-recognition | 人脸识别进程状态 |
| ASR | POST | /api/asr | 启动 ASR |
| ASR | DELETE | /api/asr | 停止 ASR |
| ASR | GET | /api/asr | ASR 进程状态 |
| Webhook | POST | /api/webhooks/face-recognition | 人脸识别结果回调 |
| Webhook | POST | /api/webhooks/asr/audio | ASR 音频上传 |
| 通用 | GET | /api/common/actions | 获取 action 列表 |
| 通用 | POST | /api/common | 通用调用 |

以上所有接口（除 Webhooks 由机器人调用外）均需在请求头中携带 `X-API-KEY`。
