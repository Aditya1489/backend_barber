from fastapi import APIRouter, HTTPException, Query
from app.core.config import settings
import urllib.request
import json
import re

router = APIRouter(prefix="/navigation", tags=["navigation"])

def clean_html(raw_html):
    """Remove HTML tags from Google Directions instructions."""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext

@router.get("/route")
async def get_route(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float
):
    api_key = settings.GOOGLE_MAPS_API_KEY
    if not api_key:
        raise HTTPException(status_code=500, detail="Google Maps API Key not configured")

    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin_lat},{origin_lng}&destination={dest_lat},{dest_lng}&key={api_key}&mode=driving"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
        if data["status"] != "OK":
            return HTTPException(status_code=400, detail=f"Google API Error: {data.get('status')}")

        # Process the data to simplify for mobile
        route = data["routes"][0]
        leg = route["legs"][0]
        
        processed_steps = []
        for step in leg["steps"]:
            processed_steps.append({
                "instruction": clean_html(step["html_instructions"]),
                "distance_text": step["distance"]["text"],
                "distance_value": step["distance"]["value"], # in meters
                "duration_text": step["duration"]["text"],
                "duration_value": step["duration"]["value"], # in seconds
                "start_location": step["start_location"],
                "end_location": step["end_location"],
                "maneuver": step.get("maneuver", "straight")
            })

        return {
            "status": "success",
            "polyline": route["overview_polyline"]["points"],
            "steps": processed_steps,
            "total_distance": leg["distance"]["text"],
            "total_duration": leg["duration"]["text"],
            "total_distance_meters": leg["distance"]["value"],
            "total_duration_seconds": leg["duration"]["value"],
            "bounds": route["bounds"],
            "destination_name": leg.get("end_address", "Destination")
        }
    except Exception as e:
        print(f"❌ Navigation API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
