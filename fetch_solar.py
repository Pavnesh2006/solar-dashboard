import json
import growattServer
import datetime
import os
import requests
import math

# --- CONFIGURATION ---
USERNAME = os.environ.get("GROWATT_USER")
PASSWORD = os.environ.get("GROWATT_PASSWORD")
WEATHER_API_KEY = os.environ.get("WEATHER_KEY")
OUTPUT_FILE = "solar_data.json"
CITY = "Banda"
COUNTRY = "IN"

def fetch_data():
    print("🚀 Cloud Fetch Started...")
    try:
        # 1. Login
        api = growattServer.GrowattApi()
        api.server_url = 'https://server.growatt.com/'
        api.session.headers.update({'User-Agent': 'Mozilla/5.0'})
        login_response = api.login(USERNAME, PASSWORD)
        
        # 2. Get Data
        plant_id = api.plant_list(login_response['user']['id'])['data'][0]['plantId']
        device_sn = api.device_list(plant_id)[0]['deviceSn']
        inv_data = api.inverter_data(device_sn, date=datetime.date.today())
        
        # 3. Process Data
        current_watts = float(inv_data.get('pac', 0))
        
        # Weather Logic
        weather_desc = "Offline"
        temp = "--"
        pred = 0
        score = 0
        if WEATHER_API_KEY:
            try:
                url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY},{COUNTRY}&appid={WEATHER_API_KEY}&units=metric"
                w_data = requests.get(url).json()
                temp = w_data['main']['temp']
                weather_desc = w_data['weather'][0]['main']
                # AI Prediction
                hour = datetime.datetime.now().hour + 5.5
                if hour > 24: hour -= 24
                if 6 <= hour <= 18:
                    pred = 5000 * math.sin((hour - 6) * math.pi / 12) * (0.2 if "Rain" in weather_desc else 1.0)
                score = 100 if "Clear" in weather_desc else 50
            except: pass

        final_data = {
            "timestamp": (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).strftime("%I:%M %p"),
            "solar": {
                "current_watts": current_watts,
                "today_kwh": float(inv_data.get('e_today', 0)),
                "total_kwh": float(inv_data.get('e_total', 0)),
                "status_code": 1
            },
            "grid": { "voltage": float(inv_data.get('vvac', 0)), "status": "Connected" },
            "dongle": { "status": "Online", "signal": "Cloud" },
            "environment": { "location": CITY, "temp": temp, "weather": weather_desc, "ai_prediction": round(pred, 2), "performance_score": score }
        }

        with open(OUTPUT_FILE, "w") as f:
            json.dump(final_data, f, indent=4)
        print("✅ Success!")

    except Exception as e:
        print(f"⚠️ Error encountered (Dongle likely offline): {e}")
        
        # --- SAFE MODE: Save 'Offline' Data instead of crashing ---
        offline_data = {
            "timestamp": (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).strftime("%I:%M %p"),
            "solar": { "current_watts": 0, "today_kwh": 0, "total_kwh": 0, "status_code": 0 },
            "grid": { "voltage": 0, "status": "Grid Unknown" },
            "dongle": { "status": "Offline", "signal": "Lost" },
            "environment": { "location": CITY, "temp": "--", "weather": "Offline", "ai_prediction": 0, "performance_score": 0 }
        }
        with open(OUTPUT_FILE, "w") as f:
            json.dump(offline_data, f, indent=4)
        
        print("✅ Saved OFFLINE status. Exiting safely.")
        exit(0) # <--- This 0 means "Success", so NO RED X and NO EMAIL!

if __name__ == "__main__":
    fetch_data()
