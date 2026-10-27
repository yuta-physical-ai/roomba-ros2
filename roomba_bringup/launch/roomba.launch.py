import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    default_config = os.path.join(
        get_package_share_directory('roomba_bringup'), 'config', 'roomba.yaml')

    config = LaunchConfiguration('config')
    odom_source = LaunchConfiguration('odom_source')
    foxglove = LaunchConfiguration('foxglove')

    # odom_source:=user hands /odom and odom->base_footprint to roomba_odometry;
    # the driver's own estimate moves to /create/odom for comparison.
    user_odom = PythonExpression(["'", odom_source, "' == 'user'"])
    driver_publish_tf = ParameterValue(
        PythonExpression(["'", odom_source, "' != 'user'"]), value_type=bool)
    driver_odom_topic = PythonExpression(
        ["'/create/odom' if ", user_odom, " else '/odom'"])

    return LaunchDescription([
        DeclareLaunchArgument('config', default_value=default_config,
                              description='create_driver parameter file'),
        DeclareLaunchArgument('odom_source', default_value='driver',
                              choices=['driver', 'user'],
                              description='Who publishes /odom and odom->base_footprint: '
                                          'create_driver, or your own node'),
        DeclareLaunchArgument('foxglove', default_value='true',
                              description='Start foxglove_bridge (ws://<host>:8765)'),

        Node(
            package='create_driver',
            executable='create_driver',
            name='create_driver',
            output='screen',
            parameters=[config, {'publish_tf': driver_publish_tf}],
            remappings=[('odom', driver_odom_topic)],
        ),

        Node(
            package='foxglove_bridge',
            executable='foxglove_bridge',
            output='screen',
            parameters=[{'port': 8765}],
            condition=IfCondition(foxglove),
        ),
    ])
