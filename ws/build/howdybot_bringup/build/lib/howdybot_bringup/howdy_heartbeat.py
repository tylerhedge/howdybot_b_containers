"""Placeholder node: publishes a heartbeat so you can confirm the container,
ROS networking and the launch file all work before real nodes exist."""

import platform

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class HowdyHeartbeat(Node):
    def __init__(self) -> None:
        super().__init__("howdy_heartbeat")
        self.pub = self.create_publisher(String, "howdy/heartbeat", 10)
        self.count = 0
        self.create_timer(1.0, self.tick)
        self.get_logger().info(f"Howdy! Running on {platform.machine()}")

    def tick(self) -> None:
        self.count += 1
        self.pub.publish(String(data=f"howdy #{self.count} from {platform.machine()}"))


def main() -> None:
    rclpy.init()
    node = HowdyHeartbeat()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
