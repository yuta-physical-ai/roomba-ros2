#!/usr/bin/env python3
"""Keep-alive relay between teleop_twist_keyboard and the robot.

teleop_twist_keyboard publishes /cmd_vel_key only when a key arrives, but
create_driver stops the wheels when /cmd_vel is older than 0.2 s. This node
republishes the last key command on /cmd_vel at a fixed rate, and stops the
robot once no key has arrived for `timeout` seconds.
"""
import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions


class CmdVelRelay(Node):

    def __init__(self):
        super().__init__('cmd_vel_relay')
        rate = self.declare_parameter('rate', 20.0).value
        self._timeout = self.declare_parameter('timeout', 0.6).value

        # Last command from the keyboard and when it arrived; None until the first key
        self._last_cmd = None
        self._last_stamp = None

        self._cmd_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.create_subscription(Twist, 'cmd_vel_key', self._on_cmd_vel_key, 10)
        self.create_timer(1.0 / rate, self._on_timer)

    def _on_cmd_vel_key(self, msg):
        self._last_stamp = self.get_clock().now()
        self._last_cmd = msg

    def _on_timer(self):
        if self._last_cmd is None:
            return
        
        stamp = self.get_clock().now()
        
        if (stamp - self._last_stamp).nanoseconds * 1e-9 <= self._timeout:
            self._cmd_pub.publish(self._last_cmd)
        
        else:
            self._cmd_pub.publish(Twist())
            self._last_cmd = None

def main():
    # Keep the context alive on Ctrl+C so a final stop can still be published
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = CmdVelRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node._cmd_pub.publish(Twist())
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
