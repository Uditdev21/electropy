import json
import time
import sys

try:
	import serial  # pyserial
except ImportError:
	serial = None

try:
	import requests
except ImportError:
	requests = None


API_URL = "https://stage.gwtpl.co/api/monitoring/add_battery_data"
API_KEY = "6513d871943f3acaf3ef2dee663980bb2087ef2a0a1f9028367906c8d1ffe375"
SERIAL_PORT = "/dev/ttyUSB0"
BAUDRATE = 9600
READ_TIMEOUT = 2.0  # seconds
POST_INTERVAL = 5.0  # seconds between posts when data is available


def log(msg):
	ts = time.strftime("%Y-%m-%d %H:%M:%S")
	print(f"[{ts}] {msg}")


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
	# Give the device a moment after opening
	time.sleep(0.5)
	return ser


def parse_line_to_payload(line: str):
	"""
	Input line expected JSON like:
	{"ac_status":"electricity","ac_peak":"4095","battery_voltage":"52.95","battery_percentage":"92.5"}

	We ignore ac_peak (or ac_prack if present/typo) and build POST payload:
	{
		"battery_id": "1",
		"battery_percentage": "<from input>",
		"battery_status": "electricity" | "no_electricity"
	}
	"""
	try:
		data = json.loads(line)
		# Normalize keys that may appear with typos
		ac_status = str(data.get("ac_status", "")).strip()
		# battery_percentage may be string or number
		batt_pct = data.get("battery_percentage")
		if batt_pct is None:
			raise ValueError("battery_percentage missing")
		# Convert to string as API expects strings
		batt_pct_str = str(batt_pct)

		battery_status = "electricity" if ac_status == "electricity" else "no_electricity"

		payload = {
			"battery_id": "1",
			"battery_percentage": batt_pct_str,
			"battery_status": battery_status,
		}
		return payload
	except Exception as e:
		raise ValueError(f"Invalid input line: {e}")


def post_payload(payload: dict):
	headers = {
		"Content-Type": "application/json",
		"x-api-key": API_KEY,
	}
	resp = requests.post(API_URL, headers=headers, json=payload, timeout=10)
	return resp


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
				# No data within timeout; small sleep to avoid tight loop
				time.sleep(0.2)
				continue
			# Decode and strip
			line = line_bytes.decode("utf-8", errors="ignore").strip()
			if not line:
				continue

			# Some devices may prefix with non-JSON text; try to find JSON segment
			if "{" in line and "}" in line:
				line = line[line.find("{") : line.rfind("}") + 1]

			try:
				payload = parse_line_to_payload(line)
			except ValueError as e:
				log(f"Skip invalid line: {e}")
				continue

			now = time.time()
			if now - last_post_ts < POST_INTERVAL:
				# throttle posts
				time.sleep(POST_INTERVAL - (now - last_post_ts))

			try:
				resp = post_payload(payload)
				last_post_ts = time.time()
				log(f"POST {resp.status_code}: {payload}")
			except Exception as e:
				log(f"POST failed: {e}")
				# brief backoff
				time.sleep(2.0)
		except KeyboardInterrupt:
			log("Stopping...")
			break
		except Exception as e:
			log(f"Unexpected error: {e}")
			time.sleep(1.0)


if __name__ == "__main__":
	main()

