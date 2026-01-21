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


async def main():
    e = AppRobotService(httpx.AsyncClient(
        headers={"Authorization": "Bearer your-secret-key-here"}, timeout=60))
    r = await e.agent_mode_reboot()
    print(r)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
