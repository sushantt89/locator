from pymongo import MongoClient
from datetime import datetime

def get_db():
    client = MongoClient(
        "mongodb+srv://sushantmaharjan89_db_user:OQkiiTykyjeKiJYt@locator.9kzckuz.mongodb.net/locator?retryWrites=true&w=majority&appName=Locator"
    )
    db = client["locator"]
    return db


def save_listings(collection_name, listings):
    db = get_db()
    collection = db[collection_name]
    
    for listing in listings:
        listing["scraped_at"] = datetime.utcnow()
        
        # Define the unique key
        query = {
            "company": listing.get("company"),
            "title": listing.get("title"),
            "location": listing.get("location")
        }

        # Update or insert
        collection.update_one(
            query,
            {"$set": listing},
            upsert=True
        )


def get_listings(collection_name, query=None):
    db = get_db()
    collection = db[collection_name]
    return list(collection.find(query or {}))


def update_listing(collection_name, company, title, location, updated_data):
    db = get_db()
    collection = db[collection_name]
    updated_data["scraped_at"] = datetime.utcnow()
    
    query = {
        "company": company,
        "title": title,
        "location": location
    }

    collection.update_one(
        query,
        {"$set": updated_data},
        upsert=True
    )
