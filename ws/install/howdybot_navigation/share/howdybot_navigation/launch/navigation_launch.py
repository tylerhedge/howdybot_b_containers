import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    nav2_dir = get_package_share_directory('nav2_bringup')
    pkg_dir = get_package_share_directory('howdybot_navigation')

    use_sim_time = LaunchConfiguration('use_sim_time')
    map_yaml = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')
    rviz = LaunchConfiguration('rviz')

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='False'),
        DeclareLaunchArgument('map',
                              default_value=os.path.join(pkg_dir, 'maps', 'tb3_sandbox.yaml')),
        DeclareLaunchArgument('params_file',
                              default_value=os.path.join(pkg_dir, 'config', 'nav2_params.yaml')),
        DeclareLaunchArgument('rviz', default_value='True'),

        # Ground-truth localization: mock-hardware odometry is perfect, so map->odom is
        # fixed. The offset is where the robot starts on the map ((0,0) in tb3_sandbox is
        # inside the center pillar).
        Node(package='tf2_ros', executable='static_transform_publisher',
             arguments=['--x', '-2.0', '--y', '-0.5',
                        '--frame-id', 'map', '--child-frame-id', 'odom']),

        # Jazzy's bringup only starts map_server together with AMCL (use_localization),
        # so run it ourselves with its own lifecycle manager.
        Node(package='nav2_map_server', executable='map_server', name='map_server',
             output='screen',
             parameters=[{'yaml_filename': map_yaml, 'use_sim_time': use_sim_time}]),
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
             name='lifecycle_manager_map', output='screen',
             parameters=[{'autostart': True, 'node_names': ['map_server'],
                          'use_sim_time': use_sim_time}]),

        # Planner, controller, BT navigator, smoother, behaviors, etc.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(nav2_dir, 'launch', 'navigation_launch.py')),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'params_file': params_file,
            }.items(),
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(nav2_dir, 'launch', 'rviz_launch.py')),
            condition=IfCondition(rviz),
        ),
    ])
