from dotenv import load_dotenv
load_dotenv()

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, UnexpectedAlertPresentException, ElementClickInterceptedException
import time
from helper_functions import create_driver, click_button, select_dropdown, input_value, handle_popup, booking_date, available_timestamps, send_telegram_message, wait_until_target
from multiprocessing import Process, Manager
import os
from threading import Thread, Lock


def main(target_day, court_priority, preferred_time, max_retries=30):
    retry = 0
    driver = create_driver()
    court = court_priority[0]

    while retry < max_retries:
        try:
            driver.get("https://aava.com.ph/facilities-reservation/")
            close_browser = True
            
            print("Clicking terms and conditions checkbox...")

            # click I agree the terms and conditions and accept
            click_button(driver, '//input[@id="form-field-name"]')
            click_button(driver, '//button[@class="elementor-button elementor-size-sm"]')
            time.sleep(3.5)

            print("Terms and conditions accepted.")

            print(f"Selecting court {court}...")

            # select court
            select_dropdown(driver, '//label[text()="Appointment"]/following-sibling::div/select',court)
            click_button(driver, '//button[@class="bookly-next-step bookly-js-next-step bookly-btn ladda-button"]')
            time.sleep(2.5)

            print("Court selected.")

            print("Entering no. of guests...")

            # no. guests page
            click_button(driver, '//button[@class="bookly-next-step bookly-js-next-step bookly-btn ladda-button"]')

            print("No. of guests entered.")

            print("Checking if timeslots are available...")


            try:
                wait = WebDriverWait(driver, 5)

                # wait until "no timeslots available label" dissapears
                wait.until_not(
                    EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "bookly-box bookly-nav-steps bookly-clear")]'))
                )
                
                # wait for time screen container to appear
                wait.until(
                    EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "bookly-time-screen")]'))
                )

                # At least one actual timeslot button shows up
                day = booking_date(target_day)
                wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, f'//button[contains(@value, "{day}")]')
                    )
                )
                
                print("Timeslots ready.")

            except TimeoutException:
                print("timeslots not ready, retrying...")
                retry += 1
                continue


            print("Clicking preferred timeslot...")

            # get available slots
            available_slots = available_timestamps(driver, target_day)

            # Click first available preferred time
            found = False

            if preferred_time in available_slots:
                wait = WebDriverWait(driver, 5)
                wait.until(EC.presence_of_element_located(
                    (By.XPATH, f'//button[contains(@value, "{preferred_time}")]')
                )).click()
                
                found = True

            if not found:
                print("No preferred time slots available.")

                if court == court_priority[0]:
                    court = court_priority[1]
                    retry += 1
                    print(f"No preferred time slot in {court_priority[0]}... trying {court_priority[1]}")
                    continue

                else:
                    if close_browser:
                        driver.quit()
                    return {"Status": "Failed", "Court": court}


            print("Preferred timeslot chosen.")
            print("Inputting details...")

            # Input Details
            input_value(driver, '//input[@class="bookly-js-full-name"]', os.getenv("FULL_NAME"))
            input_value(driver, '//input[@class="bookly-js-user-email"]', os.getenv("EMAIL"))
            input_value(driver, '//input[@class="bookly-js-user-phone-input bookly-user-phone iti__tel-input"]', os.getenv("PHONE_NUMBER"))
            input_value(driver, '//input[@class="bookly-js-custom-field"]', os.getenv("CCODE"))

            print("Details inputted.")
            print("Submitting form...")

            # Submit
            click_button(driver,'//button[@class="bookly-next-step bookly-js-next-step bookly-btn ladda-button"]')
            handle_popup(driver)

            # Pay on-site page
            click_button(driver, '//button[@class="bookly-next-step bookly-js-next-step bookly-btn ladda-button"]')

            print("Validating form submission...")

            try:
                WebDriverWait(driver, 10).until_not(
                EC.presence_of_element_located((By.XPATH, '//button[@class="bookly-next-step bookly-js-next-step bookly-btn ladda-button"]'))
                )
                
                WebDriverWait(driver, 5).until(
                EC.any_of(
                EC.presence_of_element_located((By.XPATH, '//div[contains(text(), "Thank you!")]')),
                EC.presence_of_element_located((By.XPATH, '//button[.//span[contains(text(), "Start over")]]')),
                EC.presence_of_element_located((By.XPATH,'//button[@class="bookly-nav-btn bookly-js-start-over bookly-btn ladda-button bookly-left"]'))
                )
                )

                print("Reservation success")

                if close_browser:
                    driver.quit()
                return {"Status": "Success", "Court": court}

            except (TimeoutException, NoSuchElementException):
                print("No submission confirmation, retrying...")
                retry += 1
                continue

        except (TimeoutException, StaleElementReferenceException, NoSuchElementException, UnexpectedAlertPresentException, ElementClickInterceptedException) as e:
            print(f"Retry {retry + 1}/{max_retries} failed — refreshing page...")
            print(f"Exception type: {type(e).__name__}, Message: {e}")
            time.sleep(1)
            retry += 1
    

    if close_browser:
        driver.quit()
    return {"Status": "Failed", "Court": court}


if __name__ == "__main__":
    target_day = os.getenv("TARGET_DAY", "Saturday")
    time_slot1 = os.getenv("TIME_SLOT1", "14:00:00")
    court_input = os.getenv("COURTS", "D,C") 

    target_date = booking_date(target_day)
    preferred_times = f"{target_date} {time_slot1}"
    courts_available = ["Any", "A", "B", "C", "D"]
    court_priority = [str(courts_available.index(court.strip()) + 1) for court in court_input.split(",")]

    wait_until_target()

    slot1_result = main(target_day, court_priority, preferred_times)


    if slot1_result["Status"] == "Success":
        send_telegram_message(f"{time_slot1} booked on Court {courts_available[int(slot1_result['Court'])-1]}")

    else:
        send_telegram_message("no timeslots booked")