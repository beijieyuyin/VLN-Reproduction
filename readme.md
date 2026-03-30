#本工程用于uninavid的实机演示


#在这里非常感谢UniNavid团队的精彩工作，详细可以去他们的仓库查看。https://pku-epic.github.io/Uni-NaVid/

#I would like to take this opportunity to thank the UniNavid team for their excellent work; further details can be found on their repository.


#src只放着client端的代码，实现了fastapi的远程通讯，动作指令转换为速度指令，gif制作的实机导航效果，src存放client端代码，server.py用于云端推理，client是在jetson实现复现，下方是一些踩坑，也一起放进来了。

#The src file contains only client-side code, implementing FastAPI remote communication, converting motion commands into speed commands, and demonstrating the in-game navigation effects created using GIFs.

#gif为3条实机第一视角demo。
#The GIF consists of three first-person gameplay demos


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







