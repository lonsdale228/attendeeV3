import logging
import time
from uuid import uuid1

from selenium.common.exceptions import ElementNotInteractableException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class ZoomUIMethods:
    def locate_zoom_element(self, selector, timeout=30):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )

    def locate_el_path(self, selector, timeout=30):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, selector))
        )

    def locate_by_id(self, selector, timeout=30):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.ID, selector))
        )

    def join_meeting(self):
        try:
            pwd = "TjBtV2ZqSEt1Rmc3QVVOb1FxQ0NMQT09"
            name_field = self.locate_by_id('input-for-name')
            time.sleep(1)
            name_field.send_keys("Jopa")

            self.driver.get_screenshot_as_file(f"LambdaTestVisibleScreen_{uuid1()}.png")

            pswd_input = self.locate_by_id('input-for-pwd')
            time.sleep(1)
            pswd_input.send_keys(pwd)

            final_join = self.locate_zoom_element('.zm-btn.preview-join-button.zm-btn--default.zm-btn__outline--blue')
            final_join.click()
            time.sleep(1)

            self.driver.get_screenshot_as_file(f"LambdaTestVisibleScreen_{uuid1()}.png")
            # self.handle_meeting_controls()

        except Exception as e:
            logging.error(f"Join meeting failed: {str(e)}")
            raise

    def handle_meeting_controls(self):
        self.locate_zoom_element('#voip-tab > div > button').click()
        # self.locate_zoom_element('button[aria-label="More"]').click()
        # self.locate_zoom_element('li:contains("Switch to Gallery View")').click()