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

# Async update function
async def update_item_in_db(name: str, price: float = None, seller: str = None) -> Dict[str, Any]:
    if not name:
        return {"success": False, "message": "Item name is required for updates"}
    
    try:
        # Find the item first
        existing_item = await items_collection.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
        if not existing_item:
            return {"success": False, "message": f"Item '{name}' not found"}
        
        # Build update query
        update_fields = {}
        if price is not None and price > 0:
            update_fields["price"] = price
        if seller:
            update_fields["seller"] = seller
            
        if not update_fields:
            return {"success": False, "message": "No valid fields to update"}
        
        # Update the item
        result = await items_collection.update_one(
            {"_id": existing_item["_id"]},
            {"$set": update_fields}
        )
        
        if result.modified_count > 0:
            updated_parts = []
            if price is not None:
                updated_parts.append(f"price to ${price:.2f}")
            if seller:
                updated_parts.append(f"seller to {seller}")
            
            return {
                "success": True,
                "message": f"✅ Successfully updated {name}: {', '.join(updated_parts)}"
            }
        else:
            return {"success": False, "message": f"No changes made to {name}"}
            
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
async def update_item(name: str, price: float = None, seller: str = None) -> str:
    """Update an existing item in the inventory. You can update price, seller, or both.
    
    Args:
        name: The name of the item to update (required)
        price: The new price of the item (optional, must be positive if provided)
        seller: The new seller name (optional)
    
    Returns:
        A success or error message
    """
    try:
        result = await update_item_in_db(name, price, seller)
        return result["message"]
    except Exception as e:
        return f"❌ Error updating item: {str(e)}"

# Tools list
tools = [add_item, update_item]

# Gemini Model Setup
model = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.3,
    google_api_key="AIzaSyDsi82MHuNMwZyUoJ5q6xN8yd9Q4yBw5gM",
    convert_system_message_to_human=True
)

# Prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an intelligent inventory assistant. 
    You can both ADD new items and UPDATE existing items based on user messages.
    
    FOR ADDING ITEMS:
    When users want to add items, extract item name, price, and seller, then call 'add_item'.
    Examples:
    - 'add apple for $5 from John'
    - 'banana $2 seller Sarah'
    - 'laptop 500 dollars by Mike'
    
    FOR UPDATING ITEMS:
    When users want to update existing items, extract the item name and what they want to change, then call 'update_item'.
    Examples:
    - 'change price of bottle sold by Debjut to $10'
    - 'update apple price to $6'
    - 'bottle by Debjut now costs $8'
    - 'change seller of laptop to Alice'
    
    Always extract:
    1. Item name (string)
    2. Price (convert to number, handle different currencies) 
    3. Seller name (string)
    
    For updates, you only need to provide the fields that are changing.
    If any required information is missing, ask the user to provide it clearly.
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
                "help": "Please provide item name, price, and seller (e.g., 'add apple for $5 from John') or update instructions (e.g., 'change price of bottle to $10')"
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