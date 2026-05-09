#!/usr/bin/env python3
"""
Multica verification code WeChat forwarder
Monitor Docker logs, detect target email verification codes and send to WeChat
"""
import subprocess
import re
import requests
import time
import json
import os
import hmac
import hashlib
import signal
import sys
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Configuration from environment variables
CONTAINER_NAME = os.getenv("CONTAINER_NAME", "multica-backend-1")
TARGET_EMAIL = os.getenv("TARGET_EMAIL", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
SENT_FILE = os.getenv("SENT_FILE", "/tmp/sent_codes.json")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "10"))

# Log pattern: [DEV] Verification code for <email>: 123456
PATTERN = re.compile(r'\[DEV\] Verification code for ' + re.escape(TARGET_EMAIL) + r': (\d+)')

# Graceful shutdown
running = True

def signal_handler(sig, frame):
    global running
    print(f"\n[{datetime.now()}] Received signal {sig}, shutting down...")
    running = False

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def load_sent_codes():
    """Load sent codes list"""
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, 'r') as f:
            return json.load(f)
    return []

def save_sent_codes(codes):
    """Save sent codes list"""
    with open(SENT_FILE, 'w') as f:
        json.dump(codes, f)

def is_already_sent(code):
    """Check if code already sent"""
    return code in load_sent_codes()

def mark_as_sent(code):
    """Mark code as sent"""
    codes = load_sent_codes()
    if code not in codes:
        codes.append(code)
        save_sent_codes(codes)

def send_to_wechat(code):
    """Call webhook to send to WeChat"""
    message = f"multica verification code: {code}"
    payload = {
        "code": code,
        "email": TARGET_EMAIL,
        "message": message
    }
    payload_str = json.dumps(payload)
    sig = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()
    try:
        response = requests.post(
            WEBHOOK_URL,
            data=payload_str,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
                "X-GitHub-Event": "verification",
            },
            timeout=10
        )
        if response.status_code == 200:
            print(f"[{datetime.now()}] Code {code} sent to WeChat")
            return True
        else:
            print(f"[{datetime.now()}] Send failed: {response.status_code} {response.text}")
            return False
    except Exception as e:
        print(f"[{datetime.now()}] Webhook call failed: {e}")
        return False

def get_recent_logs(since_time):
    """Fetch recent logs from Docker container using --since"""
    try:
        since_str = since_time.strftime("%Y-%m-%dT%H:%M:%S")
        result = subprocess.run(
            ["docker", "logs", "--since", since_str, CONTAINER_NAME],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return result.stdout
        else:
            return ""
    except subprocess.TimeoutExpired:
        print(f"[{datetime.now()}] docker logs timed out")
        return ""
    except Exception as e:
        print(f"[{datetime.now()}] Error fetching logs: {e}")
        return ""

def monitor_logs():
    """Monitor Docker logs using polling"""
    if not TARGET_EMAIL or not WEBHOOK_URL or not WEBHOOK_SECRET:
        print("Error: Missing required environment variables!")
        print("Please configure .env file. See .env.example for reference.")
        return

    print(f"Starting verification code monitor (polling mode)...")
    print(f"  Target email: {TARGET_EMAIL}")
    print(f"  Container: {CONTAINER_NAME}")
    print(f"  Webhook: {WEBHOOK_URL}")
    print(f"  Poll interval: {POLL_INTERVAL}s")
    print(f"  Press Ctrl+C to stop\n")
    
    # Start from 2 minutes ago to catch any recent codes
    last_check = datetime.now(timezone.utc) - timedelta(minutes=2)
    
    while running:
        try:
            # Fetch logs since last check
            logs = get_recent_logs(last_check)
            last_check = datetime.now(timezone.utc)
            
            if logs:
                for line in logs.split('\n'):
                    match = PATTERN.search(line)
                    if match:
                        code = match.group(1)
                        print(f"[{datetime.now()}] Detected code: {code}")
                        
                        if not is_already_sent(code):
                            if send_to_wechat(code):
                                mark_as_sent(code)
                        else:
                            print(f"[{datetime.now()}] Code already sent, skipping")
            
            # Sleep until next poll
            for _ in range(POLL_INTERVAL):
                if not running:
                    break
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nMonitor stopped")
            break
        except Exception as e:
            if running:
                print(f"[{datetime.now()}] Error: {e}")
                time.sleep(POLL_INTERVAL)

    print("Monitor stopped.")

if __name__ == "__main__":
    monitor_logs()
