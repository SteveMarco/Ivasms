import os
import time
import re
import asyncio
import threading
from datetime import datetime
from flask import Flask
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from telegram import Bot

# ================= CONFIG =================

BOT_TOKEN = os.getenv("8716921626:AAFiDkSoen6APOK-dqxF5VN5M0vEnNWEeVA")
CHAT_ID = os.getenv("8443707949")
IVASMS_EMAIL = os.getenv("teamdvg02@gmail.com")
IVASMS_PASSWORD = os.getenv("Classy07@")

if not BOT_TOKEN or not CHAT_ID or not IVASMS_EMAIL or not IVASMS_PASSWORD:
    raise ValueError("Missing environment variables!")

bot = Bot(token=BOT_TOKEN)
app = Flask(__name__)

last_scraped_message_id = None

# ================= CHROME OPTIONS =================

def get_chrome_options():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.binary_location = "/usr/bin/chromium"
    return chrome_options

# ================= OTP EXTRACTION =================

def extract_otp_and_service(sms_text):
    otp_match = re.search(r"\b\d{4,8}\b", sms_text)
    otp_code = otp_match.group() if otp_match else "N/A"

    sms_lower = sms_text.lower()
    service = "Unknown"

    if "whatsapp" in sms_lower:
        service = "WhatsApp"
    elif "facebook" in sms_lower:
        service = "Facebook"
    elif "google" in sms_lower:
        service = "Google"
    elif "telegram" in sms_lower:
        service = "Telegram"
    elif "instagram" in sms_lower:
        service = "Instagram"

    return otp_code, service

# ================= SCRAPER =================

def scrape_ivasms():
    global last_scraped_message_id
    driver = None

    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=get_chrome_options())

        driver.get("https://www.ivasms.com/portal/sms/received")

        # Login
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.NAME, "email"))
        ).send_keys(IVASMS_EMAIL)

        driver.find_element(By.NAME, "password").send_keys(IVASMS_PASSWORD)
        driver.find_element(By.XPATH, "//button[contains(text(),'Sign in')]").click()

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//table"))
        )

        first_row = driver.find_element(By.XPATH, "//table/tbody/tr[1]")
        cols = first_row.find_elements(By.TAG_NAME, "td")

        if len(cols) < 4:
            return None

        date_time = cols[1].text.strip()
        number = cols[2].text.strip()
        sms_text = cols[3].text.strip()

        current_id = f"{date_time}-{number}-{sms_text}"

        if current_id == last_scraped_message_id:
            return None

        last_scraped_message_id = current_id

        otp, service_name = extract_otp_and_service(sms_text)

        message = f"""
✨ {service_name} OTP ALERT ✨

🕐 {date_time}
📱 {number}

🔑 OTP: {otp}

{s}
""".replace("{s}", sms_text)

        return message

    except TimeoutException:
        print("Timeout loading page.")
        return None
    except WebDriverException as e:
        print("WebDriver error:", e)
        return None
    except Exception as e:
        print("Unexpected error:", e)
        return None
    finally:
        if driver:
            driver.quit()

# ================= TELEGRAM SEND =================

async def send_telegram(message):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=message)
        print("OTP Sent.")
    except Exception as e:
        print("Telegram error:", e)

# ================= MAIN LOOP =================

async def scraper_loop():
    while True:
        print("Checking for new OTP...")
        otp_message = scrape_ivasms()
        if otp_message:
            await send_telegram(otp_message)
        await asyncio.sleep(30)

def start_scraper():
    asyncio.run(scraper_loop())

# ================= FLASK ROUTES =================

@app.route("/")
def home():
    return "IVASMS Telegram Bot is running!"

@app.route("/health")
def health():
    return "OK", 200

# ================= START =================

if __name__ == "__main__":
    threading.Thread(target=start_scraper).start()
    app.run(host="0.0.0.0", port=10000)
