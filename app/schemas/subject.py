"""
Schémas pour les matières.
"""

from marshmallow import Schema, fields, validate


class SubjectSchema(Schema):
    """Schéma de lecture d'une matière."""
    id = fields.String(dump_only=True)
    domain_id = fields.String()
    domain_name = fields.String(dump_only=True)
    name = fields.String()
    description = fields.String(allow_none=True)
    competences_count = fields.Integer(dump_only=True)
    has_curriculum = fields.Boolean(dump_only=True)
    created_at = fields.String(dump_only=True)


class SubjectCreateSchema(Schema):
    """Schéma de création d'une matière."""
    domain_id = fields.String(required=True)
    name = fields.String(
        required=True,
        validate=validate.Length(min=2, max=150)
    )
    description = fields.String(
        allow_none=True,
        validate=validate.Length(max=500)
    )


class SubjectUpdateSchema(Schema):
    """Schéma de mise à jour d'une matière."""
    name = fields.String(validate=validate.Length(min=2, max=150))
    description = fields.String(allow_none=True, validate=validate.Length(max=500))