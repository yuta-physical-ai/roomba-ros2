cmake_minimum_required(VERSION 3.8)
project(roomba_gazebo)

find_package(ament_cmake REQUIRED)

install(DIRECTORY urdf worlds launch config rviz
  DESTINATION share/${PROJECT_NAME})

install(PROGRAMS scripts/joint_state_throttle.py
  DESTINATION lib/${PROJECT_NAME})

ament_package()
