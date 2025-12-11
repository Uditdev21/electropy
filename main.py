import json
import time
import sys
import os

try:
    import serial  # pyserial
except ImportError:
    serial = None

try:
    import requests
except ImportError:
    requests = None


# Read from environment variables
API_URL = os.getenv("API_URL", "https://stage.gwtpl.co/api/monitoring/add_battery_data")
API_KEY = os.getenv(
    "API_KEY",
    "6513d871943f3acaf3ef2dee663980bb2087ef2a0a1f9028367906c8d1ffe375"
)
SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyUSB1")
BAUDRATE = int(os.getenv("BAUDRATE", "115200"))  # UPDATED
READ_TIMEOUT = 2.0
POST_INTERVAL = 5.0


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def ensure_deps():
    missing = []
    if serial is None:
        missing.append("pyserial")
    if requests is None:
        missing.append("requests")
    if missing:
        log("Missing dependencies: " + ", ".join(missing))
        log("Install with: pip install " + " ".join(missing))
        sys.exit(1)


def open_serial(port: str, baudrate: int, timeout: float):
    ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
    time.sleep(0.5)
    return ser


def parse_line_to_payload(line: str):
    """
    Example expected input:
    {"ac_status":"electricity","battery_voltage":"52.95","battery_percentage":"92.5"}
    """
    try:
        data = json.loads(line)

        ac_status = str(data.get("ac_status", "")).strip()
        batt_pct = data.get("battery_percentage")
        if batt_pct is None:
            raise ValueError("battery_percentage missing")

        payload = {
            "battery_id": "2",
            "battery_percentage": str(batt_pct),
            "battery_status": "electricity" if ac_status == "electricity" else "no_electricity",
        }

        return payload

    except Exception as e:
        raise ValueError(f"Invalid input line: {e}")


def post_payload(payload: dict):
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
    }
    return requests.post(API_URL, headers=headers, json=payload, timeout=10)


def main():
    ensure_deps()
    log(f"Opening serial port {SERIAL_PORT} @ {BAUDRATE}...")

    try:
        ser = open_serial(SERIAL_PORT, BAUDRATE, READ_TIMEOUT)
    except Exception as e:
        log(f"Failed to open serial port: {e}")
        sys.exit(1)

    log("Starting read → post loop. Ctrl+C to stop.")
    last_post_ts = 0.0

    while True:
        try:
            line_bytes = ser.readline()
            if not line_bytes:
                time.sleep(0.2)
                continue

            line = line_bytes.decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            if "{" in line and "}" in line:
                line = line[line.find("{"): line.rfind("}") + 1]

            try:
                payload = parse_line_to_payload(line)
            except ValueError as e:
                log(f"Skip invalid line: {e}")
                continue

            now = time.time()
            if now - last_post_ts < POST_INTERVAL:
                time.sleep(POST_INTERVAL - (now - last_post_ts))

            try:
                resp = post_payload(payload)
                last_post_ts = time.time()
                log(f"POST {resp.status_code}: {payload}")
            except Exception as e:
                log(f"POST failed: {e}")
                time.sleep(2.0)

        except KeyboardInterrupt:
            log("Stopping...")
            break

        except Exception as e:
            log(f"Unexpected error: {e}")
            time.sleep(1.0)


if __name__ == "__main__":
    main()
