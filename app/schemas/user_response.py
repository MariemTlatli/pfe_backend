"""
Schémas Marshmallow pour UserResponse.
"""

from marshmallow import Schema, fields, validate


class UserResponseSchema(Schema):
    """Schéma complet d'une réponse utilisateur."""
    id = fields.String(dump_only=True, attribute="_id")
    user_id = fields.String(required=True)
    exercise_id = fields.String(required=True)
    competence_id = fields.String(required=True)
    lesson_id = fields.String(required=True)
    answer = fields.Raw(required=True)
    is_correct = fields.Boolean(dump_only=True)
    time_spent = fields.Integer(load_default=0)
    created_at = fields.DateTime(dump_only=True)


class SubmitResponseSchema(Schema):
    """Schéma pour soumettre une réponse."""
    user_id = fields.String(required=True)
    exercise_id = fields.String(required=True)
    answer = fields.Raw(required=True)
    time_spent = fields.Integer(
        load_default=0,
        validate=validate.Range(min=0),
        metadata={"description": "Temps passé en secondes"}
    )


class UserStatsSchema(Schema):
    """Schéma pour les stats utilisateur."""
    total = fields.Integer()
    correct = fields.Integer()
    incorrect = fields.Integer()
    success_rate = fields.Float()
    avg_time = fields.Integer()
    streak = fields.Integer()
    best_streak = fields.Integer()


class CompetenceSummarySchema(Schema):
    """Schéma pour le résumé par compétence."""
    competence_id = fields.String()
    total = fields.Integer()
    correct = fields.Integer()
    incorrect = fields.Integer()
    success_rate = fields.Float()
    avg_time = fields.Integer()
    last_response = fields.DateTime()
