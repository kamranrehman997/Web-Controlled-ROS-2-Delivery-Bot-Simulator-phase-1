import asyncio
import threading
import time
from contextlib import asynccontextmanager

import cv2
import numpy as np
import rclpy
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from geometry_msgs.msg import Twist
from pydantic import BaseModel
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image


class DriveCommand(BaseModel):
    linear_x: float = 0.0
    angular_z: float = 0.0


class RobotBridgeNode(Node):
    def __init__(self, image_topic: str = "/camera/image_raw", cmd_topic: str = "/cmd_vel") -> None:
        super().__init__("fastapi_robot_bridge_node")
        self._lock = threading.Lock()
        self._latest_jpeg: bytes | None = None
        self._last_frame_time: float = 0.0

        img_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )
        self.create_subscription(Image, image_topic, self._image_callback, img_qos)
        self._cmd_pub = self.create_publisher(Twist, cmd_topic, 10)
        self.get_logger().info(f"Subscribed to {image_topic} and publishing to {cmd_topic}")

    def publish_cmd_vel(self, linear_x: float, angular_z: float) -> None:
        msg = Twist()
        msg.linear.x = float(linear_x)
        msg.angular.z = float(angular_z)
        self._cmd_pub.publish(msg)

    def _image_to_bgr(self, msg: Image) -> np.ndarray | None:
        if msg.height == 0 or msg.width == 0 or len(msg.data) == 0:
            return None

        raw = np.frombuffer(msg.data, dtype=np.uint8)
        encoding = msg.encoding.lower()

        if encoding in ("rgb8", "bgr8"):
            channels = 3
            expected = msg.height * msg.width * channels
            if raw.size < expected:
                return None
            img = raw[:expected].reshape((msg.height, msg.width, channels))
            if encoding == "rgb8":
                return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            return img

        if encoding in ("rgba8", "bgra8"):
            channels = 4
            expected = msg.height * msg.width * channels
            if raw.size < expected:
                return None
            img = raw[:expected].reshape((msg.height, msg.width, channels))
            if encoding == "rgba8":
                return cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        if encoding in ("mono8", "8uc1"):
            expected = msg.height * msg.width
            if raw.size < expected:
                return None
            gray = raw[:expected].reshape((msg.height, msg.width))
            return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        self.get_logger().warning(f"Unsupported image encoding: {msg.encoding}")
        return None

    def _image_callback(self, msg: Image) -> None:
        bgr = self._image_to_bgr(msg)
        if bgr is None:
            return

        ok, encoded = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ok:
            return

        jpeg_bytes = encoded.tobytes()
        with self._lock:
            self._latest_jpeg = jpeg_bytes
            self._last_frame_time = time.monotonic()

    def get_latest_jpeg(self) -> tuple[bytes | None, float]:
        with self._lock:
            return self._latest_jpeg, self._last_frame_time


class RosSpinThread:
    def __init__(self, node: RobotBridgeNode) -> None:
        self._node = node
        self._executor = SingleThreadedExecutor()
        self._executor.add_node(self._node)
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop_event.is_set() and rclpy.ok():
            self._executor.spin_once(timeout_sec=0.05)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._executor.remove_node(self._node)
        self._node.destroy_node()
        self._executor.shutdown()
        self._thread.join(timeout=2.0)


ros_node: RobotBridgeNode | None = None
ros_spinner: RosSpinThread | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ros_node, ros_spinner
    if not rclpy.ok():
        rclpy.init()
    ros_node = RobotBridgeNode("/camera/image_raw", "/cmd_vel")
    ros_spinner = RosSpinThread(ros_node)
    ros_spinner.start()
    try:
        yield
    finally:
        if ros_spinner is not None:
            ros_spinner.stop()
        if rclpy.ok():
            rclpy.shutdown()


app = FastAPI(title="Delivery Bot Control & Camera Stream", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return """
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8" />
        <title>Delivery Bot Dashboard</title>
        <style>
          body { font-family: Arial, sans-serif; background: #111; color: #eee; text-align: center; padding: 24px; }
          img { max-width: 90vw; border: 2px solid #333; border-radius: 8px; background: #000; }
          .controls { margin-top: 20px; display: inline-grid; grid-template-columns: repeat(3, 90px); gap: 8px; }
          button { padding: 12px; font-size: 14px; border-radius: 6px; border: 1px solid #444; background: #222; color: #fff; cursor: pointer; }
          button:hover { background: #333; }
          .stop { background: #7a1f1f; border-color: #a33; }
          .stop:hover { background: #962727; }
          .status { margin-top: 12px; color: #9ec; font-family: monospace; }
        </style>
      </head>
      <body>
        <h2>Delivery Bot — Live Camera & Drive Control</h2>
        <img src="/video_feed" alt="Camera Stream" />
        <div class="controls">
          <div></div>
          <button onclick="sendCmd(0.3, 0.0)">Forward</button>
          <div></div>
          <button onclick="sendCmd(0.0, 0.6)">Turn Left</button>
          <button class="stop" onclick="sendCmd(0.0, 0.0)">Stop</button>
          <button onclick="sendCmd(0.0, -0.6)">Turn Right</button>
          <div></div>
          <button onclick="sendCmd(-0.3, 0.0)">Reverse</button>
          <div></div>
        </div>
        <div class="status" id="status">Cmd: linear_x=0.0, angular_z=0.0</div>
        <script>
          async function sendCmd(linear_x, angular_z) {
            const res = await fetch("/cmd_vel", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ linear_x, angular_z })
            });
            if (res.ok) {
              const data = await res.json();
              document.getElementById("status").textContent =
                `Cmd: linear_x=${data.linear_x.toFixed(2)}, angular_z=${data.angular_z.toFixed(2)}`;
            }
          }
        </script>
      </body>
    </html>
    """


@app.post("/cmd_vel")
async def post_cmd_vel(cmd: DriveCommand) -> dict:
    if ros_node is None:
        return {"ok": False, "error": "ROS node not initialized"}
    ros_node.publish_cmd_vel(cmd.linear_x, cmd.angular_z)
    return {"ok": True, "linear_x": cmd.linear_x, "angular_z": cmd.angular_z}


@app.get("/snapshot")
async def snapshot() -> Response:
    if ros_node is None:
        return Response(status_code=503, content="ROS camera node not initialized")
    frame, _ = ros_node.get_latest_jpeg()
    if frame is None:
        return Response(status_code=503, content="No camera frame received yet")
    return Response(content=frame, media_type="image/jpeg")


async def mjpeg_generator():
    boundary = b"--frame"
    while True:
        if ros_node is not None:
            frame, last_ts = ros_node.get_latest_jpeg()
            age = time.monotonic() - last_ts if last_ts > 0 else 999.0
            if frame is not None and age < 5.0:
                yield (
                    boundary
                    + b"\r\nContent-Type: image/jpeg\r\nContent-Length: "
                    + str(len(frame)).encode("ascii")
                    + b"\r\n\r\n"
                    + frame
                    + b"\r\n"
                )
        await asyncio.sleep(0.05)


@app.get("/video_feed")
async def video_feed() -> StreamingResponse:
    return StreamingResponse(
        mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
