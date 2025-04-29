import logging
import re
import subprocess
import threading
import time
from urllib.parse import urlparse, parse_qs

import cv2
import numpy as np
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from bots.web_bot_adapter import WebBotAdapter
from bots.zoom_bot_adapter.zoom_ui_methods import ZoomUIMethods


logger = logging.getLogger(__name__)

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
        self.meeting_id = None
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

    def load_cookies_from_file(self, filepath):
        cookies = []
        with open(filepath, 'r') as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue  # skip comments and empty lines
                parts = line.split('\t')
                if len(parts) != 7:
                    continue  # malformed line
                domain, flag, path, secure, expiry, name, value = parts
                cookie = {
                    'domain': domain,
                    'name': name,
                    'value': value,
                    'path': path,
                    'secure': secure.upper() == 'TRUE',
                }
                if expiry.isdigit() and int(expiry) != 0:
                    cookie['expiry'] = int(expiry)
                cookies.append(cookie)
        return cookies

    def attempt_to_join_meeting(self, virt_cable_token):


        # result = subprocess.Popen([
        #     "pactl", "load-module", "module-null-sink", f"sink_name={virt_cable_token}"
        # ])

        # logger.info(f"Running virt cable: {result},{result.stdout},{result.stderr}")

        from urllib import parse

        parsed_url = parse.urlparse(self.meeting_url)
        conf_id = parsed_url.path.split("/j/")[-1]

        self.meeting_id = conf_id

        url = f"https://zoom.us/wc/join/{conf_id}"
        self.driver.execute_cdp_cmd(
            "Browser.grantPermissions",
            {
                "origin": url,
                "permissions": [
                    "geolocation",
                    "audioCapture",
                    "displayCapture",
                    "videoCapture",
                ],
            },
        )
        self.driver.get("https://app.zoom.us/wc/join")
        time.sleep(2)

        cookie_file_path = 'app.zoom.us_cookies.txt'
        cookies = self.load_cookies_from_file(cookie_file_path)

        for cookie in cookies:
            try:
                self.driver.add_cookie(cookie)
            except Exception as e:
                logger.error(f"Error adding cookie {cookie['name']}: {e}")

        self.driver.get(url)
        self.join_meeting(self.meeting_url)

        time.sleep(3)

        self.start_modal_monitoring()
        #
        # time.sleep(15)
        #
        # self.click_leave_button()


    # def handle_websocket(self, websocket):
    #     # Similar WebSocket handling as Google Meet but for Zoom's data format
    #     while True:
    #         message = websocket.receive()
    #         # Process Zoom-specific messages
    def monitor_for_meeting_end_modal(self, check_interval=1):
        """
        Check periodically if the meeting ended modal is present.
        Adjust the selector to match the element unique to the modal.
        """
        while not self.left_meeting:
            try:
                modal_element = self.driver.find_element(By.CSS_SELECTOR, 'div[aria-label="Meeting is end now"], div[aria-label="You have been removed"]')
                if modal_element:
                    logger.info("Detected meeting end modal, triggering click_leave_button()")
                    self.click_leave_button()
                    break
            except NoSuchElementException:
                # The modal is not yet present; wait and try again.
                pass
            except Exception as ex:
                logger.error(f"Error in modal monitor thread: {ex}")
            time.sleep(check_interval)

    def start_modal_monitoring(self):
        """Starts the meeting end modal monitoring in a separate thread."""
        monitor_thread = threading.Thread(target=self.monitor_for_meeting_end_modal, daemon=True)
        monitor_thread.start()

    def click_leave_button(self):
        # self.locate_zoom_element('button[aria-label="Leave"]').click()

        self.send_message_callback({"message": self.Messages.MEETING_ENDED})

    def get_first_buffer_timestamp_ms(self):
        if self.media_sending_enable_timestamp_ms is None:
            return None
        # Doing a manual offset for now to correct for the screen recorder delay. This seems to work reliably.
        return self.media_sending_enable_timestamp_ms