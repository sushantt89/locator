from pymongo import MongoClient
from datetime import datetime

def get_db():
    client = MongoClient("mongodb+srv://sushantmaharjan89_db_user:OQkiiTykyjeKiJYt@locator.9kzckuz.mongodb.net/locator?retryWrites=true&w=majority&appName=Locator")
    db = client["locator"]
    return db

def save_listings(collection_name, listings):
    db = get_db()
    collection = db[collection_name]
    for listing in listings:
        listing["scraped_at"] = datetime.utcnow()
        collection.update_one(
            {"link": listing["link"]},  # Match by unique link
            {"$set": listing},  # Update all fields
            upsert=True
        )

def get_listings(collection_name, query=None):
    db = get_db()
    collection = db[collection_name]
    return list(collection.find(query or {}))

def update_listing(collection_name, link, updated_data):
    db = get_db()
    collection = db[collection_name]
    updated_data["scraped_at"] = datetime.utcnow()
    collection.update_one(
        {"link": link},
        {"$set": updated_data},
        upsert=True
    )