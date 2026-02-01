import json
import os
import datetime
import requests

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
    print(f"☀️ Hybrid Script Started: {TIMESTAMP_STR}")
    
    if not USERNAME or not PASSWORD:
        print("❌ Secrets missing.")
        exit(1)

    try:
        import growattServer
        api = growattServer.GrowattApi()
        api.server_url = 'https://server.growatt.com/'
        api.session.headers.update({'User-Agent': 'Mozilla/5.0'})
        
        login = api.login(USERNAME, PASSWORD)
        plant_id = api.plant_list(login['user']['id'])['data'][0]['plantId']
        
        # 1. GET TOTALS (From Dashboard - Always Correct)
        plant_info = api.plant_info(plant_id)
        today_kwh = float(plant_info.get('eToday', 0))
        month_kwh = float(plant_info.get('eMonth', 0))
        total_kwh = float(plant_info.get('eTotal', 0))
        
        # 2. GET LIVE STATUS (From Inverter - For Voltage & Watts)
        device_list = api.device_list(plant_id)
        device_sn = device_list[0]['deviceSn']
        
        try:
            # Ask Inverter for real-time data
            inv_data = api.inverter_data(device_sn, date=datetime.date.today())
            current_watts = float(inv_data.get('pac', 0))
            voltage = float(inv_data.get('vvac', 0))
        except:
            # If Inverter is offline/sleeping, assume 0
            current_watts = 0
            voltage = 0

        # 3. AI PREDICTION
        hour = int(ist_now.strftime("%H"))
        if hour >= 17:
            prediction = today_kwh
        else:
            hours_left = 17 - hour
            # Improve prediction by using current generation trend
            prediction = today_kwh + ((current_watts/1000) * hours_left * 0.5)

        # 4. DATA PACKAGING
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
                # If voltage is real (>100V), say Active. Else Failure.
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
        print(f"✅ Success: {today_kwh}kWh | {current_watts}W | {voltage}V")

    except Exception as e:
        print(f"⚠️ Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
