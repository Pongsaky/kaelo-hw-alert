#!/usr/bin/env python3
"""
Script to create and manage systemd service for Hardware Alert API
Run this script on your Raspberry Pi to set up auto-start service
"""

import subprocess
import sys
from pathlib import Path


def create_systemd_service():
    """Create systemd service file for the Hardware Alert API"""

    # Get current directory (where the project is located)
    project_dir = Path(__file__).parent.absolute()
    venv_python = project_dir / "venv" / "bin" / "python"
    main_py = project_dir / "main.py"

    # Service file content
    service_content = f"""[Unit]
Description=Hardware Alert API
After=network.target
Wants=network.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory={project_dir}
Environment=PATH={project_dir}/venv/bin
ExecStart={venv_python} -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

    service_file_path = "/etc/systemd/system/hardware-alert-api.service"

    try:
        # Write service file (requires sudo)
        print("Creating systemd service file...")
        with open("/tmp/hardware-alert-api.service", "w") as f:
            f.write(service_content)

        # Move to systemd directory with sudo
        subprocess.run(
            ["sudo", "mv", "/tmp/hardware-alert-api.service", service_file_path],
            check=True,
        )

        # Reload systemd daemon
        print("Reloading systemd daemon...")
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)

        # Enable service
        print("Enabling service...")
        subprocess.run(
            ["sudo", "systemctl", "enable", "hardware-alert-api.service"], check=True
        )

        print("✅ Systemd service created successfully!")
        print("\nService management commands:")
        print("  Start:   sudo systemctl start hardware-alert-api")
        print("  Stop:    sudo systemctl stop hardware-alert-api")
        print("  Status:  sudo systemctl status hardware-alert-api")
        print("  Logs:    sudo journalctl -u hardware-alert-api -f")
        print("  Restart: sudo systemctl restart hardware-alert-api")

        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Error creating service: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def start_service():
    """Start the hardware alert service"""
    try:
        subprocess.run(["sudo", "systemctl", "start", "hardware-alert-api"], check=True)
        print("✅ Service started successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting service: {e}")
        return False


def stop_service():
    """Stop the hardware alert service"""
    try:
        subprocess.run(["sudo", "systemctl", "stop", "hardware-alert-api"], check=True)
        print("✅ Service stopped successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error stopping service: {e}")
        return False


def service_status():
    """Check service status"""
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "status", "hardware-alert-api"],
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error checking status: {e}")
        return False


def main():
    """Main function to handle command line arguments"""
    if len(sys.argv) < 2:
        print("Usage: python3 systemd_service.py [create|start|stop|status]")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "create":
        create_systemd_service()
    elif command == "start":
        start_service()
    elif command == "stop":
        stop_service()
    elif command == "status":
        service_status()
    else:
        print("Invalid command. Use: create, start, stop, or status")
        sys.exit(1)


if __name__ == "__main__":
    main()
