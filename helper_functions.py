from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import re
from datetime import datetime, timedelta
import time
import os
import requests
from selenium.webdriver.chrome.options import Options
import pytz


def create_driver():
    options = webdriver.ChromeOptions()

     # Headless + stability
    options.add_argument("--headless=new")  
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    # Suppress ChromeDriver logging
    options.add_argument("--log-level=3") 
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)

    # Makes headless look less "bot-like"
    options.add_argument("--disable-blink-features=AutomationControlled")

    in_ci = os.getenv("GITHUB_ACTIONS") == "true" or os.getenv("DOCKER") == "true"

    if in_ci:
        service = Service("/usr/bin/chromedriver", log_output=os.devnull)
    else:
        service = Service(log_output=os.devnull)

    return webdriver.Chrome(service=service, options=options)


def click_button(driver, xpath):
    wait = WebDriverWait(driver, 8)
    button = wait.until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )
    button.click()

def select_dropdown(driver, id,value):
    wait = WebDriverWait(driver, 6)
    select_element = wait.until(
        EC.presence_of_element_located((By.XPATH, id))
    )
    dropdown = Select(select_element)
    dropdown.select_by_value(value)

def input_value(driver, xpath, value):
    wait = WebDriverWait(driver, 4)
    input_element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
    input_element.clear()
    input_element.send_keys(value)

def handle_popup(driver):
    try:
        wait = WebDriverWait(driver, 4)
        button = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//button[@class="bookly-btn-submit"]'))
        )
        button.click()

    except (TimeoutException, NoSuchElementException):
        pass

def booking_date(target_day):
    today = datetime.today()

    weekday = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    days_ahead = weekday.index(target_day) - today.weekday() 
    if days_ahead <= 0:
        days_ahead += 7 

    next_target_day = today + timedelta(days=days_ahead)

    return next_target_day.strftime("%Y-%m-%d")


def available_timestamps(driver, target_day):
    pattern = r'"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"'

    available_timestamps = []
    target_date = booking_date(target_day)

    # wait until the column is loaded
    wait = WebDriverWait(driver, 3)
    column_div = wait.until(EC.presence_of_element_located((
        By.XPATH, '//div[@class="bookly-time-screen"]'
    )))

    # get all values (timeslots) under each button
    buttons = column_div.find_elements(By.TAG_NAME, 'button')

    for btn in buttons:
        val = btn.get_attribute("value")
        if not val:
            continue
        match = re.search(pattern, val)
        if match and btn.get_attribute("disabled") is None:
            timestamp = match.group(1)

            if timestamp.startswith(target_date) :
                available_timestamps.append(timestamp)

    return available_timestamps


def send_telegram_message(message):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Telegram message: {e}")


def wait_until_target():
    tz = pytz.timezone("Asia/Manila")
    now = datetime.now(tz)

    booking_time = tz.localize(datetime.strptime("08:01:00", "%H:%M:%S").replace(
        year=now.year, month=now.month, day=now.day
    ))

    if booking_time < now:
        booking_time += timedelta(days=1)

    seconds_waiting = (booking_time - now).total_seconds()
    print(f"Now: {now}, Booking: {booking_time}, Waiting: {seconds_waiting:.0f} seconds")
    if seconds_waiting > 0:
        time.sleep(seconds_waiting)

