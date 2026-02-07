from playwright.sync_api import sync_playwright
import csv
from datetime import datetime, timedelta
from urllib.parse import quote_plus
import os, sys, uuid, hashlib, subprocess
from datetime import datetime, timezone
import time
import re

# Only force local browser path when running as EXE
if getattr(sys, "frozen", False):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "./ms-playwright"

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
today = datetime.today().date()

if os.path.exists(TRACK_FILE):
    last_run = datetime.strptime(open(TRACK_FILE, "r").read(), "%Y-%m-%d").date()
    if today < last_run:
        sys.exit()

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


# --- Add EXE-Safe Path Loader ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# --- CONFIG ---
LEO_LOGIN_URL = "http://leo-a01.sbobet.com.tw:8088/Default.aspx"
WATCHLIST_LOGIN_URL = "http://insiderinew.octagonexpress.co/login"
WATCHLIST_CURRENCY_RATE = "http://insiderinew.octagonexpress.co/getsearchexchangeRate?monthYear=2026-02&casino_type_id=2"

USERNAMES_FILE = resource_path("usernames.txt")
OUTPUT_CSV = resource_path("leo_results.csv")

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
    "Agent",
    "Master",
    "SMA",
    "Agent PT",
    "MA PT",
    "SMA PT",
    "Player Comm",
    "Agent Comm",
    "MA Comm",
    "SMA Comm",
    "Yesterday Comm",
    "7 Days Comm",
]

# --- Date format ---
yesterday = datetime.today() - timedelta(days=1)
formatted_date = yesterday.strftime("%d %b, %Y").lstrip("0")
encoded_date = quote_plus(formatted_date)

# --- Watchlist Date picker ---
from_date = yesterday.strftime("%m/%d/%Y")
to_date = today.strftime("%m/%d/%Y")


# --- Helper: Safely get frame even after reload ---
def get_frame(page, name, retries=20):
    for _ in range(retries):
        for frame in page.frames:
            if frame.name == name:
                return frame
        page.wait_for_timeout(300)
    return None


# --- Modular IP Scraper (Reusable Function) ---
def scrape_unique_ips(frame, account_id, max_ips=3):
    frame.fill("#txtAccountId", account_id)
    frame.locator("input.Button[value='Submit']").click()
    frame.wait_for_timeout(1000)
    frame.locator("input.Button[value='Submit']").click()
    frame.wait_for_timeout(500)
    frame.wait_for_selector("tbody tr", timeout=5000)

    unique_ips = []
    cells = frame.locator("tbody tr td:nth-child(5)")

    for i in range(cells.count()):
        ip = cells.nth(i).inner_text().strip()
        if ip.count(".") == 3 and ip not in unique_ips:
            unique_ips.append(ip)
        if len(unique_ips) >= max_ips:
            break
    return unique_ips


# --- Modular Watchlist IP Fill ---
def fill_ip_box(page, role, ip_list):
    value = "\n".join(ip_list) if ip_list else ""
    page.locator(f"textarea[name='ip_address[{role}]']").fill(value)


# --- Time Tracker ---
start_time = time.time()
script_start = time.time()

rows = []

# --- Step 1: Read usernames ---
with open(USERNAMES_FILE, "r") as f:
    usernames = [line.strip() for line in f if line.strip()]

total_players = len(usernames)

# --- Step 2: Login ---
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()

    # --- Log in LEO ---
    leo_page = context.new_page()
    leo_page.goto(LEO_LOGIN_URL)

    leo_page.fill("#txtUsername", LEO_USERNAME)
    leo_page.fill("#txtPassword", LEO_PASSWORD)
    leo_page.click("#btnLogin")

    leo_page.wait_for_load_state("networkidle")

    # --- Handle Failed Login Attempt Popup ---
    try:
        if leo_page.locator("#tblExchange").is_visible(timeout=3000):
            print("Login Warning Popup Detected — Clicking Continue...")
            leo_page.click("#continue")
            leo_page.wait_for_load_state("networkidle")
    except:
        pass

    print("===================================================================")
    print("Leo Website Login successful!")

    # --- Get menu frame safely ---
    menu_frame = get_frame(leo_page, "menu")

    if not menu_frame:
        print("Login may have failed")
        browser.close()
        exit()

    # --- Log in Watchlist ---
    watchlist_page = context.new_page()
    watchlist_page.goto(WATCHLIST_LOGIN_URL)

    watchlist_page.fill("#username", WATCHLIST_USERNAME)
    watchlist_page.fill("#password", WATCHLIST_PASSWORD)
    watchlist_page.click("#btn-login")

    watchlist_page.wait_for_load_state("networkidle")
    print("Watchlist Website Login successful!")
    watchlist_page.wait_for_selector("h2:has-text('Good Day')", timeout=5000)

    # --- Watchlist Currency Rate ---
    watchlist_currency = context.new_page()
    watchlist_currency.goto(WATCHLIST_CURRENCY_RATE)
    rates = {}
    rows_rate = watchlist_currency.locator("table.table tbody tr")

    for i in range(rows_rate.count()):
        row = rows_rate.nth(i)

        try:
            currency = row.locator("td").nth(0).inner_text().strip()
            rate = row.locator("input").get_attribute("value")

            if currency and rate:
                normalized_currency = currency_map.get(currency, currency)
                rates[normalized_currency] = float(rate)
        except:
            continue

    print("Watchlist Currency Rate Successfully Scraped")

    # --- Step 3: Loop Players ---
    for i, username in enumerate(usernames, start=1):
        user_start = time.time()

        print("===================================================================")
        print(f"[{i}/{total_players}] Searching: {username}")

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

            # --- Last Login IP Address ---
            ip_text = contents_frame.locator(
                "//tr[th[contains(text(),'Last Login IP')]]/td"
            ).inner_text()
            match = re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", ip_text)
            ip_address = match.group() if match else None

            # --- Currency ---
            raw_text = contents_frame.locator(
                "//tr[th[contains(text(),'Outstanding Txn')]]/td/span"
            ).inner_text()
            currency = raw_text.split()[0]
            currency = currency_map.get(currency, currency)
            exchange_rate = rates.get(currency, 1.0)

            # --- SMA / Master / Agent ---
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
            value = float(player_comm)
            player_comm = "0" if value == 0 else player_comm

            # --- Get Position Taking ---
            sma_pt = icontents_frame.locator("#LC1_SMA").input_value()
            ma_pt = icontents_frame.locator("#LC1_MA").input_value()
            agent_pt = icontents_frame.locator(
                "#LC1AgtPT option:checked"
            ).get_attribute("value")

            # --- Get banner frame ---
            top_frame = get_frame(leo_page, "banner")
            if not top_frame:
                print("contents frame missing")
                continue

            # --- Click Live Casino ---
            top_frame.wait_for_selector("a:has-text('Live Casino')")
            top_frame.click("a:has-text('Live Casino')")

            leo_page.wait_for_timeout(1200)

            # --- Click Login History ---
            itop_frame = get_frame(leo_page, "itop")
            itop_frame.wait_for_selector("a:has-text('Login History')", timeout=8000)
            itop_frame.click("a:has-text('Login History')")

            leo_page.wait_for_timeout(1200)

            # --- Checking the Date Picker ---
            icontents_frame = get_frame(leo_page, "icontents")
            icontents_frame.wait_for_selector("#dpFrom", timeout=5000)
            icontents_frame.wait_for_selector("#dpTo", timeout=5000)
            icontents_frame.evaluate(
                f"""
                const from = document.querySelector("#dpFrom");
                const to = document.querySelector("#dpTo");

                if (from && to) {{
                    from.value = "{from_date} 12:00:00 AM";
                    to.value = "{to_date} 12:00:00 AM";

                    from.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    from.dispatchEvent(new Event('change', {{ bubbles: true }}));

                    to.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    to.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            """
            )

            # --- Always get unique player IP Address ---
            unique_ip_player = scrape_unique_ips(icontents_frame, username)

            # --- Only get Agent/Master/SMA IPs if B2B ---
            unique_ip_agent = []
            unique_ip_master = []
            unique_ip_sma = []

            print("===================================================================")
            print("Player IPs:", unique_ip_player)

            if B2B_B2C == "B2B":
                # --- Get unique agent IP Address ---
                unique_ip_agent = scrape_unique_ips(icontents_frame, agent)
                # --- Get unique master IP Address ---
                unique_ip_master = scrape_unique_ips(icontents_frame, master)
                # --- Get unique sma IP Address ---
                unique_ip_sma = scrape_unique_ips(icontents_frame, sma)

                print("Agent IPs:", unique_ip_agent)
                print("Master IPs:", unique_ip_master)
                print("SMA IPs:", unique_ip_sma)

            # --- Click Statement ---
            menu_frame.click("#stmt")
            contents_frame.wait_for_selector("#tblExchange")
            contents_frame.locator("#showCols").check()

            # --- Get Yesterday and 7 Days Commission ---
            yesterday_date = (
                yesterday.date() if hasattr(yesterday, "date") else yesterday
            )

            start_7_days = yesterday_date - timedelta(days=7)
            end_7_days = yesterday_date - timedelta(days=1)

            table_rows = contents_frame.locator("#tblExchange tbody tr:not(#totalRow)")

            yesterday_commission = 0.0
            last_7_days_commission = 0.0

            for i in range(table_rows.count()):
                row = table_rows.nth(i)

                try:
                    date_text = row.locator("td").nth(1).inner_text().strip()
                    product_text = row.locator("td").nth(3).inner_text().strip()
                    comm_text = (
                        row.locator("td[name='commission']").inner_text().strip()
                    )
                except:
                    continue

                # --- Filter product ---
                if "Live Casino & Casino Games" not in product_text:
                    continue

                # --- Parse date ---
                try:
                    row_date = datetime.strptime(date_text, "%m/%d/%Y").date()
                except:
                    continue

                # --- Parse commission ---
                if not comm_text:
                    continue

                try:
                    comm_value = float(comm_text.replace(",", ""))
                except:
                    continue

                # --- Yesterday ONLY ---
                if row_date == yesterday_date:
                    yesterday_commission += comm_value

                # --- Last 7 days excluding yesterday ---
                elif start_7_days <= row_date <= end_7_days:
                    last_7_days_commission += comm_value

            converted_yesterday = yesterday_commission / exchange_rate
            converted_last_7_days = last_7_days_commission / exchange_rate

            print("===================================================================")
            print(f"Currency: {currency}")
            print(f"Exchange Rate: {exchange_rate}")
            print(f"Yesterday Commission: {converted_yesterday:,.2f}")
            print(f"Last 7 Days Commission: {converted_last_7_days:,.2f}")

            print("===================================================================")
            print(f"Successfully scraped data for username: {username}")

            # --- Save row ---
            rows.append(
                [
                    username,
                    currency,
                    agent,
                    sma,
                    master,
                    agent_pt,
                    ma_pt,
                    sma_pt,
                    player_comm,
                    agent_comm,
                    ma_comm,
                    sma_comm,
                    f"{converted_yesterday:.2f}",
                    f"{converted_last_7_days:.2f}",
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
            # --- Currency ---
            watchlist_page.locator("select[name='currency']").select_option(
                value=currency
            )

            # --- AGENT/MASTER/SMA ---
            watchlist_page.fill("#agent", agent)
            watchlist_page.fill("#ma", master)
            watchlist_page.fill("#sma", sma)

            # --- Total Commission ---
            watchlist_page.fill("#current_comm", f"{converted_yesterday:.2f}")
            watchlist_page.fill("#last_seven_comm", f"{converted_last_7_days:.2f}")

            # --- Player Taking Percentage ---
            watchlist_page.locator("input[name='pt[player]']").fill("0")
            watchlist_page.locator("input[name='pt[agent]']").fill(agent_pt)
            watchlist_page.locator("input[name='pt[ma]']").fill(ma_pt)
            watchlist_page.locator("input[name='pt[sma]']").fill(sma_pt)

            # --- Players Commission ---
            watchlist_page.locator("input[name='comm[player]']").fill(player_comm)
            watchlist_page.locator("input[name='comm[agent]']").fill(agent_comm)
            watchlist_page.locator("input[name='comm[ma]']").fill(ma_comm)
            watchlist_page.locator("input[name='comm[sma]']").fill(sma_comm)

            # --- Conclusion ---
            watchlist_page.fill("#remarks", "None")
            watchlist_page.fill("#crm_log", "None")

            # --- Check if unique_ip_player list is empty ---
            if unique_ip_player and len(unique_ip_player) > 0:
                ip_player = "\n".join(unique_ip_player)
            else:
                ip_player = ip_address if ip_address else ""

            watchlist_page.locator("textarea[name='ip_address[player]']").fill(
                ip_player
            )

            # --- Only fill Agent/Master/SMA if B2B ---
            if B2B_B2C == "B2B":
                # --- Agent IP ---
                fill_ip_box(watchlist_page, "agent", unique_ip_agent)
                # --- Master IP ---
                fill_ip_box(watchlist_page, "ma", unique_ip_master)
                # --- SMA IP ---
                fill_ip_box(watchlist_page, "sma", unique_ip_sma)

            # --- Step 5: Update the record ---
            watchlist_page.locator("button:has-text('Update Record')").click()

            # --- Time track per user ---
            user_elapsed = time.time() - user_start
            if user_elapsed < 60:
                print(
                    "==================================================================="
                )
                print(f"Watchlist updated for {username}, Time: {user_elapsed:.1f} sec")
            else:
                print(
                    "==================================================================="
                )
                print(
                    f"Watchlist updated for {username}, Time: {user_elapsed/60:.2f} mins"
                )
        except Exception as e:
            print(f"Error for {username}:", e)
            rows.append([username, "ERROR"] + [""] * (len(headers) - 2))

    # --- Save CSV ---
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    total_time = time.time() - script_start
    avg_per_player = total_time / total_players if total_players else 0
    print("===================================================================")
    print(f"Script finished in {total_time / 60:.2f} minutes")
    print(f"Avg/player: {avg_per_player:.2f} seconds")
    print("===================================================================")
    print(f"CSV saved as: {OUTPUT_CSV}")
    print("===================================================================")

    input("Press Enter to close browser...")
    browser.close()
