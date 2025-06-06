# Performance & Monitoring Enhancements

## 1. Caching

```python
from functools import lru_cache
import redis
import json
from typing import Optional

# Redis setup
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

class CacheManager:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def get(self, key: str) -> Optional[dict]:
        try:
            data = self.redis.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None
    
    async def set(self, key: str, value: dict, expire: int = 300):
        try:
            self.redis.setex(key, expire, json.dumps(value))
        except Exception:
            pass  # Cache failure shouldn't break the app
    
    async def delete(self, key: str):
        try:
            self.redis.delete(key)
        except Exception:
            pass

cache = CacheManager(redis_client)

@app.get("/items")
async def get_items_cached():
    """Get items with caching"""
    
    cache_key = "all_items"
    cached_data = await cache.get(cache_key)
    
    if cached_data:
        return cached_data
    
    try:
        items = await items_collection.find({}).to_list(1000)
        for item in items:
            item["_id"] = str(item["_id"])
        
        result = {"items": items, "count": len(items)}
        await cache.set(cache_key, result, expire=180)  # Cache for 3 minutes
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch items: {str(e)}")

# Invalidate cache when items are modified
async def invalidate_items_cache():
    await cache.delete("all_items")
    # Clear search caches too
    keys = redis_client.keys("search:*")
    if keys:
        redis_client.delete(*keys)

## 2. Database Indexing

async def create_database_indexes():
    """Create database indexes for better performance"""
    
    # Text search index
    await items_collection.create_index([("name", "text"), ("seller", "text")])
    
    # Compound indexes for common queries
    await items_collection.create_index([("seller", 1), ("price", -1)])
    await items_collection.create_index([("price", 1)])
    await items_collection.create_index([("created_at", -1)])
    
    print("✅ Database indexes created successfully")

@app.on_event("startup")
async def startup_event():
    await create_database_indexes()

## 3. Request Monitoring & Logging

import logging
import time
from datetime import datetime

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RequestLoggerMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            start_time = time.time()
            
            # Log request
            logger.info(f"Request: {scope['method']} {scope['path']}")
            
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    process_time = time.time() - start_time
                    status_code = message["status"]
                    
                    # Log response
                    logger.info(f"Response: {status_code} - {process_time:.3f}s")
                    
                    # Store metrics
                    await store_request_metrics(scope, status_code, process_time)
                
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)

app.add_middleware(RequestLoggerMiddleware)

# Metrics storage
request_metrics = []

async def store_request_metrics(scope, status_code, process_time):
    """Store request metrics for monitoring"""
    
    metric = {
        "timestamp": datetime.utcnow().isoformat(),
        "method": scope["method"],
        "path": scope["path"],
        "status_code": status_code,
        "response_time": process_time,
        "client_ip": scope.get("client", ["unknown"])[0]
    }
    
    request_metrics.append(metric)
    
    # Keep only last 1000 metrics
    if len(request_metrics) > 1000:
        request_metrics.pop(0)

@app.get("/metrics")
async def get_metrics(current_user: User = Depends(get_current_user)):
    """Get API performance metrics"""
    
    if not request_metrics:
        return {"message": "No metrics available"}
    
    # Calculate statistics
    response_times = [m["response_time"] for m in request_metrics]
    status_codes = [m["status_code"] for m in request_metrics]
    
    from collections import Counter
    import statistics
    
    return {
        "total_requests": len(request_metrics),
        "avg_response_time": round(statistics.mean(response_times), 3),
        "min_response_time": round(min(response_times), 3),
        "max_response_time": round(max(response_times), 3),
        "status_code_distribution": dict(Counter(status_codes)),
        "recent_requests": request_metrics[-10:]  # Last 10 requests
    }

## 4. Health Checks

@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Database connectivity
    try:
        await items_collection.find_one()
        health_status["checks"]["database"] = {"status": "up", "message": "Connected"}
    except Exception as e:
        health_status["checks"]["database"] = {"status": "down", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    # Redis connectivity (if using cache)
    try:
        redis_client.ping()
        health_status["checks"]["redis"] = {"status": "up", "message": "Connected"}
    except Exception as e:
        health_status["checks"]["redis"] = {"status": "down", "error": str(e)}
    
    # AI Model availability
    try:
        # Simple test of the AI model
        test_result = await agent_executor.ainvoke({
            "input": "health check",
            "chat_history": []
        })
        health_status["checks"]["ai_model"] = {"status": "up", "message": "Responding"}
    except Exception as e:
        health_status["checks"]["ai_model"] = {"status": "down", "error": str(e)}
        health_status["status"] = "degraded"
    
    # Memory usage
    import psutil
    memory_percent = psutil.virtual_memory().percent
    health_status["checks"]["memory"] = {
        "status": "up" if memory_percent < 90 else "warning",
        "usage_percent": memory_percent
    }
    
    return health_status

## 5. Background Tasks

from fastapi import BackgroundTasks

async def cleanup_old_sessions():
    """Clean up old chat sessions (background task)"""
    
    current_time = time.time()
    sessions_to_remove = []
    
    for session_id, history in chat_history_store.items():
        # Remove sessions older than 1 hour with no activity
        if current_time - getattr(history, 'last_activity', current_time) > 3600:
            sessions_to_remove.append(session_id)
    
    for session_id in sessions_to_remove:
        del chat_history_store[session_id]
    
    logger.info(f"Cleaned up {len(sessions_to_remove)} old chat sessions")

@app.post("/smart-add")
async def smart_add(
    message_input: MessageInput, 
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    # Your existing smart-add logic...
    
    # Add background cleanup task
    background_tasks.add_task(cleanup_old_sessions)
    background_tasks.add_task(invalidate_items_cache)
    
    # Return response...

## 6. Error Tracking

import traceback
from typing import List

error_log = []

class ErrorTracker:
    @staticmethod
    def log_error(error: Exception, context: dict = None):
        error_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {}
        }
        
        error_log.append(error_entry)
        
        # Keep only last 100 errors
        if len(error_log) > 100:
            error_log.pop(0)
        
        # Log to system logger
        logger.error(f"Error: {error_entry}")

@app.get("/errors")
async def get_error_log(current_user: User = Depends(get_current_user)):
    """Get recent error log (admin only)"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {
        "errors": error_log,
        "count": len(error_log)
    }

# Use in your endpoints
@app.post("/smart-add")
async def smart_add(message_input: MessageInput, current_user: User = Depends(get_current_user)):
    try:
        # Your existing logic...
        pass
    except Exception as e:
        ErrorTracker.log_error(e, {
            "endpoint": "/smart-add",
            "user": current_user.username,
            "message": message_input.message
        })
        raise HTTPException(status_code=500, detail="Internal server error")
```
