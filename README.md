# Electropy Serial to API Poster

A small Python script that reads JSON telemetry from a serial device (e.g., `/dev/ttyUSB0`) and continuously posts battery data to the monitoring API.

## What it does
- Reads lines like `{"ac_status":"electricity","ac_peak":"4095","battery_voltage":"52.95","battery_percentage":"92.5"}` from the serial port.
- Ignores `ac_peak`/`ac_prack`.
- Sends POST requests to `https://stage.gwtpl.co/api/monitoring/add_battery_data` with:
  - `battery_id`: `"1"`
  - `battery_percentage`: taken from serial input
  - `battery_status`: `"electricity"` if `ac_status == "electricity"`, else `"no_electricity"`

## Setup

```zsh
cd /Users/uditkumar/Desktop/electropy
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```zsh
python main.py
```

Ensure your device is available at `/dev/ttyUSB0`. Adjust baud rate or port in `main.py` if needed.
