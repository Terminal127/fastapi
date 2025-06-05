from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import time
from datetime import datetime

app = FastAPI()

class Post(BaseModel):
    id: Optional[int] = None
    title: str
    content: str
    created_at: Optional[datetime] = None

# Database connection area
while True:
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='fastapi',
            user='anubhav',
            password='anubhav',
            cursor_factory=RealDictCursor
        )
        cursor = conn.cursor()
        print("Database connection was successful")
        break
    except psycopg2.Error as e:
        print(f"Unable to connect to the database. Error: {e}")
        print("Retrying...")
        time.sleep(2)

# Function to get all posts from the database
def get_all_posts():
    cursor.execute("SELECT * FROM posts")
    return cursor.fetchall()

# Function to add a new post to the database
def add_post(new_post):
    cursor.execute(
        "INSERT INTO posts (title, content, created_at) VALUES (%s, %s, %s) RETURNING id",
        (new_post.title, new_post.content, new_post.created_at)
    )
    new_post.id = cursor.fetchone()["id"]
    conn.commit()

#update posts function
def update_posts(id, new_post: Post):
    cursor.execute("UPDATE posts SET title = %s, content = %s WHERE id = %s", (new_post.title, new_post.content, id))
    conn.commit()


# Function to find a post by ID
def find_post(id):
    cursor.execute("SELECT * FROM posts WHERE id = %s", (id,))
    return cursor.fetchone()

# Function to delete a post by ID
def delete_post(id):
    cursor.execute("DELETE FROM posts WHERE id = %s", (id,))
    conn.commit()

# Function to get the latest post
def get_latest_post():
    cursor.execute("SELECT * FROM posts ORDER BY id DESC LIMIT 1")
    return cursor.fetchone()

# Get all posts
@app.get("/posts")
async def posts():
    return {"data": get_all_posts()}

# Add a new post
@app.post("/addposts", status_code=status.HTTP_201_CREATED)
async def postsimages(new_post: Post):
    add_post(new_post)
    return {"data": new_post}

# Get the latest post
@app.get("/posts/latest")
async def latest_post():
    return {"data": get_latest_post()}

# Get a specific post by ID
@app.get("/posts/{id}")
async def post(id: int):
    post = find_post(id)
    if not post:
        raise HTTPException(status_code=404, detail=f"Post with id {id} not found")
    return {"data": post}

# Delete a specific post by ID
@app.delete("/posts/{id}")
async def delete_specific_post(id: int):
    post = find_post(id)
    if not post:
        raise HTTPException(status_code=404, detail=f"Post with id {id} not found")
    delete_post(id)
    return {"data": f"Deleted post with id: {id}"}

# Update a specific post by ID
@app.put("/posts/{id}")
async def update_specific_post(id: int, new_post: Post):
    post = find_post(id)
    if not post:
        raise HTTPException(status_code=404, detail=f"Post with id {id} not found")
    update_posts(id, new_post)
    return {"data": f"Updated post with id: {id}"}
