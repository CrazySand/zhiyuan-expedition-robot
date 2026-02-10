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
  "msg": "操作成功",
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

## 2. 通用接口

所有可编排的 REST 接口均收敛为单一入口，便于中控/前端统一调用。

### 2.1 获取支持的 action 列表

**GET** `/api/common/actions`

无参数。返回当前支持的 `action` 及参数说明。

**响应示例**

```json
{
  "code": 0,
  "msg": "操作成功",
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

### 2.2 通用调用

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
  "msg": "操作成功",
  "data": { ... }
}
```

**支持的 action 一览**（不含 Agent 控制、Motion Control，中控无需主动调用）

| action | params | 说明 |
|--------|--------|------|
| tts.play | `{ "text": "1~200 字" }` | 发起 TTS 播报 |
| tts.stop | `{}` | 打断 TTS 播报 |
| tts.status | `{ "trace_id": "string" }` | 查询 TTS 播报状态 |
| tts.volume.get | `{}` | 获取音量 |
| tts.volume.set | `{ "audio_volume": 0~70 }` | 设置音量 |
| face_recognition.cloud_db | `{}` | 获取云端人脸库信息 |
| face_recognition.start | `{}` | 启动人脸识别程序 |
| face_recognition.stop | `{}` | 停止人脸识别程序 |
| face_recognition.status | `{}` | 获取人脸识别进程状态 |
| asr.start | `{}` | 启动 ASR 程序 |
| asr.stop | `{}` | 停止 ASR 程序 |
| asr.status | `{}` | 获取 ASR 进程状态 |
| map.list | `{}` | 获取地图列表（含当前工作地图） |
| map.detail | `{ "map_id": "string" }` | 获取地图详情（2D+拓扑点位） |
| nav.planning_to_goal | `{ "point_id": "int 必填", 可选 "task_id" }`（使用当前工作地图） | 下发到点规划导航任务 |
| nav.task_control | `{ "action": "cancel\|pause\|resume", "task_id" }` | 取消/暂停/恢复导航任务 |
| nav.status | `{ 可选 "task_id"，0 表示最近一次 }` | 获取导航任务状态 |

若传入不支持的 `action`，返回 `code: 400`，提示可调用 `GET /api/common/actions` 查看列表。

---

## 3. TTS 播报

### 3.1 发起 TTS 播报

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
  "msg": "操作成功",
  "data": {
    "trace_id": "hafhjkqwjwefkxxxx"
  }
}
```

`trace_id` 用于后续查询该次播报状态或打断播报。

---

### 3.2 打断 TTS 播报

**DELETE** `/api/tts`

无请求体。

**响应示例**

```json
{
  "code": 0,
  "msg": "操作成功",
  "data": null
}
```

---

### 3.3 查询 TTS 播报状态

**GET** `/api/tts/status`

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| trace_id | string | 是 | 播报 id，长度 1~100 |

**响应示例**

```json
{
  "code": 0,
  "msg": "操作成功",
  "data": {
    "tts_status": "TTSStatusType_Playing"
  }
}
```

`tts_status` 常见取值：`TTSStatusType_Playing`（播报中）、`TTSStatusType_NOTInQue`（已结束/未在队列）、`TTSStatusType_InQue`（队列中）、`TTSStatusType_Stop`（已打断）、`TTSStatusType_Error`（失败）等。

---

### 3.4 获取音量

**GET** `/api/tts/volume`

无参数。

**响应示例**

```json
{
  "code": 0,
  "msg": "操作成功",
  "data": {
    "audio_volume": 50
  }
}
```

---

### 3.5 设置音量

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
  "msg": "操作成功",
  "data": null
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
  "msg": "操作成功",
  "data": [
    {
      "description": "",
      "greeting": "random",
      "name": "张三",
      "nickname": "张三",
      "priority": 1,
      "timestamp": "1764078863000",
      "uid": "AGI812541E1FB25869472CE",
      "image_base64": "..."
    },
    {
      "description": "",
      "greeting": "random",
      "name": "李四",
      "nickname": "李四",
      "priority": 2,
      "timestamp": "1764078580000",
      "uid": "AGI81254464E98DB18C2C94",
      "image_base64": "..."
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| uid | string | 人脸唯一标识，用于 FaceID 回调中的 face_id 匹配 |
| name | string | 姓名 |
| nickname | string | 昵称 |
| description | string | 描述 |
| greeting | string | 问候语类型（如 random） |
| priority | int | 优先级 |
| timestamp | string | 时间戳 |

---

### 4.2 启动人脸识别程序

**POST** `/api/face-recognition`

在机器人端启动人脸识别 Python 程序（如 get_face_id.py）。

**前置条件**：当前交互模式须为 `voice_face` 或 `normal`，否则返回 `code: 400`，`msg: "当前交互模式不是 voice_face 或 normal"`

**响应示例**

```json
{
  "code": 0,
  "msg": "操作成功",
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
  "msg": "操作成功",
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
  "msg": "操作成功",
  "data": {
    "is_running": true,
    "status": "running",
    "pid": 12345
  }
}
```

或已停止时：`"is_running": false`, `"status": "stopped"`，可能带 `return_code`。

---

### 4.5 人脸识别「按次数自动关闭」（可选）

**说明**：启动人脸识别后，机器人每识别成功一次会回调 PC 的 `/api/webhooks/face-recognition`。若启用「按次数自动关闭」，PC 端会在**累计收到指定次数**的回调后**自动调用停止人脸识别**，无需中控再发停止指令。

**配置项**（`app/config.py`）：

| 配置项 | 类型 | 说明 |
|--------|------|------|
| FACE_RECOGNITION_AUTO_STOP_ENABLED | bool | 是否启用「识别成功 N 次后自动关闭」，默认 `True`；设为 `False` 则关闭该功能 |
| FACE_RECOGNITION_AUTO_STOP_AFTER_COUNT | int | 达到此次数后自动停止人脸识别，默认 `3`；仅当上述开关为 `True` 时有效 |

每次通过接口**启动**人脸识别时，计数会清零；达到设定次数后 PC 会自动调用机器人端停止人脸识别，并打日志。

---

## 5. ASR（语音识别）

### 5.1 启动 ASR 程序

**POST** `/api/asr`

在机器人端启动 ASR 程序（get_voice.py），开始采集并上传音频到 PC 做识别。

**前置条件**：当前交互模式须为 `only_voice` 或 `voice_face`，否则返回 `code: 400`，`msg: "当前交互模式不是 only_voice 或 voice_face"`。

**响应示例**

```json
{
  "code": 0,
  "msg": "操作成功",
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
  "msg": "操作成功",
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
  "msg": "操作成功",
  "data": {
    "is_running": true,
    "status": "running",
    "pid": 12346
  }
}
```

---

## 6. Map（地图）

### 6.1 获取地图列表

**GET** `/api/map/list`

无参数。返回地图列表及当前工作地图信息。

**响应示例**

```json
{
  "code": 0,
  "msg": "操作成功",
  "data": {
    "current_working_map_id": "1764059676131",
    "current_working_map_name": "园区",
    "map_lists": [
      {
        "map_id": "1764059676131",
        "map_name": "园区",
        "map_index": 3
      }
    ]
  }
}
```

---

### 6.2 获取地图详情

**GET** `/api/map/detail`

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| map_id | string | 是 | 地图 id（可从 map/list 的 map_lists 取） |

**响应示例**

```json
{
  "code": 0,
  "msg": "操作成功",
  "data": {
    "map_id": "1764059676131",
    "map_name": "园区",
    "points": [
      {"point_id": 1, "point_name": "导航点1"}
    ]
  }
}
```

若 map_id 不存在，返回 `code: 400`，`msg: "地图ID不存在"`。

---

## 7. Nav（导航）

执行前需：MC 状态为 `RL_LOCOMOTION_DEFAULT`、已重定位、下发任务的地图 id 与重定位地图一致。

### 7.1 下发到点规划导航任务

**POST** `/api/nav/planning-to-goal`

**请求体（JSON）**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string \| null | 否 | 任务 id，不传或 null 表示自动生成，返回的 task_id 需保存以便后续控制/查询 |
| current_working_map_id | string | 是 | 当前工作地图 id（须与重定位地图一致） |
| point_id | int | 是 | 导航点 id（拓扑 point_id，可从 map/detail 的 points 取） |

**响应示例**

```json
{
  "code": 0,
  "msg": "操作成功",
  "data": {
    "task_id": "9820900024371944166"
  }
}
```

若 current_working_map_id 非当前工作地图，返回 `code: 400`，`msg: "非当前工作地图"`。到点精度约 0.4 米。

PC 端会后台轮询该任务状态；任务暂停或结束（成功/失败）时，会向中控推送事件（见《中控回调接口文档》navTaskPaused、navTaskFinished），params 包含 `task_id`、`state`、`point_id`（即本次下发的目标点 ID）。

---

### 7.2 取消 / 暂停 / 恢复导航任务

**POST** `/api/nav/task-control`

**请求体（JSON）**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | string | 是 | 枚举：`cancel`（取消）/ `pause`（暂停）/ `resume`（恢复） |
| task_id | string | 是 | 要操作的任务 id，需与下发时返回的 task_id 一致 |

**响应示例**

```json
{
  "code": 0,
  "msg": "操作成功",
  "data": null
}
```

仅当 task_id 匹配时才响应；否则返回 `code: 400`，`msg: "任务不存在、已结束或 task_id 不匹配"`。

---

### 7.3 获取导航任务状态

**GET** `/api/nav/status`

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string \| null | 否 | 任务 id；不传或传 0 表示查询最近一次任务 |

**响应示例**

```json
{
  "code": 0,
  "msg": "操作成功",
  "data": {
    "task_id": "9820900024371944166",
    "state": "PncServiceState_RUNNING"
  }
}
```

`state` 枚举：`PncServiceState_UNDEFINED`、`PncServiceState_IDLE`、`PncServiceState_RUNNING`、`PncServiceState_PAUSED`、`PncServiceState_SUCCESS`、`PncServiceState_FAILED`。

---

## 8. Agent 控制（无需主动调用）

> **说明**：PC 端会自行控制交互模式，中控无需主动调用本节接口。

### 8.1 设置交互运行模式

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
  "msg": "操作成功",
  "data": null
}
```

---

### 8.2 查询交互运行模式

**GET** `/api/agent-control/agent-properties`

无参数。

**响应示例**

```json
{
  "code": 0,
  "msg": "操作成功",
  "data": {
    "mode": "voice_face"
  }
}
```

---

## 9. Motion Control（无需主动调用）

> **说明**：PC 端会自行控制运控状态机（如导航前切换等），中控无需主动调用本节接口。

### 9.1 切换运控状态机

**POST** `/api/motion-control/mc-action`

切换运动控制状态机（异步，需轮询 GET 接口确认是否切换完成）。导航前需切到 `RL_LOCOMOTION_DEFAULT`。

**请求体（JSON）**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ext_action | string | 是 | 枚举：`RL_LOCOMOTION_DEFAULT` / `PASSIVE_UPPER_BODY_JOINT_SERVO` / `RL_LOCOMOTION_ARM_EXT_JOINT_SERVO` |

**响应示例**

```json
{
  "code": 0,
  "msg": "操作成功",
  "data": null
}
```

---

### 9.2 查询当前运控状态机

**GET** `/api/motion-control/mc-action`

无参数。

**响应示例**

```json
{
  "code": 0,
  "msg": "操作成功",
  "data": {
    "current_action": "McAction_RL_LOCOMOTION_ARM_EXT_JOINT_SERVO"
  }
}
```

---

## 10. Webhooks（机器人回调，非中控调用）

> **机器人回调接口**：本节接口由**机器人端**主动调用 **PC 端**，用于将人脸识别结果、ASR 音频上传到 PC。**中控不调用这些接口**；中控仅接收 PC 端转发后的回调（见《中控回调接口文档》）。  
> 调用方需携带 `X-API-KEY`。机器人通过 SSH 隧道访问 PC 时，通常请求 `http://127.0.0.1:8001` 对应 PC 的 8000 端口。

### 10.1 人脸识别结果回调

**POST** `/api/webhooks/face-recognition`

机器人端识别人脸成功后调用本接口，PC 会将结果转发至中控（见《中控回调接口文档》faceRecognition）。若已启用「按次数自动关闭」（见 **4.5**），PC 会在累计收到设定次数（如 3 次）后自动停止人脸识别。

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
  "msg": "操作成功",
  "data": {
    "face_id": "A210041B50001917648293023663264"
  }
}
```

---

### 10.2 ASR 音频上传

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
  "msg": "操作成功",
  "data": {
    "text": "识别出的文字内容"
  }
}
```

---

## 11. 接口总览

| 分类 | 方法 | 路径 | 说明 | 中控调用说明 |
|------|------|------|------|--------------|
| 通用 | GET | /api/common/actions | 获取 action 列表 | 中控可调用 |
| 通用 | POST | /api/common | 通用调用 | 中控可调用 |
| TTS | POST | /api/tts | 发起播报 | 中控可调用 |
| TTS | DELETE | /api/tts | 打断播报 | 中控可调用 |
| TTS | GET | /api/tts/status | 查询播报状态 | 中控可调用 |
| TTS | GET | /api/tts/volume | 获取音量 | 中控可调用 |
| TTS | PUT | /api/tts/volume | 设置音量 | 中控可调用 |
| 人脸 | GET | /api/face-recognition/cloud-db | 云端人脸库信息 | 中控可调用 |
| 人脸 | POST | /api/face-recognition | 启动人脸识别 | 中控可调用 |
| 人脸 | DELETE | /api/face-recognition | 停止人脸识别 | 中控可调用 |
| 人脸 | GET | /api/face-recognition | 人脸识别进程状态 | 中控可调用 |
| ASR | POST | /api/asr | 启动 ASR | 中控可调用 |
| ASR | DELETE | /api/asr | 停止 ASR | 中控可调用 |
| ASR | GET | /api/asr | ASR 进程状态 | 中控可调用 |
| Map | GET | /api/map/list | 获取地图列表 | 中控可调用 |
| Map | GET | /api/map/detail | 获取地图详情 | 中控可调用 |
| Nav | POST | /api/nav/planning-to-goal | 下发到点规划导航 | 中控可调用 |
| Nav | POST | /api/nav/task-control | 取消/暂停/恢复导航任务 | 中控可调用 |
| Nav | GET | /api/nav/status | 获取导航任务状态 | 中控可调用 |
| Agent（无需主动调用） | POST | /api/agent-control/agent-properties | 设置交互模式 | **中控无需主动调用**，PC 端自行控制 |
| Agent（无需主动调用） | GET | /api/agent-control/agent-properties | 查询交互模式 | **中控无需主动调用**，PC 端自行控制 |
| Motion Control（无需主动调用） | POST | /api/motion-control/mc-action | 切换运控状态机 | **中控无需主动调用**，PC 端自行控制 |
| Motion Control（无需主动调用） | GET | /api/motion-control/mc-action | 查询当前运控状态机 | **中控无需主动调用**，PC 端自行控制 |
| Webhook | POST | /api/webhooks/face-recognition | 人脸识别结果回调 | **机器人回调**，机器人→PC，非中控调用 |
| Webhook | POST | /api/webhooks/asr/audio | ASR 音频上传 | **机器人回调**，机器人→PC，非中控调用 |

以上所有接口（除 Webhooks 由机器人调用外）均需在请求头中携带 `X-API-KEY`。  
中控需提供的回调接收接口见《中控回调接口文档》。
