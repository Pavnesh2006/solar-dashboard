import json
import os
import datetime

# Try to import tools. If missing, print error but don't crash hard.
try:
    import growattServer
    import requests
except ImportError:
    print("CRITICAL: Libraries not installed.")
    exit(1)

# --- CONFIGURATION ---
USERNAME = os.environ.get("GROWATT_USER")
PASSWORD = os.environ.get("GROWATT_PASSWORD")
OUTPUT_FILE = "solar_data.json"

def save_offline(reason):
    print(f"⚠️ Going Offline: {reason}")
    data = {
        "timestamp": datetime.datetime.now().strftime("%I:%M %p"),
        "solar": { "current_watts": 0, "today_kwh": 0, "total_kwh": 0 },
        "dongle": { "status": "Offline" },
        "grid": { "status": "Unknown", "voltage": 0 },
        "environment": { "weather": "Offline", "temp": "--" }
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=4)
    exit(0) # Exit Green (Success)

def main():
    if not USERNAME or not PASSWORD:
        save_offline("Missing Secrets")

    try:
        api = growattServer.GrowattApi()
        api.server_url = 'https://server.growatt.com/'
        # Fake a browser to avoid getting blocked
        api.session.headers.update({'User-Agent': 'Mozilla/5.0'})
        
        login_response = api.login(USERNAME, PASSWORD)
        print("✅ Login Success")
        
        # Get Plant ID
        plant_list = api.plant_list(login_response['user']['id'])
        plant_id = plant_list['data'][0]['plantId']
        
        # Get Device SN
        device_list = api.device_list(plant_id)
        device_sn = device_list[0]['deviceSn']
        
        # Get Live Data
        inv_data = api.inverter_data(device_sn, date=datetime.date.today())
        
        # Success! Save Real Data
        data = {
            "timestamp": datetime.datetime.now().strftime("%I:%M %p"),
            "solar": { 
                "current_watts": float(inv_data.get('pac', 0)),
                "today_kwh": float(inv_data.get('e_today', 0)),
                "total_kwh": float(inv_data.get('e_total', 0))
            },
            "dongle": { "status": "Online" },
            "grid": { "status": "Active", "voltage": float(inv_data.get('vvac', 0)) },
            "environment": { "weather": "Clear", "temp": "25" } # Placeholder for now
        }
        
        with open(OUTPUT_FILE, "w") as f:
            json.dump(data, f, indent=4)
        print("✅ Data Saved")

    except Exception as e:
        save_offline(str(e))

if __name__ == "__main__":
    main()
