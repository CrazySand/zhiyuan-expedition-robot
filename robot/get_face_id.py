"""
{
  "faces": [
    {
      "timestamp": "1764829536028",
      "face_id": "A210041B50001917648293023663264",
      "confidence": 0.9811308,
      "face_rect": {
        "x": 326.0,
        "y": 961.0,
        "width": 105.0,
        "height": 119.0
      },
      "captured_feature_base64": "...",
      "reference_feature_base64": "..."
    }
  ]
}

source /opt/ros/humble/setup.bash
source /agibot/data/home/agi/Desktop/agibot_a2_aimdk-dev1.3/prebuilt/ros2_plugin_proto_aarch64/share/ros2_plugin_proto/local_setup.bash
source /agibot/data/home/agi/Desktop/mydev/bin/activate
export ROS_DOMAIN_ID=232
export ROS_LOCALHOST_ONLY=0
export FASTRTPS_DEFAULT_PROFILES_FILE=/agibot/software/v0/entry/bin/cfg/ros_dds_configuration.xml
python /agibot/data/home/agi/Desktop/get_face_id.py
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from ros2_plugin_proto.msg import RosMsgWrapper
from aimdk.protocol_pb2 import FaceIdResult

import json
from google.protobuf.json_format import MessageToDict
import requests

PC_CALLBACK_URL = "http://127.0.0.1:8001/api/robot-call-back/face/recognition"
X_API_KEY = "NZGNJZMSDZJD"


def callback_pc_api(face_info: dict):
    """处理 FaceID 结果"""
    response = requests.post(PC_CALLBACK_URL, json=face_info, headers={
        "Content-Type": "application/json", "X-API-KEY": X_API_KEY})
    print(response.json())


class FaceIdSubscriber(Node):

    def __init__(self):
        super().__init__("face_id_subscriber")

        qos_profile = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
        )

        self.subscription = self.create_subscription(
            RosMsgWrapper,
            "/agent/vision/face_id/pb_3Aaimdk_2Eprotocol_2EFaceIdResult",
            self.face_id_callback,
            qos_profile,
        )

        self.get_logger().info("已开始订阅 FaceID 数据...")

    def face_id_callback(self, msg):
        try:
            if msg.serialization_type != "pb":
                self.get_logger().warn(
                    f"收到不支持的序列化类型: {msg.serialization_type}"
                )
                return

            # 拼接 bytes
            raw_bytes = b"".join(msg.data)

            # 解析 protobuf
            face_id_result = FaceIdResult()
            face_id_result.ParseFromString(raw_bytes)

            face_info = MessageToDict(
                face_id_result, preserving_proto_field_name=True)["faces"][0]
            callback_pc_api(face_info)
            # 日志输出
            # self.get_logger().info(
            #     f"FaceID 结果: {face_info}")

        except Exception as e:
            self.get_logger().error(f"解析 FaceID 数据时出现错误: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = FaceIdSubscriber()

    try:
        node.get_logger().info("正在监听 FaceID 数据，按 Ctrl+C 退出...")
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("退出中...")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
