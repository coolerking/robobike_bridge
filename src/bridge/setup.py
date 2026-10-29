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
    install_requires=['setuptools', 'pygame'],
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
            'dummybike = bridge.dummybike:run_dummy_bike',
            'pub_image = bridge.pub_image:main',
            'pub_command = bridge.pub_command:main',
            'sub_image = bridge.sub_image:main',
            'pub_robobike = bridge.pub_robobike:main',
            'sub_robobike = bridge.sub_robobike:main',
        ],
    },
)
