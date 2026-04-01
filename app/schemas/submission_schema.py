"""
Schémas Marshmallow pour la soumission avec émotions.
"""

from marshmallow import Schema, fields, validate


class EmotionCaptureSchema(Schema):
    """Une capture émotionnelle individuelle."""
    emotion = fields.String(required=True)
    confidence = fields.Float(required=True, validate=validate.Range(min=0.0, max=1.0))
    timestamp = fields.DateTime(required=True)


class EmotionDataSchema(Schema):
    """Données émotionnelles complètes pour une soumission."""
    dominant_emotion = fields.String(required=True)
    confidence = fields.Float(required=True, validate=validate.Range(min=0.0, max=1.0))
    emotion_history = fields.List(fields.Nested(EmotionCaptureSchema), required=True)
    frustration_detected = fields.Boolean(required=True)
    average_confidence = fields.Float(required=True, validate=validate.Range(min=0.0, max=1.0))


class SubmitResponseWithEmotionSchema(Schema):
    """
    Schéma pour soumettre une réponse AVEC données émotionnelles.
    Étend SubmitResponseSchema avec les champs émotion.
    """
    # ── Identification ────────────────────────────
    user_id = fields.String(required=True)
    exercise_id = fields.String(required=True)
    competence_id = fields.String(required=True)
    
    # ── Réponse ───────────────────────────────────
    answer = fields.Raw(required=True)
    is_correct = fields.Boolean(load_default=None)  # Optionnel, calculé par backend
    
    # ── Performance ───────────────────────────────
    time_spent_seconds = fields.Integer(
        load_default=0,
        validate=validate.Range(min=0)
    )
    hints_used = fields.Integer(
        load_default=0,
        validate=validate.Range(min=0)
    )
    attempt_number = fields.Integer(
        load_default=1,
        validate=validate.Range(min=1)
    )
    
    # ── Émotion (NOUVEAU) ─────────────────────────
    emotion_data = fields.Nested(EmotionDataSchema, required=True)
    
    # ── ZPD/SAINT+ ────────────────────────────────
    current_zpd_zone = fields.String(
        load_default="zpd",
        validate=validate.OneOf(["mastered", "zpd", "frustration"])
    )
    current_mastery_level = fields.Float(
        load_default=0.5,
        validate=validate.Range(min=0.0, max=1.0)
    )