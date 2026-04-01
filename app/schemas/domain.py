"""
Schémas pour les domaines.
"""

from marshmallow import Schema, fields, validate


class DomainSchema(Schema):
    """Schéma de lecture d'un domaine."""
    id = fields.String(dump_only=True)
    name = fields.String()
    description = fields.String(allow_none=True)
    subjects_count = fields.Integer(dump_only=True)
    created_at = fields.String(dump_only=True)


class DomainCreateSchema(Schema):
    """Schéma de création d'un domaine."""
    name = fields.String(
        required=True,
        validate=validate.Length(min=2, max=100)
    )
    description = fields.String(
        allow_none=True,
        validate=validate.Length(max=500)
    )


class DomainUpdateSchema(Schema):
    """Schéma de mise à jour d'un domaine."""
    name = fields.String(validate=validate.Length(min=2, max=100))
    description = fields.String(allow_none=True, validate=validate.Length(max=500))