from datetime import datetime
from flask_jwt_extended import create_access_token
from app.extensions import mongo, bcrypt
from bson.objectid import ObjectId


class AuthService:
    """Gère l'inscription et la connexion des utilisateurs."""

    @staticmethod
    def register(username: str, email: str, password: str) -> dict:
        users = mongo.db.users

        if users.find_one({"email": email}):
            raise ValueError("Cet email est déjà utilisé.")

        if users.find_one({"username": username}):
            raise ValueError("Ce nom d'utilisateur est déjà pris.")

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        user_data = {
            "username": username,
            "email": email,
            "password": hashed_password,
            "created_at": datetime.utcnow(),
            "xp": 0,
            "level": 1,
            "badges": []
        }

        result = users.insert_one(user_data)
        user_id = str(result.inserted_id)
        access_token = create_access_token(identity=user_id)

        return {
            "user_id": user_id,
            "username": username,
            "email": email,
            "access_token": access_token
        }

    @staticmethod
    def login(email: str, password: str) -> dict:
        users = mongo.db.users
        user = users.find_one({"email": email})

        if not user:
            raise ValueError("Email ou mot de passe incorrect.")

        if not bcrypt.check_password_hash(user["password"], password):
            raise ValueError("Email ou mot de passe incorrect.")

        user_id = str(user["_id"])
        access_token = create_access_token(identity=user_id)

        return {
            "user_id": user_id,
            "username": user["username"],
            "email": user["email"],
            "access_token": access_token
        }