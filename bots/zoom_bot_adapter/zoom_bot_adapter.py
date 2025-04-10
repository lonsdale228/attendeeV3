import re
import subprocess
from urllib.parse import urlparse, parse_qs

import cv2
import numpy as np

from bots.web_bot_adapter import WebBotAdapter
from bots.zoom_bot_adapter.zoom_ui_methods import ZoomUIMethods


def create_black_yuv420_frame(width=640, height=360):
    # Create BGR frame (red is [0,0,0] in BGR)
    bgr_frame = np.zeros((height, width, 3), dtype=np.uint8)
    bgr_frame[:, :] = [0, 0, 0]  # Pure black in BGR

    # Convert BGR to YUV420 (I420)
    yuv_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2YUV_I420)

    # Return as bytes
    return yuv_frame.tobytes()


def parse_join_url(join_url):
    # Parse the URL into components
    parsed = urlparse(join_url)

    # Extract meeting ID using regex to match only numeric characters
    meeting_id_match = re.search(r"(\d+)", parsed.path)
    meeting_id = meeting_id_match.group(1) if meeting_id_match else None

    # Extract password from query parameters
    query_params = parse_qs(parsed.query)
    password = query_params.get("pwd", [None])[0]

    return (meeting_id, password)

class ZoomBotAdapter(WebBotAdapter, ZoomUIMethods):
    def __init__(
            self,
            *,
            display_name,
            send_message_callback,
            meeting_url,
            automatic_leave_configuration,
            **kwargs
    ):
        # Filter out platform-specific parameters
        filtered_kwargs = {k: v for k, v in kwargs.items()
                           if k not in ['use_one_way_audio', 'use_mixed_audio', 'use_video']}

        super().__init__(
            display_name=display_name,
            send_message_callback=send_message_callback,
            meeting_url=meeting_url,
            automatic_leave_configuration=automatic_leave_configuration,
            **filtered_kwargs
        )
    def get_chromedriver_payload_file_name(self):
        return "zoom_chromedriver_payload.js"

    def get_websocket_port(self):
        return 8768  # Different port from Google Meet

    def attempt_to_join_meeting(self):
        subprocess.Popen([
            "pulseaudio", "-D", "--exit-idle-time=-1", "--system"
        ])

        subprocess.run([
            "pactl", "load-module", "module-null-sink", "sink_name=virt"
        ])

        self.driver.execute_cdp_cmd(
            "Browser.grantPermissions",
            {
                "origin": self.meeting_url,
                "permissions": [
                    "geolocation",
                    "audioCapture",
                    "displayCapture",
                    "videoCapture",
                ],
            },
        )
        self.driver.get(self.meeting_url)
        self.join_meeting()


    # def handle_websocket(self, websocket):
    #     # Similar WebSocket handling as Google Meet but for Zoom's data format
    #     while True:
    #         message = websocket.receive()
    #         # Process Zoom-specific messages

    def click_leave_button(self):
        self.locate_zoom_element('button[aria-label="Leave"]').click()

    def get_first_buffer_timestamp_ms(self):
        if self.media_sending_enable_timestamp_ms is None:
            return None
        # Doing a manual offset for now to correct for the screen recorder delay. This seems to work reliably.
        return self.media_sending_enable_timestamp_ms