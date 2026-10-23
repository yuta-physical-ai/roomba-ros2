#!/usr/bin/env python3
"""Republish Gazebo's joint states at a fixed rate.

Fortress' JointStatePublisher emits on every physics step (~1 kHz), which no real
driver does; create_driver publishes /joint_states at loop_hz. This forwards the
latest message from `input` to `output` at `rate` Hz of sim time.
"""
import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import JointState


class JointStateThrottle(Node):

    def __init__(self):
        super().__init__('joint_state_throttle')
        rate = self.declare_parameter('rate', 50.0).value
        self._latest = None
        self._pub = self.create_publisher(JointState, 'output', 10)
        self.create_subscription(JointState, 'input', self._on_msg, 10)
        self.create_timer(1.0 / rate, self._on_timer)

    def _on_msg(self, msg):
        self._latest = msg

    def _on_timer(self):
        if self._latest is not None:
            self._pub.publish(self._latest)
            self._latest = None


def main():
    # Let SIGINT surface as KeyboardInterrupt instead of rclpy shutting the context
    # down under a running spin(), which raises RCLError on launch shutdown.
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = JointStateThrottle()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
