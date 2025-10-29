from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
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

# Serve uploaded files
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

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
    upvotes: int = 0
    downvotes: int = 0
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

@api_router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return user

# ============ Ideas Routes ============

@api_router.get("/ideas")
async def get_ideas(
    q: Optional[str] = None,
    category: Optional[str] = None,
    city: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius: Optional[float] = None,
    sort: str = "top",
    page: int = 1,
    per_page: int = 20
):
    query = {"parent_id": None}
    
    if q:
        query["$or"] = [{"title": {"$regex": q, "$options": "i"}}, {"body": {"$regex": q, "$options": "i"}}]
    
    if category:
        query["category_id"] = category
    
    if city:
        query["city_id"] = city
    
    if lat and lon and radius:
        # Simple radius search (not using geospatial index for MVP)
        query["geo_lat"] = {"$exists": True}
        query["geo_lon"] = {"$exists": True}
    
    sort_key = "upvotes" if sort == "top" else "created_at"
    sort_order = -1
    
    skip = (page - 1) * per_page
    
    ideas = await db.ideas.find(query, {"_id": 0}).sort(sort_key, sort_order).skip(skip).limit(per_page).to_list(per_page)
    
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
    
    total = await db.ideas.count_documents(query)
    
    return {
        "data": ideas,
        "meta": {"page": page, "per_page": per_page, "total": total}
    }

@api_router.post("/ideas")
async def create_idea(idea_data: IdeaBase, user: User = Depends(check_email_verified)):
    if not idea_data.title:
        raise HTTPException(status_code=400, detail="Title is required")
    
    if len(idea_data.body) < 10:
        raise HTTPException(status_code=400, detail="Body must be at least 10 characters")
    
    idea = Idea(
        author_id=user.id,
        title=idea_data.title,
        body=idea_data.body,
        category_id=idea_data.category_id,
        city_id=idea_data.city_id,
        geo_lat=idea_data.geo_lat,
        geo_lon=idea_data.geo_lon
    )
    
    idea_dict = idea.model_dump()
    idea_dict['created_at'] = idea_dict['created_at'].isoformat()
    idea_dict['updated_at'] = idea_dict['updated_at'].isoformat()
    
    await db.ideas.insert_one(idea_dict)
    
    return idea

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
async def create_comment(idea_id: str, comment_data: CommentCreate, user: User = Depends(check_email_verified)):
    parent = await db.ideas.find_one({"id": idea_id}, {"_id": 0})
    if not parent:
        raise HTTPException(status_code=404, detail="Parent idea not found")
    
    comment = Idea(
        author_id=user.id,
        parent_id=idea_id,
        body=comment_data.body
    )
    
    comment_dict = comment.model_dump()
    comment_dict['created_at'] = comment_dict['created_at'].isoformat()
    comment_dict['updated_at'] = comment_dict['updated_at'].isoformat()
    
    await db.ideas.insert_one(comment_dict)
    await db.ideas.update_one({"id": idea_id}, {"$inc": {"comments_count": 1}})
    
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
