#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import rospy
import cv2
import numpy as np
import json
import base64
import imageio
import os  # 新增导入
from std_msgs.msg import String

class GIFRecorder:
    def __init__(self):
        rospy.init_node('gif_recorder', anonymous=True)
        
        # 创建结果保存目录
        self.result_dir = "/home/uninavid/results"
        if not os.path.exists(self.result_dir):
            os.makedirs(self.result_dir)
            rospy.loginfo(f"Created result directory: {self.result_dir}")
        
        # 订阅话题
        self.image_action_sub = rospy.Subscriber('/image_action', String, self.image_action_callback)
        self.instruction_sub = rospy.Subscriber('/navigation_instruction', String, self.instruction_callback)
        
        # 存储当前任务的图片和动作
        self.images = []          # 存放 OpenCV 图像 (BGR)
        self.actions_list = []    # 存放对应的动作列表
        
        # 注册关闭时的回调
        rospy.on_shutdown(self.shutdown_callback)
        
        rospy.loginfo("GIFRecorder initialized. Will generate GIF on shutdown.")

    def image_action_callback(self, msg):
        """接收图片和动作，解码并保存"""
        try:
            data = json.loads(msg.data)
            img_b64 = data['image']
            actions = data['actions']
            
            # 解码 base64 为图像
            img_bytes = base64.b64decode(img_b64)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                rospy.logerr("Failed to decode image in GIFRecorder")
                return
            
            self.images.append(img)
            self.actions_list.append(actions)
            rospy.loginfo(f"Recorded image {len(self.images)} with actions {actions}")
        except Exception as e:
            rospy.logerr(f"Error in image_action_callback: {e}")

    def instruction_callback(self, msg):
        """收到新指令时清空记录，开始新任务"""
        rospy.loginfo("New instruction received, clearing previous recording.")
        self.images.clear()
        self.actions_list.clear()

    def draw_actions_on_image(self, img, actions):
        """
        在图片底部绘制动作箭头（复制自 server.py 的 draw_traj_arrows_fpv）
        """
        out = img.copy()
        h, w = out.shape[:2]
        base_x, base_y = w // 2, int(h * 0.95)
        arrow_len = 20
        arrow_gap = 2
        arrow_color = (0, 255, 0)
        arrow_thickness = 2
        tipLength = 0.35
        stop_color = (0, 0, 255)
        stop_radius = 5

        for i, action in enumerate(actions):
            if action == "stop":
                waypoint = [0.0, 0.0, 0.0]
            elif action == "forward":
                waypoint = [0.5, 0.0, 0.0]
            elif action == "left":
                waypoint = [0.0, 0.0, -np.deg2rad(30)]
            elif action == "right":
                waypoint = [0.0, 0.0, np.deg2rad(30)]
            else:
                continue

            x, y, yaw = waypoint
            start = (int(base_x), int(base_y - i * (arrow_len + arrow_gap)))

            if action == "stop":
                cv2.circle(out, start, stop_radius, stop_color, 2)
            else:
                end = (int(start[0] + arrow_len * np.sin(yaw)),
                       int(start[1] - arrow_len * np.cos(yaw)))
                cv2.arrowedLine(out, start, end, arrow_color, arrow_thickness, tipLength=tipLength)

        # 转换为 RGB（imageio 需要 RGB）
        return cv2.cvtColor(out, cv2.COLOR_BGR2RGB)

    def generate_gif(self, filename=None):
        """将记录的图片绘制动作后合成 GIF"""
        if not self.images:
            rospy.logwarn("No images recorded, skipping GIF generation.")
            return

        if filename is None:
            filename = os.path.join(self.result_dir, "navigation_result.gif")

        frames = []
        for img, actions in zip(self.images, self.actions_list):
            frame = self.draw_actions_on_image(img, actions)
            frames.append(frame)

        # 保存 GIF
        imageio.mimsave(filename, frames, duration=1)  # 每帧显示 1 秒
        rospy.loginfo(f"GIF saved to {filename}")

    def shutdown_callback(self):
        """节点关闭时生成 GIF"""
        rospy.loginfo("Shutting down, generating GIF...")
        self.generate_gif()

if __name__ == '__main__':
    try:
        recorder = GIFRecorder()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass