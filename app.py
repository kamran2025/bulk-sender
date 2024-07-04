from flask import Flask, request, jsonify, send_from_directory
import os
import pandas as pd
import pdfplumber
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging

# Setup
app = Flask(__name__, static_folder='public', static_url_path='/public')
UPLOAD_DIR = os.path.join(app.static_folder, 'uploads/')
os.makedirs(UPLOAD_DIR, exist_ok=True)
PORT = 8001
countryCode = 91  # Set your country code
loginTime = 30  # Time for login (in seconds)
newMsgTime = 5  # Time for a new message (in seconds)
sendMsgTime = 5  # Time for sending a message (in seconds)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Serve the main page
@app.route('/')
def index():
  return send_from_directory(app.static_folder, 'index.html')


# Serve static files
@app.route('/<path:filename>')
def serve_static(filename):
  return send_from_directory(app.static_folder, filename)


@app.route('/upload', methods=['POST'])
def upload_file():
  if 'file' not in request.files:
    return 'No file uploaded.', 400

  file = request.files['file']
  message = request.form.get('message', '')

  if file:
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(file_path)
    logger.info(f'File path: {file_path}')

    numbers = []
    try:
      ext = os.path.splitext(file.filename)[-1].lower()
      if ext == '.csv':
        numbers = parse_csv(file_path)
      elif ext == '.xlsx':
        numbers = parse_xlsx(file_path)
      elif ext == '.txt':
        numbers = parse_txt(file_path)
      elif ext == '.pdf':
        numbers = parse_pdf(file_path)
      else:
        raise ValueError('Unsupported file format')

      if not numbers:
        raise ValueError('No valid numbers found')

      send_whatsapp_messages(numbers, message)
      return 'Messages sent successfully!', 200
    except Exception as e:
      logger.error(f'Error processing file: {str(e)}')
      return 'Something went wrong. Please try after some time.', 500
    finally:
      if os.path.exists(file_path):
        os.remove(file_path)
        logger.info(f'File {file_path} deleted successfully')
      else:
        logger.warning(f'File not found for deletion: {file_path}')


def parse_csv(file_path):
  df = pd.read_csv(file_path, header=None)
  return df[0].dropna().astype(str).tolist()


def parse_xlsx(file_path):
  df = pd.read_excel(file_path, header=None)
  return df[0].dropna().astype(str).tolist()


def parse_txt(file_path):
  with open(file_path, 'r') as file:
    return [line.strip() for line in file if line.strip()]


def parse_pdf(file_path):
  numbers = []
  with pdfplumber.open(file_path) as pdf:
    for page in pdf.pages:
      text = page.extract_text()
      lines = text.split('\n')
      for line in lines:
        if line.strip().isdigit():
          numbers.append(line.strip())
  return numbers


def send_whatsapp_messages(numbers, message):
  chrome_options = Options()
  chrome_options.add_argument('--no-sandbox')
  chrome_options.add_argument('--disable-dev-shm-usage')
  
  driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

  try:
    driver.get('https://web.whatsapp.com')
    time.sleep(loginTime)

    for number in numbers:
      if not number or not message:
        continue

      try:
        new_chat_button = WebDriverWait(driver, newMsgTime).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'div[title="New chat"][data-tab="2"]')))
        new_chat_button.click()
        logger.info('Clicked new chat button')
      except Exception as e:
        logger.error(f'Error clicking new chat button: {str(e)}')
        continue

      try:
        contact_input = WebDriverWait(driver, newMsgTime).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR,
                 'div[contenteditable="true"][data-tab="3"]')))
        contact_input.clear()
        contact_input.send_keys(f'{countryCode}{number}')
        time.sleep(2)
        contact_input.send_keys(Keys.ENTER)
        logger.info('Entered phone number')
      except Exception as e:
        logger.error(f'Error entering phone number: {str(e)}')
        continue

      try:
        message_box = WebDriverWait(driver, newMsgTime).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR,
                 'div[contenteditable="true"][data-tab="10"]')))
        message_box.clear()

        # Split the message by new lines and send each part with a new line
        lines = message.split('\n')
        for i, line in enumerate(lines):
          message_box.send_keys(line)
          if i != len(
              lines
          ) - 1:  # if not the last line, press Shift+Enter to add a new line
            message_box.send_keys(Keys.SHIFT, Keys.ENTER)

        time.sleep(4)
        message_box.send_keys(
            Keys.ENTER)  # finally, press Enter to send the message
        logger.info('Message sent')
      except Exception as e:
        logger.error(f'Error sending message: {str(e)}')
        continue

      time.sleep(sendMsgTime)
  finally:
    driver.quit()


if __name__ == '__main__':
  app.run(port=PORT)
