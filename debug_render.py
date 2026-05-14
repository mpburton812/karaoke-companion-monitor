import os
import requests
from dotenv import load_dotenv

load_dotenv()

def find_render_details():
    api_key = os.getenv("RENDER_API_KEY")
    service_id = os.getenv("RENDER_SERVICE_ID")
    
    if not api_key or not service_id:
        print("Missing RENDER_API_KEY or RENDER_SERVICE_ID in .env")
        return

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # Step 1: Get Service Details to find ownerId
    print(f"Fetching details for service {service_id}...")
    svc_url = f"https://api.render.com/v1/services/{service_id}"
    svc_resp = requests.get(svc_url, headers=headers)
    
    if svc_resp.status_code != 200:
        print(f"Error fetching service: {svc_resp.status_code} - {svc_resp.text}")
        return
    
    svc_data = svc_resp.json()
    owner_id = svc_data.get("ownerId")
    print(f"Found Owner ID: {owner_id}")

    # Step 2: Test Logs Endpoint with ownerId and resource (serviceId)
    print("\nTesting Logs Endpoint...")
    logs_url = f"https://api.render.com/v1/logs?ownerId={owner_id}&resource={service_id}&limit=5"
    logs_resp = requests.get(logs_url, headers=headers)
    
    if logs_resp.status_code == 200:
        print("Success! Recent logs:")
        print(logs_resp.json())
    else:
        print(f"Error fetching logs: {logs_resp.status_code} - {logs_resp.text}")

if __name__ == "__main__":
    find_render_details()
