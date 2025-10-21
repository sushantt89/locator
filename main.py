from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from geocode import get_coordinates
from scrapers import scrape_seek_jobs, search_domain_accommodations
from database import save_listings, get_listings

app = FastAPI(title="Locator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/search")
async def search(address: str, radius: int = 10, category: str = "accommodation", keywords: str = ""):
    lat, lon = get_coordinates(address)
    if not lat or not lon:
        return {"error": "Invalid address"}
    
    collection_map = {
        "accommodation": "accommodations",
        "part-time": "jobs",
        "professional": "jobs",
        "aged-care": "jobs"
    }
    collection = collection_map.get(category, "jobs")
    
    # Check cache
    cached = get_listings(collection, {"category": category})
    if cached:
        return {"results": cached}
    
    # Scrape new data
    results = []
    if category == "accommodation":
        results = search_domain_accommodations(lat, lon, radius, "YOUR_API_KEY")  # Replace with key
    else:
        results = scrape_seek_jobs(address, radius, keywords, category)
    
    if results:
        save_listings(collection, results)
    return {"results": results}