#!/usr/bin/env python3
"""Encoder-based wheel odometry for a differential-drive robot.

Subscribes to /joint_states (cumulative wheel angles [rad]) and publishes
/odom plus the TF odom -> base_footprint.
"""
import math

import rclpy
from geometry_msgs.msg import Quaternion, TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from rclpy.time import Time
from sensor_msgs.msg import JointState
from tf2_ros import TransformBroadcaster


def yaw_to_quaternion(yaw):
    """Rotation of `yaw` [rad] about the z axis as a Quaternion."""
    q = Quaternion()
    q.z = math.sin(yaw * 0.5)
    q.w = math.cos(yaw * 0.5)
    return q


class WheelOdometry(Node):

    def __init__(self):
        super().__init__('wheel_odometry')
        self._wheel_radius = self.declare_parameter('wheel_radius', 0.036).value
        self._wheel_separation = self.declare_parameter('wheel_separation', 0.235).value
        self._left_joint = self.declare_parameter('left_wheel_joint', 'left_wheel_joint').value
        self._right_joint = self.declare_parameter('right_wheel_joint', 'right_wheel_joint').value
        self._odom_frame = self.declare_parameter('odom_frame', 'odom').value
        self._base_frame = self.declare_parameter('base_frame', 'base_footprint').value
        self._publish_tf = self.declare_parameter('publish_tf', True).value

        # Pose in the odom frame
        self._x = 0.0
        self._y = 0.0
        self._theta = 0.0

        # Previous wheel angles [rad] and stamp; None until the first message
        self._prev_left = None
        self._prev_right = None
        self._prev_stamp = None

        self._odom_pub = self.create_publisher(Odometry, 'odom', 10)
        self._tf_broadcaster = TransformBroadcaster(self)
        self.create_subscription(JointState, 'joint_states', self._on_joint_states, 10)

    def _on_joint_states(self, msg):
        try:
            left = msg.position[msg.name.index(self._left_joint)]
            right = msg.position[msg.name.index(self._right_joint)]
        except (ValueError, IndexError):
            self.get_logger().warn(
                f'{self._left_joint}/{self._right_joint} not in /joint_states',
                throttle_duration_sec=5.0)
            return
        stamp = Time.from_msg(msg.header.stamp)

        if self._prev_stamp is None:
            # Start from wherever the wheels are now
            self._prev_left, self._prev_right, self._prev_stamp = left, right, stamp
            return

        dt = (stamp - self._prev_stamp).nanoseconds * 1e-9
        if dt <= 0.0:
            return

        # Distance each wheel travelled since the last message [m]
        d_left = self._wheel_radius * (left - self._prev_left)
        d_right = self._wheel_radius * (right - self._prev_right)

        # Forward distance of base_footprint [m] and heading change [rad, CCW positive]
        d_center = (d_left + d_right) * 0.5
        d_theta = (d_right - d_left) / self._wheel_separation

        # Integrate using the heading at the middle of the step
        self._x += d_center * math.cos(self._theta + d_theta * 0.5)
        self._y += d_center * math.sin(self._theta + d_theta * 0.5)
        self._theta += d_theta

        # Twist is expressed in base_footprint
        v = d_center / dt
        w = d_theta / dt

        self._prev_left, self._prev_right, self._prev_stamp = left, right, stamp
        self._publish(msg.header.stamp, v, w)

    def _publish(self, stamp, v, w):
        msg = Odometry()
        msg.header.stamp = stamp
        msg.header.frame_id = self._odom_frame
        msg.child_frame_id = self._base_frame
        msg.pose.pose.position.x = self._x
        msg.pose.pose.position.y = self._y
        msg.pose.pose.orientation = yaw_to_quaternion(self._theta)
        msg.twist.twist.linear.x = v
        msg.twist.twist.angular.z = w
        self._odom_pub.publish(msg)

        if self._publish_tf:
            t = TransformStamped()
            t.header = msg.header
            t.child_frame_id = self._base_frame
            t.transform.translation.x = self._x
            t.transform.translation.y = self._y
            t.transform.rotation = msg.pose.pose.orientation
            self._tf_broadcaster.sendTransform(t)


def main():
    # Let SIGINT surface as KeyboardInterrupt instead of rclpy shutting the context
    # down under a running spin(), which raises RCLError on launch shutdown.
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = WheelOdometry()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
