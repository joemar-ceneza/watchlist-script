from playwright.sync_api import sync_playwright
import time

# --- CONFIG ---
LEO_LOGIN_URL = "http://leo-a01.sbobet.com.tw:8088/Default.aspx"
WATCHLIST_LOGIN_URL = "http://insiderinew.leekie.com/login"
USERNAMES_FILE = "usernames.txt"

# Leo credentials
LEO_USERNAME = input("Username: ")
LEO_PASSWORD = input("Password: ")

# Watchlist credentials
WATCHLIST_USERNAME = input("Username: ")
WATCHLIST_PASSWORD = input("Password: ")

# --- Step 1: Read usernames from Notepad ---
with open(USERNAMES_FILE, "r") as f:
    usernames = [line.strip() for line in f if line.strip()]

print(f"Usernames loaded: {usernames}")

# --- Step 2: Login to LEO manually ---
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Open Chrome

    context = browser.new_context()
    leo_page = context.new_page()

    # Go to login page
    leo_page.goto(LEO_LOGIN_URL)

    # Fill login form and submit
    print("Logging in manually...")
    leo_page.fill("#txtUsername", LEO_USERNAME)
    leo_page.fill("#txtPassword", LEO_PASSWORD)
    leo_page.click("#btnLogin")
    leo_page.wait_for_load_state("networkidle")

    leo_page.wait_for_selector("frame[name='menu']")
    menu_frame = leo_page.frame(name="menu")
    contents_frame = leo_page.frame(name="contents")
    itop_frame = leo_page.frame(name="itop")
    icontents_frame = leo_page.frame(name="icontents")

    if not menu_frame:
        print("Frame not found — login may have failed")
        browser.close()
        exit()

    print("Frame loaded — login successful!")

    # --- Step 3: Loop through Players ---
    for username in usernames:
        print(f"\nSearching Player: {username}")

        # Search Player
        menu_frame.fill("#T1", "")
        menu_frame.fill("#T1", username)
        menu_frame.click(".Button")

        menu_frame.wait_for_timeout(1500)

        # --- Step 4: Scrape Data ---
        try:
            raw_text = contents_frame.locator(
                "//tr[th[contains(text(),'Outstanding Txn')]]/td/span"
            ).inner_text()
            text_only = raw_text.split()[0]
            print("Outstanding Txn Type:", text_only)

            sma = menu_frame.locator(
                "//tr[th[contains(text(),'SMA')]]/td/a"
            ).inner_text()
            print("SMA:", sma)
            master = menu_frame.locator(
                "//tr[th[contains(text(),'Master')]]/td/a"
            ).inner_text()
            print("Master:", master)
            agent = menu_frame.locator(
                "//tr[th[contains(text(),'Agent')]]/td/a"
            ).inner_text()
            print("Agent:", agent)

            menu_frame.click("#detail")
            itop_frame.click("#Setting")
            icontents_frame.click(".PSelectedLC")
            ma_comm = icontents_frame.locator("#LCTextMaComm").input_value()
            print("MA Commission", ma_comm)

        except:
            print("Player not found or data missing")
            continue

        # --- Step 5: Open watchlist website ---
        # watchlist_page = context.new_page()
        # watchlist_page.goto(WATCHLIST_LOGIN_URL)

        # # Fill login form and submit
        # print("Logging in manually...")
        # watchlist_page.fill("#username", WATCHLIST_USERNAME)
        # watchlist_page.fill("#password", WATCHLIST_PASSWORD)
        # watchlist_page.click("#btn-login")
        # watchlist_page.wait_for_load_state("networkidle")

        # # --- Step 6: Fill scraped data ---
        # watchlist_page.fill("#currency")
        # watchlist_page.fill("#agent")
        # watchlist_page.fill("#ma")
        # watchlist_page.fill("#sma")

        # watchlist_page.click("#submitBtn")

        # print("Data submitted to second website")

        # watchlist_page.close

    # Keep browser open to interact
    input("Press Enter to close browser...")
    browser.close()
