from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import motor.motor_asyncio
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Dict, Any
import asyncio
import json

# MongoDB Setup
uri = "mongodb+srv://terminalishere127:hello@cluster0.ezhgpwx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = motor.motor_asyncio.AsyncIOMotorClient(uri)
db = client["shopdb"]
items_collection = db["items"]

# FastAPI App
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)