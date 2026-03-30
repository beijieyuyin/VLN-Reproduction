#!/usr/bin/env python
# coding=utf-8
import rospy
from geometry_msgs.msg import Twist
import time
import sys
import select
import termios
import tty

def getKey():
    """Reading a single key press from the terminal"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def send_velocity(pub, linear, angular, duration):
    """Issue the speed command and wait for the specified duration."""
    twist = Twist()
    twist.linear.x = linear
    twist.angular.z = angular
    
    start_time = rospy.Time.now()
    end_time = start_time + rospy.Duration(duration)
    
    # Maintain speed until the specified time
    while rospy.Time.now() < end_time and not rospy.is_shutdown():
        pub.publish(twist)
        rospy.sleep(0.01)
    
    # Stop the robot
    pub.publish(Twist())

def main():
    rospy.init_node('key_control', anonymous=True)
    pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
    
    # Robot parameters (adjust according to actual circumstances)
    LINEAR_SPEED = 0.1  # m/s (10 cm/s)
    ANGULAR_SPEED = 0.5  # rad/s (28.6 deg/s)
    
    print("Control robot:")
    print("w: Move forward 15cm")
    print("a: Turn left 15 degrees")
    print("d: Turn right 15 degrees")
    print("s: Stop")
    print("q: Quit")
    
    while not rospy.is_shutdown():
        # 等待按键输入
        key = getKey()
        
        if key == 'w':
            print("前进15cm")
            # 前进15cm (0.15m) @ 0.1m/s = 1.5秒
            send_velocity(pub, LINEAR_SPEED, 0, 1.5)
            
        elif key == 'a':
            print("左转15度")
            # 左转15度 (0.2618 rad) @ 0.5 rad/s = 0.5236秒
            send_velocity(pub, 0, ANGULAR_SPEED, 0.5)
            
        elif key == 'd':
            print("右转15度")
            send_velocity(pub, 0, -ANGULAR_SPEED, 0.5)
            
        elif key == 's':
            print("停止")
            send_velocity(pub, 0, 0, 0.1)
            
        elif key == 'q':
            print("退出")
            break
            
        else:
            print("无效按键，请按 f/l/r/s/q")

if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        pass
