# pip install selenium
# pip install numpy>=1.20.3
# pip install pandas

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

import pandas as pd
import time
import shutil
import os
import json

# -----------------------------------------------------------------------------------------

# Decorator to catch errors in my functions
def exception_handler(func):
    def wrapper(*args, **kwargs):
        try:
            # Call the original function
            return func(*args, **kwargs)
        except Exception as e:
            # Print the error message
            print(f"Error in function {func.__name__}: {e}")
    return wrapper

# Trying to login with cookies (no exception here because its in a try block below)
def try_logging_in_w_cookies(driver):
    print("Trying to login with cookies")
    # Opening Fwango page to check login status
    driver.get("https://fwango.io/signin?r=/dashboard")

    # Opening cookies file from last session
    with open('cookies.json', 'r') as f:
        cookies = json.load(f)

    # Add cookies to the browser session
    for cookie in cookies:
        driver.add_cookie(cookie)

    # Refresh the page or navigate to a new page to apply the cookies
    driver.refresh()

    # Wait for a couple seconds to see if were redirected from the login page due to the cookies
    wait = WebDriverWait(driver, 2)
    element_after_login = wait.until(EC.url_contains("fwango.io/dashboard"))

# Function to manually login to fwango
# @exception_handler
def login(driver):
    print("Cookies failed; trying to log in manually")
    # Navigate to the login page
    login_url = "https://fwango.io/signin?r=/dashboard"  # Replace with your login page URL
    driver.get(login_url)

    # Wait for manual login up 5 minutes until the login redirects you to the dashboard
    wait = WebDriverWait(driver, int(5*60))
    # element_after_login = wait.until(EC.url_contains("fwango.io/dashboard"))

    email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, 'email'))
        )
    password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, 'password'))
        )

    email = "events@usaroundnet.org"
    password = "Ev3nt5upport!"
    email_input.send_keys(email)
    password_input.send_keys(password)

    # WebDriverWait(driver, int(5*60)).until(EC.url_contains("fwango.io/dashboard"))

    login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    login_button.click()


# Function to log into Fwango
# def login(driver):
#     # Set up the WebDriver
#     # driver = webdriver.Chrome()  # Using chrome
#     # wait = WebDriverWait(driver, 5) # Setting up the driver to wait until elements load up to 5 seconds
#     # Input your credentials
#     email = "events@usaroundnet.org"
#     password = "Ev3nt5upport!"
#     # Navigate to the login page
#     login_url = "https://fwango.io/signin?r=/dashboard"  # Replace with your login page URL
#     driver.get(login_url)
#     wait = WebDriverWait(driver, int(5*60))
#     # Use "name" attribute for locating elements
#     email_input = WebDriverWait(driver, 10).until(
#             EC.presence_of_element_located((By.NAME, 'email'))
#         )
#     password_input = WebDriverWait(driver, 10).until(
#             EC.presence_of_element_located((By.NAME, 'password'))
#         )
#     # Enter the email and password
#     email_input.send_keys(email)
#     password_input.send_keys(password)
#     time.sleep(3)
#     # Submit the login form
#     # login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")  # Replace with the actual name of the login button
#     # login_button.click()



# Loading page and waiting until ready
@exception_handler
def load_page(driver, wait, url):
    driver.get(url)
    # myElem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button[className='BaseButton-sc-1f7jfq6-0 LightButton-sc-1vjey5p-0 hlvvwe iSsvnO']")))
            
# Getting the tournament name
@exception_handler
def get_tournament_name(wait):
    # Find the h1 element with class "name"
    h1_element = wait.until(EC.presence_of_element_located((By.XPATH, "//h1[@class='name']")))
    # Get the text of the h1 element
    return h1_element.text.replace("|", "_")

# Function to get the address field from the webpage
@exception_handler
def get_address(driver):
    # Wait for the icon container with the map marker icon to be present
    wait = WebDriverWait(driver, 10)
    icon_container = wait.until(EC.presence_of_element_located((By.XPATH, '//div[@class="icon-container"]/i[@class="fas fa-map-marker-alt"]')))

    # Navigate to the parent div and get the text content of the adjacent div
    address_container = icon_container.find_element(By.XPATH, '../following-sibling::div')

    # Get the text content of the address div
    address_text = address_container.text.replace("Show map", "")

    # Returning the address
    return address_text

# Navigate to Pool Play / Group Stage on Fwango
@exception_handler
def click_pool_play(driver, wait):
    # Click Expand arrow
    buttons = driver.find_elements(By.CLASS_NAME, "IconButtonBase-sc-g1y1-0")
    buttons[0].click()
    
    # Find buttons on nav bar
    buttons = driver.find_elements(By.CLASS_NAME, "BaseButton-sc-1f7jfq6-0")
    
    # Find Pool Play button
    found = False
    for b in buttons:
        if b.text.lower().find("pool play") != -1 or b.text.lower().find("group stage") != -1:
            pool_button = b
            found = True
            break
    
    if found:
        pool_button.click()
    else:
        print("Error: Pool Play not found")

# Clicking the download button for games data
@exception_handler
def click_download_button_match_results(driver, wait):
    container = wait.until(EC.presence_of_element_located((By.ID, "tournament-main-container")))

    # Select Export dropdown menu
    download_button = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "BaseButton-sc-1f7jfq6-0")))
    download_button.click()

    # Select Match Results option
    match_results = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "DropdownMenu__MenuItem-sc-1rahj45-3")))
    match_results = driver.find_elements(By.CLASS_NAME, "DropdownMenu__MenuItem-sc-1rahj45-3")
    match_results[2].click()

    # Find Buttons that match "Export results" button
    results = driver.find_elements(By.CLASS_NAME, "SolidButton-sc-1b0q07k-0")
    while len(results) != 4:
        results = driver.find_elements(By.CLASS_NAME, "SolidButton-sc-1b0q07k-0")

    # Identify which is the "Export results button"
    for r in results:
        if r.text == "Export results":
            export_results = r
            break

    # Click button to download file
    driver.execute_script("arguments[0].click();", export_results)
    print("Downloading All Match Results Now")

# --------------------------------------------------------------------------------------------
# Getting all tournament URLs from Tourney List csv

urls = []
df = pd.read_csv('Tourney List.csv')
for tourney in df.iterrows():
    if tourney[1]["Scraped?"] == 'N':
        urls.append(tourney[1]["full URL"])

print("URLs: ", urls)

# -----
# Use to get specific tournaments
# for tourney in df.iterrows():
#     print(tourney)
#     if tourney[1]['Year'] == 2023 and tourney[1]['Type'] == "Challenger":
#         urls.append(tourney[1]["full URL"])
# -----

# print("URLs: ", urls)

# --------------------------------------------------
# Export Tounrament data

# manual list of URLs (for testing)
# urls = [ "https://fwango.io/nationals2024" , "https://fwango.io/chicago2024" ]


# Specify the path to your downloads folder
# downloads_folder = "/Users/coolk/Downloads"

# Specify the path where you want to save the downloaded CSV files
# destination_folder = "/Users/coolk/OneDrive/Documents/Roundnet/USAR rankings/rankings_model/Tourney Results/Manual Downloads"

# Set up the WebDriver

# if github actions:
if os.environ['GITHUB_RUN_NUMBER'] != 0:
    print("Using Github Actions Workflow ", os.environ['GITHUB_RUN_NUMBER'])
    chrome_service = Service() #os.environ['CHROMEWEBDRIVER'/chromedriver]) might also work
    chrome_options = Options()
    for option in ['--headless','--disable-gpu','--window-size=1920,1200','--ignore-certificate-errors','--disable-extensions','--no-sandbox','--disable-dev-shm-usage']:
        chrome_options.add_argument(option)
    driver = webdriver.Chrome(service = chrome_service,options = chrome_options)
else:
    print("Testing on local device")
    # driver = webdriver.Chrome()  # Using chrome

wait = WebDriverWait(driver, 5) # Setting up the driver to wait until elements load up to 5 seconds

# Trying to load the cookies from the last session to see if we can skip the manual login
try:
    try_logging_in_w_cookies(driver)
    print("Logged in?")
except:
    # Logging into fwango manually (email & password)
    login(driver)
    print("After log in attempt")

print("Logged In!?")
time.sleep(5)
print("Yes!")
# Save cookies
cookies = driver.get_cookies()
with open('cookies.json', 'w') as f:
    json.dump(cookies, f)

# Loop through each URL
completed = 0
collected_data = []
for url in urls:
    print(f"{completed+1}/{len(urls)} Trying to get data for {url}", end='\t')
    
    # Loading page and waiting until ready
    load_page(driver, wait, url)
    
    # Getting the tourney name
    tourney_name = get_tournament_name(wait)
    print("Tournament Name: ", tourney_name)
    
    # Accessing the address of this tournament
    # tournament_address = get_address(driver)
    
    # Navigate to pool play stage
    click_pool_play(driver, wait)
        
    # Click on the download button
    click_download_button_match_results(driver, wait)

    time.sleep(20)
