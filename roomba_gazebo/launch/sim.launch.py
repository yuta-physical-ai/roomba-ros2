import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (AppendEnvironmentVariable, DeclareLaunchArgument,
                            IncludeLaunchDescription)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = get_package_share_directory('roomba_gazebo')
    xacro_file = os.path.join(pkg_share, 'urdf', 'roomba.urdf.xacro')
    bridge_config = os.path.join(pkg_share, 'config', 'bridge.yaml')
    default_world = os.path.join(pkg_share, 'worlds', 'empty.sdf')

    # Lets Gazebo resolve package://create_description/... mesh URIs
    description_share_parent = os.path.dirname(
        get_package_share_directory('create_description'))

    world = LaunchConfiguration('world')
    gui = LaunchConfiguration('gui')
    render_engine = LaunchConfiguration('render_engine')

    robot_description = ParameterValue(Command(['xacro ', xacro_file]), value_type=str)

    # -s runs the server only (no GUI); -r starts the simulation unpaused
    gz_args = PythonExpression([
        "'-r ' + ('' if '", gui, "' == 'true' else '-s ') + "
        "'--render-engine ", render_engine, " ' + '", world, "'"])

    return LaunchDescription([
        DeclareLaunchArgument('world', default_value=default_world,
                              description='SDF world file'),
        DeclareLaunchArgument('gui', default_value='false',
                              description='Start the Gazebo GUI alongside the server'),
        # ogre2 segfaults on Jetson Orin Nano (NvMap allocation fails in the compositor)
        DeclareLaunchArgument('render_engine', default_value='ogre',
                              description='Gazebo render engine (ogre or ogre2)'),

        AppendEnvironmentVariable('IGN_GAZEBO_RESOURCE_PATH', description_share_parent),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(
                get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')),
            launch_arguments={'gz_args': gz_args}.items(),
        ),

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': robot_description, 'use_sim_time': True}],
        ),

        Node(
            package='ros_gz_sim',
            executable='create',
            output='screen',
            arguments=['-topic', 'robot_description', '-name', 'roomba'],
        ),

        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            output='screen',
            parameters=[{'config_file': bridge_config}],
        ),
    ])
