import os
import certifi
from pymongo import AsyncMongoClient
from dotenv import load_dotenv

load_dotenv()


class MongoDB:
    def __init__(self):
        self.client = None
        self.database = None


mongodb = MongoDB()


async def connect_to_mongodb():
    try:
        mongodb_url = os.getenv("MONGODB_URL")
        database_name = os.getenv("DATABASE_NAME")

        if not mongodb_url:
            raise ValueError("MONGODB_URL is missing from .env")

        if not database_name:
            raise ValueError("DATABASE_NAME is missing from .env")

        print("Connecting to MongoDB...")

        mongodb.client = AsyncMongoClient(
            mongodb_url,
            tls=True,
            tlsCAFile=certifi.where()
        )

        mongodb.database = mongodb.client[database_name]

        await mongodb.client.admin.command("ping")

        print("MongoDB connected successfully!")

    except Exception as e:
        print("MongoDB connection failed:", e)
        raise


async def close_mongodb_connection():
    if mongodb.client:
        mongodb.client.close()
        print("MongoDB connection closed")