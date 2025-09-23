# 3x-ui Fail2ban Manager

[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/YOUR-USERNAME/3x-ui-fail2ban-manager/blob/main/LICENSE)
[![Version](https://img.shields.io/badge/version-3.0-blue)](https://github.com/YOUR-USERNAME/3x-ui-fail2ban-manager)
[![Python Version](https://img.shields.io/badge/python-3.6%2B-brightgreen)](https://www.python.org/)

An automated tool to integrate Fail2ban with 3x-ui panels, automatically disabling users upon suspicious activity and sending real-time Telegram notifications.

This project is designed to manage concurrent user connections on a 3x-ui panel, specifically for scenarios where the inbound traffic is proxied through a CDN. In this setup, user requests reach the server via CDN IP addresses, rendering Fail2ban ineffective on its own for limiting individual users. This script bridges that gap by linking the banned IP to the correct user.

---

## ✨ Key Features

- **Automated User Management**: Automatically disables a user in the 3x-ui panel when their IP is banned by Fail2ban.
- **Auto Re-enable**: Automatically re-enables the user once Fail2ban unbans their IP.
- **Telegram Notifications**: Sends detailed, real-time notifications for both ban and unban events.
- **Easy Setup Wizard**: An interactive command-line wizard for initial configuration (`config.json`). No manual file editing is required!
- **Systemd Service Installer**: Includes a user-friendly `systemd.sh` script to run the monitor as a persistent background service after successful testing.
- **Smart Log Parsing**: Intelligently searches 3x-ui access logs to link a banned IP address to a user's email.
- **Secure by Default**: Uses `getpass` to hide sensitive password input during the setup process.

## 🚀 Installation & Setup

The setup process is divided into two main parts: initial configuration and testing, followed by installation as a permanent service.

### Prerequisites
- A Linux server with `systemd` and root access.
- Python 3.6 or higher.
- `requests` library for Python. If not installed, run: `pip3 install requests`.
- `Fail2ban` installed and configured.
- `3x-ui` panel installed.

Step 1: Clone and Configure

First, we will configure the script and test it manually to ensure everything works correctly.

Clone the repository :
    Log in to your server via SSH and clone this repository.
```
git clone https://github.com/MrNobody1513/3x-ui-fail2ban-manager.git
```
```
cd UserLimit
```
Run the script for the first time (as a regular user):This will trigger the interactive configuration wizard.

        

```
python3 UserLimit-V3.py
```

Follow the setup wizard:

The script will detect that config.json is missing and will ask for the following information:
  3x-ui Panel URL, Secret Path, Username, and Password.
  Paths to your Fail2ban and 3x-ui access logs (defaults are provided).
  Your Telegram Bot Token and Chat ID (optional).

After you provide the details, the config.json file will be created, and the script will exit.


Step 2: Test the Script

Now that the configuration is saved, run the script again to test its functionality.

Run the monitor manually:

```
python3 UserLimit-V3.py
```

The script will now start monitoring the log files. You should see a "Starting Fail2ban log monitor..." message.

Verify its operation:

Keep the script running and trigger a ban event with Fail2ban (e.g., by making several failed SSH login attempts from a test device). Check the script’s output to see if it detects the ban, finds the user, disables them, and sends a Telegram notification.

Stop the manual test:

Once you are confident that the script is working correctly, press Ctrl+C to stop it.


Step 3: Install as a Systemd Service

After successful testing, you can now install the script as a permanent background service that starts automatically on boot.

Make the installer executable:

```
chmod +x systemd.sh
```

Run the installer script with sudo:This script will create and enable the systemd service file for you.

```
sudo ./systemd.sh
```

The installer will handle everything: creating the service file, reloading the systemd daemon, and starting the service.

🎉 Installation is complete! The monitor is now running permanently in the background.
🛠️ Service Management

Once installed as a service, you can manage it using standard systemctl commands.

Check Service Status:

```
  sudo systemctl status UserLimit-V3.service
```

View Live Logs:This is the best way to see the monitor in action and check for any issues.

```
  sudo journalctl -u UserLimit-V3.service -f
```

Stop the Service:

```
  sudo systemctl stop UserLimit-V3.service
```

Start the Service:

```
  sudo systemctl start UserLimit-V3.service
```
