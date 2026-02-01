from playwright.sync_api import sync_playwright

# --- CONFIG ---
LEO_LOGIN_URL = "https://the-internet.herokuapp.com/login"
USERNAMES_FILE = "usernames.txt"

LEO_USERNAME = "tomsmith"
LEO_PASSWORD = "SuperSecretPassword!"

# --- Step 1: Read usernames from Notepad ---
with open(USERNAMES_FILE, "r") as f:
    usernames = [line.strip() for line in f if line.strip()]

print(f"Usernames loaded: {usernames}")

# --- Step 2: Login to LEO manually ---
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Open Chrome

    context = browser.new_context()
    page = context.new_page()

    # Go to login page
    page.goto(LEO_LOGIN_URL)

    # Fill login form and submit
    print("Logging in manually...")
    page.fill("#username", LEO_USERNAME)
    page.fill("#password", LEO_PASSWORD)
    page.click(".radius")
    page.wait_for_load_state("networkidle")

    print("Login completed!")

    # Keep browser open to interact
    input("Press Enter to close browser...")
    browser.close()
