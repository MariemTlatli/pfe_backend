"""
Routes Health Check - Vérification état de l'API.
"""

from flask.views import MethodView
from flask_smorest import Blueprint
from marshmallow import Schema, fields

from app.services.ollama_service import OllamaService
from app.extensions import mongo


blp = Blueprint(
    "Health",
    __name__,
    url_prefix="/api/health",
    description="Vérification de l'état de l'API"
)


class HealthResponseSchema(Schema):
    """Schéma de réponse health check."""
    status = fields.String()
    api = fields.String()
    database = fields.String()
    ollama = fields.String()
    ollama_models = fields.List(fields.String())


@blp.route("")
class HealthCheck(MethodView):
    """Vérification de l'état de l'API."""
    
    @blp.response(200, HealthResponseSchema)
    def get(self):
        """Vérifier l'état de l'API, MongoDB et Ollama."""
        
        # Vérifier MongoDB
        try:
            mongo.db.command('ping')
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # Vérifier Ollama
        ollama_available = OllamaService.is_available()
        ollama_models = OllamaService.get_models() if ollama_available else []
        
        return {
            "status": "healthy" if db_status == "connected" and ollama_available else "degraded",
            "api": "running",
            "database": db_status,
            "ollama": "connected" if ollama_available else "disconnected",
            "ollama_models": ollama_models
        }


@blp.route("/ping")
class Ping(MethodView):
    """Simple ping."""
    
    @blp.response(200)
    def get(self):
        """Ping simple."""
        return {"message": "pong"}