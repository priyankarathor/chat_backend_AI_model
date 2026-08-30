from passlib.context import CryptContext
from fastApi.mongodb import mongodb

from utils.security import create_access_token
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


class AuthService:

    @staticmethod
    async def register_user(user):

        # MongoDB database check
        if mongodb.database is None:
            raise Exception("MongoDB database is not connected")

        # Users collection
        users_collection = mongodb.database["users"]

        # Check email already exists
        existing_user = await users_collection.find_one(
            {"email": user.email}
        )

        if existing_user:
            return {
                "success": False,
                "message": "Email already registered"
            }

        # Password hash
        hashed_password = pwd_context.hash(user.password)

        # User data
        user_data = {
            "name": user.name,
            "email": user.email,
            "password": hashed_password
        }

        # Insert user
        result = await users_collection.insert_one(user_data)

        return {
            "success": True,
            "message": "User registered successfully",
            "user_id": str(result.inserted_id)
        }

        # =========================
    # LOGIN USER
    # =========================

    @staticmethod
    async def login_user(user):

        if mongodb.database is None:
            raise Exception("MongoDB database is not connected")

        users_collection = mongodb.database["users"]

        # Step 1: Find user by email
        existing_user = await users_collection.find_one(
            {"email": user.email}
        )

        # User not found
        if not existing_user:
            return {
                "success": False,
                "message": "Invalid email or password"
            }

        # Step 2: Verify password
        password_valid = pwd_context.verify(
            user.password,
            existing_user["password"]
        )

        if not password_valid:
            return {
                "success": False,
                "message": "Invalid email or password"
            }

        # Step 3: Create JWT token
        access_token = create_access_token(
            data={
                "sub": str(existing_user["_id"]),
                "email": existing_user["email"]
            }
        )

        return {
            "success": True,
            "message": "Login successful",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": str(existing_user["_id"]),
                "name": existing_user["name"],
                "email": existing_user["email"]
            }
        }