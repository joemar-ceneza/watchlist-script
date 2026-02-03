from playwright.sync_api import sync_playwright

# --- CONFIG ---
LEO_LOGIN_URL = "http://leo-a01.sbobet.com.tw:8088/Default.aspx"
USERNAMES_FILE = "usernames.txt"

# Leo credentials
LEO_USERNAME = input("LEO Username: ")
LEO_PASSWORD = input("LEO Password: ")


# --- Helper: Safely get frame even after reload ---
def get_frame(page, name, retries=20):
    for _ in range(retries):
        for frame in page.frames:
            if frame.name == name:
                return frame
        page.wait_for_timeout(300)
    return None


# --- Step 1: Read usernames ---
with open(USERNAMES_FILE, "r") as f:
    usernames = [line.strip() for line in f if line.strip()]

print(f"Usernames loaded: {usernames}")

# --- Step 2: Login ---
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    leo_page = context.new_page()

    leo_page.goto(LEO_LOGIN_URL)

    print("Logging in manually...")
    leo_page.fill("#txtUsername", LEO_USERNAME)
    leo_page.fill("#txtPassword", LEO_PASSWORD)
    leo_page.click("#btnLogin")

    leo_page.wait_for_load_state("networkidle")

    # Get menu frame safely
    menu_frame = get_frame(leo_page, "menu")

    if not menu_frame:
        print("Login may have failed")
        browser.close()
        exit()

    print("Login successful!")

    # --- Step 3: Loop Players ---
    for username in usernames:
        print(f"\nSearching Player: {username}")

        try:
            # Refresh menu frame every loop
            menu_frame = get_frame(leo_page, "menu")

            # --- Search Player ---
            menu_frame.fill("#T1", "")
            menu_frame.fill("#T1", username)
            menu_frame.click(".Button")

            leo_page.wait_for_timeout(1200)

            # --- Get contents frame ---
            contents_frame = get_frame(leo_page, "contents")

            if not contents_frame:
                print("contents frame missing")
                continue

            # --- Scrape Outstanding Txn ---
            raw_text = contents_frame.locator(
                "//tr[th[contains(text(),'Outstanding Txn')]]/td/span"
            ).inner_text()
            text_only = raw_text.split()[0]
            print("Currency:", text_only)

            # --- SMA / MASTER / AGENT ---
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
            leo_page.wait_for_timeout(1200)

            # --- Get itop frame ---
            itop_frame = get_frame(leo_page, "itop")

            if not itop_frame:
                print("itop frame not found")
                continue

            itop_frame.wait_for_selector("#Setting", timeout=5000)
            itop_frame.click("#Setting")

            leo_page.wait_for_timeout(1200)

            # --- Get icontents frame ---
            icontents_frame = get_frame(leo_page, "icontents")

            if not icontents_frame:
                print("icontents frame missing")
                continue

            # --- Click Live Casino & Casino Games ---
            icontents_frame.wait_for_selector(
                "td:has-text('Live Casino & Casino Games')", timeout=5000
            )
            icontents_frame.click("td:has-text('Live Casino & Casino Games')")

            leo_page.wait_for_timeout(800)

            # --- Get Commission ---
            sma_comm = icontents_frame.locator("#LCTextSmaComm").input_value()
            ma_comm = icontents_frame.locator("#LCTextMaComm").input_value()
            agent_comm = icontents_frame.locator("#LCTextAgtComm").input_value()
            player_comm = icontents_frame.locator("#LCTextPlayerComm").input_value()

            print("SMA Commission:", sma_comm)
            print("MA Commission:", ma_comm)
            print("AGENT Commission:", agent_comm)
            print("PLAYER Commission:", player_comm)

            # --- Get Position Taking ---
            sma_pt = icontents_frame.locator("#LC1_SMA").input_value()
            ma_pt = icontents_frame.locator("#LC1_MA").input_value()
            agent_pt = icontents_frame.locator(
                "#LC1AgtPT option:checked"
            ).get_attribute("value")

            print("SMA Position Taking:", sma_pt)
            print("MA Position Taking:", ma_pt)
            print("Agent Position Taking:", agent_pt)

        except Exception as e:
            print("Error for player:", username)
            print("Reason:", e)
            continue

    input("Press Enter to close browser...")
    browser.close()
