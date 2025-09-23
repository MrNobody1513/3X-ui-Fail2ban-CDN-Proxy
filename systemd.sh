    #!/bin/bash

    # setup.sh - A script to install the UserLimit-V3 monitor as a systemd service.

    # --- Style Definitions ---
    BOLD=$(tput bold)
    BLUE=$(tput setaf 4)
    GREEN=$(tput setaf 2)
    RED=$(tput setaf 1)
    NC=$(tput sgr0) # No Color

    echo "${BLUE}${BOLD}--- 3x-ui UserLimit-V3 Service Installer ---${NC}"
    echo

    # --- Pre-check: Must be run as root ---
    if [ "$(id -u)" -ne 0 ]; then
        echo "${RED}❌ This script must be run as root. Please use 'sudo ./setup.sh'${NC}"
        exit 1
    fi

    # --- Configuration ---
    DEFAULT_SERVICE_NAME="UserLimit-V3.service"
    PYTHON_SCRIPT_NAME="UserLimit-V3.py"
    
    # Get the absolute path to the directory containing this script
    SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
    PYTHON_SCRIPT_PATH="$SCRIPT_DIR/$PYTHON_SCRIPT_NAME"

    # --- Pre-check: Python script must exist ---
    if [ ! -f "$PYTHON_SCRIPT_PATH" ]; then
        echo "${RED}❌ Error: Python script '$PYTHON_SCRIPT_NAME' not found in the same directory as the installer.${NC}"
        exit 1
    fi

    # --- Step 1: Find Python 3 path ---
    echo "[*] Searching for Python 3 interpreter..."
    PYTHON_PATH=$(which python3)
    if [ -z "$PYTHON_PATH" ]; then
        echo "${RED}❌ Error: 'python3' command not found. Please install Python 3 and ensure it's in your PATH.${NC}"
        exit 1
    fi
    echo "${GREEN}✅ Python 3 found at: $PYTHON_PATH${NC}"
    echo

    # --- Step 2: Define Service ---
    SERVICE_NAME=${DEFAULT_SERVICE_NAME}
    SERVICE_FILE_PATH="/etc/systemd/system/$SERVICE_NAME"
    
    echo "This will install the service as '${BOLD}$SERVICE_NAME${NC}'."
    echo "Service file will be created at: ${BOLD}$SERVICE_FILE_PATH${NC}"
    echo

    # --- Step 3: Create systemd service file ---
    echo "[*] Creating systemd service file..."

    # Use a 'here document' to write the service file content
    cat > "$SERVICE_FILE_PATH" << EOF
[Unit]
Description=3x-ui Fail2ban UserLimit-V3 Monitor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$SCRIPT_DIR
ExecStart=$PYTHON_PATH $PYTHON_SCRIPT_PATH
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    if [ $? -ne 0 ]; then
        echo "${RED}❌ Error: Failed to create systemd service file.${NC}"
        exit 1
    fi
    echo "${GREEN}✅ Service file created successfully.${NC}"
    echo

    # --- Step 4: Manage systemd service ---
    echo "[*] Reloading systemd daemon..."
    systemctl daemon-reload

    echo "[*] Enabling the service to start on boot..."
    systemctl enable "$SERVICE_NAME"

    echo "[*] Starting the service now..."
    systemctl start "$SERVICE_NAME"
    
    # Wait a moment for the service to initialize
    sleep 2 

    echo
    echo "${GREEN}${BOLD}🎉 Installation Complete! 🎉${NC}"
    echo "The UserLimit-V3 monitor is now running in the background."
    echo

    # --- Step 5: Show status ---
    echo "To check the status of the service, use:"
    echo "${BOLD}sudo systemctl status $SERVICE_NAME${NC}"
    echo
    echo "To view live logs, use:"
    echo "${BOLD}sudo journalctl -u $SERVICE_NAME -f${NC}"
    echo
    
    # Display the current status
    systemctl status "$SERVICE_NAME"