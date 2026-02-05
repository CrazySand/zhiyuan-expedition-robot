from typing import Literal
import httpx


class RobotAPIClient:
    """调用机器人端 API 的客户端"""

    def __init__(self, client: httpx.AsyncClient, orin_mapped_ip: str, x86_ip: str):
        self.client = client
        self.orin_mapped_ip = orin_mapped_ip
        self.x86_ip = x86_ip

    # ============================= TTS ========================================

    async def play_tts(
        self,
        text: str,
        priority_level: str = "INTERACTION_L6",
        domain: str = "example",
        trace_id: str = "hafhjkqwjwefk",
        is_interrupted: bool = True
    ) -> dict:
        """
        TTS 播报接口，依赖联网

        Note:
            - 只支持短文本请求，最高只支持 1024 字节，约 200 个中文/英文
            - 麦克风优先级是最高的，如果麦克风有播报，tts 会被加入队列
            - is_interrupted 参数似乎没用

        Args:
            text (str): 播报文本内容
            priority_level (str): 优先级，保持 INTERACTION_L6 即可
            domain (str): 调用方来源标识，可以传入自定义的客户端字符串，方便问题排查等
            trace_id (str): 播报 id，如果需要获取播报状态，则需要传入该字段，并将其值作为查询播报状态的参数
            is_interrupted (bool): 是否打断同等优先级播报，请默认传 true，有队列播报的需求可以使用 false

        Returns:
            dict: 包含以下字段的字典：
                - text (str): 播报文本内容
                - priority_level (str): 优先级等级，无需关注
                - priority_weight (int): 优先级权重，无需关注
                - domain (str): 调用方来源标识，返回请求中传入的自定义字符串，方便问题排查
                - trace_id (str): 播报 id，返回请求中传入的自定义字符串 + 一段随机字符串，用于播报状态查询等
                - is_success (bool): 优先级校验是否成功，一般均为 true，不代表会播放，例如传入错误或不存在的文件名仍会返回 true，只有当前有更高优先级的内容播报时才会返回 false，例如当前有故障报警播报时
                - error_message (str): 错误信息
                - estimated_duration (int): 无效字段，无需关注，无法估算播放时长
        """
        url = f"http://{self.orin_mapped_ip}:59301/rpc/aimdk.protocol.TTSService/PlayTTS"
        payload = {
            "text": text,
            "priority_level": priority_level,
            "domain": domain,
            "trace_id": trace_id,
            "is_interrupted": is_interrupted
        }
        response = await self.client.post(url, json=payload)
        return response.json()

    async def stop_tts(self, trace_id: str = "hafhjkqwjwefk") -> dict:
        """
        打断单个文件/TTS播放

        Args:
            trace_id (str): 播报 id，填写调用 PlayTTS 或 PlayMediaFile 接口时传入的自定义 id

        Returns:
            dict: 包含以下字段的字典：
                - state (str): 调用请求状态，无需关注具体值，HTTP 请求返回 200 即代表成功
        """
        url = f"http://{self.orin_mapped_ip}:59301/rpc/aimdk.protocol.TTSService/StopTTSTraceId"
        payload = {
            "trace_id": trace_id
        }
        response = await self.client.post(url, json=payload)
        return response.json()

    async def get_audio_status(self, trace_id: str) -> dict:
        """
        TTS/音频文件播放状态查询

        Note:
            实际上大多情况下只能获取到 "TTSStatusType_Playing" 和 "TTSStatusType_NOTInQue" 这两种状态

        Args:
            trace_id (str): 播报 id，填写调用 PlayTTS 或 PlayMediaFile 接口时传入的自定义 id

        Returns:
            dict: 包含以下字段的字典：
                - tts_status (dict): 播报状态对象，包含以下字段：
                    - text (str): 无效字段，无需关注
                    - priority (int): 无效字段，无需关注
                    - trace_id (str): 无效字段，无需关注
                    - tts_status (str): 播报状态，枚举值：
                        - "TTSConfigStatusType_Unknown": 未知状态
                        - "TTSStatusType_Begin": 开始播报，短暂，一般查询不到这个状态
                        - "TTSStatusType_Playing": 播报中
                        - "TTSStatusType_End": 播报结束，短暂，一般查询不到这个状态
                        - "TTSStatusType_Stop": 暂停播报/取消播报/中断播报
                        - "TTSStatusType_Error": 播报失败
                        - "TTSStatusType_InQue": 在播报队列中，尚未开始播报
                        - "TTSStatusType_NOTInQue": 播报队列无此文本，也不在播报，播报结束后会进入此状态
                    - domain (str): 无效字段，无需关注
                    - error_message (str): 错误信息
        """
        url = f"http://{self.orin_mapped_ip}:59301/rpc/aimdk.protocol.TTSService/GetAudioStatus"
        payload = {
            "trace_id": trace_id
        }
        response = await self.client.post(url, json=payload)
        return response.json()

    async def get_audio_volume(self) -> dict:
        """
        获取当前音量大小

        Returns:
            dict: 包含以下字段的字典：
                - header (dict): 响应头信息，包含 code、msg、trace_id、domin 字段
                - audio_volume (int): 音量大小，0-100 的数值
                - is_mute (bool): 是否静音
                - type (str): 扬声器类型，枚举值：
                    - "SPEAKRE_BUILT_IN": 内置扬声器
                    - "SPERKER_BULETOOTH": 蓝牙扬声器
        """
        url = f"http://{self.orin_mapped_ip}:56666/rpc/aimdk.protocol.HalAudioService/GetAudioVolume"
        response = await self.client.post(url, json={})
        return response.json()

    async def set_audio_volume(
        self,
        audio_volume: int,
        is_mute: bool = False,
        type: str = "SPEAKRE_BUILT_IN"
    ) -> dict:
        """
        调节音量

        Note:
            - 注意不要调节音量超过 70，音量超出此范围扬声器经功放放大后会超额定工作，造成扬声器损坏
            - 如需静音，请将 audio_volume 字段设为 0，is_mute 设为 true

        Args:
            audio_volume (int): 音量大小，0-100 的数值
            is_mute (bool): 是否静音
            type (str): 扬声器类型，默认为 "SPEAKRE_BUILT_IN"（内置扬声器）

        Returns:
            dict: 包含以下字段的字典：
                - header (dict): 响应头信息，包含 code、msg、trace_id、domin 字段
                - pkg_name (str): 无效字段，无需关注
                - is_success (bool): 无效字段，无需关注
        """
        url = f"http://{self.orin_mapped_ip}:56666/rpc/aimdk.protocol.HalAudioService/SetAudioVolume"
        payload = {
            "audio_volume": audio_volume,
            "is_mute": is_mute,
            "type": type
        }
        response = await self.client.post(url, json=payload)
        return response.json()

    # ============================= Agent Control ========================================

    async def set_agent_properties(self, mode: Literal["only_voice", "voice_face", "normal"]) -> dict:
        """
        设置交互运行模式

        Note:
            - 调用后需要重启 agent 或重启机器人方可生效
            - 调用后返回值为 "CommonState_UNKNOWN" 是正常现象，可以调用 get_agent_properties 接口，查看交互运行模式是否切换成功

        Args:
            mode (Literal["only_voice", "voice_face", "normal"]): 交互运行模式，枚举值：
                - "only_voice": 仅输出降噪麦克音频 /agent/process_audio_output，后续链路全部断开
                - "voice_face": 输出降噪麦克音频 /agent/process_audio_output 和人脸识别结果 /agent/vision/face_id，后续链路全部断开
                - "normal": 常规运行模式，交互正常运行

        Returns:
            dict: 包含以下字段的字典：
                - state (str): 调用请求状态，返回 "CommonState_UNKNOWN" 是正常现象，无需关注具体值，HTTP 请求返回 200 即代表成功
        """
        url = f"http://{self.orin_mapped_ip}:59301/rpc/aimdk.protocol.AgentControlService/SetAgentPropertiesRequest"
        payload = {
            "contents": {
                "properties": {
                    "2": mode
                }
            }
        }
        response = await self.client.post(url, json=payload)
        return response.json()

    async def get_agent_properties(self) -> dict:
        """查询交互运行模式"""
        url = f"http://{self.orin_mapped_ip}:59301/rpc/aimdk.protocol.AgentControlService/GetAgentPropertiesRequest"
        payload = {
            "property_ids": [2]
        }
        response = await self.client.post(url, json=payload)
        return response.json()

    async def agent_mode_reboot(self) -> dict:
        """重启 agent 模块（机器人端 59888）"""
        url = f"http://{self.orin_mapped_ip}:59888/api/agent-mode-reboot"
        response = await self.client.post(url)
        return response.json()

    # ============================= Motion Control ========================================

    async def set_mc_action(self, ext_action: Literal["DEFAULT", "RL_LOCOMOTION_DEFAULT", "PASSIVE_UPPER_BODY_JOINT_SERVO", "RL_LOCOMOTION_ARM_EXT_JOINT_SERVO"], action: str = "McAction_USE_EXT_CMD") -> dict:
        """
        切换运动控制状态机（异步接口，调用完成不代表切换即完成，需配合 get_mc_action 查询是否切换成功）
        导航模式需要用到 RL_LOCOMOTION_DEFAULT，切换该模式后不影响非二开功能

        Args:
            ext_action: 目标运控 Action，枚举值：
                - "DEFAULT": 默认模式，运控启动后的默认 action，这个模式似乎代表着急停，切换到此模式之后机器人双脚无力，并且不能再切换为其它模式
                - "RL_LOCOMOTION_DEFAULT": 强化行走模式（拟人行走，走路时手臂会摆动）
                - "PASSIVE_UPPER_BODY_JOINT_SERVO": 下肢被动上肢伺服模式（下肢不使能，手臂可接收外部关节伺服指令）
                - "RL_LOCOMOTION_ARM_EXT_JOINT_SERVO"：强化行走上肢伺服模式（下肢拟人行走或站立，上肢接受外部关节伺服指令，行走或站立时做动作（使用全身控制的强化模型，更具有稳定性）
            action: 固定填写为 McAction_USE_EXT_CMD，一般无需修改

        Returns:
            dict: 包含 header、state 等字段；state 为 "CommonState_SUCCESS" 表示请求成功，实际切换完成需轮询 get_mc_action
        """
        url = f"http://{self.x86_ip}:56322/rpc/aimdk.protocol.McActionService/SetAction"
        payload = {
            # "header": {
            #     "timestamp": {
            #         "seconds": 1763614279,
            #         "nanos": 847810000,
            #         "ms_since_epoch": 1763614279847
            #     },
            #     "control_source": "ControlSource_SAFE"
            # },
            "command": {
                "action": action,
                "ext_action": ext_action
            }
        }
        response = await self.client.post(url, json=payload)
        return response.json()

    async def get_mc_action(self) -> dict:
        """
        查询当前运动控制状态机

        Returns:
            dict: 包含 info 等字段；info.current_action 为当前运行的 Action（如 McAction_RL_LOCOMOTION_ARM_EXT_JOINT_SERVO）
        """
        url = f"http://{self.x86_ip}:56322/rpc/aimdk.protocol.McActionService/GetAction"
        response = await self.client.post(url, json={})
        return response.json()

    # ============================= Face Recognition ========================================

    async def get_cloud_face_db_info(self) -> dict:
        """获取云端人脸数据库信息"""
        url = f"http://{self.orin_mapped_ip}:59888/api/face-recognition/cloud-db"
        response = await self.client.get(url)
        return response.json()

    async def start_face_recognition(self) -> dict:
        """启动人脸识别 Python 程序"""
        url = f"http://{self.orin_mapped_ip}:59888/api/face-recognition"
        response = await self.client.post(url)
        return response.json()

    async def stop_face_recognition(self) -> dict:
        """停止人脸识别 Python 程序"""
        url = f"http://{self.orin_mapped_ip}:59888/api/face-recognition"
        response = await self.client.delete(url)
        return response.json()

    async def get_face_recognition_status(self) -> dict:
        """获取人脸识别进程状态"""
        url = f"http://{self.orin_mapped_ip}:59888/api/face-recognition"
        response = await self.client.get(url)
        return response.json()

    # ============================= ASR =======================================================

    async def start_asr(self) -> dict:
        """启动 ASR 程序（get_voice.py）"""
        url = f"http://{self.orin_mapped_ip}:59888/api/asr"
        response = await self.client.post(url)
        return response.json()

    async def stop_asr(self) -> dict:
        """停止 ASR 程序"""
        url = f"http://{self.orin_mapped_ip}:59888/api/asr"
        response = await self.client.delete(url)
        return response.json()

    async def get_asr_status(self) -> dict:
        """获取 ASR 进程状态"""
        url = f"http://{self.orin_mapped_ip}:59888/api/asr"
        response = await self.client.get(url)
        return response.json()

    # ============================= MAP =======================================================

    async def get_stored_map_names(self, command: str = "MappingCommand_GET_STORED_MAP_NAME") -> dict:
        """
        获取地图列表

        Returns:
            dict: 响应体，通常含 data 字段，data 内包含：
                - map_lists (list): 地图列表，每项包含：
                    - map_id (str): 地图 id，供 get_2d_whole_map、get_topo_msgs 使用
                    - map_name (str): 地图名称
                    - map_index (int): 地图索引
        """
        url = f"http://{self.orin_mapped_ip}:50807/rpc/aimdk.protocol.MappingService/GetStoredMapNames"
        payload = {
            "command": command
        }
        response = await self.client.post(url, json=payload)
        return response.json()

    async def get_2d_whole_map(self, map_id: str, command: str = "MappingCommand_GET_2D_WHOLE_MAP") -> dict:
        """
        获取 2D 地图数据（MappingService）根据地图 id 返回整张 2D 地图的元数据及栅格数据（PNG）

        Args:
            map_id: 需要获取信息的地图 id，可从 get_stored_map_names 得到
            command: 固定为 MappingCommand_GET_2D_WHOLE_MAP，一般无需修改

        Returns:
            dict: 响应体，通常含 data 字段，data 内包含：
                - map_id (str): 地图 id
                - map_name (str): 地图名称
                - width (int): 地图宽度（像素）
                - height (int): 地图高度（像素）
                - resolution (int): 分辨率
                - origin_x, origin_y (int): 建图时坐标原点，可视为地图原点
                - map_data (str): 地图数据，PNG 格式
                - rotate_angle (float): 旋转角度，供客户端展示用，可忽略
                - map_url (str): 无效字段，可忽略
        """
        url = f"http://{self.orin_mapped_ip}:50807/rpc/aimdk.protocol.MappingService/Get2DWholeMap"
        payload = {
            "command": command,
            "map_id": map_id
        }
        response = await self.client.post(url, json=payload)
        return response.json()

    async def get_topo_msgs(self, map_id: str, command: str = "TopoCommand_GET_TOPO_MSG") -> dict:
        """
        获取地图拓扑数据（LocalizationService）。点位可用于动线讲解、导航等；paths、regions 一般不使用。

        Args:
            map_id: 地图 id，可与 get_stored_map_names / get_2d_whole_map 使用同一 id。
            command: 固定为 TopoCommand_GET_TOPO_MSG，一般无需修改。

        Returns:
            dict: 响应体，通常含 data 字段，data 内包含：
                - points (list): 点位列表，每项包含：
                    - point_id (int): 点位 id
                    - name (str): 点位名称
                    - point_type (str): 点位类型（如 NaviPointType_NAVI_POINT）
                    - pixel_pose (dict): 像素坐标，含 position.u、position.v、angle
                    - pose (dict): 世界坐标，含 position.x、position.y、position.z
                - paths (list): 路线，一般不使用，无需关注
                - regions (list): 区域，一般不使用，无需关注
        """
        url = f"http://{self.orin_mapped_ip}:50807/rpc/aimdk.protocol.LocalizationService/GetTopoMsgs"
        payload = {
            "command": command,
            "map_id": map_id
        }
        response = await self.client.post(url, json=payload)
        return response.json()
