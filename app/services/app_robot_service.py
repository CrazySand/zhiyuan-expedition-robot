import httpx


class AppRobotService:

    def __init__(self, client: httpx.AsyncClient, server_ip: str = "127.0.0.1"):
        self.client = client
        self.server_ip = server_ip

    async def agent_mode_reboot(self):
        """重启 agent 模块"""
        url = f"http://{self.server_ip}:59888/api/agent-mode-reboot"
        data = {}
        response = await self.client.post(url, json=data)
        return response.json()

    async def get_cloud_face_db_info(self):
        """获取云端人脸数据库信息"""
        url = f"http://{self.server_ip}:59888/api/cloud-face-db-info"
        response = await self.client.get(url)
        return response.json()

    async def start_face_recognition(self):
        """启动人脸识别 Python 程序"""
        url = f"http://{self.server_ip}:59888/api/face-recognition/start"
        response = await self.client.post(url)
        return response.json()
    
    async def stop_face_recognition(self):
        """停止人脸识别 Python 程序"""
        url = f"http://{self.server_ip}:59888/api/face-recognition/stop"
        response = await self.client.post(url)
        return response.json()
    
    async def get_face_recognition_status(self):
        """获取人脸识别进程状态"""
        url = f"http://{self.server_ip}:59888/api/face-recognition/status"
        response = await self.client.get(url)
        return response.json()

