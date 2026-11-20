# Phase 2 Overview

Phase 2 connects the `delivery_bot` simulation to a browser interface using FastAPI and ROS 2 topics.

## What This Phase Does
- Streams live camera video from `/camera/image_raw` to the browser.
- Sends movement commands (`linear_x` and `angular_z`) over `/cmd_vel` from the web dashboard.
- Uses `ros_gz_bridge` to link Gazebo Harmonic topics with ROS 2 Jazzy.
