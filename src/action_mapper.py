#!/usr/bin/env python3
import rospy
import json
from std_msgs.msg import String, Bool
from geometry_msgs.msg import Twist
import time

class ActionMapper:
    def __init__(self):
        rospy.init_node('uninavid_action_mapper', anonymous=True)
        self.action_sub = rospy.Subscriber('/action_sequence', String, self.action_callback)
        self.completed_pub = rospy.Publisher('/action_completed', Bool, queue_size=1)
        self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        
        # 机器人参数
        self.LINEAR_SPEED = 0.15  # m/s
        self.ANGULAR_SPEED = 0.6  # rad/s

    def action_callback(self, msg):
        actions = json.loads(msg.data)
        rospy.loginfo("Executing actions: %s", actions)
        
        for action in actions:
            if action == "forward":
                self.move_forward(0.15)  # 15cm
            elif action == "left":
                self.turn_left(15)  # 15度
            elif action == "right":
                self.turn_right(15)  # 15度
            elif action == "stop":
                self.stop()
                self.completed_pub.publish(True)
                rospy.loginfo("Stop action encountered, shutting down node.")
                rospy.signal_shutdown("Stop action received")  # 退出节点
                return  # 确保回调退出
        
        # 发布完成信号
        self.completed_pub.publish(True)

    def move_forward(self, distance):
        duration = distance / self.LINEAR_SPEED
        self.publish_velocity(self.LINEAR_SPEED, 0, duration)
    
    def turn_left(self, degrees):
        radians = degrees * (3.14159 / 180)
        duration = radians / self.ANGULAR_SPEED
        self.publish_velocity(0, self.ANGULAR_SPEED, duration)
    
    def turn_right(self, degrees):
        radians = degrees * (3.14159 / 180)
        duration = radians / self.ANGULAR_SPEED
        self.publish_velocity(0, -self.ANGULAR_SPEED, duration)
    
    def stop(self):
        self.publish_velocity(0, 0, 0.1)
    
    def publish_velocity(self, linear, angular, duration):
        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        
        start_time = rospy.Time.now()
        end_time = start_time + rospy.Duration(duration)
        
        while rospy.Time.now() < end_time and not rospy.is_shutdown():
            self.cmd_vel_pub.publish(twist)
            rospy.sleep(0.01)
        
        # 确保停止
        self.cmd_vel_pub.publish(Twist())

if __name__ == '__main__':
    try:
        mapper = ActionMapper()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass