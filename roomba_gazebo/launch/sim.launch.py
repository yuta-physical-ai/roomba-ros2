import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (AppendEnvironmentVariable, DeclareLaunchArgument,
                            IncludeLaunchDescription, SetEnvironmentVariable)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (Command, LaunchConfiguration, PathJoinSubstitution,
                                  PythonExpression)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def x_display_env():
    """The LiDAR is rendered with OGRE/GLX, which needs an X display even when the
    server runs headless. Over SSH, fall back to the Jetson's GNOME desktop."""
    if os.environ.get('DISPLAY'):
        return []
    actions = [SetEnvironmentVariable('DISPLAY', ':0')]
    gdm_xauth = f'/run/user/{os.getuid()}/gdm/Xauthority'
    if not os.environ.get('XAUTHORITY') and os.path.exists(gdm_xauth):
        actions.append(SetEnvironmentVariable('XAUTHORITY', gdm_xauth))
    return actions


def generate_launch_description():
    pkg_share = get_package_share_directory('roomba_gazebo')
    xacro_file = os.path.join(pkg_share, 'urdf', 'roomba.urdf.xacro')
    bridge_config = os.path.join(pkg_share, 'config', 'bridge.yaml')
    default_world = os.path.join(pkg_share, 'worlds', 'room.sdf')
    rviz_config = os.path.join(pkg_share, 'rviz', 'sim.rviz')

    # Lets Gazebo resolve package://create_description/... mesh URIs
    description_share_parent = os.path.dirname(
        get_package_share_directory('create_description'))

    world = LaunchConfiguration('world')
    gui = LaunchConfiguration('gui')
    render_engine = LaunchConfiguration('render_engine')
    odom_source = LaunchConfiguration('odom_source')
    rviz = LaunchConfiguration('rviz')
    joint_state_rate = LaunchConfiguration('joint_state_rate')

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
        DeclareLaunchArgument('odom_source', default_value='gazebo',
                              choices=['gazebo', 'user'],
                              description='Who publishes /odom and odom->base_footprint: '
                                          'the DiffDrive plugin, or your own node'),
        DeclareLaunchArgument('rviz', default_value='false',
                              description='Start RViz'),
        DeclareLaunchArgument('joint_state_rate', default_value='50.0',
                              description='/joint_states rate in Hz (the real create_driver '
                                          'publishes at its loop_hz)'),

        AppendEnvironmentVariable('IGN_GAZEBO_RESOURCE_PATH', description_share_parent),
        *x_display_env(),

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

        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='odom_bridge',
            output='screen',
            parameters=[{'config_file': PathJoinSubstitution(
                [pkg_share, 'config', ['bridge_odom_', odom_source, '.yaml']])}],
        ),

        Node(
            package='roomba_gazebo',
            executable='joint_state_throttle.py',
            output='screen',
            parameters=[{'rate': ParameterValue(joint_state_rate, value_type=float),
                         'use_sim_time': True}],
            remappings=[('input', '/gz/joint_states'), ('output', '/joint_states')],
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            output='screen',
            arguments=['-d', rviz_config],
            parameters=[{'use_sim_time': True}],
            condition=IfCondition(rviz),
        ),
    ])
