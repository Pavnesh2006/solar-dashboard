import growattServer
import requests
import os

# CREDENTIALS
USERNAME = os.environ.get("GROWATT_USER")
PASSWORD = os.environ.get("GROWATT_PASSWORD")

# LIST OF DOORS TO KNOCK ON
SERVERS = [
    "https://server.growatt.com/",       # Global (The one we tried)
    "https://server-api.growatt.com/",   # Mobile App API
    "https://openapi.growatt.com/",      # Open API
    "https://server-us.growatt.com/",    # US Server (Sometimes works)
    "https://oss.growatt.com/"           # Installer Server
]

# LIST OF DISGUISES (User Agents)
AGENTS = [
    # Chrome on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
    # Growatt App (iPhone)
    'Growatt/2.0 (iPhone; iOS 15.0; Scale/3.00)',
    # Android App
    'Dalvik/2.1.0 (Linux; U; Android 11; SM-G991B Build/RP1A.200720.012)'
]

def main():
    print("🕵️ STARTING CLOUD SERVER HUNT...")
    
    found_any = False

    for server in SERVERS:
        print(f"\n👉 Trying Server: {server}")
        for agent in AGENTS:
            try:
                api = growattServer.GrowattApi()
                api.server_url = server
                api.session.headers.update({'User-Agent': agent})
                
                login = api.login(USERNAME, PASSWORD)
                user_id = login['user']['id']
                
                # If we get here, Login worked. NOW CHECK FOR REAL DATA.
                plant_list = api.plant_list(user_id)
                plant_id = plant_list['data'][0]['plantId']
                
                # Check Plant Total (If this is > 0, we found a working server!)
                plant_info = api.plant_info(plant_id)
                total_energy = float(plant_info.get('eTotal', 0))
                
                if total_energy > 0:
                    print(f"✅✅ JACKPOT! WORKING COMBINATION FOUND!")
                    print(f"Server: {server}")
                    print(f"Agent: {agent}")
                    print(f"Data: {total_energy} kWh")
                    found_any = True
                    return # Stop searching, we found it!
                else:
                    print(f"❌ Login OK, but Data is 0 (Soft Block).")

            except Exception as e:
                # print(f"❌ Failed: {e}") 
                pass # Just keep trying silently

    if not found_any:
        print("\n💀 CONCLUSION: Growatt has blocked ALL GitHub Cloud IPs.")
        print("You MUST use the Laptop Method.")

if __name__ == "__main__":
    main()
