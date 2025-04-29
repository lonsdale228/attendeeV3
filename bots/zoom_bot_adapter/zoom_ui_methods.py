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

    def join_meeting(self, url):
        try:
            from urllib import parse
            parsed_url = parse.urlparse(url)

            query_params = parse.parse_qs(parsed_url.query)
            pwd = query_params.get("pwd", [None])[0]

            self.driver.get_screenshot_as_file(f"LambdaTestVisibleScreen_{uuid1()}.png")

            WebDriverWait(self.driver, 10).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, "webclient"))
            )

            # 2) hide the cookie‐banner overlay
            self.driver.execute_script("""
              var over = document.getElementById('onetrust-policy-text');
              if(over){ over.style.display='none'; }
            """)

            try:
                agree_btn = self.locate_by_id('wc_agree1')
                agree_btn.click()
            except Exception as e:
                logging.error(f"Agree button not found: {str(e)}")

            self.driver.get_screenshot_as_file(f"LambdaTestVisibleScreen_{uuid1()}.png")

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