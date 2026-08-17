from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

# --- CONFIG ---
LINKEDIN_EMAIL = "your_email@example.com"  # Replace with your LinkedIn email
LINKEDIN_PASSWORD = "your_password"        # Replace with your LinkedIn password
NOTION_EMAIL = "your_email@example.com"    # Replace with your Notion email
NOTION_PASSWORD = "your_password"          # Replace with your Notion password

# --- SETUP ---
def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def linkedin_login_and_like(driver, person_name):
    driver.get("https://www.linkedin.com/login")
    time.sleep(2)
    driver.find_element(By.ID, "username").send_keys(LINKEDIN_EMAIL)
    driver.find_element(By.ID, "password").send_keys(LINKEDIN_PASSWORD)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    time.sleep(3)
    # Search for the person
    search_box = driver.find_element(By.XPATH, "//input[@placeholder='Search']")
    search_box.send_keys(person_name)
    search_box.send_keys(Keys.RETURN)
    time.sleep(3)
    # Click on the first profile
    profiles = driver.find_elements(By.XPATH, "//a[contains(@href, '/in/')]")
    if profiles:
        profiles[0].click()
        time.sleep(3)
        # Scroll and like the latest post (if available)
        like_buttons = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Like')]")
        if like_buttons:
            like_buttons[0].click()
            print(f"Liked the latest post from {person_name}!")
        else:
            print("No like button found on the latest post.")
    else:
        print("No profile found for", person_name)

def notion_login_and_create_page(driver):
    driver.get("https://www.notion.so/login")
    time.sleep(2)
    driver.find_element(By.NAME, "email").send_keys(NOTION_EMAIL)
    driver.find_element(By.XPATH, "//button[contains(text(), 'Continue with email')]").click()
    time.sleep(2)
    driver.find_element(By.NAME, "password").send_keys(NOTION_PASSWORD)
    driver.find_element(By.XPATH, "//button[contains(text(), 'Continue with password')]").click()
    time.sleep(5)
    # Create a new page
    driver.get("https://www.notion.so/")
    time.sleep(3)
    driver.find_element(By.XPATH, "//div[text()='Add a page']").click()
    time.sleep(2)
    page_title = driver.switch_to.active_element
    page_title.send_keys("Automated Page by AI")
    page_title.send_keys(Keys.RETURN)
    print("Created a new Notion page!")

if __name__ == "__main__":
    driver = get_driver()
    try:
        linkedin_login_and_like(driver, "XYZ")
        notion_login_and_create_page(driver)
    finally:
        driver.quit()
