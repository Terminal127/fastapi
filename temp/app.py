from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from bson import ObjectId
from typing import List
import motor.motor_asyncio
import asyncio

# Initialize FastAPI app
app = FastAPI(title="Simple Shop API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection configuration
uri = "mongodb+srv://terminalishere127:hello@cluster0.ezhgpwx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Create async MongoDB client with timeout settings
client = motor.motor_asyncio.AsyncIOMotorClient(
    uri,
    serverSelectionTimeoutMS=5000,  # 5 second timeout for server selection
    connectTimeoutMS=5000,  # 5 second timeout for initial connection
    socketTimeoutMS=5000,  # 5 second timeout for socket operations
)
db = client["shopdb"]
items_collection = db["items"]

class Item(BaseModel):
    name: str
    price: float
    seller: str

class ItemResponse(Item):
    id: str

@app.on_event("startup")
async def startup_db_client():
    try:
        # Test the connection during startup
        await client.admin.command('ping')
        print("✅ MongoDB connection successful")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        raise

@app.get("/", response_model=dict)
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "API is running"}

@app.post("/items", response_model=ItemResponse)
async def create_item(item: Item):
    try:
        result = await items_collection.insert_one(item.dict())
        return {
            "id": str(result.inserted_id),
            **item.dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create item: {str(e)}")

@app.get("/items", response_model=List[ItemResponse])
async def get_items():
    try:
        cursor = items_collection.find()
        items = await cursor.to_list(length=100)  # Limit to 100 items per request for better performance
        return [{
            "id": str(item["_id"]),
            "name": item["name"],
            "price": item["price"],
            "seller": item["seller"]
        } for item in items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch items: {str(e)}")

@app.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: str):
    try:
        item = await items_collection.find_one({"_id": ObjectId(item_id)})
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return {
            "id": str(item["_id"]),
            "name": item["name"],
            "price": item["price"],
            "seller": item["seller"]
        }
    except Exception as e:
        if "Invalid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid item ID format")
        raise HTTPException(status_code=500, detail=f"Failed to fetch item: {str(e)}")

@app.delete("/items/{item_id}")
async def delete_item(item_id: str):
    try:
        result = await items_collection.delete_one({"_id": ObjectId(item_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"status": "success", "message": "Item deleted successfully"}
    except Exception as e:
        if "Invalid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid item ID format")
        raise HTTPException(status_code=500, detail=f"Failed to delete item: {str(e)}")
