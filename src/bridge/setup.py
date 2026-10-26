from setuptools import find_packages, setup

package_name = 'bridge'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    package_data={'': ['py.typed']},
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='tontonton/140494',
    maintainer_email='Sammoxxxxxxxx@gmail.com',
    description='Bridge Node for ROBOBIKE',
    license='MIT License',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'bridge_node = bridge.bridge_node:main',
            'dummybike = bridge.dummybike:run_dummy_bike',
            'pub_camera = bridge.pub_camera:main',
            'pub_robobike = bridge.pub_robobike:main',
            'sub_camera = bridge.sub_camera:main',
        ],
    },
)
