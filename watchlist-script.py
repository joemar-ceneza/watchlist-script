from playwright.sync_api import sync_playwright

# --- CONFIG ---
LEO_LOGIN_URL = "http://leo-a01.sbobet.com.tw:8088/Default.aspx"
# WATCHLIST_LOGIN_URL = "http://insiderinew.leekie.com/login"
USERNAMES_FILE = "usernames.txt"

# Leo credentials
LEO_USERNAME = input("LEO Username: ")
LEO_PASSWORD = input("LEO Password: ")

# Watchlist credentials
# WATCHLIST_USERNAME = input("Watchlist Username: ")
# WATCHLIST_PASSWORD = input("Watchlist Password: ")

# --- Step 1: Read usernames from Notepad ---
with open(USERNAMES_FILE, "r") as f:
    usernames = [line.strip() for line in f if line.strip()]

print(f"Usernames loaded: {usernames}")

# --- Step 2: Login to LEO manually ---
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

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

    if not menu_frame:
        print("Login may have failed")
        browser.close()
        exit()

    print("Login successful!")

    # --- Step 3: Loop through Players ---
    for username in usernames:
        print(f"\nSearching Player: {username}")

        try:
            # --- Search Player ---
            menu_frame.fill("#T1", "")
            menu_frame.fill("#T1", username)
            menu_frame.click(".Button")

            menu_frame.wait_for_timeout(1500)

            # --- Step 4: Scrape Data ---
            raw_text = menu_frame.locator(
                "//tr[th[contains(text(),'Outstanding Txn')]]/td/span"
            ).inner_text()
            text_only = raw_text.split()[0]
            print("Currency:", text_only)

            # --- Scrape SMA / MASTER / AGENT ---
            sma = menu_frame.locator(
                "//tr[th[contains(text(),'SMA')]]/td/a"
            ).inner_text()
            master = menu_frame.locator(
                "//tr[th[contains(text(),'Master')]]/td/a"
            ).inner_text()
            agent = menu_frame.locator(
                "//tr[th[contains(text(),'Agent')]]/td/a"
            ).inner_text()

            print("SMA:", sma)
            print("Master:", master)
            print("Agent:", agent)

            # --- Click Detail ---
            menu_frame.click("#detail")

            # --- Get contents frame ---
            leo_page.wait_for_selector("frame[name='contents']")
            contents_frame = leo_page.frame(name="contents")

            # --- Get itop frame ---
            itop_frame = None
            for frame in contents_frame.child_frames:
                if frame.name == "itop":
                    itop_frame = frame

            if not itop_frame:
                print("itop frame missing")
                continue

            # --- Click setting ---
            itop_frame.wait_for_selector("#Setting")
            itop_frame.click("#Setting", force=True)

            # --- Get icontents frame ---
            icontents_frame = None
            for frame in contents_frame.child_frames:
                if frame.name == "icontents":
                    icontents_frame = frame

            if not icontents_frame:
                print("icontents frame missing")
                continue

            # --- Open commision Tab ---
            icontents_frame.click(".PSelectedLC")

            # --- Get MA commission ---
            ma_comm = icontents_frame.locator("#LCTextMaComm").input_value()
            print("MA Commission:", ma_comm)

        except Exception as e:
            print("Error for player:", username)
            print("Reason:", e)
            continue

    # Keep browser open to interact
    input("Press Enter to close browser...")
    browser.close()
