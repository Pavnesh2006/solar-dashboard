import json
import os
import datetime
import requests
import growattServer

# --- CONFIGURATION ---
utc_now = datetime.datetime.utcnow()
ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
TIMESTAMP_STR = ist_now.strftime("%I:%M %p")
DATE_STR = ist_now.strftime("%d %b %Y")

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
    print(f"🚀 Starting Script: {TIMESTAMP_STR}")
    
    if not USERNAME or not PASSWORD:
        print("❌ Secrets missing.")
        exit(1)

    try:
        api = growattServer.GrowattApi()
        
        # --- THE FIX THAT WORKED ON YOUR LAPTOP ---
        # This line tricks the server into thinking we are Chrome
        api.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
        })
        
        # This is the URL that your test confirmed works
        api.server_url = 'https://server.growatt.com/'

        login = api.login(USERNAME, PASSWORD)
        print(f"✅ Login Success! (User ID: {login['user']['id']})")
        
        # Get Plant Data
        plant_list = api.plant_list(login['user']['id'])
        plant_id = plant_list['data'][0]['plantId']
        
        # Get Dashboard Totals (Always correct)
        plant_info = api.plant_info(plant_id)
        
        today_kwh = float(plant_info.get('eToday', 0))
        month_kwh = float(plant_info.get('eMonth', 0))
        total_kwh = float(plant_info.get('eTotal', 0))
        
        # Get Live Power
        device_list = api.device_list(plant_id)
        device_sn = device_list[0]['deviceSn']
        
        # Try-Catch for Live Data
        try:
            inv_data = api.inverter_data(device_sn, date=datetime.date.today())
            current_watts = float(inv_data.get('pac', 0))
            voltage = float(inv_data.get('vvac', 0))
        except:
            current_watts = 0
            voltage = 0

        # AI Prediction
        hour = int(ist_now.strftime("%H"))
        if hour >= 17:
            prediction = today_kwh
        else:
            hours_left = 17 - hour
            prediction = today_kwh + ((current_watts/1000) * hours_left * 0.5)

        # Build Data
        data = {
            "meta": {
                "timestamp": TIMESTAMP_STR,
                "date": DATE_STR,
                "prediction": round(prediction, 1)
            },
            "solar": { 
                "watts": current_watts, 
                "today": today_kwh,
                "month": month_kwh,
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
        print(f"✅ Data Saved: {current_watts}W | {today_kwh}kWh")

    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
