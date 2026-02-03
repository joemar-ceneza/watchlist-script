from playwright.sync_api import sync_playwright
import csv
from datetime import datetime, timedelta
from urllib.parse import quote_plus
import os, sys, uuid, hashlib, subprocess
from datetime import datetime, timezone

# --- Secure Storage Path ---
local_appdata = os.getenv("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
BASE_DIR = os.path.join(local_appdata, "SystemCache")
os.makedirs(BASE_DIR, exist_ok=True)

DEVICE_FILE = os.path.join(BASE_DIR, "sys.lock")
TRACK_FILE = os.path.join(BASE_DIR, "sys.time")

# --- Settings ---
EXPIRY_DATE = "2026-03-01"

# --- Machine Lock ---
device_id = hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()

if os.path.exists(DEVICE_FILE):
    saved_id = open(DEVICE_FILE, "r").read()
    if saved_id != device_id:
        sys.exit()
else:
    open(DEVICE_FILE, "w").write(device_id)

# --- Anti Clock-Tampering (UTC Safe) ---
today = datetime.now(timezone.utc).date()

if os.path.exists(TRACK_FILE):
    last_run = datetime.strptime(open(TRACK_FILE, "r").read(), "%Y-%m-%d").date()
    if today < last_run:
        sys.exit()  # Time rollback detected

open(TRACK_FILE, "w").write(str(today))

# --- Expiry Check ---
expiry = datetime.strptime(EXPIRY_DATE, "%Y-%m-%d").date()

if today >= expiry:
    exe_path = os.path.abspath(sys.argv[0])
    delete_cmd = f'cmd /c timeout 2 > nul & del "{exe_path}"'

    try:
        subprocess.Popen(delete_cmd, shell=True)
        if os.path.exists(DEVICE_FILE):
            os.remove(DEVICE_FILE)
        if os.path.exists(TRACK_FILE):
            os.remove(TRACK_FILE)
    except:
        pass

    sys.exit()

# --- CONFIG ---
LEO_LOGIN_URL = "http://leo-a01.sbobet.com.tw:8088/Default.aspx"
WATCHLIST_LOGIN_URL = "http://insiderinew.octagonexpress.co/login"

USERNAMES_FILE = "usernames.txt"
OUTPUT_CSV = "leo_results.csv"

# --- B2B OR B2C ---
while True:
    B2B_B2C = input("Enter business type (B2B or B2C): ").strip().upper()
    if B2B_B2C in ["B2B", "B2C"]:
        break
    print("Invalid input. Please enter only B2B or B2C.")

# --- Leo credentials ---
LEO_USERNAME = input("LEO Username: ")
LEO_PASSWORD = input("LEO Password: ")

# --- Watchlist credentials ---
WATCHLIST_USERNAME = input("WATCHLIST Username: ")
WATCHLIST_PASSWORD = input("WATCHLIST Password: ")

# --- Normalize currency codes ---
currency_map = {"Pp": "IDR", "TB": "THB"}

headers = [
    "Username",
    "Currency",
    "SMA",
    "Master",
    "Agent",
    "Agent Position Taking",
    "MA Position Taking",
    "SMA Position Taking",
    "Player Commission",
    "Agent Commission",
    "MA Commission",
    "SMA Commission",
]

# --- Date format ---
yesterday = datetime.today() - timedelta(days=1)
formatted_date = yesterday.strftime("%d %b, %Y").lstrip("0")
encoded_date = quote_plus(formatted_date)


# --- Helper: Safely get frame even after reload ---
def get_frame(page, name, retries=20):
    for _ in range(retries):
        for frame in page.frames:
            if frame.name == name:
                return frame
        page.wait_for_timeout(300)
    return None


rows = []

# --- Step 1: Read usernames ---
with open(USERNAMES_FILE, "r") as f:
    usernames = [line.strip() for line in f if line.strip()]

# --- Step 2: Login ---
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()

    # --- Log in LEO ---
    leo_page = context.new_page()
    leo_page.goto(LEO_LOGIN_URL)

    leo_page.fill("#txtUsername", LEO_USERNAME)
    leo_page.fill("#txtPassword", LEO_PASSWORD)
    leo_page.click("#btnLogin")

    leo_page.wait_for_load_state("networkidle")

    # --- Get menu frame safely ---
    menu_frame = get_frame(leo_page, "menu")

    if not menu_frame:
        print("Login may have failed")
        browser.close()
        exit()

    print("Leo Website Login successful!")

    # --- Log in Watchlist ---
    watchlist_page = context.new_page()
    watchlist_page.goto(WATCHLIST_LOGIN_URL)

    watchlist_page.fill("#username", WATCHLIST_USERNAME)
    watchlist_page.fill("#password", WATCHLIST_PASSWORD)
    watchlist_page.click("#btn-login")

    watchlist_page.wait_for_load_state("networkidle")
    print("Watchlist Website Login successful!")

    # --- Step 3: Loop Players ---
    for username in usernames:
        print(f"\nSearching Player: {username}")

        try:
            # --- Refresh menu frame every loop ---
            menu_frame = get_frame(leo_page, "menu")

            # --- Search Player ---
            menu_frame.fill("#T1", username)
            menu_frame.click(".Button")

            leo_page.wait_for_timeout(1200)

            # --- Get contents frame ---
            contents_frame = get_frame(leo_page, "contents")

            if not contents_frame:
                print("contents frame missing")
                continue

            # --- Currency ---
            raw_text = contents_frame.locator(
                "//tr[th[contains(text(),'Outstanding Txn')]]/td/span"
            ).inner_text()
            currency = raw_text.split()[0]
            currency = currency_map.get(currency, currency)

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

            # --- Get Position Taking ---
            sma_pt = icontents_frame.locator("#LC1_SMA").input_value()
            ma_pt = icontents_frame.locator("#LC1_MA").input_value()
            agent_pt = icontents_frame.locator(
                "#LC1AgtPT option:checked"
            ).get_attribute("value")

            print(f"Successfully scraped data for username: {username}")
            # --- Save row ---
            rows.append(
                [
                    username,
                    currency,
                    sma,
                    master,
                    agent,
                    agent_pt,
                    ma_pt,
                    sma_pt,
                    player_comm,
                    agent_comm,
                    ma_comm,
                    sma_comm,
                ]
            )

            # --- Step 4: Watchlist Update ---
            watchlist_url = (
                f"http://insiderinew.octagonexpress.co/getsearchplayerWatchlistSGD2"
                f"?business_type={B2B_B2C}&date={encoded_date}"
            )
            watchlist_page.goto(watchlist_url)
            watchlist_page.wait_for_selector("tr.border-b")

            # --- Find Edit and Click ---
            edit_btn = watchlist_page.locator(
                f"tr:has(td:has-text('{username}')) a:has-text('Edit')"
            )
            if edit_btn.count() == 0:
                print(f"Player not found in Watchlist: {username}")
                continue
            edit_btn.click()

            # --- Fill the form ---
            # Currency
            watchlist_page.locator("select[name='currency']").select_option(
                value=currency
            )

            # AGENT/MASTER/SMA
            watchlist_page.fill("#agent", agent)
            watchlist_page.fill("#ma", master)
            watchlist_page.fill("#sma", sma)

            # Total Commission
            watchlist_page.fill("#current_comm", "0")
            watchlist_page.fill("#last_seven_comm", "0")

            # Player Taking Percentage
            watchlist_page.locator("input[name='pt[player]']").fill("0")
            watchlist_page.locator("input[name='pt[agent]']").fill(agent_pt)
            watchlist_page.locator("input[name='pt[ma]']").fill(ma_pt)
            watchlist_page.locator("input[name='pt[sma]']").fill(sma_pt)

            # Players Commission
            watchlist_page.locator("input[name='comm[player]']").fill(player_comm)
            watchlist_page.locator("input[name='comm[agent]']").fill(agent_comm)
            watchlist_page.locator("input[name='comm[ma]']").fill(ma_comm)
            watchlist_page.locator("input[name='comm[sma]']").fill(sma_comm)

            # Conclusion
            watchlist_page.fill("#remarks", "None")
            watchlist_page.fill("#crm_log", "None")

            # Step 5: Update the record
            watchlist_page.locator("button:has-text('Update Record')").click()

            print(f"Watchlist updated for {username}")

        except Exception as e:
            print("Error for {username}:", e)
            rows.append([username, "ERROR"] + [""] * (len(headers) - 2))

    # --- Save CSV ---
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"\nCSV saved as: {OUTPUT_CSV}")

    input("Press Enter to close browser...")
    browser.close()
