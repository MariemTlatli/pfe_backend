"""
Configuration centrale — SAINT+ (remplace BKT).
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration centrale de l'application d'apprentissage adaptatif."""

    MODEL_PATH = "models/emotiondetector.h5"
    LABELS = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
    IMAGE_SIZE = (48, 48)

    # ── Flask Core ──
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-CHANGE-IN-PRODUCTION")
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"

    # ── JWT ──
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-jwt-secret-CHANGE-IN-PRODUCTION")
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "86400"))
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    # ── MongoDB ──
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/adaptive_learning_db")

    # ── Ollama (GenAI) ──
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "5000"))
    OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))

    # ══════════════════════════════════════════════
    # SAINT+ 
    # ══════════════════════════════════════════════
    SAINT_MODEL_PATH = os.getenv(
        "SAINT_MODEL_PATH",
        os.path.join("models", "saint_full", "best_model.pt")
    )
    SAINT_MAX_SEQ_LEN = int(os.getenv("SAINT_MAX_SEQ_LEN", "200"))
    SAINT_MASTERY_THRESHOLD = float(os.getenv("SAINT_MASTERY_THRESHOLD", "0.85"))

    # ── Génération de contenu ──
    MAX_COMPETENCES_PER_SUBJECT = int(os.getenv("MAX_COMPETENCES", "15"))
    MAX_LESSONS_PER_COMPETENCE = int(os.getenv("MAX_LESSONS", "5"))

    # ── Flask-Smorest (OpenAPI) ──
    API_TITLE = "API Apprentissage Adaptatif"
    API_VERSION = "v1.0"
    OPENAPI_VERSION = "3.0.3"
    OPENAPI_URL_PREFIX = "/"
    OPENAPI_SWAGGER_UI_PATH = "/docs"
    OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    OPENAPI_REDOC_PATH = "/redoc"
    OPENAPI_REDOC_URL = "https://cdn.jsdelivr.net/npm/redoc/bundles/redoc.standalone.js"

    API_SPEC_OPTIONS = {
        "info": {
            "description": (
                "API pour la génération automatique de curriculums d'apprentissage "
                "avec suivi adaptatif basé sur SAINT+ (Deep Learning) "
                "et génération de contenu par IA"
            ),
            "contact": {"email": "support@adaptive-learning.com"},
            "license": {"name": "MIT"}
        },
        "servers": [
            {"url": "http://localhost:5000", "description": "Serveur de développement"},
            {"url": "https://api.votre-domaine.com", "description": "Production"}
        ],
        "components": {
            "securitySchemes": {
                "Bearer": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "Token JWT pour authentification"
                }
            }
        },
        "security": [{"Bearer": []}],
        "tags": [
            {"name": "auth", "description": "Authentification et gestion utilisateurs"},
            {"name": "Domains", "description": "Gestion des domaines de connaissance"},
            {"name": "Subjects", "description": "Matières et sujets d'étude"},
            {"name": "Curriculum", "description": "Génération de graphes de compétences"},
            {"name": "Lessons", "description": "Contenu pédagogique"},
            {"name": "exercises", "description": "Exercices et évaluations"},
            {"name": "progress", "description": "Suivi de progression (SAINT+)"},
            {"name": "zpd", "description": "Analyse des zones proximales de développement"}
        ]
    }


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class TestingConfig(Config):
    TESTING = True
    MONGO_URI = "mongodb://localhost:27017/adaptive_learning_test_db"
    JWT_ACCESS_TOKEN_EXPIRES = 3600


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig
}


def get_config():
    env = os.getenv("FLASK_ENV", "development")
    return config_by_name.get(env, DevelopmentConfig)