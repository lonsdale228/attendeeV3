from bots.web_bot_adapter import WebBotAdapter
from bots.zoom_bot_adapter.zoom_ui_methods import ZoomUIMethods


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
        return 8766  # Different port from Google Meet

    def attempt_to_join_meeting(self):
        self.driver.get(self.meeting_url)
        self.join_meeting()

    def handle_websocket(self, websocket):
        # Similar WebSocket handling as Google Meet but for Zoom's data format
        while True:
            message = websocket.receive()
            # Process Zoom-specific messages

    def click_leave_button(self):
        self.locate_zoom_element('button[aria-label="Leave"]').click()