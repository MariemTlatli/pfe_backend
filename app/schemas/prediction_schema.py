"""
Schémas pour la prédiction d'émotions.
"""

from marshmallow import Schema, fields, validate
from app.config import Config


class HealthResponseSchema(Schema):
    """Schéma de réponse pour le endpoint health."""
    status = fields.String(
        required=True,
        validate=validate.OneOf(['ok', 'error'])
    )
    model_loaded = fields.Boolean(required=True)


class PredictionResponseSchema(Schema):
    """Schéma de réponse pour une prédiction d'émotion."""
    emotion = fields.String(
        required=True,
        validate=validate.OneOf(Config.LABELS)
    )
    confidence = fields.Float(
        required=True,
        validate=validate.Range(min=0.0, max=1.0)
    )
    all_probabilities = fields.Dict(
        keys=fields.String(),
        values=fields.Float(),
        required=True
    )


class PredictionRequestSchema(Schema):
    file = fields.Field(
        required=True,
        metadata={"type": "string", "format": "binary"}
    )