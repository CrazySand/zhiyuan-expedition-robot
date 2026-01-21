import json
import aiofiles


async def read_cloud_face_db_info():
    """读取云端人脸数据库信息"""
    async with aiofiles.open("/agibot/data/param/interaction/face_id/user_info.json", "r", encoding="utf-8") as f:
        data = await f.read()
        return json.loads(data)
