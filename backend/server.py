from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Query, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
from fastapi.staticfiles import StaticFiles
import math
import shutil
import re
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'idea-index-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'

# Create uploads directory
UPLOADS_DIR = ROOT_DIR / 'uploads'
UPLOADS_DIR.mkdir(exist_ok=True)

app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Serve uploaded files under /api/uploads to match Kubernetes ingress routing
app.mount("/api/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# ============ Models ============

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    username: str
    email: EmailStr
    bio: Optional[str] = ""
    avatar_url: Optional[str] = ""
    is_verified_email: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    location_city: Optional[str] = None
    leader_score: int = 0

class UserCreate(BaseModel):
    name: str
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Category(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    slug: str

class City(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    slug: str
    region: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

class IdeaBase(BaseModel):
    title: Optional[str] = None
    body: str
    category_id: Optional[str] = None
    city_id: Optional[str] = None
    geo_lat: Optional[float] = None
    geo_lon: Optional[float] = None

class Idea(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    author_id: str
    parent_id: Optional[str] = None
    title: Optional[str] = None
    body: str
    category_id: Optional[str] = None
    city_id: Optional[str] = None
    geo_lat: Optional[float] = None
    geo_lon: Optional[float] = None
    attachments: List[str] = []
    tags: List[str] = []  # Hashtags for discovery
    upvotes: int = 0
    downvotes: int = 0
    saves_count: int = 0  # Bookmark count
    is_promoted: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    comments_count: int = 0

class Vote(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    idea_id: str
    vote_value: int  # 1 or -1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class VoteRequest(BaseModel):
    vote: int  # 1 or -1

class EmailVerificationToken(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    token: str
    expires_at: datetime
    used: bool = False

class ModerationReport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reporter_id: str
    idea_id: str
    reason: str
    status: str = "new"  # new, under_review, actioned
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Bookmark(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    idea_id: str
    collection: Optional[str] = None  # Optional collection name
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Notification(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    type: str  # "comment", "upvote", "mention", "reply"
    title: str
    body: str
    link: Optional[str] = None
    from_user_id: Optional[str] = None
    read: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============ Helper Functions ============

def create_jwt_token(user_id: str, email: str) -> str:
    payload = {
        'sub': user_id,
        'email': email,
        'exp': datetime.now(timezone.utc) + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get('sub')
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return User(**user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

async def check_email_verified(user: User = Depends(get_current_user)):
    if not user.is_verified_email:
        raise HTTPException(status_code=403, detail="Email verification required")
    return user

async def swap_promotion_check(idea_id: str):
    """Check if a comment should be promoted to main idea"""
    idea = await db.ideas.find_one({"id": idea_id}, {"_id": 0})
    if not idea or not idea.get('parent_id'):
        return
    
    parent_id = idea['parent_id']
    parent = await db.ideas.find_one({"id": parent_id}, {"_id": 0})
    
    if not parent or parent.get('parent_id'):
        return
    
    # Swap if comment has more upvotes than parent
    if idea['upvotes'] > parent['upvotes']:
        # Swap content
        idea_copy = {**idea}
        parent_copy = {**parent}
        
        await db.ideas.update_one(
            {"id": idea_id},
            {"$set": {
                "title": parent_copy.get('title'),
                "body": parent_copy['body'],
                "category_id": parent_copy.get('category_id'),
                "city_id": parent_copy.get('city_id'),
                "geo_lat": parent_copy.get('geo_lat'),
                "geo_lon": parent_copy.get('geo_lon'),
                "parent_id": None,
                "is_promoted": True
            }}
        )
        
        await db.ideas.update_one(
            {"id": parent_id},
            {"$set": {
                "title": None,
                "body": idea_copy['body'],
                "category_id": None,
                "city_id": None,
                "geo_lat": None,
                "geo_lon": None,
                "parent_id": idea_id,
                "is_promoted": False
            }}
        )

# ============ Auth Routes ============

@api_router.post("/signup")
async def signup(user_data: UserCreate):
    # Check if user exists
    existing = await db.users.find_one({"$or": [{"email": user_data.email}, {"username": user_data.username}]}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Hash password
    password_hash = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Create user
    user = User(
        name=user_data.name,
        username=user_data.username,
        email=user_data.email
    )
    
    user_dict = user.model_dump()
    user_dict['password_hash'] = password_hash
    user_dict['created_at'] = user_dict['created_at'].isoformat()
    user_dict['updated_at'] = user_dict['updated_at'].isoformat()
    
    await db.users.insert_one(user_dict)
    
    # Create verification token
    token = str(uuid.uuid4())
    verification = EmailVerificationToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
    )
    
    verification_dict = verification.model_dump()
    verification_dict['expires_at'] = verification_dict['expires_at'].isoformat()
    await db.email_verification_tokens.insert_one(verification_dict)
    
    # Mock email (console log)
    print(f"\n=== EMAIL VERIFICATION ===")
    print(f"To: {user_data.email}")
    print(f"Subject: Verify your Idea Index email")
    print(f"Verification link: /verify-email?token={token}")
    print(f"==========================\n")
    
    jwt_token = create_jwt_token(user.id, user.email)
    return {"token": jwt_token, "user": user, "message": "Verification email sent (check console)"}

@api_router.post("/login")
async def login(credentials: UserLogin):
    user_data = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not bcrypt.checkpw(credentials.password.encode('utf-8'), user_data['password_hash'].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user_data.pop('password_hash')
    if isinstance(user_data.get('created_at'), str):
        user_data['created_at'] = datetime.fromisoformat(user_data['created_at'])
    if isinstance(user_data.get('updated_at'), str):
        user_data['updated_at'] = datetime.fromisoformat(user_data['updated_at'])
    
    user = User(**user_data)
    jwt_token = create_jwt_token(user.id, user.email)
    
    return {"token": jwt_token, "user": user}

@api_router.get("/verify-email")
async def verify_email(token: str):
    verification = await db.email_verification_tokens.find_one({"token": token}, {"_id": 0})
    
    if not verification:
        raise HTTPException(status_code=404, detail="Invalid token")
    
    if verification['used']:
        raise HTTPException(status_code=400, detail="Token already used")
    
    expires_at = datetime.fromisoformat(verification['expires_at']) if isinstance(verification['expires_at'], str) else verification['expires_at']
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token expired")
    
    await db.users.update_one({"id": verification['user_id']}, {"$set": {"is_verified_email": True}})
    await db.email_verification_tokens.update_one({"token": token}, {"$set": {"used": True}})
    
    return {"message": "Email verified successfully"}

@api_router.post("/verify-email-auto")
async def verify_email_auto(user: User = Depends(get_current_user)):
    """Auto-verify email for MVP - bypass token requirement"""
    await db.users.update_one({"id": user.id}, {"$set": {"is_verified_email": True}})
    return {"message": "Email verified successfully"}

@api_router.post("/reset-password")
async def reset_password(email: EmailStr, new_password: str):
    """Reset password for MVP - no email verification needed"""
    user_data = await db.users.find_one({"email": email}, {"_id": 0})
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Hash new password
    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    await db.users.update_one(
        {"email": email},
        {"$set": {"password_hash": password_hash}}
    )
    
    print(f"\n=== PASSWORD RESET ===")
    print(f"Email: {email}")
    print(f"New password has been set")
    print(f"=====================\n")
    
    return {"message": "Password reset successfully"}

@api_router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return user

@api_router.get("/my-votes")
async def get_my_votes(idea_ids: str, user: User = Depends(get_current_user)):
    """Get user's votes for specific ideas"""
    idea_id_list = idea_ids.split(',')
    votes = await db.votes.find({
        "user_id": user.id,
        "idea_id": {"$in": idea_id_list}
    }, {"_id": 0}).to_list(1000)
    
    return votes

@api_router.get("/settings")
async def get_settings(user: User = Depends(get_current_user)):
    """Get user settings"""
    user_doc = await db.users.find_one({"id": user.id}, {"_id": 0})
    settings = user_doc.get('settings', {
        'replies_in_feed': 2,  # Default: show top 2 replies
        'dark_mode': False,
        'email_notifications': True,
        'feed_density': 'comfortable'  # compact, comfortable, spacious
    })
    return settings

@api_router.put("/settings")
async def update_settings(
    replies_in_feed: Optional[int] = None,
    dark_mode: Optional[bool] = None,
    email_notifications: Optional[bool] = None,
    feed_density: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """Update user settings"""
    update_data = {}
    
    if replies_in_feed is not None:
        update_data['settings.replies_in_feed'] = max(0, min(replies_in_feed, 10))  # 0-10 range
    if dark_mode is not None:
        update_data['settings.dark_mode'] = dark_mode
    if email_notifications is not None:
        update_data['settings.email_notifications'] = email_notifications
    if feed_density is not None and feed_density in ['compact', 'comfortable', 'spacious']:
        update_data['settings.feed_density'] = feed_density
    
    if update_data:
        await db.users.update_one(
            {"id": user.id},
            {"$set": update_data}
        )
    
    # Return updated settings
    user_doc = await db.users.find_one({"id": user.id}, {"_id": 0})

# ============ AI Title Generation ============
@api_router.post("/generate-title")
async def generate_title(
    body: str,
    user: User = Depends(get_current_user)
):
    """Generate a title for an idea using AI"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    try:
        # Initialize AI chat
        chat = LlmChat(
            api_key=os.environ.get('EMERGENT_LLM_KEY'),
            session_id=f"title-gen-{user.id}",
            system_message="You are a title generator. Generate concise, compelling titles (3-10 words) for ideas. Return ONLY the title, nothing else."
        ).with_model("openai", "gpt-4o-mini")
        
        # Create prompt
        prompt = f"Generate a concise, compelling title for this idea:\n\n{body[:500]}"
        
        # Get AI response
        user_message = UserMessage(text=prompt)
        title = await chat.send_message(user_message)
        
        # Clean up the title (remove quotes if AI added them)
        title = title.strip().strip('"').strip("'")
        
        return {"title": title}
    except Exception as e:
        logging.error(f"AI title generation failed: {e}")
        # Fallback: Use first sentence or truncated body
        fallback_title = body.split('.')[0][:50] + ('...' if len(body) > 50 else '')

@api_router.post("/ideas/{idea_id}/promote")
async def promote_to_level_one(
    idea_id: str,
    title: str,
    category_id: Optional[str] = None,
    city_id: Optional[str] = None,
    tags: Optional[str] = None,
    user: User = Depends(check_email_verified)
):
    """Promote a nested idea to Level 1 (top-level)"""
    idea = await db.ideas.find_one({"id": idea_id})
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    # Check if user is the author
    if idea['author_id'] != user.id:
        raise HTTPException(status_code=403, detail="You can only promote your own ideas")
    
    # Create a new top-level idea with the same content
    new_idea_dict = {
        "id": str(uuid.uuid4()),
        "title": title,
        "body": idea['body'],
        "author_id": user.id,
        "upvotes": 0,  # Start fresh as Level 1
        "downvotes": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "category_id": category_id or idea.get('category_id'),
        "city_id": city_id or idea.get('city_id'),
        "tags": [t.strip().lower() for t in tags.split(',')] if tags else idea.get('tags', []),
        "parent_id": None,  # Top-level
        "attachments": idea.get('attachments', []),
        "comments_count": 0
    }
    
    # Get category name
    if new_idea_dict['category_id']:
        category = await db.categories.find_one({"id": new_idea_dict['category_id']}, {"_id": 0})
        if category:
            new_idea_dict['category'] = category['name']
    
    # Get city coordinates
    if new_idea_dict['city_id']:
        city = await db.cities.find_one({"id": new_idea_dict['city_id']}, {"_id": 0})
        if city:
            new_idea_dict['city'] = city['name']
            new_idea_dict['geo_lat'] = city.get('geo_lat')
            new_idea_dict['geo_lon'] = city.get('geo_lon')
    
    await db.ideas.insert_one(new_idea_dict)
    
    # Convert datetime for response
    new_idea_dict['created_at'] = datetime.fromisoformat(new_idea_dict['created_at'])
    new_idea_dict['updated_at'] = datetime.fromisoformat(new_idea_dict['updated_at'])
    
    return new_idea_dict


@api_router.get("/url-preview")
async def get_url_preview(url: str):
    """Fetch Open Graph metadata for URL preview"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, follow_redirects=True)
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Could not fetch URL")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract Open Graph tags
            og_title = soup.find('meta', property='og:title')
            og_description = soup.find('meta', property='og:description')
            og_image = soup.find('meta', property='og:image')
            
            # Fallback to regular meta tags
            title = og_title['content'] if og_title else (soup.find('title').text if soup.find('title') else urlparse(url).netloc)
            description = og_description['content'] if og_description else (soup.find('meta', attrs={'name': 'description'})['content'] if soup.find('meta', attrs={'name': 'description'}) else '')
            image = og_image['content'] if og_image else None
            
            return {
                'url': url,
                'title': title[:200] if title else url,
                'description': description[:300] if description else '',
                'image': image,
                'domain': urlparse(url).netloc
            }
    except Exception as e:
        return {
            'url': url,
            'title': urlparse(url).netloc,
            'description': '',
            'image': None,
            'domain': urlparse(url).netloc
        }

# ============ Bookmarks ============

@api_router.post("/bookmarks")
async def bookmark_idea(idea_id: str, collection: Optional[str] = None, user: User = Depends(get_current_user)):
    """Save/bookmark an idea"""
    # Check if already bookmarked
    existing = await db.bookmarks.find_one({"user_id": user.id, "idea_id": idea_id}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Already bookmarked")
    
    bookmark = Bookmark(
        user_id=user.id,
        idea_id=idea_id,
        collection=collection
    )
    
    bookmark_dict = bookmark.model_dump()
    bookmark_dict['created_at'] = bookmark_dict['created_at'].isoformat()
    await db.bookmarks.insert_one(bookmark_dict)
    
    # Increment saves count
    await db.ideas.update_one({"id": idea_id}, {"$inc": {"saves_count": 1}})
    
    return {"message": "Bookmarked successfully"}

@api_router.delete("/bookmarks/{idea_id}")
async def unbookmark_idea(idea_id: str, user: User = Depends(get_current_user)):
    """Remove bookmark"""
    result = await db.bookmarks.delete_one({"user_id": user.id, "idea_id": idea_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    # Decrement saves count
    await db.ideas.update_one({"id": idea_id}, {"$inc": {"saves_count": -1}})
    
    return {"message": "Bookmark removed"}

@api_router.get("/bookmarks")
async def get_my_bookmarks(collection: Optional[str] = None, user: User = Depends(get_current_user)):
    """Get user's bookmarks"""
    query = {"user_id": user.id}
    if collection:
        query["collection"] = collection
    
    bookmarks = await db.bookmarks.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # Fetch full idea data
    idea_ids = [b['idea_id'] for b in bookmarks]
    ideas = await db.ideas.find({"id": {"$in": idea_ids}}, {"_id": 0}).to_list(1000)
    
    # Enrich ideas
    for idea in ideas:
        if isinstance(idea.get('created_at'), str):
            idea['created_at'] = datetime.fromisoformat(idea['created_at'])
        if isinstance(idea.get('updated_at'), str):
            idea['updated_at'] = datetime.fromisoformat(idea['updated_at'])
        
        author = await db.users.find_one({"id": idea['author_id']}, {"_id": 0, "password_hash": 0})
        if author:
            if isinstance(author.get('created_at'), str):
                author['created_at'] = datetime.fromisoformat(author['created_at'])
            if isinstance(author.get('updated_at'), str):
                author['updated_at'] = datetime.fromisoformat(author['updated_at'])
            idea['author'] = author
    
    return ideas

@api_router.get("/bookmarks/collections")
async def get_my_collections(user: User = Depends(get_current_user)):
    """Get user's bookmark collections"""
    bookmarks = await db.bookmarks.find({"user_id": user.id}, {"_id": 0}).to_list(1000)
    
    collections = {}
    for bookmark in bookmarks:
        coll_name = bookmark.get('collection') or 'Uncategorized'
        if coll_name not in collections:
            collections[coll_name] = 0
        collections[coll_name] += 1
    
    return [{"name": name, "count": count} for name, count in collections.items()]

# ============ Tags & Trending ============

@api_router.get("/tags/trending")
async def get_trending_tags(limit: int = 20):
    """Get trending tags"""
    # Aggregate tags from recent ideas (last 7 days)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    ideas = await db.ideas.find({
        "created_at": {"$gte": week_ago.isoformat()},
        "tags": {"$exists": True, "$ne": []}
    }, {"_id": 0, "tags": 1}).to_list(10000)
    
    # Count tag frequency
    tag_counts = {}
    for idea in ideas:
        for tag in idea.get('tags', []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    # Sort by count
    trending = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    return [{"tag": tag, "count": count} for tag, count in trending]

@api_router.get("/tags/search")
async def search_tags(q: str):
    """Search for tags (autocomplete)"""
    # Find ideas with tags matching query
    ideas = await db.ideas.find({
        "tags": {"$regex": f"^{q.lower()}", "$options": "i"}
    }, {"_id": 0, "tags": 1}).to_list(1000)
    
    # Collect unique matching tags
    matching_tags = set()
    for idea in ideas:
        for tag in idea.get('tags', []):
            if tag.lower().startswith(q.lower()):
                matching_tags.add(tag)
    
    return sorted(list(matching_tags))[:20]

# ============ Notifications ============

async def create_notification(user_id: str, notif_type: str, title: str, body: str, link: str = None, from_user_id: str = None):
    """Helper to create a notification"""
    notification = Notification(
        user_id=user_id,
        type=notif_type,
        title=title,
        body=body,
        link=link,
        from_user_id=from_user_id
    )
    
    notif_dict = notification.model_dump()
    notif_dict['created_at'] = notif_dict['created_at'].isoformat()
    await db.notifications.insert_one(notif_dict)

@api_router.get("/notifications")
async def get_notifications(unread_only: bool = False, limit: int = 50, user: User = Depends(get_current_user)):
    """Get user's notifications"""
    query = {"user_id": user.id}
    if unread_only:
        query["read"] = False
    
    notifications = await db.notifications.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Enrich with from_user info
    for notif in notifications:
        if isinstance(notif.get('created_at'), str):
            notif['created_at'] = datetime.fromisoformat(notif['created_at'])
        
        if notif.get('from_user_id'):
            from_user = await db.users.find_one({"id": notif['from_user_id']}, {"_id": 0, "password_hash": 0, "id": 1, "name": 1, "username": 1, "avatar_url": 1})
            if from_user:
                notif['from_user'] = from_user
    
    return notifications

@api_router.get("/notifications/unread-count")
async def get_unread_count(user: User = Depends(get_current_user)):
    """Get count of unread notifications"""
    count = await db.notifications.count_documents({"user_id": user.id, "read": False})
    return {"count": count}

@api_router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user: User = Depends(get_current_user)):
    """Mark notification as read"""
    await db.notifications.update_one(
        {"id": notification_id, "user_id": user.id},
        {"$set": {"read": True}}
    )
    return {"message": "Marked as read"}

@api_router.post("/notifications/mark-all-read")
async def mark_all_read(user: User = Depends(get_current_user)):
    """Mark all notifications as read"""
    await db.notifications.update_many(
        {"user_id": user.id, "read": False},
        {"$set": {"read": True}}
    )
    return {"message": "All marked as read"}

# ============ Ideas Routes ============

@api_router.get("/ideas")
async def get_ideas(
    q: Optional[str] = None,
    category: Optional[List[str]] = Query(None),
    city: Optional[str] = None,
    tags: Optional[str] = None,  # Comma-separated tags
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius: Optional[float] = None,
    sort: str = "hot",  # hot, top, new, rising
    page: int = 1,
    per_page: int = 20
):
    query = {"parent_id": None}
    
    if q:
        query["$or"] = [{"title": {"$regex": q, "$options": "i"}}, {"body": {"$regex": q, "$options": "i"}}]
    
    if category and len(category) > 0:
        query["category_id"] = {"$in": category}
    
    if city:
        query["city_id"] = city
    
    if tags:
        tag_list = [t.strip().lower() for t in tags.split(',')]
        query["tags"] = {"$in": tag_list}
    
    if lat and lon and radius:
        query["geo_lat"] = {"$exists": True}
        query["geo_lon"] = {"$exists": True}
    
    # Sorting algorithm
    if sort == "new":
        sort_key = "created_at"
        sort_order = -1
    elif sort == "top":
        sort_key = "upvotes"
        sort_order = -1
    elif sort == "rising":
        # Rising: ideas from last 24h sorted by upvotes
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        query["created_at"] = {"$gte": yesterday.isoformat()}
        sort_key = "upvotes"
        sort_order = -1
    else:  # hot (default)
        # Hot algorithm: score based on votes and age
        # We'll fetch all and sort in memory for simplicity
        sort_key = "created_at"
        sort_order = -1
    
    skip = (page - 1) * per_page
    
    ideas = await db.ideas.find(query, {"_id": 0}).sort(sort_key, sort_order).skip(skip).limit(per_page * 3).to_list(per_page * 3)
    
    # Calculate hot score if needed
    if sort == "hot":
        now = datetime.now(timezone.utc)
        for idea in ideas:
            created = datetime.fromisoformat(idea['created_at']) if isinstance(idea['created_at'], str) else idea['created_at']
            age_hours = (now - created).total_seconds() / 3600
            score = (idea['upvotes'] - idea['downvotes']) / ((age_hours + 2) ** 1.5)
            idea['_hot_score'] = score
        
        ideas.sort(key=lambda x: x.get('_hot_score', 0), reverse=True)
        ideas = ideas[:per_page]
    
    # Enrich with author and category info
    for idea in ideas:
        if isinstance(idea.get('created_at'), str):
            idea['created_at'] = datetime.fromisoformat(idea['created_at'])
        if isinstance(idea.get('updated_at'), str):
            idea['updated_at'] = datetime.fromisoformat(idea['updated_at'])
        
        author = await db.users.find_one({"id": idea['author_id']}, {"_id": 0, "password_hash": 0})
        if author:
            if isinstance(author.get('created_at'), str):
                author['created_at'] = datetime.fromisoformat(author['created_at'])
            if isinstance(author.get('updated_at'), str):
                author['updated_at'] = datetime.fromisoformat(author['updated_at'])
            idea['author'] = author
        
        if idea.get('category_id'):
            category_obj = await db.categories.find_one({"id": idea['category_id']}, {"_id": 0})
            if category_obj:
                idea['category'] = category_obj['name']
        
        if idea.get('city_id'):
            city_obj = await db.cities.find_one({"id": idea['city_id']}, {"_id": 0})
            if city_obj:
                idea['city'] = city_obj['name']
        
        # Fetch top 2 comments for this idea (sorted by upvotes)
        top_comments = await db.ideas.find(
            {"parent_id": idea['id']},
            {"_id": 0}
        ).sort("upvotes", -1).limit(2).to_list(2)
        
        # Enrich comments with author info
        for comment in top_comments:
            if isinstance(comment.get('created_at'), str):
                comment['created_at'] = datetime.fromisoformat(comment['created_at'])
            if isinstance(comment.get('updated_at'), str):
                comment['updated_at'] = datetime.fromisoformat(comment['updated_at'])
            
            comment_author = await db.users.find_one({"id": comment['author_id']}, {"_id": 0, "password_hash": 0})
            if comment_author:
                if isinstance(comment_author.get('created_at'), str):
                    comment_author['created_at'] = datetime.fromisoformat(comment_author['created_at'])
                if isinstance(comment_author.get('updated_at'), str):
                    comment_author['updated_at'] = datetime.fromisoformat(comment_author['updated_at'])
                comment['author'] = comment_author
        
        idea['top_comments'] = top_comments
        
        # Remove hot score from response
        if '_hot_score' in idea:
            del idea['_hot_score']
    
    total = await db.ideas.count_documents(query)
    
    return {
        "data": ideas,
        "meta": {"page": page, "per_page": per_page, "total": total}
    }

@api_router.post("/ideas")
async def create_idea(
    title: Optional[str] = Form(None),
    body: str = Form(None),
    category_id: Optional[str] = Form(None),
    city_id: Optional[str] = Form(None),
    geo_lat: Optional[float] = Form(None),
    geo_lon: Optional[float] = Form(None),
    tags: Optional[str] = Form(None),  # Comma-separated tags
    images: List[UploadFile] = File(default=[]),
    user: User = Depends(check_email_verified)
):
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")
    
    # Require either body text or images
    if (not body or not body.strip()) and not images:
        raise HTTPException(status_code=400, detail="Please provide either text or images")
    
    # Filter out empty/null images
    valid_images = [img for img in images if img and img.filename]
    
    # Handle image uploads
    attachments = []
    if valid_images:
        for image in valid_images:
            file_extension = image.filename.split('.')[-1]
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = UPLOADS_DIR / unique_filename
            
            with file_path.open('wb') as buffer:
                shutil.copyfileobj(image.file, buffer)
            
            attachments.append(f"/api/uploads/{unique_filename}")
    
    # Parse tags
    tags_list = []
    if tags:
        tags_list = [t.strip().lower() for t in tags.split(',') if t.strip()]
    
    idea = Idea(
        author_id=user.id,
        title=title,
        body=body,
        category_id=category_id,
        city_id=city_id,
        geo_lat=geo_lat,
        geo_lon=geo_lon,
        attachments=attachments,
        tags=tags_list
    )
    
    idea_dict = idea.model_dump()
    idea_dict['created_at'] = idea_dict['created_at'].isoformat()
    idea_dict['updated_at'] = idea_dict['updated_at'].isoformat()
    
    await db.ideas.insert_one(idea_dict)
    
    return idea



def is_minor_edit(old_text: str, new_text: str) -> bool:
    """Check if edit is minor (typo fix, punctuation) vs major content change"""
    import difflib
    
    # If texts are identical, allow
    if old_text == new_text:
        return True
    
    # Calculate similarity ratio
    similarity = difflib.SequenceMatcher(None, old_text.lower(), new_text.lower()).ratio()
    
    # If more than 85% similar, consider it minor
    if similarity >= 0.85:
        return True
    
    # Check character-level changes
    old_words = old_text.split()
    new_words = new_text.split()
    
    # If word count changed significantly (>20%), it's major
    if abs(len(old_words) - len(new_words)) > max(len(old_words), len(new_words)) * 0.2:
        return False
    
    # Count how many words changed
    word_changes = sum(1 for a, b in zip(old_words, new_words) if a.lower() != b.lower())
    change_ratio = word_changes / max(len(old_words), 1)
    
    # If more than 15% of words changed, it's major
    return change_ratio <= 0.15

@api_router.put("/ideas/{idea_id}")
async def edit_idea(
    idea_id: str,
    title: Optional[str] = Form(None),
    body: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    user: User = Depends(check_email_verified)
):
    """Edit an existing idea (only by the author)"""
    idea = await db.ideas.find_one({"id": idea_id})
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    # Check if user is the author
    if idea['author_id'] != user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own ideas")
    
    # Smart editing rules: If idea has upvotes, limit changes
    upvotes = idea.get('upvotes', 0)
    has_engagement = upvotes > 0
    
    # Update fields
    update_data = {"updated_at": datetime.now(timezone.utc)}
    
    if title is not None:
        if has_engagement:
            # Allow minor changes only (typos, formatting)
            old_title = idea.get('title', '')
            if not is_minor_edit(old_title, title):
                raise HTTPException(
                    status_code=400, 
                    detail="Cannot make major changes to title after receiving upvotes. Only typo fixes allowed."
                )
        update_data['title'] = title
        
    if body is not None:
        if has_engagement:
            # Allow minor changes only
            old_body = idea.get('body', '')
            if not is_minor_edit(old_body, body):
                raise HTTPException(
                    status_code=400,
                    detail="Cannot make major changes to content after receiving upvotes. Only typo/grammar fixes allowed."
                )
        update_data['body'] = body
    if category_id is not None:
        update_data['category_id'] = category_id
        # Get category name
        category = await db.categories.find_one({"id": category_id}, {"_id": 0})
        if category:
            update_data['category'] = category['name']
    if tags is not None:
        tag_list = [t.strip().lower() for t in tags.split(',') if t.strip()]
        update_data['tags'] = tag_list
    
    # Convert datetime for MongoDB
    update_data['updated_at'] = update_data['updated_at'].isoformat()
    
    await db.ideas.update_one({"id": idea_id}, {"$set": update_data})
    
    # Return updated idea
    updated_idea = await db.ideas.find_one({"id": idea_id}, {"_id": 0})
    if isinstance(updated_idea.get('created_at'), str):
        updated_idea['created_at'] = datetime.fromisoformat(updated_idea['created_at'])
    if isinstance(updated_idea.get('updated_at'), str):
        updated_idea['updated_at'] = datetime.fromisoformat(updated_idea['updated_at'])
    
    return updated_idea

@api_router.delete("/ideas/{idea_id}")
async def delete_idea(
    idea_id: str,
    user: User = Depends(check_email_verified)
):
    """Delete an idea (only by the author)"""
    idea = await db.ideas.find_one({"id": idea_id})
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    # Check if user is the author
    if idea['author_id'] != user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own ideas")
    
    # Delete the idea and all its comments
    await db.ideas.delete_many({"$or": [{"id": idea_id}, {"parent_id": idea_id}]})
    
    return {"message": "Idea deleted successfully"}

@api_router.get("/ideas/{idea_id}")
async def get_idea(idea_id: str):
    idea = await db.ideas.find_one({"id": idea_id}, {"_id": 0})
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    if isinstance(idea.get('created_at'), str):
        idea['created_at'] = datetime.fromisoformat(idea['created_at'])
    if isinstance(idea.get('updated_at'), str):
        idea['updated_at'] = datetime.fromisoformat(idea['updated_at'])
    
    # Get author
    author = await db.users.find_one({"id": idea['author_id']}, {"_id": 0, "password_hash": 0})
    if author:
        if isinstance(author.get('created_at'), str):
            author['created_at'] = datetime.fromisoformat(author['created_at'])
        if isinstance(author.get('updated_at'), str):
            author['updated_at'] = datetime.fromisoformat(author['updated_at'])
        idea['author'] = author
    
    # Get comments (nested)
    comments = await get_comments_recursive(idea_id)
    idea['comments'] = comments
    
    return idea

async def get_comments_recursive(parent_id: str, depth: int = 0, max_depth: int = 5):
    if depth > max_depth:
        return []
    
    comments = await db.ideas.find({"parent_id": parent_id}, {"_id": 0}).sort("upvotes", -1).to_list(1000)
    
    for comment in comments:
        if isinstance(comment.get('created_at'), str):
            comment['created_at'] = datetime.fromisoformat(comment['created_at'])
        if isinstance(comment.get('updated_at'), str):
            comment['updated_at'] = datetime.fromisoformat(comment['updated_at'])
        
        author = await db.users.find_one({"id": comment['author_id']}, {"_id": 0, "password_hash": 0})
        if author:
            if isinstance(author.get('created_at'), str):
                author['created_at'] = datetime.fromisoformat(author['created_at'])
            if isinstance(author.get('updated_at'), str):
                author['updated_at'] = datetime.fromisoformat(author['updated_at'])
            comment['author'] = author
        
        # Get nested comments
        comment['comments'] = await get_comments_recursive(comment['id'], depth + 1, max_depth)
    
    return comments

class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1)

@api_router.post("/ideas/{idea_id}/comments")
async def create_comment(
    idea_id: str,
    body: str = Form(None),
    images: List[UploadFile] = File(default=[]),
    user: User = Depends(check_email_verified)
):
    parent = await db.ideas.find_one({"id": idea_id}, {"_id": 0})
    if not parent:
        raise HTTPException(status_code=404, detail="Parent idea not found")
    
    # Filter out empty/null images
    valid_images = [img for img in images if img and img.filename]
    
    # Require either body or images
    if (not body or len(body.strip()) == 0) and len(valid_images) == 0:
        raise HTTPException(status_code=400, detail="Please provide text or an image")
    
    # Handle image uploads
    attachments = []
    if valid_images:
        for image in valid_images:
            file_extension = image.filename.split('.')[-1]
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = UPLOADS_DIR / unique_filename
            
            with file_path.open('wb') as buffer:
                shutil.copyfileobj(image.file, buffer)
            
            attachments.append(f"/api/uploads/{unique_filename}")
    
    # Use empty string if no body text - images can stand alone
    final_body = body.strip() if body and body.strip() else ""
    
    comment = Idea(
        author_id=user.id,
        parent_id=idea_id,
        body=final_body,
        attachments=attachments
    )
    
    comment_dict = comment.model_dump()
    comment_dict['created_at'] = comment_dict['created_at'].isoformat()
    comment_dict['updated_at'] = comment_dict['updated_at'].isoformat()
    
    await db.ideas.insert_one(comment_dict)
    await db.ideas.update_one({"id": idea_id}, {"$inc": {"comments_count": 1}})
    
    # Create notification for parent idea author (if not self-comment)
    if parent['author_id'] != user.id:
        parent_title = parent.get('title', 'your idea')
        await create_notification(
            user_id=parent['author_id'],
            notif_type="comment",
            title=f"{user.name} commented on {parent_title}",
            body=body[:100] + "..." if len(body) > 100 else body,
            link=f"/ideas/{parent['id']}",
            from_user_id=user.id
        )
    
    # Check for @mentions in body
    mention_pattern = r'@(\w+)'
    mentions = re.findall(mention_pattern, body)
    for username in set(mentions):
        mentioned_user = await db.users.find_one({"username": username}, {"_id": 0})
        if mentioned_user and mentioned_user['id'] != user.id:
            await create_notification(
                user_id=mentioned_user['id'],
                notif_type="mention",
                title=f"{user.name} mentioned you",
                body=body[:100] + "..." if len(body) > 100 else body,
                link=f"/ideas/{parent['id']}",
                from_user_id=user.id
            )
    
    return comment

@api_router.post("/ideas/{idea_id}/vote")
async def vote_idea(idea_id: str, vote_data: VoteRequest, user: User = Depends(check_email_verified)):
    if vote_data.vote not in [1, -1]:
        raise HTTPException(status_code=400, detail="Vote must be 1 or -1")
    
    idea = await db.ideas.find_one({"id": idea_id}, {"_id": 0})
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    # Check existing vote
    existing_vote = await db.votes.find_one({"user_id": user.id, "idea_id": idea_id}, {"_id": 0})
    
    if existing_vote:
        old_value = existing_vote['vote_value']
        if old_value == vote_data.vote:
            # Remove vote (toggle off)
            await db.votes.delete_one({"user_id": user.id, "idea_id": idea_id})
            if vote_data.vote == 1:
                await db.ideas.update_one({"id": idea_id}, {"$inc": {"upvotes": -1}})
            else:
                await db.ideas.update_one({"id": idea_id}, {"$inc": {"downvotes": -1}})
        else:
            # Change vote
            await db.votes.update_one(
                {"user_id": user.id, "idea_id": idea_id},
                {"$set": {"vote_value": vote_data.vote}}
            )
            if vote_data.vote == 1:
                await db.ideas.update_one({"id": idea_id}, {"$inc": {"upvotes": 1, "downvotes": -1}})
            else:
                await db.ideas.update_one({"id": idea_id}, {"$inc": {"upvotes": -1, "downvotes": 1}})
    else:
        # New vote
        vote = Vote(
            user_id=user.id,
            idea_id=idea_id,
            vote_value=vote_data.vote
        )
        
        vote_dict = vote.model_dump()
        vote_dict['created_at'] = vote_dict['created_at'].isoformat()
        await db.votes.insert_one(vote_dict)
        
        if vote_data.vote == 1:
            await db.ideas.update_one({"id": idea_id}, {"$inc": {"upvotes": 1}})
        else:
            await db.ideas.update_one({"id": idea_id}, {"$inc": {"downvotes": 1}})
    
    # Check for swap promotion
    await swap_promotion_check(idea_id)
    
    # Create notification for idea author on upvote (throttle to avoid spam)
    if vote_data.vote == 1 and not existing_vote:
        idea = await db.ideas.find_one({"id": idea_id}, {"_id": 0})
        if idea and idea['author_id'] != user.id:
            # Only notify on milestones to reduce noise: 1, 5, 10, 25, 50, 100, etc.
            new_count = idea['upvotes'] + 1
            milestones = [1, 5, 10, 25, 50, 100, 250, 500, 1000]
            if new_count in milestones:
                idea_title = idea.get('title', 'your idea')
                await create_notification(
                    user_id=idea['author_id'],
                    notif_type="upvote",
                    title=f"Your idea reached {new_count} upvotes!",
                    body=f'"{idea_title}" is gaining traction',
                    link=f"/ideas/{idea_id}",
                    from_user_id=None
                )
    
    updated_idea = await db.ideas.find_one({"id": idea_id}, {"_id": 0})
    return {"upvotes": updated_idea['upvotes'], "downvotes": updated_idea['downvotes']}

# ============ Leaders Routes ============

@api_router.get("/leaders")
async def get_leaders(city: Optional[str] = None, sort: str = "score", page: int = 1, per_page: int = 20):
    query = {}
    if city:
        query["location_city"] = city
    
    sort_key = "leader_score" if sort == "score" else "created_at"
    skip = (page - 1) * per_page
    
    leaders = await db.users.find(query, {"_id": 0, "password_hash": 0}).sort(sort_key, -1).skip(skip).limit(per_page).to_list(per_page)
    
    for leader in leaders:
        if isinstance(leader.get('created_at'), str):
            leader['created_at'] = datetime.fromisoformat(leader['created_at'])
        if isinstance(leader.get('updated_at'), str):
            leader['updated_at'] = datetime.fromisoformat(leader['updated_at'])
    
    total = await db.users.count_documents(query)
    
    return {
        "data": leaders,
        "meta": {"page": page, "per_page": per_page, "total": total}
    }

@api_router.get("/leaders/{username}")
async def get_leader_profile(username: str):
    leader = await db.users.find_one({"username": username}, {"_id": 0, "password_hash": 0})
    if not leader:
        raise HTTPException(status_code=404, detail="Leader not found")
    
    if isinstance(leader.get('created_at'), str):
        leader['created_at'] = datetime.fromisoformat(leader['created_at'])
    if isinstance(leader.get('updated_at'), str):
        leader['updated_at'] = datetime.fromisoformat(leader['updated_at'])
    
    # Get leader's ideas
    ideas = await db.ideas.find({"author_id": leader['id'], "parent_id": None}, {"_id": 0}).sort("created_at", -1).to_list(100)
    for idea in ideas:
        if isinstance(idea.get('created_at'), str):
            idea['created_at'] = datetime.fromisoformat(idea['created_at'])
        if isinstance(idea.get('updated_at'), str):
            idea['updated_at'] = datetime.fromisoformat(idea['updated_at'])
    
    # Get leader's comments
    comments = await db.ideas.find({"author_id": leader['id'], "parent_id": {"$ne": None}}, {"_id": 0}).sort("created_at", -1).to_list(100)
    for comment in comments:
        if isinstance(comment.get('created_at'), str):
            comment['created_at'] = datetime.fromisoformat(comment['created_at'])
        if isinstance(comment.get('updated_at'), str):
            comment['updated_at'] = datetime.fromisoformat(comment['updated_at'])
    
    leader['ideas'] = ideas
    leader['comments'] = comments
    
    return leader

# ============ Categories & Cities ============

@api_router.get("/categories")
async def get_categories():
    categories = await db.categories.find({}, {"_id": 0}).to_list(100)
    return categories

@api_router.get("/cities")
async def get_cities():
    cities = await db.cities.find({}, {"_id": 0}).to_list(100)
    return cities

# ============ Moderation ============

@api_router.post("/moderation/reports")
async def create_report(idea_id: str, reason: str, user: User = Depends(check_email_verified)):
    report = ModerationReport(
        reporter_id=user.id,
        idea_id=idea_id,
        reason=reason
    )
    
    report_dict = report.model_dump()
    report_dict['created_at'] = report_dict['created_at'].isoformat()
    await db.moderation_reports.insert_one(report_dict)
    
    return {"message": "Report submitted successfully"}

# ============ Seed Data ============

@api_router.post("/seed")
async def seed_data():
    # Check if already seeded
    existing_categories = await db.categories.count_documents({})
    if existing_categories > 0:
        return {"message": "Data already seeded"}
    
    # Seed categories
    categories_data = [
        "Housing", "Education", "App", "Technology", "Science", "Health",
        "Energy", "Transport", "Environment", "Food", "Finance", "Policy",
        "Community", "Arts", "Sports", "Mobility", "Urban Design", "Childcare",
        "Workplace", "Open Source"
    ]
    
    for cat_name in categories_data:
        category = Category(name=cat_name, slug=cat_name.lower().replace(' ', '-'))
        await db.categories.insert_one(category.model_dump())
    
    # Seed cities
    cities_data = [
        {"name": "Chicago", "region": "Midwest", "lat": 41.88, "lon": -87.63},
        {"name": "Seattle", "region": "Pacific Northwest", "lat": 47.61, "lon": -122.33},
        {"name": "New York", "region": "Northeast", "lat": 40.71, "lon": -74.01},
        {"name": "Los Angeles", "region": "West Coast", "lat": 34.05, "lon": -118.24},
        {"name": "San Francisco", "region": "West Coast", "lat": 37.77, "lon": -122.42},
        {"name": "Miami", "region": "Southeast", "lat": 25.76, "lon": -80.19},
        {"name": "Austin", "region": "South", "lat": 30.27, "lon": -97.74},
        {"name": "Boston", "region": "Northeast", "lat": 42.36, "lon": -71.06},
        {"name": "Denver", "region": "Mountain", "lat": 39.74, "lon": -104.99},
        {"name": "Portland", "region": "Pacific Northwest", "lat": 45.52, "lon": -122.68}
    ]
    
    for city_data in cities_data:
        city = City(**city_data, slug=city_data['name'].lower().replace(' ', '-'))
        await db.cities.insert_one(city.model_dump())
    
    return {"message": "Data seeded successfully"}

@api_router.post("/backfill-coordinates")
async def backfill_coordinates():
    """Add coordinates to ideas that have city but missing geo data"""
    ideas_without_coords = await db.ideas.find({
        "city_id": {"$ne": None},
        "$or": [
            {"geo_lat": None},
            {"geo_lon": None},
            {"geo_lat": {"$exists": False}},
            {"geo_lon": {"$exists": False}}
        ]
    }, {"_id": 0}).to_list(1000)
    
    updated_count = 0
    for idea in ideas_without_coords:
        city = await db.cities.find_one({"id": idea['city_id']}, {"_id": 0})
        if city and city.get('lat') and city.get('lon'):
            await db.ideas.update_one(
                {"id": idea['id']},
                {"$set": {"geo_lat": city['lat'], "geo_lon": city['lon']}}
            )
            updated_count += 1
    
    return {"message": f"Backfilled coordinates for {updated_count} ideas"}

@api_router.post("/migrate-image-paths")
async def migrate_image_paths():
    """Migrate existing image paths from /uploads/ to /api/uploads/"""
    updated_count = 0
    
    # Update ideas with attachments
    ideas = await db.ideas.find({"attachments": {"$exists": True, "$ne": []}}).to_list(length=None)
    for idea in ideas:
        old_attachments = idea.get('attachments', [])
        new_attachments = [att.replace('/uploads/', '/api/uploads/') if att.startswith('/uploads/') else att for att in old_attachments]
        if old_attachments != new_attachments:
            await db.ideas.update_one(
                {"id": idea['id']},
                {"$set": {"attachments": new_attachments}}
            )
            updated_count += 1
    
    return {"message": f"Migrated image paths for {updated_count} ideas"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
