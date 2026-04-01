"""
Routes pour la détection d'émotions.
"""

from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask import request

from app.schemas.prediction_schema import (
    HealthResponseSchema,
    PredictionResponseSchema,
    PredictionRequestSchema
)
from app.schemas.common import MessageSchema
from app.services.emotion_detection_service import get_emotion_prediction
from app.models.emotion_model import emotion_model


blp = Blueprint(
    "Emotions",
    __name__,
    url_prefix="/api/emotions",
    description="API de détection d'émotions faciales"
)


@blp.route("/health")
class EmotionHealth(MethodView):
    """Vérification de l'état de l'API."""
    
    @blp.response(200, HealthResponseSchema)  # Passer la CLASSE, pas l'instance
    def get(self):
        """Vérifier l'état de l'API et du modèle."""
        return {
            "status": "ok",
            "model_loaded": emotion_model.is_loaded
        }


@blp.route("/predict")
class EmotionPredict(MethodView):
    """Prédiction d'émotions à partir d'images."""
    
    @blp.arguments(PredictionRequestSchema, location='files')
    @blp.response(200)  # Passer la CLASSE
    @blp.alt_response(400, description="Fichier manquant ou invalide")
    @blp.alt_response(503, description="Modèle non chargé")
    @blp.alt_response(500, description="Erreur de traitement")
    
    def post(self , data):
        """
        Prédire l'émotion d'un visage à partir d'une image.
        """
        if not emotion_model.is_loaded:
            abort(503, message="Modèle non chargé")
        
        if 'file' not in request.files:
            abort(400, message="Aucun fichier envoyé. Clé attendue : 'file'")
        
        file = data.get('file')

        
        if not file.content_type or not file.content_type.startswith('image/'):
            abort(400, message="Le fichier doit être une image")
        
        try:
            file_bytes = file.read()
            result = get_emotion_prediction(file_bytes)
            return result
            
        except RuntimeError as e:
            abort(503, message=str(e))
        except Exception as e:
            abort(500, message=f"Erreur traitement : {str(e)}")


@blp.route("")
class EmotionRoot(MethodView):
    """Point d'entrée principal."""
    
    @blp.response(200, MessageSchema)  # Passer la CLASSE
    def get(self):
        """Information sur l'API."""
        return {
            "message": "API Détection d'Émotions prête. POST /api/emotions/predict pour prédire"
        }