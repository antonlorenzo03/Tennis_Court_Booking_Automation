from dotenv import load_dotenv
load_dotenv()

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, UnexpectedAlertPresentException, ElementClickInterceptedException
import time
from helper_functions import create_driver, click_button, select_dropdown, input_value, handle_popup, booking_date, available_timestamps, send_telegram_message
from multiprocessing import Process, Manager
import os


def main(results_dict, label, target_day, court_priority, preferred_time, max_retries=30):
    retry = 0
    driver = create_driver()
    court = court_priority[0]

    while retry < max_retries:
        try:
            driver.get("https://aava.com.ph/facilities-reservation/")
            close_browser = False
            
            # click I agree the terms and conditions and accept
            click_button(driver, '//input[@id="form-field-name"]')
            click_button(driver, '//button[@class="elementor-button elementor-size-sm"]')
            time.sleep(3.5)

            # select court
            select_dropdown(driver, '//label[text()="Appointment"]/following-sibling::div/select',court)
            click_button(driver, '//button[@class="bookly-next-step bookly-js-next-step bookly-btn ladda-button"]')
            time.sleep(2)

            # no. guests page
            click_button(driver, '//button[@class="bookly-next-step bookly-js-next-step bookly-btn ladda-button"]')

            # check if slots are available already
            WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "bookly-time-screen")]'))
            )

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
                    continue

                else:
                    results_dict[label] = {
                        "status": "Failed",
                        "court": court
                    }
                    if close_browser:
                        driver.quit()
                    return False


            # Input Details
            input_value(driver, '//input[@class="bookly-js-full-name"]', os.getenv("FULL_NAME"))
            input_value(driver, '//input[@class="bookly-js-user-email"]', os.getenv("EMAIL"))
            input_value(driver, '//input[@class="bookly-js-user-phone-input bookly-user-phone iti__tel-input"]', os.getenv("PHONE_NUMBER"))
            input_value(driver, '//input[@class="bookly-js-custom-field"]', os.getenv("CCODE"))

            # Submit
            click_button(driver,'//button[@class="bookly-next-step bookly-js-next-step bookly-btn ladda-button"]')
            handle_popup(driver)

            # results_dict[label] = {
            #     "status": "Success",
            #     "court": court
            # }
            # if close_browser:
            #     driver.quit()
            # return True

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

                results_dict[label] = {
                    "status": "Success",
                    "court": court
                }
                if close_browser:
                    driver.quit()
                return True

            except (TimeoutException, NoSuchElementException):
                print("Reservation likely failed, retrying...")
                retry += 1
                continue

        except (TimeoutException, StaleElementReferenceException, NoSuchElementException, UnexpectedAlertPresentException, ElementClickInterceptedException):
            print(f"Retry {retry + 1}/{max_retries} failed — refreshing page...")
            time.sleep(1)
            retry += 1
    

    results_dict[label] = {
        "status": "Failed",
        "court": court
    }
    if close_browser:
        driver.quit()
    return False


if __name__ == "__main__":

    with Manager() as manager:
        results = manager.dict()

        target_day = os.getenv("TARGET_DAY", "Saturday")
        time_slot1 = os.getenv("TIME_SLOT1", "14:00:00")
        time_slot2 = os.getenv("TIME_SLOT2", "15:00:00")
        court_input = os.getenv("COURTS", "D,C") 

        target_date = booking_date(target_day)
        preferred_times = [
        f"{target_date} {time_slot1}",
        f"{target_date} {time_slot2}",
        ]
        courts_available = ["Any", "A", "B", "C", "D"]
        court_priority = [str(courts_available.index(court.strip()) + 1) for court in court_input.split(",")]

        p1 = Process(target=main, args=(results, time_slot1, target_day, court_priority, preferred_times[0]))
        p2 = Process(target=main, args=(results, time_slot2, target_day, court_priority, preferred_times[1]))

        p1.start()
        p2.start()
        p1.join()
        p2.join()

        slot1_result = results.get(time_slot1)
        slot2_result = results.get(time_slot2)

        if slot1_result and slot1_result["status"] == "Success" and \
        slot2_result and slot2_result["status"] == "Success":
            send_telegram_message(f"{time_slot1} and {time_slot2} booked on Courts {courts_available[int(slot1_result['court'])-1]} and {courts_available[int(slot2_result['court'])-1]}")

        elif slot1_result and slot1_result["status"] == "Success":
            send_telegram_message(f"{time_slot1} booked on Court {courts_available[int(slot1_result['court'])-1]} only")

        elif slot2_result and slot2_result["status"] == "Success":
            send_telegram_message(f"{time_slot2} booked on Court {courts_available[int(slot2_result['court'])-1]} only")

        else:
            send_telegram_message("no timeslots booked")
