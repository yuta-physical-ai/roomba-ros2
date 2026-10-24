from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    params = PathJoinSubstitution(
        [FindPackageShare('roomba_odometry'), 'config', 'wheel_odometry.yaml'])

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true',
                              description='true for Gazebo, false on the real robot'),

        Node(
            package='roomba_odometry',
            executable='wheel_odometry',
            output='screen',
            parameters=[params, {'use_sim_time': use_sim_time}],
        ),
    ])
