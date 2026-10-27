"""Start the cmd_vel relay.

teleop_twist_keyboard reads keys from its terminal, so run it separately:
  ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=cmd_vel_key
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    params = PathJoinSubstitution(
        [FindPackageShare('roomba_teleop'), 'config', 'cmd_vel_relay.yaml'])

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false',
                              description='true for Gazebo, false on the real robot'),

        Node(
            package='roomba_teleop',
            executable='cmd_vel_relay',
            output='screen',
            parameters=[params, {'use_sim_time': use_sim_time}],
        ),
    ])
