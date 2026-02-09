#!/usr/bin/env python3

import logging
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from ros2_plugin_proto.msg import RosMsgWrapper

from aimdk.protocol_pb2 import ProcessedAudioOutput, AudioVADState

import datetime
import os
import time
import io
import requests


logger = logging.getLogger(__name__)

# PC 回调接口配置（模块级别）
PC_CALLBACK_URL = "http://127.0.0.1:8001/api/webhooks/asr/audio"
X_API_KEY = "NZGNJZMSDZJD"


def callback_pc_api(audio_data: bytes):
    """将音频通过 multipart/form-data 发送到 PC 回调接口（模块级函数）"""
    files = {"file": ("audio.pcm", io.BytesIO(audio_data), "audio/pcm")}
    response = requests.post(
        PC_CALLBACK_URL, files=files, headers={"X-API-KEY": X_API_KEY}, timeout=10
    )
    logger.info(f"ASR 回调响应: {response.json()}")


class AudioSubscriber(Node):
    def __init__(self):
        super().__init__("audio_subscriber")

        # 音频缓冲区，按stream_id分别存储
        self.audio_buffers = {}  # {stream_id: bytearray()}
        self.recording_state = {}  # {stream_id: bool} 记录是否正在录音
        # 记录每个流最后一次收到音频数据的时间戳（用于超时判断）
        self.last_activity = {}  # {stream_id: timestamp}
        # 录音超时阈值（秒），如果在该时间内未收到新的音频数据，则视为语音结束
        self.timeout_seconds = 2.0

        # 诊断计数
        self.vad_state_count = {}  # {stream_id: {state: count}}

        # 创建音频文件存储目录
        self.audio_output_dir = "audio_recordings"
        os.makedirs(self.audio_output_dir, exist_ok=True)

        qos_profile = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
        )

        self.subscription = self.create_subscription(
            RosMsgWrapper,
            "/agent/process_audio_output/pb_3Aaimdk_2Eprotocol_2EProcessedAudioOutput",
            self.audio_callback,
            qos_profile,
        )

        # 定时器：定期检查录音超时并在需要时结束录音保存文件
        self.create_timer(0.5, self.check_timeouts)

        self.get_logger().info("开始订阅降噪音频数据...")

    def audio_callback(self, msg):
        try:
            # 检查序列化类型是否为 pb
            if msg.serialization_type != "pb":
                self.get_logger().warn(f"不支持的序列化类型: {msg.serialization_type}")
                return

            # 将 data 字段从 list[bytes] 转换为 bytes
            audio_data_bytes = b"".join(msg.data)

            # 使用生成的 protobuf 类解析消息
            processed_audio = ProcessedAudioOutput()
            processed_audio.ParseFromString(audio_data_bytes)

            import json
            from google.protobuf.json_format import MessageToDict

            logger.debug(
                f"{json.dumps(MessageToDict(processed_audio, preserving_proto_field_name=True), ensure_ascii=False, indent=2)}"
            )

            # self.get_logger().info(
            #     f"收到音频数据: stream_id={processed_audio.stream_id}, "
            #     f"vad_state={processed_audio.vad_state}, "
            #     f"audio_size={len(processed_audio.audio_data)} bytes"
            # )

            # 根据VAD状态处理音频
            self.handle_vad_state(processed_audio)

        except Exception as e:
            self.get_logger().error(f"处理音频消息时出错: {e}")

    def handle_vad_state(self, processed_audio):
        """处理不同的VAD状态"""
        vad_state = processed_audio.vad_state
        stream_id = processed_audio.stream_id
        audio_data = processed_audio.audio_data

        # 初始化该stream_id的缓冲区（如果不存在）
        if stream_id not in self.audio_buffers:
            self.audio_buffers[stream_id] = bytearray()
            self.recording_state[stream_id] = False
            self.last_activity[stream_id] = 0.0
            self.vad_state_count[stream_id] = {}

        # VAD状态名称映射
        vad_state_names = {
            AudioVADState.AUDIO_VAD_STATE_NONE: "无语音",
            AudioVADState.AUDIO_VAD_STATE_BEGIN: "语音开始",
            AudioVADState.AUDIO_VAD_STATE_PROCESSING: "语音处理中",
            AudioVADState.AUDIO_VAD_STATE_END: "语音结束",
        }

        stream_names = {1: "内置麦克风", 2: "外置麦克风"}

        # 统计 VAD 状态
        if vad_state not in self.vad_state_count[stream_id]:
            self.vad_state_count[stream_id][vad_state] = 0
        self.vad_state_count[stream_id][vad_state] += 1

        # self.get_logger().info(
        #     f"[{stream_names.get(stream_id, f'未知流{stream_id}')}] "
        #     f"VAD状态: {vad_state_names.get(vad_state, f'未知状态{vad_state}')} (#{self.vad_state_count[stream_id][vad_state]}) "
        #     f"音频数据: {len(audio_data)} bytes"
        # )

        # 根据VAD状态处理音频数据
        if vad_state == AudioVADState.AUDIO_VAD_STATE_BEGIN:
            self.get_logger().info("🎤 检测到语音开始")
            # 只在首次开始录音时清空缓冲区，避免连续 BEGIN 数据丢失
            if not self.recording_state[stream_id]:
                self.audio_buffers[stream_id].clear()
            self.recording_state[stream_id] = True
            # 添加当前音频数据
            if len(audio_data) > 0:
                self.audio_buffers[stream_id].extend(audio_data)
                self.last_activity[stream_id] = time.time()
            else:
                # 记录开始时的时间戳，即使暂时没有音频数据
                self.last_activity[stream_id] = time.time()

        elif vad_state == AudioVADState.AUDIO_VAD_STATE_PROCESSING:
            self.get_logger().info("🔄 语音处理中...")
            # 如果正在录音，继续添加音频数据到缓冲区
            if self.recording_state[stream_id]:
                if len(audio_data) > 0:
                    self.audio_buffers[stream_id].extend(audio_data)
                # 无论是否有音频数据，都更新 last_activity（用于超时判断）
                self.last_activity[stream_id] = time.time()

        elif vad_state == AudioVADState.AUDIO_VAD_STATE_END:
            self.get_logger().info("✅ 语音结束")
            # 添加最后的音频数据
            if self.recording_state[stream_id] and len(audio_data) > 0:
                self.audio_buffers[stream_id].extend(audio_data)
            # 不立即保存，而是等待 timeout 机制来保存（与外置麦逻辑统一）
            self.last_activity[stream_id] = time.time()

        elif vad_state == AudioVADState.AUDIO_VAD_STATE_NONE:
            # 无语音状态，检查是否需要保存（处理缺少 END 的情况）
            if self.recording_state[stream_id]:
                # 如果正在录音且缓冲区有数据，先保存再重置
                if len(self.audio_buffers[stream_id]) > 0:
                    self.get_logger().info("⏹️ 检测到无语音状态，保存缓冲区音频")
                    self.save_audio_segment(
                        bytes(self.audio_buffers[stream_id]), stream_id)
                    self.audio_buffers[stream_id].clear()
                self.get_logger().info("⏹️ 录音状态重置")
                self.recording_state[stream_id] = False

        # 更新最后活动时间（如果收到任何音频数据）
        if len(audio_data) > 0:
            self.last_activity[stream_id] = time.time()

        # 输出当前缓冲区状态
        if stream_id in self.audio_buffers:
            buffer_size = len(self.audio_buffers[stream_id])
            recording = self.recording_state[stream_id]
            self.get_logger().debug(
                f"[Stream {stream_id}] 缓冲区大小: {buffer_size} bytes, 录音状态: {recording}"
            )

    def save_audio_segment(self, audio_data, stream_id):
        """保存音频段 16kHz, 16位, 单声道 PCM"""
        if len(audio_data) > 0:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")

            # 按stream_id创建子目录
            stream_dir = os.path.join(
                self.audio_output_dir, f"stream_{stream_id}")
            os.makedirs(stream_dir, exist_ok=True)

            # 生成文件名
            stream_names = {1: "internal_mic", 2: "external_mic"}
            stream_name = stream_names.get(stream_id, f"stream_{stream_id}")
            filename = f"{stream_name}_{timestamp}.pcm"
            filepath = os.path.join(stream_dir, filename)

            try:
                with open(filepath, "wb") as f:
                    f.write(audio_data)

                # 计算时长
                sample_rate = 16000
                bits_per_sample = 16
                channels = 1
                bytes_per_sample = bits_per_sample // 8
                total_samples = len(
                    audio_data) // (bytes_per_sample * channels)
                duration_seconds = total_samples / sample_rate

                # 打印诊断信息
                vad_counts = self.vad_state_count.get(stream_id, {})
                # self.get_logger().info(
                #     f"音频段已保存: {filepath} (大小: {len(audio_data)} bytes, 时长: {duration_seconds:.2f}s) "
                #     f"VAD统计: BEGIN={vad_counts.get(1, 0)} PROCESSING={vad_counts.get(2, 0)} END={vad_counts.get(3, 0)} NONE={vad_counts.get(0, 0)}"
                # )

                # 发送到 PC 回调接口
                try:
                    callback_pc_api(audio_data)
                except Exception as e:
                    self.get_logger().error(f"发送音频到回调接口失败: {e}")

            except Exception as e:
                self.get_logger().error(f"保存音频文件失败: {e}")

    def get_buffer_info(self):
        """获取所有缓冲区的信息（用于调试）"""
        info = {}
        for stream_id in self.audio_buffers:
            info[stream_id] = {
                "buffer_size": len(self.audio_buffers[stream_id]),
                "recording": self.recording_state[stream_id],
                "last_activity": self.last_activity.get(stream_id, 0.0),
            }
        return info

    def check_timeouts(self):
        """定时检查：对于处于录音中的流，如果超过超时阈值未收到新数据，则视为语音结束并保存。"""
        now = time.time()
        for stream_id, recording in list(self.recording_state.items()):
            if not recording:
                continue
            last = self.last_activity.get(stream_id, 0.0)
            if last <= 0:
                # 尚未有活动时间，跳过
                continue
            if now - last > self.timeout_seconds:
                # 超时，保存并重置状态
                buffer_bytes = bytes(self.audio_buffers.get(stream_id, b""))
                if len(buffer_bytes) > 0:
                    self.get_logger().info(
                        f"超时未收到结束信号，自动结束并保存流 {stream_id} 的音频（{now-last:.2f}s 无新数据）"
                    )
                    self.save_audio_segment(buffer_bytes, stream_id)
                # 重置状态
                self.recording_state[stream_id] = False
                self.audio_buffers[stream_id].clear()
                self.last_activity[stream_id] = 0.0


def main(args=None):
    rclpy.init(args=args)

    audio_subscriber = AudioSubscriber()

    try:
        audio_subscriber.get_logger().info("正在监听降噪音频数据，按 Ctrl+C 退出...")
        rclpy.spin(audio_subscriber)
    except KeyboardInterrupt:
        audio_subscriber.get_logger().info("收到退出信号，正在关闭...")
    finally:
        audio_subscriber.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
