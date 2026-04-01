"""
Schémas communs (messages, erreurs, pagination).
"""

from marshmallow import Schema, fields


class MessageSchema(Schema):
    """Schéma pour les messages simples."""
    message = fields.String(required=True)
    status = fields.String(dump_default="success")


class ErrorSchema(Schema):
    """Schéma pour les erreurs."""
    message = fields.String(required=True)
    status = fields.String(dump_default="error")
    code = fields.Integer(dump_default=400)
    details = fields.Dict(keys=fields.String(), values=fields.String())


class PaginationSchema(Schema):
    """Schéma pour la pagination."""
    page = fields.Integer(dump_default=1)
    per_page = fields.Integer(dump_default=20)
    total = fields.Integer()
    pages = fields.Integer()