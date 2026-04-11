## 工程简介

本工程基于UniNavid的实机复现。

工程搭建了一个通用的端到端视觉语言导航实机框架，只需在云端更换模型即可实现部署。

本工程使用松灵底盘，英特尔深度相机，jetson。

## 框架简介

环境：ubuntu 20.04+ros1 

ros的安装推荐鱼香ros一键安装。

该框架部署在jetson，UniNavid模型部署在云服务器(比如autodl)，使用fatapi搭建client端和server端的通讯，注意uninavid_client.py需要填入url。就以autodl来说，需要填入对应服务器端口的映射公网地址+/health。其中/health为检测端点。

src只放着client端的代码，这些代码请在ros中创建新的pkg，进行存放。例如uninavid_tel。

**注意：该框架为串行控制即每次执行完4个动作后，才再次采集图片请求服务器推理获取动作。所以存在明显延迟，并且action_mapper.py中动作的速度较慢，需要根据实际情况进行调整。在action_mapper.py中首次获取到stop后动作，则会退出，agent不再运动**

如果要实现高频控制，可以使用**局域网**搭建本地服务器与jetson的通讯，并且使用**并行推理控制**。简单举个例子，例如在每次第二个动作执行完成后，再次采集图片请求获取动作，第三个动作同步执行，当第三个动作执行完后，舍弃原本第四个动作，使用新的动作序列，循环往复。请根据传输延迟实际考虑。

### 代码作用

uninavid_client.py负责fastapi通讯，打包信息，获取动作。

action_mapper.py将模型返回的4个动作指令转换为速度指令。

gif_recorder.py制作第一人称视角的实机导航gif。

teleop.py是方便键鼠遥控底盘。

voice_commander.py收集语音信息，发布导航指令(使用模型转换为中文，然后使用匹配进行英文指令的转换)。

## 感谢

在这里非常感谢UniNavid团队的精彩工作，详细可以去他们的仓库查看。https://pku-epic.github.io/Uni-NaVid/ 

其中的语音识别使用到了大佬LJ-Hao jiahaoli的开源工程，详细请看。https://github.com/LJ-Hao/Deploy-Whisper-on-NVIDIA-Jetson-Orin-for-Real-time-Speech-to-Text.git

I would like to take this opportunity to thank the UniNavid team for their excellent work; further details can be found on their repository.

The speech recognition in this project utilises the open-source project by LJ-Hao jiahaoli; please see here for further details.

## 其他

.gif文件为3条实机第一视角demo。 #The GIF consists of three first-person gameplay demos

以下是所有工程文件的的相关说明，

catkin_ws 相关pkg存放在src目录下，使用catkin build进行编译

其中涉及英特尔相机的pkg如下 

ddynamic_reconfigure 

librealsnese 

realsense-ros

涉及松灵底盘的pkg如下 

tracer_ros ugv_sdk

uninavid的相关pkg 

uninavid_tel

特别注意，**在jetson中英特尔相机的opencv4存在路径问题**，不容易修复，该工程的解决办法为：**不要在相机发布节点的终端使用source devel/setup.bash(x86平台，例如虚拟机则不会出现这个情况)**，由于没有相关文件下进行源操作，所以会出现有些pkg无法运行，**其他节点则需要在当前终端source devel/setup.bash**

## 相关指令 

### 松灵底盘

cd catkin_ws进入工作空间

在终端使用source devel/setup.bash查看can设备是否连接在小电脑上； 

使用roslaunch tracer_bringup tracer_robot_base.launch开启底盘节点；

如果存在启动失败，则重新插拔can设备

还是失败则设置sudo ip link set can0 up type can bitrate 500000 然后使用candump can0查看是否有通讯信息

### 英特尔相机 

直接在终端使用roslaunch realsense2_camera rs_camera.launch开启相机节点

### uninavid_tel

cd catkin_ws

在终端使用source devel/setup.bash，接着运行uninavid_client.py和action_mapper.py以及gif_recorder.py。如果要使用语言下达指令请运行voice_commander.py；若只是文本指令，在其他终端运行例如rostopic pub /navigation_instruction std_msgs/String "data: 'forward to the cardboard box, then turn left and move forward to the water dispenser and stop.'" --once



欢迎与我讨论。




