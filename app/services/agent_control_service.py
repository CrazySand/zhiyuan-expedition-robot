from typing import Literal
import httpx


class AgentControlService:

    def __init__(self, client: httpx.AsyncClient, server_ip: str = "127.0.0.1"):
        self.client = client
        self.server_ip = server_ip

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
        url = f"http://{self.server_ip}:59301/rpc/aimdk.protocol.AgentControlService/SetAgentPropertiesRequest"
        data = {
            "contents": {
                "properties": {
                    "2": mode
                }
            }
        }
        response = await self.client.post(url, json=data)
        return response.json()

    async def get_agent_properties(self) -> Literal["only_voice", "voice_face", "normal"]:
        """
        查询交互运行模式

        Returns:
            Literal["only_voice", "voice_face", "normal"]: 当前交互运行模式，枚举值：
                - "only_voice": 仅输出降噪麦克音频 /agent/process_audio_output，后续链路全部断开
                - "voice_face": 输出降噪麦克音频 /agent/process_audio_output 和人脸识别结果 /agent/vision/face_id，后续链路全部断开
                - "normal": 常规运行模式，交互正常运行
        """
        url = f"http://{self.server_ip}:59301/rpc/aimdk.protocol.AgentControlService/GetAgentPropertiesRequest"
        data = {
            "property_ids": [2]
        }
        response = await self.client.post(url, json=data)
        return response.json()

