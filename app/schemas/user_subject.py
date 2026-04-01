"""
Schémas de validation pour les inscriptions utilisateur-matière.
"""

from marshmallow import Schema, fields, validate


class EnrollmentSchema(Schema):
    """Schéma d'une inscription."""
    id = fields.Str(dump_only=True)
    user_id = fields.Str(required=True)
    subject_id = fields.Str(required=True)
    enrolled_at = fields.DateTime(dump_only=True)
    status = fields.Str(dump_default='active', validate=validate.OneOf(['active', 'paused', 'completed']))
    progress = fields.Float(dump_default=0.0)
    current_competence_id = fields.Str(allow_none=True)
    completed_competences = fields.List(fields.Str(), dump_default=[])
    stats = fields.Dict(dump_default={})


class BulkEnrollSchema(Schema):
    """Schéma pour inscription multiple."""
    subject_ids = fields.List(
        fields.Str(),
        required=True,
        validate=validate.Length(min=1, max=20)
    )


class EnrollResponseSchema(Schema):
    """Schéma de réponse d'inscription."""
    enrollment_id = fields.Str()
    subject_id = fields.Str()
    enrolled_at = fields.DateTime()
    message = fields.Str()


class BulkEnrollResponseSchema(Schema):
    """Schéma de réponse d'inscription multiple."""
    enrolled = fields.List(fields.Dict())
    already_enrolled = fields.List(fields.Str())
    total = fields.Int()
    message = fields.Str()


class UpdateProgressSchema(Schema):
    """Schéma pour la mise à jour de la progression."""
    current_competence_id = fields.Str(allow_none=True)
    progress = fields.Float()
    status = fields.Str(validate=validate.OneOf(['active', 'paused', 'completed']))
    stats = fields.Dict()


class UserSubjectDetailSchema(Schema):
    """Schéma détaillé d'une matière d'utilisateur."""
    enrollment_id = fields.Str()
    subject = fields.Dict()
    enrolled_at = fields.DateTime()
    status = fields.Str()
    progress = fields.Dict()
    current_competence_id = fields.Str(allow_none=True)
    stats = fields.Dict()