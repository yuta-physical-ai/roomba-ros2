from glob import glob

from setuptools import setup

package_name = 'roomba_odometry'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='yuta-physical-ai',
    maintainer_email='242810455+yuta-physical-ai@users.noreply.github.com',
    description='Encoder-based wheel odometry for the Roomba 600 series',
    license='MIT',
    entry_points={
        'console_scripts': [
            'wheel_odometry = roomba_odometry.wheel_odometry:main',
        ],
    },
)
