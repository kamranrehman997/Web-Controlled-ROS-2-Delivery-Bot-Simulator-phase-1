# Web-Controlled ROS 2 Delivery Bot Simulator

A browser-teleoperated delivery robot simulation built with **ROS 2 Jazzy**, **Gazebo Harmonic**, **`ros_gz_bridge`**, and **FastAPI / Uvicorn** on **Ubuntu 24.04 (WSL2)**.

---

## Phase 1: Browser Teleoperation Baseline (Completed)

Phase 1 establishes the end-to-end control loop from a browser UI into Gazebo Harmonic via ROS 2 `/cmd_vel` velocity commands.

### Tech Stack & Architecture
* **Simulation:** ROS 2 Jazzy + Gazebo Harmonic
* **Topic Bridging:** `ros_gz_bridge` connecting Gazebo simulation topics with ROS 2 interfaces
* **Backend & Web UI:** FastAPI served with Uvicorn (`delivery_bot_web`), publishing velocity commands to `/cmd_vel`
* **Robot Description & Launch:** `delivery_bot_description`
* **Environment:** WSL2 / Ubuntu 24.04

### Repository Layout (`~/ros2_ws`)
* `src/delivery_bot_description/` — Robot model, simulation assets, and launch files
* `src/delivery_bot_web/` — FastAPI/Uvicorn web server and browser teleoperation interface
* `.gitignore` — Excludes `build/`, `install/`, `log/`, caches, and IDE files

### Running Phase 1 (Three-Terminal Workflow)
Source ROS 2 Jazzy and your workspace overlay (`install/setup.bash`) in each terminal as needed:

1. **Terminal 1 — Simulation & Bridge:** Launch the delivery bot world in Gazebo Harmonic and start `ros_gz_bridge` for `/cmd_vel` (and associated robot topics).
2. **Terminal 2 — FastAPI / Uvicorn Server:** Start the `delivery_bot_web` backend so the browser controller and ROS 2 publisher node are active.
3. **Terminal 3 — Verification & Teleoperation:** Open the web control UI in your browser to drive the robot, and inspect `/cmd_vel` or active nodes/topics with `ros2 topic` / `ros2 node` CLI tools when verifying behavior.

### Roadmap
* **Phase 1 (Current):** Gazebo Harmonic simulation, `ros_gz_bridge`, and FastAPI `/cmd_vel` browser teleoperation.
* **Phase 2 (Next):** Attach a simulated camera sensor, bridge image topics into ROS 2, and stream live frames to the web UI.
