import json
import os
import datetime
import requests

# --- CONFIGURATION ---
# Timezone: India (IST)
utc_now = datetime.datetime.utcnow()
ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
TIMESTAMP_STR = ist_now.strftime("%I:%M %p")
DATE_STR = ist_now.strftime("%d %b %Y")

# Secrets
USERNAME = os.environ.get("GROWATT_USER")
PASSWORD = os.environ.get("GROWATT_PASSWORD")
OUTPUT_FILE = "solar_data.json"

def get_weather():
    """Fetches simple weather data"""
    try:
        url = "https://wttr.in/Banda?format=%C+%t" 
        res = requests.get(url, timeout=5)
        text = res.text.strip().split(" ")
        return text[0], text[1] # Condition, Temp
    except:
        return "Unknown", "--°C"

def calculate_ai_prediction(current_kwh, current_watts):
    """
    Simple 'AI' Prediction logic:
    Estimates end-of-day total based on time remaining and current power.
    """
    hour = int(ist_now.strftime("%H"))
    
    # If it's night (after 6 PM) or too early (before 6 AM), prediction is just current total
    if hour >= 18 or hour < 6:
        return current_kwh
    
    # Calculate remaining sun hours (approx sunset at 6 PM)
    hours_left = 18 - hour
    
    # Basic Physics Formula: Current kWh + (Avg Power * Hours Left * Efficiency Factor)
    # We assume power will drop as sun sets, so we multiply by 0.6 (avg decay)
    predicted_extra = (current_watts / 1000) * hours_left * 0.6
    
    total_prediction = current_kwh + predicted_extra
    return round(total_prediction, 2)

def main():
    weather_cond, weather_temp = get_weather()
    print(f"🌍 Weather: {weather_cond} {weather_temp}")

    if not USERNAME or not PASSWORD:
        print("❌ Secrets missing")
        exit(1)

    try:
        import growattServer
        api = growattServer.GrowattApi()
        api.server_url = 'https://server.growatt.com/'
        api.session.headers.update({'User-Agent': 'Mozilla/5.0'})
        
        login = api.login(USERNAME, PASSWORD)
        plant_list = api.plant_list(login['user']['id'])
        plant_id = plant_list['data'][0]['plantId']
        
        # 1. Get TOTAL Plant Data (Includes Monthly & Total)
        plant_info = api.plant_info(plant_id)
        # Note: Different API versions verify keys differently. 
        # We try to fetch safely.
        monthly_kwh = float(plant_info.get('energyMonth', 0))
        total_kwh = float(plant_info.get('energyTotal', 0))

        # 2. Get LIVE Inverter Data (Real-time Watts)
        device_list = api.device_list(plant_id)
        device_sn = device_list[0]['deviceSn']
        inv_data = api.inverter_data(device_sn, date=datetime.date.today())
        
        current_watts = float(inv_data.get('pac', 0))
        today_kwh = float(inv_data.get('e_today', 0))
        voltage = float(inv_data.get('vvac', 0))

        # 3. Run AI Prediction
        prediction = calculate_ai_prediction(today_kwh, current_watts)

        # 4. Build Modern JSON
        data = {
            "meta": {
                "timestamp": TIMESTAMP_STR,
                "date": DATE_STR,
                "prediction": prediction
            },
            "solar": { 
                "watts": current_watts,
                "today": today_kwh,
                "month": monthly_kwh,
                "lifetime": total_kwh
            },
            "grid": { 
                "status": "Active" if voltage > 100 else "Grid Failure", 
                "voltage": voltage 
            },
            "environment": { 
                "weather": weather_cond, 
                "temp": weather_temp,
                "location": "Banda, UP"
            }
        }

        with open(OUTPUT_FILE, "w") as f:
            json.dump(data, f, indent=4)
        print("✅ Data Updated Successfully")

    except Exception as e:
        print(f"⚠️ Error: {e}")
        exit(0)

if __name__ == "__main__":
    main()
