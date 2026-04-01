"""
Schémas pour les leçons.
"""

from marshmallow import Schema, fields, validate


class LessonSchema(Schema):
    """Schéma de lecture d'une leçon."""
    id = fields.String(dump_only=True)
    competence_id = fields.String()
    title = fields.String()
    content = fields.String()
    order = fields.Integer()
    estimated_time = fields.Integer(allow_none=True)
    created_at = fields.String(dump_only=True)


class LessonCreateSchema(Schema):
    """Schéma de création d'une leçon."""
    title = fields.String(
        required=True,
        validate=validate.Length(min=3, max=200)
    )
    content = fields.String(
        required=True,
        validate=validate.Length(min=50)
    )
    order = fields.Integer(load_default=1)
    estimated_time = fields.Integer(
        allow_none=True,
        validate=validate.Range(min=1, max=120)
    )


class LessonGenerateSchema(Schema):
    """Schéma pour la génération de leçons."""
    regenerate = fields.Boolean(load_default=False)


class LessonsResponseSchema(Schema):
    """Schéma de réponse pour les leçons générées."""
    lessons = fields.List(fields.Nested(LessonSchema))
    competence = fields.Dict()
    count = fields.Integer()