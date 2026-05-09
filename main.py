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
from datetime import datetime

# Configuration - customize these values for your environment
CONTAINER_NAME = "multica-backend-1"
TARGET_EMAIL = "YOUR_EMAIL@example.com"  # Replace with your email
WEBHOOK_URL = "http://YOUR_WEBHOOK_HOST:8644/webhooks/verification-monitor"
WEBHOOK_SECRET = "your-webhook-secret-here"  # Replace with your secret
SENT_FILE = "/tmp/sent_codes.json"

# Log pattern: [DEV] Verification code for YOUR_EMAIL@example.com: 123456
PATTERN = re.compile(r'\[DEV\] Verification code for ' + re.escape(TARGET_EMAIL) + r': (\d+)')

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

def monitor_logs():
    """Monitor Docker logs"""
    print(f"Starting verification code monitor...")
    print(f"  Target email: {TARGET_EMAIL}")
    print(f"  Container: {CONTAINER_NAME}")
    print(f"  Webhook: {WEBHOOK_URL}")
    print(f"  Press Ctrl+C to stop\n")
    
    # Use docker logs --follow to get real-time logs
    process = subprocess.Popen(
        ["docker", "logs", "--follow", "--tail", "0", CONTAINER_NAME],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    try:
        for line in process.stdout:
            match = PATTERN.search(line)
            if match:
                code = match.group(1)
                print(f"[{datetime.now()}] Detected code: {code}")
                
                if not is_already_sent(code):
                    if send_to_wechat(code):
                        mark_as_sent(code)
                else:
                    print(f"[{datetime.now()}] Code already sent, skipping")
                    
    except KeyboardInterrupt:
        print("\nMonitor stopped")
        process.terminate()
    except Exception as e:
        print(f"Error: {e}")
        process.terminate()

if __name__ == "__main__":
    monitor_logs()
