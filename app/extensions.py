from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_smorest import Api

# ── Instances partagées ──
mongo = PyMongo()
jwt = JWTManager()
bcrypt = Bcrypt()
cors = CORS()
api = Api()