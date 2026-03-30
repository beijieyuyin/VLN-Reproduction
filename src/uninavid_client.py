#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import rospy
from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge, CvBridgeError
import time
import requests
import json
import base64
from std_msgs.msg import String, Bool

class NavigationAgent:
    def __init__(self):
        rospy.init_node('uninavid_client', anonymous=True)
        self.bridge = CvBridge()
        
        # 订阅相机话题，只保存最新一帧图像
        self.image_sub = rospy.Subscriber('/camera/color/image_raw', Image, self.image_callback)
        self.latest_image = None          # 存储最新一帧图像
        
        self.instruction = None
        # 服务器地址（根据实际情况修改）
        self.server_url = "https://uu724042-b565-a503a25e.bjb1.seetacloud.com:8443/generate"
        
        # 状态标志
        self.waiting_for_response = False           # 是否正在等待服务器响应
        self.waiting_for_action_completion = False  # 是否正在等待动作执行完成
        self.executing_actions = False # 
        self.reset_history = False
        
        self.actions = []
        self.action_index = 0
        self.need_new_image=False # 是否动作直行完可以拍摄下一张图片
        
        # 时间测量
        self.request_sent_time = None                # 发送请求的时刻
        self.cycle_time_pub = rospy.Publisher('/cycle_time', String, queue_size=1)  # 可选，发布周期时间
        
        # 发布动作序列
        self.action_sequence_pub = rospy.Publisher('/action_sequence', String, queue_size=1)
        # 订阅动作完成信号
        self.action_completed_sub = rospy.Subscriber('/action_completed', Bool, self.action_completed_callback)
        #发布gif信息
        self.image_action_pub = rospy.Publisher('/image_action', String, queue_size=10)
        rospy.loginfo("NavigationAgent initialized")

    def image_callback(self, msg):
        """只保存最新一帧图像，不触发请求"""
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            self.latest_image = cv_image  # 覆盖为最新帧
        except CvBridgeError as e:
            rospy.logerr("CvBridge Error: %s", str(e))
        except Exception as e:
            rospy.logerr("Image callback error: %s", str(e))
            
        # 如果已有指令和最新图像，且不在等待响应或执行动作，则立即发送请求
        if self.need_new_image and self.instruction is not None and self.latest_image is not None:
            self.send_request(self.latest_image)
            self.need_new_image = False#该标志在动作完成回调中重置，确保每次动作完成后才允许下一张图片触发请求

    def send_request(self, image):
        """发送单张图像到服务器进行推理"""
        self.waiting_for_response = True
        self.request_sent_time = time.time()  # 记录发送时刻
        
        # 将图像编码为 base64
        _, buffer = cv2.imencode('.jpg', image)
        image_b64 = base64.b64encode(buffer).decode('utf-8')
        
        payload = {
            "instruction": self.instruction,
            "image": image_b64,   # 发送单张图片
            "reset": self.reset_history
        }
        self.reset_history=False
        try:
            response = requests.post(self.server_url, json=payload, timeout=10)  # 超时10秒
            if response.status_code == 200:
                result = response.json()
                self.actions = result.get("response", {}).get("actions", [])
                rospy.loginfo("Received actions: %s", str(self.actions))
                
                if self.actions:
                    action_str = json.dumps(self.actions)
                    self.action_sequence_pub.publish(action_str)
                    rospy.loginfo("Published action sequence: %s", action_str)
                    #打包上传图片和返回动作至gif节点
                    msg_data = {
                        'image': image_b64,
                        'actions': self.actions
                    }
                    self.image_action_pub.publish(json.dumps(msg_data))
                    self.waiting_for_action_completion = True
                    self.executing_actions = True
                else:
                    rospy.logwarn("Empty actions received, resetting state")
                    self.reset_state()
            else:
                rospy.logerr("Server error %d: %s", response.status_code, response.text)
                self.reset_state()
        except Exception as e:
            rospy.logerr("Request failed: %s", str(e))
            self.reset_state()
        finally:
            self.waiting_for_response = False

    def reset_state(self):
        """重置状态（不清空最新图像）"""
        self.actions = []
        self.action_index = 0
        self.waiting_for_action_completion = False
        self.executing_actions = False
        # 注意：不重置 latest_image，以便后续继续使用

    def action_completed_callback(self, msg):
        """动作执行完成时触发：计算周期时间，并发送下一轮请求"""
        if msg.data:
            rospy.loginfo("Action sequence completed!")
            # 计算从发送请求到完成的时间
            if self.request_sent_time is not None:
                elapsed = time.time() - self.request_sent_time
                rospy.loginfo("Cycle time (image capture to actions done): %.2f seconds", elapsed)
                # 可发布到话题供记录
                self.cycle_time_pub.publish(json.dumps({"cycle_time": elapsed}))
            
            # 重置状态（但保留 latest_image）
            self.reset_state()
            self.need_new_image = True   # 标记需要新图像


    def set_instruction(self, msg):
        """设置新指令，并立即触发第一轮推理（如果有图像）"""
        rospy.loginfo("New instruction: %s", msg.data)
        self.instruction = msg.data
        # 重置所有状态，准备开始新任务
        self.reset_history = True
        self.reset_state()
        self.waiting_for_response = False
        # 如果已有图像，立即发送请求
        if self.latest_image is not None:
            self.send_request(self.latest_image)

def main():
    agent = NavigationAgent()
    rospy.Subscriber('/navigation_instruction', String, agent.set_instruction)
    
    rate = rospy.Rate(10)  # 10Hz循环，保持节点存活
    while not rospy.is_shutdown():
        rate.sleep()

if __name__ == '__main__':
    main()