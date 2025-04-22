import os

from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    RegisterEventHandler,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import xacro


def generate_launch_description():

    # 当前包名
    this_package = "rm_eco65_gripper"

    default_robot_name = "rm_eco65_gripper_description"

    this_pkg_share = get_package_share_directory(this_package)

    gazebo_models_path = os.path.join(this_pkg_share, "models")

    # Launch configuration variables specific to simulation
    robot_name = LaunchConfiguration("robot_name")

    # Declare the launch options
    declare_robot_name_cmd = DeclareLaunchArgument(
        name="robot_name",
        default_value=default_robot_name,
        description="The name for the robot",
    )

    use_rviz = LaunchConfiguration("use_rviz")
    declare_use_rviz_cmd = DeclareLaunchArgument(
        name="use_rviz", default_value="False", description="Whether to start RVIZ"
    )

    use_sim_time = LaunchConfiguration("use_sim_time")
    declare_use_sim_time_cmd = DeclareLaunchArgument(
        name="use_sim_time",
        default_value="true",
        description="Use simulation (Gazebo) clock if true",
    )

    use_simulator = LaunchConfiguration("use_simulator")
    declare_use_simulator_cmd = DeclareLaunchArgument(
        name="use_simulator",
        default_value="True",
        description="Whether to start Gazebo",
    )

    headless = LaunchConfiguration("headless")
    declare_simulator_cmd = DeclareLaunchArgument(
        name="headless",
        default_value="False",
        description="Display the Gazebo GUI if False, otherwise run in headless mode",
    )

    # Specify the actions
    set_env_vars_resources = AppendEnvironmentVariable(
        "GAZEBO_MODEL_PATH", gazebo_models_path
    )

    # TODO: 1. Gazebo
    # Start Gazebo server
    pkg_gazebo_ros = get_package_share_directory("gazebo_ros")
    start_gazebo_server_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, "launch", "gzserver.launch.py")
        ),
        condition=IfCondition(use_simulator),
    )
    # Start Gazebo client
    start_gazebo_client_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, "launch", "gzclient.launch.py")
        ),
        condition=IfCondition(PythonExpression([use_simulator, " and not ", headless])),
    )

    # TODO: 2. Spawn the robot
    # Subscribe to the joint states of the robot, and publish the 3D pose of each link.
    doc = xacro.parse(open(os.path.join(this_pkg_share, "urdf", "rm_eco65_gripper_description.urdf.xacro")))
    xacro.process_doc(doc)
    robot_description_config = doc.toxml()
    start_robot_state_publisher_cmd = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[
            {
                "use_sim_time": use_sim_time,
                "robot_description": robot_description_config,
            }
        ],
    )
    start_gazebo_ros_spawner_cmd = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        arguments=[
            "-entity",
            robot_name,
            "-topic",
            "robot_description",
        ],
        output="screen",
    )

    # TODO: 3. Controllers
    # Launch arm controller
    start_arm_controller_cmd = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["rm_eco65_group_controller", "--controller-manager", "/controller_manager"],
    )
    start_gripper_controller_cmd = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["rm_gripper_group_controller", "--controller-manager", "/controller_manager"],
    )
    start_joint_state_broadcaster_cmd = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager",
            "/controller_manager",
        ],
    )
    load_joint_state_broadcaster_cmd = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=start_gazebo_ros_spawner_cmd,
            on_exit=[start_joint_state_broadcaster_cmd],
        )
    )
    load_arm_controller_cmd = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=start_joint_state_broadcaster_cmd,
            on_exit=[start_arm_controller_cmd],
        )
    )
    load_gripper_controller_cmd = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=start_arm_controller_cmd,
            on_exit=[start_gripper_controller_cmd],
        )
    )

    # TODO: 3. RViz
    # rviz_config_file = os.path.join(this_pkg_share, "rviz", "gazebo.rviz")
    # rviz_node = Node(
    #     condition=IfCondition(use_rviz),
    #     package="rviz2",
    #     executable="rviz2",
    #     name="rviz2",
    #     output="screen",
    #     arguments=["-d", rviz_config_file],
    #     parameters=[{"use_sim_time": use_sim_time}],
    # )
    # start_rviz_cmd = RegisterEventHandler(
    #     event_handler=OnProcessExit(
    #         target_action=start_joint_state_broadcaster_cmd,
    #         on_exit=[rviz_node],
    #     )
    # )

    # Create the launch description and populate
    ld = LaunchDescription()

    # Declare the launch options
    ld.add_action(declare_robot_name_cmd)
    ld.add_action(declare_use_rviz_cmd)
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_use_simulator_cmd)
    ld.add_action(declare_simulator_cmd)

    # Add any actions
    ld.add_action(set_env_vars_resources)
    ld.add_action(start_gazebo_server_cmd)
    ld.add_action(start_gazebo_client_cmd)
    ld.add_action(start_robot_state_publisher_cmd)
    ld.add_action(start_gazebo_ros_spawner_cmd)
    #ld.add_action(start_rviz_cmd)

    ld.add_action(load_joint_state_broadcaster_cmd)
    ld.add_action(load_arm_controller_cmd)
    ld.add_action(load_gripper_controller_cmd)

    return ld