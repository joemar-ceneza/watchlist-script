from playwright.sync_api import sync_playwright

# --- CONFIG ---
LEO_LOGIN_URL = "https://the-internet.herokuapp.com/login"
USERNAMES_FILE = "usernames.txt"

LEO_USERNAME = "tomsmith"
LEO_PASSWORD = "SuperSecretPassword!"

LEO_STORAGE = "leo_storage.json"

# --- Step 1: Read usernames from Notepad ---
with open(USERNAMES_FILE, "r") as f:
    usernames = [line.strip() for line in f if line.strip()]

print(f"Usernames loaded: {usernames}")

# --- Step 2: Login to LEO ---
with sync_playwright() as p:
    # Launch browser
    browser = p.chromium.launch(headless=False)

    try:
        leo_context = browser.new_context(storage_state=LEO_STORAGE)
        print("LEO session loaded from storage.")
    except:
        leo_context = browser.new_context()
        print("No valid storage found, will login manually.")

    leo_page = leo_context.new_page()
    leo_page.goto(LEO_LOGIN_URL)

    # Check if login is required
    if "login" in leo_page.url:
        print("Logging in manually...")
        leo_page.fill("#username", LEO_USERNAME)
        leo_page.fill("#password", LEO_PASSWORD)
        leo_page.click(".radius")
        leo_page.wait_for_load_state("networkidle")
        # Save storage for next run
        leo_context.storage_state(path=LEO_STORAGE)
        print("LEO login saved for future sessions.")
    else:
        print("Already logged in!")

    input("Press Enter to close browser...")
    browser.close()
