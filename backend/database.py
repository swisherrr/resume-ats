from motor.motor_asyncio import AsyncIOMotorClient
import redis
from typing import Optional
from .config import settings

class Database:
    client: Optional[AsyncIOMotorClient] = None
    redis: Optional[redis.Redis] = None

db = Database()

async def connect_to_mongo():
    """Create database connection."""
    db.client = AsyncIOMotorClient(settings.mongodb_url)
    print("Connected to MongoDB.")

async def close_mongo_connection():
    """Close database connection."""
    if db.client:
        db.client.close()
        print("Disconnected from MongoDB.")

async def connect_to_redis():
    """Create Redis connection."""
    db.redis = redis.from_url(settings.redis_url, decode_responses=True)
    print("Connected to Redis.")

async def close_redis_connection():
    """Close Redis connection."""
    if db.redis:
        db.redis.close()
        print("Disconnected from Redis.")

def get_database():
    """Get database instance."""
    return db.client[settings.mongodb_database]

def get_redis():
    """Get Redis instance."""
    return db.redis 