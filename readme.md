#本工程基于uninavid的实机复现，使用ubuntu 22.04+ros1
#搭建了一个通用的端到端视觉语言导航系统，只需在云端更换模型即可实现部署。


#在这里非常感谢UniNavid团队的精彩工作，详细可以去他们的仓库查看。https://pku-epic.github.io/Uni-NaVid/
#其中的语音识别使用到了大佬LJ-Hao jiahaoli的开源工程，详细请看。https://github.com/LJ-Hao/Deploy-Whisper-on-NVIDIA-Jetson-Orin-for-Real-time-Speech-to-Text.git

#I would like to take this opportunity to thank the UniNavid team for their excellent work; further details can be found on their repository.

#The speech recognition in this project utilises the open-source project by LJ-Hao jiahaoli; please see here for further details.

#src只放着client端的代码，使用fastapi的远程通讯，连接云服务器

#action_mapper将模型返回的4个动作指令转换为速度指令

#gif_recorder制作第一人称视角的实机导航gif

#teleop是方便键鼠遥控底盘

#voice收集语音信息，使用模型转换为中文，然后使用匹配进行英文指令的转换

#The src file contains only client-side code, implementing FastAPI remote communication, converting motion commands into speed commands, and demonstrating the in-game navigation effects created using GIFs.

#.gif文件为3条实机第一视角demo。
#The GIF consists of three first-person gameplay demos

#以下是所有工程文件的的相关说明

#catkin_ws
相关pkg存放在src目录下，使用catkin build进行编译

其中涉及英特尔相机的pkg如下
ddynamic_reconfigure
librealsnese
realsense-ros

涉及松灵底盘的pkg如下
tracer_ros
ugv_sdk

uninavid的相关pkg
uninavid_tel

特别注意，由于英特尔相机的opencv4存在路径问题，不要在相机终端使用source devel/setup.bash，由于没有相关文件下进行源操作，所以会出现有些pkg无法运行
其他节点则需要在当前终端source devel/setup.bash

#相关指令
松灵底盘
cd catkin_ws在终端使用source devel/setup.bash查看can设备是否连接在小电脑上；
使用roslaunch tracer_bringup tracer_robot_base.launch开启底盘节点
如果存在启动失败，则重新插拔can设备
还是失败则设置sudo ip link set can0 up type can bitrate 500000
然后使用candump can0查看是否有通讯信息

英特尔相机
直接在终端使用roslaunch realsense2_camera rs_camera.launch开启相机节点

uninavid
cd catkin_ws在终端使用source devel/setup.bash，接着运行uninavid_client.py和action_mapper.py；
最后使用其他终端发布导航指令话题


#欢迎与我讨论。




