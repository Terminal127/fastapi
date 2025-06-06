from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from pydantic import BaseModel, Field
import motor.motor_asyncio
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Dict, Any, List, Optional
import asyncio
import json
import logging
from datetime import datetime, timedelta
import io
import qrcode
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import seaborn as sns
import pandas as pd
import hashlib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import httpx
from collections import defaultdict, Counter
import uuid
import csv
from io import StringIO
import base64
import psutil

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Track startup time for uptime calculation
import time
startup_time = time.time()

# MongoDB Setup
uri = "mongodb+srv://terminalishere127:hello@cluster0.ezhgpwx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = motor.motor_asyncio.AsyncIOMotorClient(uri)
db = client["shopdb"]
items_collection = db["items"]
# New collections for cool features
analytics_collection = db["analytics"]
notifications_collection = db["notifications"]
webhooks_collection = db["webhooks"]
alerts_collection = db["alerts"]
reports_collection = db["reports"]
inventory_events_collection = db["inventory_events"]

# FastAPI App
app = FastAPI(
    title="🚀 Smart Inventory System Pro",
    description="Advanced AI-powered inventory management with analytics, alerts, and automation",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enhanced data models
class MessageInput(BaseModel):
    message: str
    session_id: str = "default"

class WebhookConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    events: List[str] = ["item_added", "item_deleted", "low_stock", "price_change"]
    secret: Optional[str] = None

class AlertConfig(BaseModel):
    name: str
    condition: str  # "low_stock", "high_price", "duplicate_items"
    threshold: Optional[float] = None
    email: Optional[str] = None
    webhook_url: Optional[str] = None

class BulkOperation(BaseModel):
    operation: str  # "add", "update", "delete"
    items: List[Dict[str, Any]]

class InventoryFilter(BaseModel):
    seller: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    name_contains: Optional[str] = None
    sort_by: str = "name"  # "name", "price", "seller", "date_added"
    sort_order: str = "asc"  # "asc", "desc"

# Global state for cool features
notification_subscribers = set()
webhook_configs = []
active_alerts = {}

# In-memory chat history storage (up to 5 messages per session)
chat_history_store = {}

# Pydantic Request Model
class MessageInput(BaseModel):
    message: str
    session_id: str = "default"  # Optional session ID for multiple users

# Async database function
async def add_item_to_db(name: str, price: float, seller: str) -> Dict[str, Any]:
    if not name or not seller:
        return {"success": False, "message": "Name and seller are required"}
    
    if price <= 0:
        return {"success": False, "message": "Price must be greater than 0"}
    
    try:
        item = {"name": name, "price": price, "seller": seller}
        await items_collection.insert_one(item)
        return {
            "success": True,
            "message": f"✅ Successfully added {name} for ${price:.2f} from seller {seller}"
        }
    except Exception as e:
        return {"success": False, "message": f"❌ DB Error: {str(e)}"}

# Async delete function
async def delete_item_in_db(name: str, target_seller: str = None) -> Dict[str, Any]:
    if not name:
        return {"success": False, "message": "Item name is required for deletion"}
    
    try:
        # First, find all items with this name to check for duplicates
        all_items = await items_collection.find({"name": {"$regex": f"^{name}$", "$options": "i"}}).to_list(100)
        
        if not all_items:
            return {"success": False, "message": f"Item '{name}' not found"}
        
        # If multiple items found and no specific seller mentioned
        if len(all_items) > 1 and not target_seller:
            sellers_list = [f"• {item['name']} - ${item['price']:.2f} (Seller: {item['seller']})" for item in all_items]
            return {
                "success": False, 
                "message": f"⚠️ Multiple '{name}' items found! Please specify which seller to delete:\n\n" + "\n".join(sellers_list) + f"\n\nExample: 'delete {name} from seller [SellerName]'"
            }
        
        # Find the specific item to delete
        if target_seller:
            # Look for item with specific seller
            existing_item = None
            for item in all_items:
                if item['seller'].lower() == target_seller.lower():
                    existing_item = item
                    break
            if not existing_item:
                available_sellers = [item['seller'] for item in all_items]
                return {
                    "success": False, 
                    "message": f"❌ No '{name}' found from seller '{target_seller}'. Available sellers: {', '.join(available_sellers)}"
                }
        else:
            # Only one item found, use it
            existing_item = all_items[0]
        
        # Delete the specific item
        result = await items_collection.delete_one({"_id": existing_item["_id"]})
        
        if result.deleted_count > 0:
            return {
                "success": True,
                "message": f"✅ Successfully deleted {name} (${existing_item['price']:.2f}) from seller {existing_item['seller']}"
            }
        else:
            return {"success": False, "message": f"Failed to delete {name}"}
            
    except Exception as e:
        return {"success": False, "message": f"❌ DB Error: {str(e)}"}

# NEW: Async update function
async def update_item_in_db(name: str, new_price: float, target_seller: str = None) -> Dict[str, Any]:
    """Update an existing item's price with smart duplicate handling"""
    if not name:
        return {"success": False, "message": "Item name is required for update"}
    if new_price <= 0:
        return {"success": False, "message": "Price must be greater than 0"}
    
    try:
        # First, find all items with this name to check for duplicates
        all_items = await items_collection.find({"name": {"$regex": f"^{name}$", "$options": "i"}}).to_list(100)
        
        if not all_items:
            return {"success": False, "message": f"Item '{name}' not found"}
        
        # If multiple items found and no specific seller mentioned
        if len(all_items) > 1 and not target_seller:
            sellers_list = [f"• {item['name']} - ${item['price']:.2f} (Seller: {item['seller']})" for item in all_items]
            return {
                "success": False, 
                "message": f"⚠️ Multiple '{name}' items found! Please specify which seller to update:\n\n" + "\n".join(sellers_list) + f"\n\nExample: 'update {name} price to $10 from seller [SellerName]'"
            }
        
        # Find the specific item to update
        if target_seller:
            # Look for item with specific seller
            existing_item = None
            for item in all_items:
                if item['seller'].lower() == target_seller.lower():
                    existing_item = item
                    break
            if not existing_item:
                available_sellers = [item['seller'] for item in all_items]
                return {
                    "success": False, 
                    "message": f"❌ No '{name}' found from seller '{target_seller}'. Available sellers: {', '.join(available_sellers)}"
                }
        else:
            # Only one item found, use it
            existing_item = all_items[0]
        
        # Update the specific item
        old_price = existing_item['price']
        result = await items_collection.update_one(
            {"_id": existing_item["_id"]}, 
            {"$set": {"price": new_price}}
        )
        
        if result.modified_count > 0:
            return {
                "success": True,
                "message": f"✅ Updated {name} price from ${old_price:.2f} to ${new_price:.2f} (Seller: {existing_item['seller']})"
            }
        else:
            return {"success": False, "message": f"Failed to update {name}"}
            
    except Exception as e:
        return {"success": False, "message": f"❌ DB Error: {str(e)}"}

# NEW: Async bulk delete function for complex queries
async def bulk_delete_items(query_type: str, item_name: str = None, seller_name: str = None, condition: str = None) -> Dict[str, Any]:
    """
    Handle complex deletion queries:
    - delete_all_from_seller: Delete all items from a specific seller
    - delete_sellers_with_only_item: Delete all sellers who only sell a specific item
    - delete_all_items_named: Delete all items with a specific name regardless of seller
    """
    try:
        if query_type == "delete_all_from_seller":
            if not seller_name:
                return {"success": False, "message": "Seller name is required"}
            
            # Find all items from this seller
            items_to_delete = await items_collection.find({"seller": {"$regex": f"^{seller_name}$", "$options": "i"}}).to_list(100)
            if not items_to_delete:
                return {"success": False, "message": f"No items found from seller '{seller_name}'"}
            
            # Delete all items from this seller
            result = await items_collection.delete_many({"seller": {"$regex": f"^{seller_name}$", "$options": "i"}})
            item_names = [item['name'] for item in items_to_delete]
            return {
                "success": True,
                "message": f"✅ Deleted {result.deleted_count} items from seller '{seller_name}': {', '.join(item_names)}"
            }
            
        elif query_type == "delete_sellers_with_only_item":
            if not item_name:
                return {"success": False, "message": "Item name is required"}
            
            # Get all sellers and their items
            all_items = await items_collection.find({}).to_list(1000)
            seller_items = {}
            for item in all_items:
                seller = item['seller']
                if seller not in seller_items:
                    seller_items[seller] = []
                seller_items[seller].append(item['name'].lower())
            
            # Find sellers who only sell the specified item
            sellers_to_delete = []
            for seller, items in seller_items.items():
                unique_items = set(items)
                if len(unique_items) == 1 and item_name.lower() in unique_items:
                    sellers_to_delete.append(seller)
            
            if not sellers_to_delete:
                return {"success": False, "message": f"No sellers found who only sell '{item_name}'"}
            
            # Delete all items from these sellers
            total_deleted = 0
            for seller in sellers_to_delete:
                result = await items_collection.delete_many({"seller": seller})
                total_deleted += result.deleted_count
            
            return {
                "success": True,
                "message": f"✅ Deleted {total_deleted} items from {len(sellers_to_delete)} sellers who only sold '{item_name}': {', '.join(sellers_to_delete)}"
            }
            
        elif query_type == "delete_all_items_named":
            if not item_name:
                return {"success": False, "message": "Item name is required"}
            
            # Delete all items with this name regardless of seller
            result = await items_collection.delete_many({"name": {"$regex": f"^{item_name}$", "$options": "i"}})
            if result.deleted_count == 0:
                return {"success": False, "message": f"No items named '{item_name}' found"}
            
            return {
                "success": True,
                "message": f"✅ Deleted {result.deleted_count} items named '{item_name}' from all sellers"
            }
            
        else:
            return {"success": False, "message": f"Unknown query type: {query_type}"}
            
    except Exception as e:
        return {"success": False, "message": f"❌ DB Error: {str(e)}"}

# NEW: Async bulk update function
async def bulk_update_items(query_type: str, new_price: float = None, seller_name: str = None, item_name: str = None, price_multiplier: float = None) -> Dict[str, Any]:
    """
    Handle bulk update operations:
    - update_all_from_seller: Update all items from a specific seller
    - update_all_items_named: Update all items with specific name
    - update_prices_by_percentage: Update all prices by a percentage
    """
    try:
        if query_type == "update_all_from_seller":
            if not seller_name or not new_price:
                return {"success": False, "message": "Seller name and new price are required"}
            
            if new_price <= 0:
                return {"success": False, "message": "Price must be greater than 0"}
            
            # Update all items from this seller
            result = await items_collection.update_many(
                {"seller": {"$regex": f"^{seller_name}$", "$options": "i"}},
                {"$set": {"price": new_price}}
            )
            
            if result.matched_count == 0:
                return {"success": False, "message": f"No items found from seller '{seller_name}'"}
            
            return {
                "success": True,
                "message": f"✅ Updated {result.modified_count} items from seller '{seller_name}' to ${new_price:.2f}"
            }
            
        elif query_type == "update_all_items_named":
            if not item_name or not new_price:
                return {"success": False, "message": "Item name and new price are required"}
            
            if new_price <= 0:
                return {"success": False, "message": "Price must be greater than 0"}
            
            # Update all items with this name
            result = await items_collection.update_many(
                {"name": {"$regex": f"^{item_name}$", "$options": "i"}},
                {"$set": {"price": new_price}}
            )
            
            if result.matched_count == 0:
                return {"success": False, "message": f"No items named '{item_name}' found"}
            
            return {
                "success": True,
                "message": f"✅ Updated {result.modified_count} items named '{item_name}' to ${new_price:.2f}"
            }
            
        elif query_type == "update_prices_by_percentage":
            if not price_multiplier:
                return {"success": False, "message": "Price multiplier is required"}
            
            # Get all items and update their prices
            all_items = await items_collection.find({}).to_list(1000)
            if not all_items:
                return {"success": False, "message": "No items found to update"}
            
            updated_count = 0
            for item in all_items:
                new_price = item['price'] * price_multiplier
                await items_collection.update_one(
                    {"_id": item["_id"]},
                    {"$set": {"price": new_price}}
                )
                updated_count += 1
            
            percentage_change = (price_multiplier - 1) * 100
            return {
                "success": True,
                "message": f"✅ Updated {updated_count} item prices by {percentage_change:+.1f}%"
            }
            
        else:
            return {"success": False, "message": f"Unknown query type: {query_type}"}
            
    except Exception as e:
        return {"success": False, "message": f"❌ DB Error: {str(e)}"}

# NEW: Async bulk add function
async def bulk_add_items(items_data: list) -> Dict[str, Any]:
    """Add multiple items at once"""
    try:
        if not items_data:
            return {"success": False, "message": "No items provided"}
        
        # Validate all items first
        valid_items = []
        for item_data in items_data:
            name = item_data.get('name', '').strip()
            price = item_data.get('price', 0)
            seller = item_data.get('seller', '').strip()
            
            if not name or not seller:
                return {"success": False, "message": f"Invalid item data: name and seller required for all items"}
            if price <= 0:
                return {"success": False, "message": f"Invalid price for '{name}': must be greater than 0"}
            
            valid_items.append({"name": name, "price": price, "seller": seller})
        
        # Insert all items
        result = await items_collection.insert_many(valid_items)
        
        # Create summary message
        item_summary = []
        for item in valid_items:
            item_summary.append(f"• {item['name']} - ${item['price']:.2f} (Seller: {item['seller']})")
        
        return {
            "success": True,
            "message": f"✅ Successfully added {len(valid_items)} items:\n" + "\n".join(item_summary)
        }
        
    except Exception as e:
        return {"success": False, "message": f"❌ DB Error: {str(e)}"}

# LangChain tool using the @tool decorator (much simpler approach)
@tool
async def add_item(name: str, price: float, seller: str) -> str:
    """Add an item to the inventory with name, price, and seller information.
    
    Args:
        name: The name of the item to add
        price: The price of the item (must be positive)
        seller: The name of the seller
      Returns:
        A success or error message
    """
    try:
        result = await add_item_to_db(name, price, seller)
        return result["message"]
    except Exception as e:
        return f"❌ Error adding item: {str(e)}"

@tool
async def delete_item(name: str, target_seller: str = None) -> str:
    """Delete an item from the inventory by name and optionally by seller.
    
    Args:
        name: The name of the item to delete (required)
        target_seller: The seller name to identify which item to delete (optional, use when multiple items have same name)
    
    Returns:
        A success or error message
    """
    try:
        result = await delete_item_in_db(name, target_seller)
        return result["message"]
    except Exception as e:
        return f"❌ Error deleting item: {str(e)}"

@tool
async def bulk_delete(query_type: str, item_name: str = None, seller_name: str = None) -> str:
    """Handle complex deletion operations.
    
    Args:
        query_type: Type of bulk deletion:
            - "delete_all_from_seller": Delete all items from a specific seller
            - "delete_sellers_with_only_item": Delete all sellers who only sell a specific item
            - "delete_all_items_named": Delete all items with a specific name
        item_name: Name of the item (required for some query types)
        seller_name: Name of the seller (required for some query types)
    
    Returns:
        A success or error message
    """
    try:
        result = await bulk_delete_items(query_type, item_name, seller_name)
        return result["message"]
    except Exception as e:
        return f"❌ Error in bulk delete: {str(e)}"

@tool
async def bulk_update(query_type: str, new_price: float = None, seller_name: str = None, item_name: str = None, price_multiplier: float = None) -> str:
    """Handle bulk update operations.
    
    Args:
        query_type: Type of bulk update:
            - "update_all_from_seller": Update all items from a specific seller
            - "update_all_items_named": Update all items with specific name
            - "update_prices_by_percentage": Update all prices by a percentage
        new_price: New price to set (required for price updates)
        seller_name: Name of the seller (required for seller updates)
        item_name: Name of the item (required for item updates)
        price_multiplier: Multiplier for percentage updates (e.g., 1.1 for 10% increase)
    
    Returns:
        A success or error message
    """
    try:
        result = await bulk_update_items(query_type, new_price, seller_name, item_name, price_multiplier)
        return result["message"]
    except Exception as e:
        return f"❌ Error in bulk update: {str(e)}"

@tool
async def bulk_add(items_list: str) -> str:
    """Add multiple items at once from a formatted string.
    
    Args:
        items_list: A JSON string containing list of items with name, price, and seller
                   Format: '[{"name": "apple", "price": 5.0, "seller": "John"}, ...]'
    
    Returns:
        A success or error message
    """
    try:
        import json
        items_data = json.loads(items_list)
        result = await bulk_add_items(items_data)
        return result["message"]
    except json.JSONDecodeError:
        return "❌ Error: Invalid JSON format for items list"
    except Exception as e:
        return f"❌ Error in bulk add: {str(e)}"

@tool
async def update_item(name: str, new_price: float, target_seller: str = None) -> str:
    """Update an existing item's price, with optional seller specification.
    
    Args:
        name: The name of the item to update
        new_price: The new price for the item
        target_seller: The seller name to identify which item to update (optional, use when multiple items have same name)
    
    Returns:
        A success or error message
    """
    try:
        result = await update_item_in_db(name, new_price, target_seller)
        return result["message"]
    except Exception as e:
        return f"❌ Error updating item: {str(e)}"

# Tools list
tools = [add_item, delete_item, bulk_delete, bulk_update, bulk_add, update_item]

# Gemini Model Setup
model = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.3,
    google_api_key="AIzaSyDsi82MHuNMwZyUoJ5q6xN8yd9Q4yBw5gM",
    convert_system_message_to_human=True
)

# Prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an intelligent inventory assistant that can handle simple and complex operations.
    
    AVAILABLE TOOLS:
    1. add_item(name, price, seller) - Add single item
    2. update_item(name, new_price, target_seller) - Update single item
    3. delete_item(name, target_seller) - Delete single item
    4. bulk_add(items_list) - Add multiple items at once
    5. bulk_update(query_type, new_price, seller_name, item_name, price_multiplier) - Bulk updates
    6. bulk_delete(query_type, item_name, seller_name) - Complex deletions
    
    COMPLEX QUERY EXAMPLES AND HOW TO HANDLE:
      📦 BULK ADDITIONS:
    "add 3 apples for $5 from John and 2 bananas for $3 from Sarah"
    → Call bulk_add with: '[{{"name":"apple","price":5,"seller":"John"}},{{"name":"apple","price":5,"seller":"John"}},{{"name":"apple","price":5,"seller":"John"}},{{"name":"banana","price":3,"seller":"Sarah"}},{{"name":"banana","price":3,"seller":"Sarah"}}]'
    
    🗑️ COMPLEX DELETIONS:
    "delete all items from Mike" → bulk_delete("delete_all_from_seller", seller_name="Mike")
    "delete all persons selling only bottle" → bulk_delete("delete_sellers_with_only_item", item_name="bottle")
    "delete all apples" → bulk_delete("delete_all_items_named", item_name="apple")
    "remove bottle from Debjut" → delete_item("bottle", target_seller="Debjut")
    
    🔄 COMPLEX UPDATES:
    "update all items from John to $10" → bulk_update("update_all_from_seller", new_price=10, seller_name="John")
    "change all apple prices to $8" → bulk_update("update_all_items_named", new_price=8, item_name="apple")
    "increase all prices by 20%" → bulk_update("update_prices_by_percentage", price_multiplier=1.2)
    "decrease all prices by 10%" → bulk_update("update_prices_by_percentage", price_multiplier=0.9)
    "update bottle price to $5 from Mike" → update_item("bottle", 5, target_seller="Mike")
    
    🔗 COMBINED OPERATIONS:
    "add phone for $500 from Alex and delete all items from old sellers and update all apple prices to $6"
    → Execute multiple tool calls in sequence
    
    PARSING GUIDELINES:
    1. **Identify operation type**: Look for keywords like add/create, update/change, delete/remove
    2. **Detect bulk operations**: Words like "all", "every", "multiple", numbers (3 apples)
    3. **Extract entities**: item names, prices, seller names, conditions
    4. **Handle seller specification**: "from X", "sold by X", "by X", "seller X"
    5. **Parse price changes**: "to $X", "by X%", "increase/decrease"
    6. **Handle complex conditions**: "only selling X", "all items from Y"
    
    IMPORTANT EXTRACTION RULES:
    - For percentages: "increase by 20%" → multiplier = 1.2, "decrease by 10%" → multiplier = 0.9
    - For bulk adds with quantities: "3 apples for $5" → create 3 separate apple entries
    - For "only selling X": Use bulk_delete with "delete_sellers_with_only_item"
    - For "all items from seller": Use bulk_delete with "delete_all_from_seller"
    - Always preserve exact seller names and item names from user input
    
    If any information is missing or ambiguous, ask for clarification before proceeding.
    """),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create agent
agent = create_openai_tools_agent(model, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Smart Inventory Endpoint
@app.post("/smart-add")
async def smart_add(message_input: MessageInput):
    try:
        # Get or initialize chat history for this session
        session_id = message_input.session_id
        if session_id not in chat_history_store:
            chat_history_store[session_id] = []
        
        # Get current chat history (limit to last 4 messages to keep room for new one)
        current_history = chat_history_store[session_id][-4:]
        
        # Run the agent with chat history
        result = await agent_executor.ainvoke({
            "input": message_input.message,
            "chat_history": current_history
        })
        
        output = result.get("output", "")
        if not output:
            raise ValueError("No response from agent")
        
        # Add current conversation to history
        current_history.extend([
            ("human", message_input.message),
            ("assistant", output)
        ])
        
        # Keep only last 5 messages (10 entries = 5 human + 5 assistant)
        chat_history_store[session_id] = current_history[-10:]
            
        return {
            "status": "success",
            "result": output,
            "details": {
                "processed": True,
                "message": message_input.message,
                "session_id": session_id,
                "history_length": len(chat_history_store[session_id]) // 2
            }
        }
    except Exception as e:
        error_msg = str(e)
        return {
            "status": "error",
            "result": f"Failed to process: {error_msg}",
            "details": {
                "error": error_msg,
                "help": "Please provide item name, price, and seller (e.g., 'add apple for $5 from John') or delete instructions (e.g., 'delete bottle from Debjut')"
            }
        }

# Health check endpoint
@app.get("/")
async def root():
    return {"message": "Smart Inventory API is running!", "version": "1.0"}

# Manual add endpoint for testing
@app.post("/add-item")
async def manual_add(name: str, price: float, seller: str):
    result = await add_item_to_db(name, price, seller)
    return result

# Get all items endpoint
@app.get("/items")
async def get_items():
    try:
        items = await items_collection.find({}).to_list(100)
        # Convert ObjectId to string for JSON serialization
        for item in items:
            item["_id"] = str(item["_id"])
        return {"items": items, "count": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch items: {str(e)}")


# NEW: Webhook to receive real-time notifications
@app.post("/webhook/{webhook_id}")
async def receive_webhook(webhook_id: str, payload: dict):
    """Receive real-time notifications via webhook"""
    try:
        # Find the webhook config
        webhook_config = next((config for config in webhook_configs if config["id"] == webhook_id), None)
        if not webhook_config:
            return {"success": False, "message": "Webhook not found"}
        
        # Validate the payload (basic example, extend as needed)
        required_fields = ["event", "data"]
        for field in required_fields:
            if field not in payload:
                return {"success": False, "message": f"Missing field: {field}"}
        
        # Process the event (basic example, extend as needed)
        event_type = payload["event"]
        event_data = payload["data"]
        
        if event_type == "item_added":
            # Example: Log the new item addition
            logger.info(f"New item added: {event_data}")
        elif event_type == "item_deleted":
            # Example: Log the item deletion
            logger.info(f"Item deleted: {event_data}")
        elif event_type == "low_stock":
            # Example: Trigger an alert for low stock
            logger.warning(f"Low stock alert: {event_data}")
        elif event_type == "price_change":
            # Example: Log the price change
            logger.info(f"Price change: {event_data}")
        else:
            logger.warning(f"Unknown event type: {event_type}")
        
        return {"success": True, "message": "Webhook received"}
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}

# NEW: Configure a webhook
@app.post("/webhook-config")
async def configure_webhook(config: WebhookConfig):
    """Configure a webhook for real-time notifications"""
    try:
        # Check for existing config
        existing_config = next((c for c in webhook_configs if c["id"] == config.id), None)
        if existing_config:
            return {"success": False, "message": "Webhook with this ID already exists"}
        
        # Add the new config
        webhook_configs.append(config.dict())
        
        return {
            "success": True,
            "message": "Webhook configured successfully",
            "data": config
        }
    except Exception as e:
        return {"success": False, "message": f"Error configuring webhook: {str(e)}"}

# NEW: Trigger an event (for testing)
@app.post("/trigger-event")
async def trigger_event(event_type: str, item_id: str = None):
    """Trigger a test event to all configured webhooks"""
    try:
        # Create a sample payload
        payload = {
            "event": event_type,
            "data": {
                "item_id": item_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Send the payload to all configured webhooks
        for config in webhook_configs:
            webhook_url = config["url"]
            async with httpx.AsyncClient() as client:
                await client.post(webhook_url, json=payload)
        
        return {"success": True, "message": "Event triggered", "payload": payload}
    except Exception as e:
        return {"success": False, "message": f"Error triggering event: {str(e)}"}

# NEW: Create an alert
@app.post("/alert")
async def create_alert(alert: AlertConfig):
    """Create a new alert for inventory events"""
    try:
        # Generate a unique ID for the alert
        alert_id = str(uuid.uuid4())
        
        # Add the alert to the active alerts
        active_alerts[alert_id] = alert.dict()
        
        return {
            "success": True,
            "message": "Alert created",
            "alert_id": alert_id
        }
    except Exception as e:
        return {"success": False, "message": f"Error creating alert: {str(e)}"}

# NEW: Check alerts (for testing)
@app.get("/check-alerts")
async def check_alerts():
    """Check and trigger active alerts"""
    try:
        # Example: Check for low stock alerts (extend logic as needed)
        for alert_id, alert in active_alerts.items():
            if alert["condition"] == "low_stock":
                # Find items for this seller
                items = await items_collection.find({"seller": alert["seller"]}).to_list(100)
                
                # Check stock level (example: trigger if any item is below the threshold)
                for item in items:
                    if item["stock"] < alert["threshold"]:
                        # Trigger the alert (e.g., send email, call webhook)
                        if alert.get("email"):
                            # Send email notification (basic example, extend as needed)
                            send_email_alert(alert["email"], item)
                        
                        break  # Exit after triggering once
                
        return {"success": True, "message": "Alerts checked"}
    except Exception as e:
        return {"success": False, "message": f"Error checking alerts: {str(e)}"}

# NEW: Send email alert (helper function)
def send_email_alert(to_email: str, item: Dict[str, Any]):
    """Send an email alert for a low stock item"""
    try:
        # Email configuration (use env variables or config file in production)
        smtp_server = "smtp.example.com"
        smtp_port = 587
        smtp_user = "your_email@example.com"
        smtp_password = "your_password"
        
        # Create the email content
        subject = "Low Stock Alert: {}".format(item["name"])
        body = "The stock for item '{}' is low. Current stock: {}".format(item["name"], item["stock"])
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    except Exception as e:
        logger.error(f"Error sending email alert: {str(e)}")

# NEW: Analytics - Get item statistics
@app.get("/analytics/items")
async def get_item_statistics():
    """Get statistics about items in the inventory"""
    try:
        # Example: Return count of items, average price, etc.
        item_count = await items_collection.count_documents({})
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "average_price": {"$avg": "$price"},
                    "total_value": {"$sum": "$price"}
                }
            }
        ]
        stats = await items_collection.aggregate(pipeline).to_list(1)
        if stats:
            average_price = stats[0]["average_price"]
            total_value = stats[0]["total_value"]
        else:
            average_price = 0
            total_value = 0
        
        return {
            "success": True,
            "data": {
                "item_count": item_count,
                "average_price": average_price,
                "total_value": total_value
            }
        }
    except Exception as e:
        return {"success": False, "message": f"Error fetching analytics: {str(e)}"}

# NEW: Reports - Generate sales report (example)
@app.get("/reports/sales")
async def generate_sales_report():
    """Generate a sales report (example)"""
    try:
        # Example: Simple report - extend with real data and logic
        report_data = [
            {"item": "Apple", "quantity": 10, "total_sales": 50},
            {"item": "Banana", "quantity": 5, "total_sales": 30},
        ]
        
        # Convert to DataFrame for better formatting (optional)
        df = pd.DataFrame(report_data)
        
        # Generate a simple plot (example)
        plt.figure(figsize=(10, 6))
        sns.barplot(data=df, x="item", y="total_sales")
        plt.title("Sales Report")
        plt.xlabel("Item")
        plt.ylabel("Total Sales")
        
        # Save the plot to a BytesIO object
        img_bytes = io.BytesIO()
        plt.savefig(img_bytes, format='png')
        img_bytes.seek(0)
        
        # Convert plot to base64 string for embedding in report
        img_base64 = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
        
        return {
            "success": True,
            "message": "Sales report generated",
            "report": {
                "data": report_data,
                "chart": f"data:image/png;base64,{img_base64}"
            }
        }
    except Exception as e:
        return {"success": False, "message": f"Error generating report: {str(e)}"}

# NEW: Inventory optimization suggestion
@app.get("/optimize-inventory")
async def optimize_inventory():
    """Suggest optimization for inventory (example)"""
    try:
        # Example: Simple optimization suggestion - extend with real logic
        low_stock_items = await items_collection.find({"stock": {"$lt": 10}}).to_list(100)
        
        suggestions = []
        for item in low_stock_items:
            suggested_order_quantity = 10 - item["stock"]  # Example: Order enough to reach 10 in stock
            suggestions.append({
                "item": item["name"],
                "current_stock": item["stock"],
                "suggested_order_quantity": suggested_order_quantity
            })
        
        return {
            "success": True,
            "suggestions": suggestions
        }
    except Exception as e:
        return {"success": False, "message": f"Error optimizing inventory: {str(e)}"}

# NEW: Advanced search
@app.get("/search/items")
async def search_items(
    name: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    seller: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
):
    """Search for items with advanced filters"""
    try:
        # Build the query
        query = {}
        if name:
            query["name"] = {"$regex": name, "$options": "i"}
        if min_price is not None:
            query["price"] = {"$gte": min_price}
        if max_price is not None:
            query["price"] = {"$lte": max_price}
        if seller:
            query["seller"] = {"$regex": seller, "$options": "i"}
        
        # Sort order
        sort_order = 1 if sort_order == "asc" else -1
        
        # Execute the search
        items = await items_collection.find(query).sort(sort_by, sort_order).to_list(100)
        
        # Convert ObjectId to string for JSON serialization
        for item in items:
            item["_id"] = str(item["_id"])
        
        return {"items": items, "count": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search items: {str(e)}")

# NEW: Generate QR Code for item
@app.get("/qr-code/{item_id}")
async def generate_qr_code(item_id: str):
    """Generate QR code for an item"""
    try:
        # Find the item
        item = await items_collection.find_one({"_id": item_id})
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        # Create QR code data
        qr_data = {
            "id": str(item["_id"]),
            "name": item["name"],
            "price": item["price"],
            "seller": item["seller"]
        }
        qr_text = json.dumps(qr_data)
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_text)
        qr.make(fit=True)
        
        # Create QR code image
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        qr_img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return StreamingResponse(img_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate QR code: {str(e)}")

# NEW: Bulk operations
@app.post("/bulk-operations")
async def bulk_operations(operation: BulkOperation):
    """Perform bulk operations on items"""
    try:
        results = []
        
        if operation.operation == "add":
            for item_data in operation.items:
                result = await add_item_to_db(
                    item_data.get("name"),
                    item_data.get("price"),
                    item_data.get("seller")
                )
                results.append(result)
        
        elif operation.operation == "update":
            for item_data in operation.items:
                item_id = item_data.get("_id")
                update_data = {k: v for k, v in item_data.items() if k != "_id"}
                
                result = await items_collection.update_one(
                    {"_id": item_id},
                    {"$set": update_data}
                )
                results.append({
                    "success": result.modified_count > 0,
                    "message": f"Updated item {item_id}" if result.modified_count > 0 else f"No changes for item {item_id}"
                })
        
        elif operation.operation == "delete":
            for item_data in operation.items:
                item_id = item_data.get("_id")
                result = await items_collection.delete_one({"_id": item_id})
                results.append({
                    "success": result.deleted_count > 0,
                    "message": f"Deleted item {item_id}" if result.deleted_count > 0 else f"Item {item_id} not found"
                })
        
        return {
            "success": True,
            "message": f"Bulk {operation.operation} completed",
            "results": results
        }
    except Exception as e:
        return {"success": False, "message": f"Bulk operation failed: {str(e)}"}

# NEW: Export inventory to CSV
@app.get("/export/csv")
async def export_csv():
    """Export inventory data to CSV"""
    try:
        items = await items_collection.find({}).to_list(1000)
        
        # Create CSV content
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(["ID", "Name", "Price", "Seller", "Date Added"])
        
        # Write data
        for item in items:
            writer.writerow([
                str(item["_id"]),
                item["name"],
                item["price"],
                item["seller"],
                item.get("date_added", "N/A")
            ])
        
        # Create response
        csv_content = output.getvalue()
        output.close()
        
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=inventory.csv"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export CSV: {str(e)}")

# NEW: Import from CSV
@app.post("/import/csv")
async def import_csv(csv_data: str):
    """Import inventory data from CSV"""
    try:
        reader = csv.DictReader(StringIO(csv_data))
        imported_count = 0
        errors = []
        
        for row in reader:
            try:
                await add_item_to_db(
                    row.get("name", "").strip(),
                    float(row.get("price", 0)),
                    row.get("seller", "").strip()
                )
                imported_count += 1
            except Exception as e:
                errors.append(f"Row {reader.line_num}: {str(e)}")
        
        return {
            "success": True,
            "message": f"Imported {imported_count} items",
            "errors": errors
        }
    except Exception as e:
        return {"success": False, "message": f"CSV import failed: {str(e)}"}

# NEW: Advanced analytics with charts
@app.get("/analytics/charts")
async def get_analytics_charts():
    """Generate analytics charts"""
    try:
        items = await items_collection.find({}).to_list(1000)
        
        if not items:
            return {"success": False, "message": "No data available"}
        
        # Convert to DataFrame
        df = pd.DataFrame(items)
        
        charts = {}
        
        # 1. Price distribution histogram
        plt.figure(figsize=(10, 6))
        plt.hist(df['price'], bins=20, edgecolor='black', alpha=0.7)
        plt.title('Price Distribution')
        plt.xlabel('Price ($)')
        plt.ylabel('Frequency')
        
        img_bytes = io.BytesIO()
        plt.savefig(img_bytes, format='png', bbox_inches='tight')
        img_bytes.seek(0)
        charts['price_distribution'] = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
        plt.close()
        
        # 2. Items by seller (top 10)
        seller_counts = df['seller'].value_counts().head(10)
        plt.figure(figsize=(12, 6))
        seller_counts.plot(kind='bar')
        plt.title('Top 10 Sellers by Item Count')
        plt.xlabel('Seller')
        plt.ylabel('Number of Items')
        plt.xticks(rotation=45)
        
        img_bytes = io.BytesIO()
        plt.savefig(img_bytes, format='png', bbox_inches='tight')
        img_bytes.seek(0)
        charts['sellers_chart'] = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
        plt.close()
        
        # 3. Average price by seller
        avg_prices = df.groupby('seller')['price'].mean().sort_values(ascending=False).head(10)
        plt.figure(figsize=(12, 6))
        avg_prices.plot(kind='bar', color='green', alpha=0.7)
        plt.title('Average Price by Seller (Top 10)')        
        plt.xlabel('Seller')
        plt.ylabel('Average Price ($)')
        plt.xticks(rotation=45)
        
        img_bytes = io.BytesIO()
        plt.savefig(img_bytes, format='png', bbox_inches='tight')
        img_bytes.seek(0)
        charts['avg_price_by_seller'] = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
        plt.close()
        
        return {
            "success": True,
            "charts": charts,
            "stats": {
                "total_items": len(items),
                "total_sellers": df['seller'].nunique(),
                "avg_price": df['price'].mean(),
                "price_range": {
                    "min": df['price'].min(),
                    "max": df['price'].max()
                }
            }
        }
    except Exception as e:
        return {"success": False, "message": f"Failed to generate charts: {str(e)}"}

# NEW: Display charts as HTML page
@app.get("/analytics/charts-view", response_class=HTMLResponse)
async def get_charts_view():
    """Display analytics charts in a web page"""
    try:
        # Get chart data
        charts_data = await get_analytics_charts()
        
        if not charts_data["success"]:
            return "<h1>Error loading charts</h1>"
        
        charts = charts_data["charts"]
        stats = charts_data["stats"]
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Analytics Dashboard</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    background: #1a1a1a; 
                    color: white; 
                    margin: 0; 
                    padding: 20px; 
                }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .stats {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                    gap: 20px; 
                    margin-bottom: 30px; 
                }}
                .stat-card {{ 
                    background: #2a2a2a; 
                    padding: 20px; 
                    border-radius: 8px; 
                    text-align: center; 
                }}
                .stat-value {{ font-size: 2em; font-weight: bold; color: #4CAF50; }}
                .chart {{ margin-bottom: 30px; text-align: center; }}
                .chart img {{ max-width: 100%; border-radius: 8px; }}
                h1, h2 {{ color: #4CAF50; }}
                .refresh-btn {{ 
                    background: #4CAF50; 
                    color: white; 
                    border: none; 
                    padding: 10px 20px; 
                    border-radius: 5px; 
                    cursor: pointer; 
                    margin-bottom: 20px; 
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 Smart Inventory Analytics Dashboard</h1>
                <button class="refresh-btn" onclick="location.reload()">🔄 Refresh Data</button>
                
                <div class="stats">
                    <div class="stat-card">
                        <h3>Total Items</h3>
                        <div class="stat-value">{stats['total_items']}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Total Sellers</h3>
                        <div class="stat-value">{stats['total_sellers']}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Average Price</h3>
                        <div class="stat-value">${stats['avg_price']:.2f}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Price Range</h3>
                        <div class="stat-value">${stats['price_range']['min']:.2f} - ${stats['price_range']['max']:.2f}</div>
                    </div>
                </div>
                
                <div class="chart">
                    <h2>📈 Price Distribution</h2>
                    <img src="data:image/png;base64,{charts['price_distribution']}" alt="Price Distribution Chart" />
                </div>
                
                <div class="chart">
                    <h2>👥 Top Sellers by Item Count</h2>
                    <img src="data:image/png;base64,{charts['sellers_chart']}" alt="Sellers Chart" />
                </div>
                
                <div class="chart">
                    <h2>💰 Average Price by Seller</h2>
                    <img src="data:image/png;base64,{charts['avg_price_by_seller']}" alt="Average Price by Seller Chart" />
                </div>
                
                <p style="text-align: center; color: #666; margin-top: 40px;">
                    🔗 <a href="/analytics/system-stats" style="color: #4CAF50;">System Statistics</a> | 
                    <a href="/docs" style="color: #4CAF50;">API Documentation</a> | 
                    <a href="/" style="color: #4CAF50;">Back to Main</a>
                </p>
            </div>
        </body>
        </html>
        """
        
        return html_content
        
    except Exception as e:
        return f"<h1>Error: {str(e)}</h1>"

# NEW: System Statistics Endpoint
@app.get("/analytics/system-stats")
async def get_system_stats():
    """Get comprehensive system statistics"""
    try:
        import psutil
        import time
        from datetime import datetime
        
        # Database stats
        total_items = await items_collection.count_documents({})
        
        # Get unique sellers
        pipeline = [
            {"$group": {"_id": "$seller"}},
            {"$count": "total_sellers"}
        ]
        seller_stats = await items_collection.aggregate(pipeline).to_list(1)
        total_sellers = seller_stats[0]["total_sellers"] if seller_stats else 0
        
        # Price statistics
        price_pipeline = [
            {
                "$group": {
                    "_id": None,
                    "avg_price": {"$avg": "$price"},
                    "min_price": {"$min": "$price"},
                    "max_price": {"$max": "$price"},
                    "total_value": {"$sum": "$price"}
                }
            }
        ]
        price_stats = await items_collection.aggregate(price_pipeline).to_list(1)
        
        if price_stats:
            price_data = price_stats[0]
        else:
            price_data = {"avg_price": 0, "min_price": 0, "max_price": 0, "total_value": 0}
        
        # System metrics
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # API metrics (if available)
        api_uptime = time.time() - startup_time if 'startup_time' in globals() else 0
        
        return {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "total_items": total_items,
                "total_sellers": total_sellers,
                "total_inventory_value": price_data["total_value"],
                "price_statistics": {
                    "average": round(price_data["avg_price"], 2),
                    "minimum": price_data["min_price"],
                    "maximum": price_data["max_price"]
                }
            },
            "system": {
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "used_percent": round((disk.used / disk.total) * 100, 2)
                },
                "cpu_usage_percent": cpu_percent
            },
            "api": {
                "uptime_hours": round(api_uptime / 3600, 2),
                "active_webhooks": len(webhook_configs) if 'webhook_configs' in globals() else 0,
                "active_alerts": len(active_alerts) if 'active_alerts' in globals() else 0
            },
            "health_status": "healthy" if memory.percent < 85 and cpu_percent < 90 else "warning"
        }
        
    except Exception as e:
        return {"success": False, "message": f"Failed to get system stats: {str(e)}"}

# NEW: System Stats HTML View
@app.get("/analytics/system-stats-view", response_class=HTMLResponse)
async def get_system_stats_view():
    """Display system statistics in a web page"""
    try:
        stats_data = await get_system_stats()
        
        if not stats_data["success"]:
            return "<h1>Error loading system stats</h1>"
        
        stats = stats_data
        db = stats["database"]
        sys = stats["system"]
        api = stats["api"]
        
        # Health status color
        health_color = "#4CAF50" if stats["health_status"] == "healthy" else "#FF9800"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>System Statistics</title>
            <style>
                body {{ 
                    font-family: 'Courier New', monospace; 
                    background: #0a0a0a; 
                    color: #00ff00; 
                    margin: 0; 
                    padding: 20px; 
                }}
                .container {{ max-width: 800px; margin: 0 auto; }}
                .section {{ 
                    background: #1a1a1a; 
                    margin: 20px 0; 
                    padding: 20px; 
                    border: 1px solid #333; 
                    border-radius: 5px; 
                }}
                .metric {{ 
                    display: flex; 
                    justify-content: space-between; 
                    margin: 10px 0; 
                    padding: 5px 0; 
                    border-bottom: 1px dotted #333; 
                }}
                .metric-name {{ color: #00ffff; }}
                .metric-value {{ color: #ffff00; font-weight: bold; }}
                .health-good {{ color: #4CAF50; }}
                .health-warning {{ color: #FF9800; }}
                h1, h2 {{ color: #ff6b6b; text-align: center; }}
                .refresh {{ 
                    text-align: center; 
                    margin: 20px 0; 
                }}
                .refresh button {{ 
                    background: #333; 
                    color: #00ff00; 
                    border: 1px solid #666; 
                    padding: 10px 20px; 
                    cursor: pointer; 
                    font-family: inherit; 
                }}
                .timestamp {{ 
                    text-align: center; 
                    color: #666; 
                    font-size: 0.9em; 
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>⚡ System Statistics Monitor</h1>
                <div class="timestamp">Last Updated: {stats['timestamp']}</div>
                
                <div class="refresh">
                    <button onclick="location.reload()">🔄 Refresh Stats</button>
                </div>
                
                <div class="section">
                    <h2>📊 Database Statistics</h2>
                    <div class="metric">
                        <span class="metric-name">Total Items:</span>
                        <span class="metric-value">{db['total_items']}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-name">Total Sellers:</span>
                        <span class="metric-value">{db['total_sellers']}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-name">Inventory Value:</span>
                        <span class="metric-value">${db['total_inventory_value']:.2f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-name">Average Price:</span>
                        <span class="metric-value">${db['price_statistics']['average']}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-name">Price Range:</span>
                        <span class="metric-value">${db['price_statistics']['minimum']} - ${db['price_statistics']['maximum']}</span>
                    </div>
                </div>
                
                <div class="section">
                    <h2>💾 System Resources</h2>
                    <div class="metric">
                        <span class="metric-name">Memory Usage:</span>
                        <span class="metric-value">{sys['memory']['used_percent']}% ({sys['memory']['available_gb']:.1f}GB free)</span>
                    </div>
                    <div class="metric">
                        <span class="metric-name">Disk Usage:</span>
                        <span class="metric-value">{sys['disk']['used_percent']}% ({sys['disk']['free_gb']:.1f}GB free)</span>
                    </div>
                    <div class="metric">
                        <span class="metric-name">CPU Usage:</span>
                        <span class="metric-value">{sys['cpu_usage_percent']}%</span>
                    </div>
                </div>
                
                <div class="section">
                    <h2>🚀 API Statistics</h2>
                    <div class="metric">
                        <span class="metric-name">Uptime:</span>
                        <span class="metric-value">{api['uptime_hours']:.1f} hours</span>
                    </div>
                    <div class="metric">
                        <span class="metric-name">Active Webhooks:</span>
                        <span class="metric-value">{api['active_webhooks']}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-name">Active Alerts:</span>
                        <span class="metric-value">{api['active_alerts']}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-name">Health Status:</span>
                        <span class="metric-value" style="color: {health_color};">● {stats['health_status'].upper()}</span>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 40px;">
                    <a href="/analytics/charts-view" style="color: #00ffff;">📈 View Charts</a> | 
                    <a href="/health" style="color: #00ffff;">🔍 Health Check</a> | 
                    <a href="/docs" style="color: #00ffff;">📚 API Docs</a>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content
        
    except Exception as e:
        return f"<h1>Error: {str(e)}</h1>"

# NEW: Health check with detailed status
@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    try:
        # Check database connection
        db_status = "healthy"
        try:
            await items_collection.count_documents({})
        except Exception:
            db_status = "unhealthy"
        
        # Check system metrics
        item_count = await items_collection.count_documents({})
        
        # Memory usage (simplified)
        import psutil
        memory_usage = psutil.virtual_memory().percent
        
        return {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": db_status,
                "api": "healthy"
            },
            "metrics": {
                "total_items": item_count,
                "memory_usage_percent": memory_usage,
                "active_webhooks": len(webhook_configs),
                "active_alerts": len(active_alerts)
            },
            "version": "2.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

# NEW: Inventory insights and recommendations
@app.get("/insights")
async def get_inventory_insights():
    """Get intelligent insights about inventory"""
    try:
        items = await items_collection.find({}).to_list(1000)
        
        if not items:
            return {"success": False, "message": "No inventory data available"}
        
        df = pd.DataFrame(items)
        insights = []
        
        # Price insights
        avg_price = df['price'].mean()
        expensive_items = df[df['price'] > avg_price * 2]
        if len(expensive_items) > 0:
            insights.append({
                "type": "pricing",
                "severity": "info",
                "message": f"Found {len(expensive_items)} items priced significantly above average (>${avg_price:.2f})",
                "items": expensive_items[['name', 'price', 'seller']].to_dict('records')
            })
        
        # Seller insights
        seller_counts = df['seller'].value_counts()
        dominant_sellers = seller_counts[seller_counts > len(items) * 0.3]
        if len(dominant_sellers) > 0:
            insights.append({
                "type": "seller_concentration",
                "severity": "warning",
                "message": f"High concentration: {len(dominant_sellers)} seller(s) control >30% of inventory",
                "sellers": dominant_sellers.to_dict()
            })
        
        # Duplicate detection
        duplicates = df[df.duplicated(['name', 'seller'], keep=False)]
        if len(duplicates) > 0:
            insights.append({
                "type": "duplicates",
                "severity": "warning",
                "message": f"Found {len(duplicates)} potential duplicate items",
                "duplicates": duplicates[['name', 'price', 'seller']].to_dict('records')
            })
        
        # Price consistency
        name_groups = df.groupby('name')['price'].agg(['mean', 'std', 'count'])
        inconsistent_pricing = name_groups[
            (name_groups['std'] > name_groups['mean'] * 0.5) & 
            (name_groups['count'] > 1)
        ]
        if len(inconsistent_pricing) > 0:
            insights.append({
                "type": "price_inconsistency",
                "severity": "info", 
                "message": f"Price inconsistency detected for {len(inconsistent_pricing)} item types",
                "items": inconsistent_pricing.index.tolist()
            })
        
        return {
            "success": True,
            "insights": insights,
            "summary": {
                "total_insights": len(insights),
                "warnings": len([i for i in insights if i['severity'] == 'warning']),
                "info": len([i for i in insights if i['severity'] == 'info'])
            }
        }
    except Exception as e:
        return {"success": False, "message": f"Failed to generate insights: {str(e)}"}

# NEW: Get trending items (most frequently added)
@app.get("/trends")
async def get_trends():
    """Get trending items and analytics"""
    try:
        # Get items added in last 7 days (if date_added field exists)
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        # For demo purposes, use all items since we might not have date_added
        items = await items_collection.find({}).to_list(1000)
        
        if not items:
            return {"success": False, "message": "No data available"}
        
        df = pd.DataFrame(items)
        
        # Most common items
        item_trends = df['name'].str.lower().value_counts().head(10)
        
        # Most active sellers
        seller_trends = df['seller'].value_counts().head(10)
        
        # Price trends by category (simplified)
        price_ranges = {
            "budget": len(df[df['price'] < 10]),
            "mid_range": len(df[(df['price'] >= 10) & (df['price'] < 100)]),
            "premium": len(df[df['price'] >= 100])
        }
        
        return {
            "success": True,
            "trends": {
                "popular_items": item_trends.to_dict(),
                "active_sellers": seller_trends.to_dict(),
                "price_distribution": price_ranges
            },
            "period": "last_7_days",
            "total_items_analyzed": len(items)
        }
    except Exception as e:
        return {"success": False, "message": f"Failed to get trends: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)