# geocode.py
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

def get_coordinates(address):
    geolocator = Nominatim(user_agent="locator_app")
    try:
        location = geolocator.geocode(address + ", Australia", exactly_one=True, timeout=10)
        if not location:
            return None, None, "sydney"

        lat, lon = location.latitude, location.longitude
        raw = location.raw
        address = raw.get("address", {})

        city = (
            address.get("city") or
            address.get("town") or
            address.get("suburb") or
            address.get("village") or
            address.get("county") or
            raw.get("display_name", "").split(",")[0].strip()
        ).lower().replace(" ", "-")

        if not city or city == "":
            parts = raw.get("display_name", "").split(",")
            city = parts[0].strip().lower().replace(" ", "-") if parts else "sydney"

        return lat, lon, city

    except Exception as e:
        print(f"Geocoding failed: {e}")
        return None, None, "sydney"


def filter_by_radius(results, user_lat, user_lon, radius_km):
    if user_lat is None or user_lon is None:
        return results

    filtered = []
    for result in results:
        loc_str = result.get("location")
        if not loc_str:
            continue

        lat2, lon2, _ = get_coordinates(loc_str)
        if lat2 and lon2:
            dist = geodesic((user_lat, user_lon), (lat2, lon2)).km
            if dist <= radius_km:
                filtered.append(result)
    return filtered