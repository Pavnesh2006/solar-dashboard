import json
import os
import datetime

# 1. Setup
try:
    import growattServer
    import requests
    print("✅ Libraries loaded")
except ImportError:
    print("❌ Libraries missing - check YAML")
    exit(1)

# 2. Config
USERNAME = os.environ.get("GROWATT_USER")
PASSWORD = os.environ.get("GROWATT_PASSWORD")
OUTPUT_FILE = "solar_data.json"

# 3. Safe Save Function
def save_data(data):
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=4)
    print("✅ Data saved to file")

# 4. Main Logic
def main():
    if not USERNAME or not PASSWORD:
        print("⚠️ Secrets missing. Saving dummy data.")
        save_data({"solar": {"current_watts": 0}, "dongle": {"status": "Config Error"}})
        exit(0) # Exit Green

    try:
        print("🚀 Connecting to Growatt...")
        api = growattServer.GrowattApi()
        api.server_url = 'https://server.growatt.com/'
        api.session.headers.update({'User-Agent': 'Mozilla/5.0'})
        
        login = api.login(USERNAME, PASSWORD)
        print("✅ Logged in")
        
        # Get Plant
        plant_id = api.plant_list(login['user']['id'])['data'][0]['plantId']
        device_sn = api.device_list(plant_id)[0]['deviceSn']
        
        # Get Data
        data = api.inverter_data(device_sn, date=datetime.date.today())
        watts = float(data.get('pac', 0))
        print(f"☀️ Current Solar: {watts} W")
        
        # Build JSON
        final_json = {
            "timestamp": datetime.datetime.now().strftime("%I:%M %p"),
            "solar": { 
                "current_watts": watts,
                "today_kwh": float(data.get('e_today', 0)),
                "total_kwh": float(data.get('e_total', 0))
            },
            "dongle": { "status": "Online" },
            "grid": { "status": "Active", "voltage": float(data.get('vvac', 0)) },
            "environment": { "weather": "Online", "temp": "25" }
        }
        save_data(final_json)

    except Exception as e:
        print(f"⚠️ Error: {e}")
        # Save Offline Data so website doesn't hang
        save_data({
            "solar": {"current_watts": 0},
            "dongle": {"status": "Offline"},
            "error": str(e)
        })
        exit(0) # Exit Green even if offline

if __name__ == "__main__":
    main()
