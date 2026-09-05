import os

import certifi
from dotenv import load_dotenv
from pymongo import AsyncMongoClient


load_dotenv()


class MongoDB:
    def __init__(self):
        self.client = None
        self.database = None


mongodb = MongoDB()


async def connect_to_mongodb():

    mongodb_url = os.getenv("MONGODB_URL")
    database_name = os.getenv("DATABASE_NAME")

    if not mongodb_url:
        print("MONGODB_URL environment variable is missing")
        return False

    if not database_name:
        print("DATABASE_NAME environment variable is missing")
        return False

    print("Connecting to MongoDB...")

    try:

        mongodb.client = AsyncMongoClient(
            mongodb_url,
            tls=True,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=10000,
        )

        mongodb.database = mongodb.client[database_name]

        # Test connection
        await mongodb.client.admin.command("ping")

        print("MongoDB connected successfully!")
        return True

    except Exception as e:

        print(f"MongoDB connection failed: {e}")

        # Clean up failed connection
        if mongodb.client:
            mongodb.client.close()

        mongodb.client = None
        mongodb.database = None

        return False


async def close_mongodb_connection():

    if mongodb.client:

        try:
            mongodb.client.close()
            print("MongoDB connection closed")

        except Exception as e:
            print(f"Error closing MongoDB: {e}")

        finally:
            mongodb.client = None
            mongodb.database = None
