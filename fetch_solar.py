import json
import os
import datetime
import requests

# --- CONFIGURATION ---
# 1. Force Timezone to India (IST)
utc_now = datetime.datetime.utcnow()
ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
TIMESTAMP_STR = ist_now.strftime("%I:%M %p") # e.g., "06:30 PM"
DATE_STR = ist_now.strftime("%d %b %Y")

# 2. Get Secrets
USERNAME = os.environ.get("GROWATT_USER")
PASSWORD = os.environ.get("GROWATT_PASSWORD")
OUTPUT_FILE = "solar_data.json"

def get_weather():
    try:
        url = "https://wttr.in/Banda?format=%C+%t"
        res = requests.get(url, timeout=5)
        text = res.text.strip().split(" ")
        return text[0], text[1]
    except:
        return "Clear", "25°C"

def main():
    print(f"🕒 Script started at {TIMESTAMP_STR} (IST)")
    
    if not USERNAME or not PASSWORD:
        print("❌ Secrets missing.")
        exit(1)

    try:
        import growattServer
        api = growattServer.GrowattApi()
        api.server_url = 'https://server.growatt.com/'
        api.session.headers.update({'User-Agent': 'Mozilla/5.0'})
        
        # 1. Login
        login = api.login(USERNAME, PASSWORD)
        user_id = login['user']['id']
        plant_list = api.plant_list(user_id)
        plant_id = plant_list['data'][0]['plantId']
        
        # 2. FETCH PLANT TOTALS (This fixes the "0 kWh" bug)
        # We ask the 'Plant' for history, not the 'Inverter' for live data.
        plant_info = api.plant_info(plant_id)
        print("🌱 Plant Info Fetched:", plant_info)
        
        # Extract totals safely
        today_kwh = float(plant_info.get('eToday', 0))       # 7.4 kWh
        month_kwh = float(plant_info.get('eMonth', 0))       # 262.9 kWh
        total_kwh = float(plant_info.get('eTotal', 0))       # Lifetime
        
        # 3. FETCH LIVE POWER (Watts)
        device_list = api.device_list(plant_id)
        device_sn = device_list[0]['deviceSn']
        inv_data = api.inverter_data(device_sn, date=datetime.date.today())
        
        current_watts = float(inv_data.get('pac', 0))
        voltage = float(inv_data.get('vvac', 0))
        
        # 4. AI PREDICTION (Simple Logic)
        # If it's 6 PM, prediction = current total (because sun is gone)
        hour = int(ist_now.strftime("%H"))
        if hour >= 17: 
            prediction = today_kwh
        else:
            # Simple formula: Current + (Watts * Hours Left * 0.5)
            hours_left = 17 - hour
            prediction = today_kwh + ((current_watts/1000) * hours_left * 0.5)

        # 5. Build Data
        data = {
            "meta": {
                "timestamp": TIMESTAMP_STR,
                "date": DATE_STR,
                "prediction": round(prediction, 1)
            },
            "solar": { 
                "watts": current_watts, 
                "today": today_kwh,    # This will now show 7.4!
                "month": month_kwh,    # This will now show 262.9!
                "lifetime": total_kwh
            },
            "grid": { 
                "status": "Active" if voltage > 100 else "Grid Failure", 
                "voltage": voltage 
            },
            "environment": { 
                "weather": get_weather()[0], 
                "temp": get_weather()[1],
                "location": "Banda, UP"
            }
        }

        with open(OUTPUT_FILE, "w") as f:
            json.dump(data, f, indent=4)
        print(f"✅ Saved: {today_kwh}kWh Today, {current_watts}W Live")

    except Exception as e:
        print(f"⚠️ Error: {e}")
        exit(1) # Fail so we know something is wrong

if __name__ == "__main__":
    main()
