#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import sys
import termios
import tty
import select
import whisper
import numpy as np
import re
import subprocess
import tempfile
import wave
import os
from zhconv import convert
from std_msgs.msg import String

class VoiceCommander:
    def __init__(self):
        rospy.init_node('voice_commander', anonymous=True)
        self.pub = rospy.Publisher('/navigation_instruction', String, queue_size=1)

        # 加载Whisper中文模型
        rospy.loginfo("Loading Whisper model (base)...")
        self.model = whisper.load_model("base")
        rospy.loginfo("Model loaded.")

        # 物体名称映射
        self.object_map = {
            "饮水机": "water dispenser",
            "门": "door",
            "椅子": "the black chair",
            "白色椅子": "white chair",
            "桌子": "table",
            "沙发": "sofa",
            "风扇": "the black fan",
            "垃圾桶": "trash can",
            "纸箱": "cardboard box"
        }

        rospy.loginfo("Voice commander ready. Press ENTER to start recording...")

    def get_key(self):
        """非阻塞获取按键"""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    def record_audio(self, timeout=12, phrase_time_limit=12):
        """使用 arecord 录制音频，返回 numpy 数组 (float32, -1..1)"""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            filename = tmp.name
        cmd = [
            'arecord', '-D', 'sysdefault:CARD=Camera',  # 使用系统默认的摄像头设备
            '-f', 'S16_LE', '-r', '16000',
            '-d', str(phrase_time_limit),
            filename
        ]
        rospy.loginfo("Recording...")
        try:
            subprocess.run(cmd, check=True, timeout=timeout+1)
            rospy.loginfo("Recording finished.")
            with wave.open(filename, 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                audio_np = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            os.unlink(filename)
            return audio_np
        except subprocess.CalledProcessError as e:
            rospy.logerr(f"arecord failed: {e}")
            return None
        except subprocess.TimeoutExpired:
            rospy.logwarn("Recording timeout")
            return None

    def transcribe_audio(self, audio_np):
        """使用Whisper将numpy数组转写为文本"""
        result = self.model.transcribe(audio_np, fp16=False, temperature=0.0, language="zh")
        return result['text'].strip()

    def parse_instruction(self, chinese_text):

        chinese_text = convert(chinese_text, 'zh-cn')
        # 按顺序连接词分割
        segments = re.split(r'[,，]?\s*然后\s*|[,，]?\s*接着\s*|[,，]?\s*最后\s*|[,，]', chinese_text)
        segments = [s.strip() for s in segments if s.strip()]

        action_groups = []
        stop_found = False

        for seg in segments:
            actions = self._parse_segment(seg)
            if actions:
                if 'stop' in actions:
                    stop_found = True
                    actions.remove('stop')
                if actions:
                    action_groups.append(actions)

        if not action_groups:
            return ""

        english_parts = []
        for group in action_groups:
            if len(group) == 1:
                part = group[0]
            else:
                part = " and ".join(group)
            english_parts.append(part)

        instruction = ", then ".join(english_parts)
        if stop_found:
            instruction += " and stop"
        
        return instruction

    def _parse_segment(self, seg):
        actions = []
        # 转向
        if re.search(r'左转|向左转', seg):
            actions.append("turn left")
        if re.search(r'右转|向右转', seg):
            actions.append("turn right")
        # 移动
        move_match = re.search(r'走到(.+)|去(.+)|穿过(.+)|通过(.+)', seg)
        if move_match:
            obj = move_match.group(1) or move_match.group(2) or move_match.group(3) or move_match.group(4)
            if obj:
                obj_en = self._translate_object(obj.strip())
                if re.search(r'穿过|通过', seg):
                    actions.append(f"go through {obj_en}")
                else:
                    actions.append(f"move forward to {obj_en}")
        else:
            obj = self._extract_object(seg)
            if obj:
                actions.append(f"forward to {obj}")
        # 停止
        if re.search(r'停下|停止', seg):
            actions.append("stop")
        return actions


    def _translate_object(self, obj_text):
        obj_text = obj_text.strip()
        if obj_text in self.object_map:
            return self.object_map[obj_text]
        return obj_text

    def _extract_object(self, text):
        for cn, en in self.object_map.items():
            if cn in text:
                return en
        return None

    def run(self):
        """主循环：等待回车，录音，转写，解析，发布"""
        while not rospy.is_shutdown():
            print("\nPress ENTER to start voice command (or 'q' to quit)...")
            while True:
                key = self.get_key()
                if key == '\r' or key == '\n':
                    break
                elif key == 'q':
                    rospy.loginfo("Exiting...")
                    return

            audio_np = self.record_audio(timeout=5, phrase_time_limit=5)
            if audio_np is None:
                continue

            try:
                chinese_text = self.transcribe_audio(audio_np)
                rospy.loginfo(f"Transcribed: {chinese_text}")

                if chinese_text:
                    english_instruction = self.parse_instruction(chinese_text)
                    rospy.loginfo(f"Parsed instruction: {english_instruction}")

                    if english_instruction:
                        self.pub.publish(english_instruction)
                        rospy.loginfo(f"Published navigation instruction: {english_instruction}")
                    else:
                        rospy.logwarn("Could not generate instruction, skipping.")
                else:
                    rospy.logwarn("Empty transcription, ignoring.")
            except Exception as e:
                rospy.logerr(f"Error: {e}")

if __name__ == '__main__':
    try:
        commander = VoiceCommander()
        commander.run()
    except rospy.ROSInterruptException:
        pass