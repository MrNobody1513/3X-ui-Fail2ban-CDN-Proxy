# -----------------------------------------------------------------------------
# 3x-ui Fail2ban Manager
#
# A Python script to monitor Fail2ban logs, automatically disable/re-enable
# users in a 3x-ui panel, and send Telegram notifications.
#
# Author: MrNobody1513
# Version: 3.0
# -----------------------------------------------------------------------------

import os
import time
import requests
import json
import threading
from datetime import datetime
import urllib.parse
import sys
import getpass

# --- CONFIGURATION FILE HANDLING ---
CONFIG_FILE = 'config.json'

def create_config_wizard():
    """
    An interactive wizard to create the config.json file.
    """
    print("--- ⚙️ 3x-ui Fail2ban Manager Initial Setup by MrNobody1513 ---")
    print("Configuration file not found. Let's create one.")
    print("Please provide the following details. Press Enter to use the default value if available.\n")

    config = {}

    # Panel Details
    print("--- 1. 3x-ui Panel Details ---")
    config['PANEL_URL'] = input("Enter Panel URL (e.g., https://yourdomain.com:2083): ").strip()
    config['PANEL_PATH_SECRET'] = input("Enter Panel Secret Path (the part after the port): ").strip()
    config['USERNAME'] = input("Enter Panel Username: ").strip()
    # Use getpass for password to hide input
    config['PASSWORD'] = getpass.getpass("Enter Panel Password: ").strip()
    print("✅ Panel details saved.\n")

    # Log File Paths
    print("--- 2. Log File Paths ---")
    config['FAIL2BAN_LOG_PATH'] = input("Enter Fail2ban log path [Default: /var/log/fail2ban.log]: ").strip() or "/var/log/fail2ban.log"
    config['X_UI_ACCESS_LOG_PATH'] = input("Enter 3x-ui access log path [Default: /var/log/3xipl-ap.log]: ").strip() or "/var/log/3xipl-ap.log"
    print("✅ Log paths saved.\n")

    # Telegram Details
    print("--- 3. Telegram Notifications (Optional) ---")
    print("You can get these from BotFather on Telegram.")
    config['TELEGRAM_BOT_TOKEN'] = input("Enter Telegram Bot Token (leave empty to disable): ").strip()
    config['TELEGRAM_CHAT_ID'] = input("Enter your Telegram Chat ID (leave empty to disable): ").strip()
    print("✅ Telegram details saved.\n")

    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"🎉 Configuration successfully saved to '{CONFIG_FILE}'.")
        print("You can now run the script again to start the monitor.")
        return config
    except IOError as e:
        print(f"❌ CRITICAL ERROR: Could not write configuration to '{CONFIG_FILE}'.")
        print(f"Error details: {e}")
        return None

def load_config():
    """
    Loads configuration from config.json. If not found, runs the wizard.
    """
    if not os.path.exists(CONFIG_FILE):
        config = create_config_wizard()
        if config is None:
            sys.exit(1) # Exit if config creation failed
        # Exit after first-time setup to let the user review and restart
        print("Please restart the script to begin monitoring.")
        sys.exit(0)

    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

# --- Load Configuration ---
# All constants are now loaded from the config file
CONFIG = load_config()

# --- SCRIPT ---

def send_telegram_message(message):
    """Sends a message to a specific Telegram chat."""
    bot_token = CONFIG.get('TELEGRAM_BOT_TOKEN')
    chat_id = CONFIG.get('TELEGRAM_CHAT_ID')

    if not bot_token or not chat_id:
        print("[!] Telegram credentials not set in config.json. Skipping notification.")
        return
    
    # Add a branded footer to the message
    footer = "\n\n`--- Sent by 3x-ui Manager by MrNobody1513 ---`"
    full_message = message + footer

    encoded_message = urllib.parse.quote_plus(message)
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={encoded_message}&parse_mode=Markdown"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("[+] ✅ Telegram notification sent successfully.")
        else:
            print(f"[!] ❌ Failed to send Telegram notification. Status: {response.status_code}, Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"[!] ❌ Exception while sending Telegram notification: {e}")

class XUIApiClient:
    """A client to interact with the 3x-ui panel API."""
    def __init__(self, base_url, secret_path, username, password):
        self.base_api_url = f"{base_url}/{secret_path}/panel/api"
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/json'})
        self.session.verify = False
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
        self.inbounds_cache = None
        self.inbounds_cache_time = 0

    def login(self):
        login_url = f"{self.base_api_url.replace('/panel/api', '')}/login"
        payload = {'username': self.username, 'password': self.password}
        try:
            response = self.session.post(login_url, data=payload, timeout=10)
            if response.status_code == 200 and response.json().get('success'):
                print("[+] ✅ Successfully logged into 3x-ui panel.")
                return True
            else:
                print(f"[!] ❌ Failed to login. Status: {response.status_code}, Response: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"[!] ❌ Exception during login: {e}")
            return False

    def _get_inbounds(self):
        if time.time() - self.inbounds_cache_time < 60 and self.inbounds_cache:
            return self.inbounds_cache
        list_url = f"{self.base_api_url}/inbounds/list"
        try:
            response = self.session.get(list_url, timeout=10)
            if response.status_code == 200 and response.json().get('success'):
                self.inbounds_cache = response.json().get('obj', [])
                self.inbounds_cache_time = time.time()
                return self.inbounds_cache
            else:
                print(f"[!] ❌ Failed to get inbounds list. Status: {response.status_code}")
                # Try to re-login if session might have expired
                if response.status_code == 401:
                    print("[!] Session might be invalid. Attempting to re-login...")
                    self.login()
                return None
        except requests.exceptions.RequestException as e:
            print(f"[!] ❌ Exception while fetching inbounds: {e}")
            return None
    
    def find_client_by_email(self, email):
        inbounds = self._get_inbounds()
        if not inbounds:
            return None, None, None
        for inbound in inbounds:
            try:
                settings_str = inbound.get('settings', '{}')
                settings = json.loads(settings_str)
                clients = settings.get('clients', [])
                for client in clients:
                    if client.get('email') == email:
                        print(f"[*] 🕵️ Found client '{email}' in Inbound ID {inbound['id']} ('{inbound.get('remark', 'N/A')}')")
                        return inbound, client, inbound['id']
            except (json.JSONDecodeError, TypeError):
                continue
        print(f"[!] ⚠️ Client with email '{email}' not found in any inbound.")
        return None, None, None

    def _update_client_status(self, inbound_id, client_uuid, full_client_settings, enable=False):
        update_url = f"{self.base_api_url}/inbounds/updateClient/{client_uuid}"
        # Create a deep copy to avoid modifying the original client_data
        client_settings_copy = json.loads(json.dumps(full_client_settings))
        client_settings_copy["enable"] = enable
        
        settings_payload = {"clients": [client_settings_copy]}
        form_data = {'id': inbound_id, 'settings': json.dumps(settings_payload)}
        try:
            response = self.session.post(update_url, data=form_data, timeout=10)
            return response.status_code == 200 and response.json().get('success')
        except requests.exceptions.RequestException as e:
            print(f"[!] ❌ Exception during client status update: {e}")
            return False

    def _force_disconnect_all(self):
        disconnect_url = f"{self.base_api_url}/inbounds/onlines"
        try:
            print("[*] ⚡ Sending force-disconnect signal...")
            response = self.session.post(disconnect_url, timeout=10)
            if response.status_code == 200 and response.json().get('success'):
                print("[+] ✅ Force-disconnect signal sent successfully.")
                return True
            else:
                print(f"[!] ❌ Failed to send force-disconnect signal.")
                return False
        except requests.exceptions.RequestException as e:
            print(f"[!] ❌ Exception during force-disconnect: {e}")
            return False

    def disable_client(self, email):
        inbound_data, client_data, inbound_id = self.find_client_by_email(email)
        if not client_data:
            return None, None
        client_uuid = client_data.get('id')
        if not self._update_client_status(inbound_id, client_uuid, client_data, enable=False):
            return None, None
        print(f"[+] ✅ Successfully DISABLED client '{email}' in panel config.")
        self._force_disconnect_all()
        return client_data, inbound_data.get('remark', 'N/A')

    def enable_client(self, email):
        inbound_data, client_data, inbound_id = self.find_client_by_email(email)
        if not client_data:
            return None, None
        client_uuid = client_data.get('id')
        if self._update_client_status(inbound_id, client_uuid, client_data, enable=True):
            print(f"[+] ✅ Successfully RE-ENABLED client '{email}'.")
            return client_data, inbound_data.get('remark', 'N/A')
        return None, None

def find_email_for_ip_in_log(ip_address, log_file):
    print(f"[*] 🔎 Searching for IP '{ip_address}' in access log '{log_file}'...")
    try:
        with open(log_file, 'rb') as f:
            # Efficiently search from the end of the file
            f.seek(0, os.SEEK_END)
            position = f.tell()
            line = b''
            while position >= 0:
                f.seek(position)
                next_char = f.read(1)
                if next_char == b'\n':
                    decoded_line = line.decode('utf-8', errors='ignore').strip()
                    if ip_address in decoded_line and "accepted" in decoded_line:
                        parts = decoded_line.split()
                        try:
                            # The email is expected to be the last part, enclosed in brackets
                            email = parts[-1].strip('[]')
                            print(f"[+] ✅ Found email '{email}' for IP '{ip_address}'.")
                            return email
                        except IndexError: pass
                    line = b''
                else:
                    line = next_char + line
                position -= 1
    except FileNotFoundError:
        print(f"[!] ❌ ERROR: Access log file not found at '{log_file}'")
    except Exception as e:
        print(f"[!] ❌ An error occurred while reading the access log: {e}")

    print(f"[!] ⚠️ Could not find an email for IP '{ip_address}'.")
    return None

def monitor_log():
    log_path = CONFIG['FAIL2BAN_LOG_PATH']
    xui_log_path = CONFIG['X_UI_ACCESS_LOG_PATH']
    
    print("----------------------------------------------------------")
    print("      3x-ui Fail2ban Manager by MrNobody1513")
    print("----------------------------------------------------------")
    print(f"[*] 🛡️ Starting Fail2ban log monitor for '{log_path}'...")
    print("[*] ℹ️  Relying on Fail2ban for ban/unban timing.")
    processed_bans = set()
    banned_ip_to_email = {}  # To track {banned_ip: associated_email}

    api_client = XUIApiClient(
        CONFIG['PANEL_URL'],
        CONFIG['PANEL_PATH_SECRET'],
        CONFIG['USERNAME'],
        CONFIG['PASSWORD']
    )

    try:
        with open(log_path, 'r') as file:
            # Go to the end of the file
            file.seek(0, 2)
            while True:
                line = file.readline()
                if not line:
                    time.sleep(1)
                    continue

                timestamp_obj = datetime.now()
                timestamp_str = timestamp_obj.strftime('%Y-%m-%d %H:%M:%S')

                if "Ban" in line:
                    try:
                        ip_address = line.split()[-1]
                        log_entry = f"{timestamp_str}-{ip_address}"

                        if ip_address and log_entry not in processed_bans:
                            processed_bans.add(log_entry)
                            print(f"\n--- [ {timestamp_str} | BAN DETECTED ] ---")
                            print(f"[+] 🚫 Banned IP detected: {ip_address}")

                            email = find_email_for_ip_in_log(ip_address, xui_log_path)
                            if email:
                                # Store the mapping so we know who to unban later
                                banned_ip_to_email[ip_address] = email
                                print(f"[*] 🔗 Linking IP '{ip_address}' to user '{email}'.")
                                
                                if api_client.login():
                                    client_data, inbound_remark = api_client.disable_client(email)
                                    if client_data:
                                        message = (
                                            f"🚫 *User Banned by Fail2ban*\n\n"
                                            f"User `{email}` has been automatically disabled due to suspicious activity from IP `{ip_address}`.\n\n"
                                            f"• *User:* `{email}`\n"
                                            f"• *Inbound:* `{inbound_remark}`\n"
                                            f"• *Trigger IP:* `{ip_address}`\n"
                                            f"• *Status:* `DISABLED`\n"
                                            f"• *Time:* `{timestamp_str}`"
                                        )
                                        send_telegram_message(message)
                            print("-----------------------------------------")

                    except (IndexError, ValueError):
                        pass

                elif "Unban" in line:
                    try:
                        ip_address = line.split()[-1]
                        print(f"\n--- [ {timestamp_str} | UNBAN DETECTED ] ---")
                        print(f"[+] 🔓 Unbanned IP detected: {ip_address}")

                        # Check if we have a user associated with this unbanned IP
                        email_to_unban = banned_ip_to_email.pop(ip_address, None)

                        if email_to_unban:
                            print(f"[*] 🟢 Found associated user '{email_to_unban}' for IP '{ip_address}'. Re-enabling...")
                            if api_client.login():
                                client_data, inbound_remark = api_client.enable_client(email_to_unban)
                                if client_data:
                                    message = (
                                        f"✅ *User Re-enabled*\n\n"
                                        f"Fail2ban has unbanned IP `{ip_address}`. User `{email_to_unban}` is now re-enabled.\n\n"
                                        f"• *User:* `{email_to_unban}`\n"
                                        f"• *Inbound:* `{inbound_remark}`\n"
                                        f"• *Status:* `ENABLED`\n"
                                        f"• *Trigger IP:* `{ip_address}`\n"
                                        f"• *Time:* `{timestamp_str}`"
                                    )
                                    send_telegram_message(message)
                        else:
                            print(f"[*] ⚠️ Received unban for IP '{ip_address}', but no associated user was found in memory. Ignoring.")
                        print("-------------------------------------------")

                    except (IndexError, ValueError) as e:
                        print(f"[!] Error processing unban line: {e}")
                        pass

    except FileNotFoundError:
        print(f"[!] ❌ CRITICAL: Fail2ban log file not found at '{log_path}'. Exiting.")
        sys.exit(1) # Exit if log is not found
    except Exception as e:
        print(f"[!] ❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    try:
        monitor_log()
    except KeyboardInterrupt:
        print("\n[*] 👋 Exiting script gracefully. Goodbye!")
        sys.exit(0)