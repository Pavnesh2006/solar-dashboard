import json
import growattServer
import datetime
import os  # <--- Essential for reading Secrets
import requests
import math

# --- SECURE CONFIGURATION (Reads from GitHub Secrets) ---
USERNAME = os.environ.get("GROWATT_USER")
PASSWORD = os.environ.get("GROWATT_PASSWORD")
WEATHER_API_KEY = os.environ.get("WEATHER_KEY")
OUTPUT_FILE = "solar_data.json"

CITY = "Banda"
COUNTRY = "IN"

def get_weather_and_predict(current_power):
    try:
        if not WEATHER_API_KEY:
            return {"temp": "--", "condition": "No Key", "prediction_watts": 0, "efficiency_score": 0}
            
        url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY},{COUNTRY}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url).json()
        
        temp = response['main']['temp']
        condition = response['weather'][0]['main']
        clouds = response['clouds']['all']
        
        # Simple Prediction Logic
        SYSTEM_CAPACITY = 5000 
        hour = datetime.datetime.now().hour + 5.5 # Adjust for India Time (UTC+5:30) if server is UTC
        if hour > 24: hour -= 24
        
        if 6 <= hour <= 18:
            sun_factor = math.sin((hour - 6) * math.pi / 12) 
        else:
            sun_factor = 0
            
        weather_efficiency = 1.0
        if "Rain" in condition: weather_efficiency = 0.2
        elif "Clouds" in condition: weather_efficiency = 1.0 - (clouds / 100 * 0.6)

        predicted_power = max(0, SYSTEM_CAPACITY * sun_factor * weather_efficiency)
        
        return {
            "temp": temp,
            "condition": condition,
            "prediction_watts": round(predicted_power, 2),
            "efficiency_score": int(weather_efficiency * 100)
        }
    except:
        return {"temp": "--", "condition": "Error", "prediction_watts": 0, "efficiency_score": 0}

def fetch_data():
    print("🚀 Cloud Fetch Started...")
    try:
        api = growattServer.GrowattApi()
        api.server_url = 'https://server.growatt.com/'
        api.session.headers.update({'User-Agent': 'Mozilla/5.0'})
        login_response = api.login(USERNAME, PASSWORD)
        
        plant_id = api.plant_list(login_response['user']['id'])['data'][0]['plantId']
        device_sn = api.device_list(plant_id)[0]['deviceSn']

        # Get Raw Data
        inv_data = api.inverter_data(device_sn, date=datetime.date.today())
        current_watts = float(inv_data.get('pac', 0))
        
        # Get AI Data
        ai_data = get_weather_and_predict(current_watts)

        # Build JSON
        final_data = {
            "timestamp": (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).strftime("%I:%M %p"),
            "solar": {
                "current_watts": current_watts,
                "today_kwh": float(inv_data.get('e_today', 0)),
                "total_kwh": float(inv_data.get('e_total', 0)),
                "status_code": 1
            },
            "grid": {
                "voltage": float(inv_data.get('vvac', 0)),
                "status": "Connected" if float(inv_data.get('vvac', 0)) > 10 else "Grid Failure"
            },
            "dongle": {"status": "Online", "signal": "Cloud"},
            "environment": {
                "location": CITY,
                "temp": ai_data['temp'],
                "weather": ai_data['condition'],
                "ai_prediction": ai_data['prediction_watts'],
                "performance_score": ai_data['efficiency_score']
            }
        }

        with open(OUTPUT_FILE, "w") as f:
            json.dump(final_data, f, indent=4)
        
        print("✅ Data Saved Successfully")

    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1) # Tell GitHub the script failed

if __name__ == "__main__":
    fetch_data()