import threading
import time
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

# Initialize FastAPI app
app = FastAPI()

# Global ROS 2 publisher handle
ros_node = None
cmd_publisher = None

class WebBridgeNode(Node):
    def __init__(self):
        super().__init__('web_bridge_node')
        self.get_logger().info('Web Bridge ROS 2 Node has started.')

def ros_spin_thread():
    global ros_node, cmd_publisher
    rclpy.init()
    ros_node = WebBridgeNode()
    cmd_publisher = ros_node.create_publisher(Twist, '/cmd_vel', 10)
    rclpy.spin(ros_node)
    ros_node.destroy_node()
    rclpy.shutdown()

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=ros_spin_thread, daemon=True)
    t.start()
    time.sleep(1) # Give ROS node a moment to initialize

@app.get("/", response_class=HTMLResponse)
def control_panel():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Delivery Bot Controller</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; background: #f4f4f9; margin-top: 50px; }
            h1 { color: #333; }
            .btn { font-size: 20px; padding: 15px 30px; margin: 10px; cursor: pointer; background: #007bff; color: white; border: none; border-radius: 8px; }
            .btn:active { background: #0056b3; }
        </style>
    </head>
    <body>
        <h1>Delivery Bot Web Controller</h1>
        <p>Click the buttons below to command your robot in Gazebo!</p>
        <div>
            <button class="btn" onclick="sendCmd(0.5, 0)">FORWARD</button><br>
            <button class="btn" onclick="sendCmd(0, 0.5)">LEFT</button>
            <button class="btn" onclick="sendCmd(0, 0)">STOP</button>
            <button class="btn" onclick="sendCmd(0, -0.5)">RIGHT</button><br>
            <button class="btn" onclick="sendCmd(-0.5, 0)">BACKWARD</button>
        </div>
        <script>
            function sendCmd(linear, angular) {
                fetch('/move?linear=' + linear + '&angular=' + angular, { method: 'POST' })
                    .then(response => response.json())
                    .then(data => console.log(data));
            }
        </script>
    </body>
    </html>
    """

@app.post("/move")
def move_robot(linear: float, angular: float):
    global cmd_publisher
    if cmd_publisher:
        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        cmd_publisher.publish(twist)
        return {"status": "success", "linear": linear, "angular": angular}
    return {"status": "error", "message": "ROS publisher not ready"}

def main():
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == '__main__':
    main()
