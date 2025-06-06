import logging
import os
import time
from uuid import uuid1

from selenium.common.exceptions import ElementNotInteractableException, NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from bots.web_bot_adapter.ui_methods import UiMeetingNotFoundException


class ZoomUIMethods:
    DO_SCR = True

    def locate_zoom_element(self, selector, timeout=30):
        return WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))

    def locate_el_path(self, selector, timeout=30):
        return WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((By.XPATH, selector)))

    def locate_by_id(self, selector, timeout=30):
        return WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((By.ID, selector)))

    def make_screenshot(self):
        os.makedirs("screenshots", exist_ok=True)
        if self.DO_SCR:
            self.driver.get_screenshot_as_file(f"screenshots/Screen_{uuid1()}.png")

    def join_meeting(self, url):
        try:
            from urllib import parse

            parsed_url = parse.urlparse(url)

            query_params = parse.parse_qs(parsed_url.query)
            pwd = query_params.get("pwd", [None])[0]

            self.make_screenshot()

            try:
                err_msg = self.locate_el_path("//span[@class='error-message']", timeout=3)
                if err_msg:
                    logging.error(f"Meeting isn't started!")
                    raise
            except TimeoutException:
                ...

            try:
                name_field = self.locate_by_id("input-for-name", timeout=10)
            except TimeoutException:
                policies_button = self.locate_el_path("//button[@id='wc_agree1']")
                policies_button.click()

                name_field = self.locate_by_id("input-for-name", timeout=20)

            time.sleep(1)
            name_field.send_keys("Skriba Bot")

            self.make_screenshot()

            try:
                pswd_input = self.locate_by_id("input-for-pwd", timeout=5)
                time.sleep(1)
                pswd_input.send_keys(pwd)
            except TimeoutException:
                logging.error("There is not pwd input!")

            final_join = self.locate_zoom_element(".zm-btn.preview-join-button.zm-btn--default.zm-btn__outline--blue")
            final_join.click()
            time.sleep(1)

            try:
                footbar = self.locate_el_path("//div[@id='foot-bar']", timeout=10)
            except TimeoutException:
                raise UiMeetingNotFoundException("aboba")

            self.make_screenshot()
            # self.handle_meeting_controls()

        except Exception as e:
            logging.error(f"Join meeting failed: {str(e)}")
            raise

    def handle_meeting_controls(self):
        self.locate_zoom_element("#voip-tab > div > button").click()
        # self.locate_zoom_element('button[aria-label="More"]').click()
        # self.locate_zoom_element('li:contains("Switch to Gallery View")').click()