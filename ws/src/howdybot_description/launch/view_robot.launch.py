# Mecanum teleop demo: mock hardware + ros2_control + RViz.
# Adapted from ros2_control_demos example_2 (Apache-2.0, Stogl Robotics Consulting).
#
# Drive it with:
#   ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args \
#     -p stamped:=true -r cmd_vel:=/mecanum_drive_controller/reference

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = FindPackageShare("howdybot_description")
    gui = LaunchConfiguration("gui")
    use_mock_hardware = LaunchConfiguration("use_mock_hardware")

    robot_description = {
        "robot_description": ParameterValue(
            Command(
                [
                    "xacro ",
                    PathJoinSubstitution([pkg, "urdf", "howdybot.urdf.xacro"]),
                    " use_mock_hardware:=",
                    use_mock_hardware,
                ]
            ),
            value_type=str,
        )
    }
    controllers_file = PathJoinSubstitution([pkg, "config", "howdybot_controllers.yaml"])
    rviz_config = PathJoinSubstitution([pkg, "rviz", "howdybot.rviz"])

    # Publishes /robot_description (read by ros2_control_node on Jazzy) and the
    # wheel TFs from /joint_states.
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[robot_description],
    )

    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        output="both",
        parameters=[controllers_file],
        # The mecanum controller publishes odom->base_link on ~/tf_odometry, not /tf.
        remappings=[("/mecanum_drive_controller/tf_odometry", "/tf")],
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
    )

    mecanum_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["mecanum_drive_controller", "--controller-manager", "/controller_manager"],
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config],
        condition=IfCondition(gui),
    )

    # Start the drive controller only after joint states are flowing, and RViz
    # after that, so the model doesn't flash up with missing transforms.
    delay_mecanum_after_jsb = RegisterEventHandler(
        OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[mecanum_controller_spawner],
        )
    )
    delay_rviz_after_mecanum = RegisterEventHandler(
        OnProcessExit(target_action=mecanum_controller_spawner, on_exit=[rviz])
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("gui", default_value="true", description="Start RViz."),
            DeclareLaunchArgument(
                "use_mock_hardware",
                default_value="true",
                description="Use mock_components/GenericSystem instead of real drivers.",
            ),
            robot_state_publisher,
            control_node,
            joint_state_broadcaster_spawner,
            delay_mecanum_after_jsb,
            delay_rviz_after_mecanum,
        ]
    )
