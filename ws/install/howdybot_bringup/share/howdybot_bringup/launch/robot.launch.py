"""Entry point the robot container runs on boot.
Add sensor drivers, Nav2, person detection, audio, etc. here as they're built."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    foxglove = LaunchConfiguration("foxglove")

    return LaunchDescription([
        DeclareLaunchArgument(
            "foxglove", default_value="true",
            description="Start foxglove_bridge on port 8765 for remote viewing",
        ),
        Node(
            package="howdybot_bringup",
            executable="howdy_heartbeat",
            output="screen",
        ),
        Node(
            package="foxglove_bridge",
            executable="foxglove_bridge",
            parameters=[{"port": 8765}],
            condition=IfCondition(foxglove),
            output="screen",
        ),
    ])
