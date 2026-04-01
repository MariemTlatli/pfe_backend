"""
Schémas Marshmallow pour UserProgress.
"""

from marshmallow import Schema, fields


class LastPredictionSchema(Schema):
    """Schéma pour la dernière prédiction SAINT+."""
    p_correct = fields.Float()
    zone = fields.String()
    engagement = fields.Float()
    confidence = fields.String()
    anomaly_detected = fields.Boolean()


class UserProgressSchema(Schema):
    """Schéma pour une progression utilisateur."""
    id = fields.String(dump_only=True, attribute="_id")
    user_id = fields.String(required=True)
    competence_id = fields.String(required=True)
    mastery = fields.Float(required=True)
    source = fields.String(required=True)
    exercises_completed = fields.Integer(required=True)
    last_attempt = fields.DateTime()
    updated_at = fields.DateTime()
    last_prediction = fields.Nested(LastPredictionSchema)


class UserProgressListSchema(Schema):
    """Schéma pour la liste des progressions d'un utilisateur."""
    user_id = fields.String(required=True)
    competences_count = fields.Integer(required=True)
    progresses = fields.List(fields.Nested(UserProgressSchema))