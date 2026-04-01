"""
Schémas Marshmallow pour Exercise.
"""

from marshmallow import Schema, fields, validate


class ExerciseSchema(Schema):
    """Schéma complet d'un exercice."""
    id = fields.String(dump_only=True, attribute="_id")
    competence_id = fields.String(required=True)
    lesson_id = fields.String(required=True)
    type = fields.String(
        required=True,
        validate=validate.OneOf([
            "qcm", "qcm_multiple", "vrai_faux", "texte_a_trous",
            "code_completion", "code_libre", "debugging", "projet_mini"
        ])
    )
    difficulty = fields.Float(validate=validate.Range(min=0.0, max=1.0), required=True)
    question = fields.String(load_default="")
    options = fields.List(fields.String(), load_default=[])
    correct_answer = fields.Raw(load_default="")
    explanation = fields.String(load_default="")
    hints = fields.List(fields.String(), load_default=[])
    code_template = fields.String(load_default="")
    expected_output = fields.String(load_default="")
    estimated_time = fields.Integer(load_default=60)
    status = fields.String(
        validate=validate.OneOf(["planned", "generating", "generated", "error"]),
        load_default="planned"
    )
    attempt_count = fields.Integer(dump_only=True)
    success_count = fields.Integer(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class ExercisePublicSchema(Schema):
    """Schéma public (sans correct_answer) — envoyé à l'élève."""
    id = fields.String(dump_only=True, attribute="_id")
    competence_id = fields.String()
    lesson_id = fields.String()
    type = fields.String()
    difficulty = fields.Float()
    question = fields.String()
    options = fields.List(fields.String())
    hints = fields.List(fields.String())
    code_template = fields.String()
    estimated_time = fields.Integer()


class ExerciseCorrectionSchema(Schema):
    """Schéma de correction — retourné après soumission."""
    is_correct = fields.Boolean()
    correct_answer = fields.Raw()
    explanation = fields.String()


class GenerateExercisesRequestSchema(Schema):
    """
    Schéma pour la requête de génération d'exercices adaptatifs avec SAINT+.
    """
    user_id = fields.String(
        required=True,
        metadata={"description": "ID utilisateur pour analyse SAINT+"}
    )
    
    count = fields.Integer(
        load_default=3,
        validate=validate.Range(min=1, max=10),
        metadata={"description": "Nombre d'exercices à générer (1-10)"}
    )
    
    regenerate = fields.Boolean(
        load_default=False,
        metadata={"description": "Régénérer les exercices existants"}
    )


class SubmitAnswerSchema(Schema):
    """Schéma pour soumettre une réponse."""
    answer = fields.Raw(required=True, metadata={"description": "Réponse de l'utilisateur"})
    time_spent = fields.Integer(load_default=0, metadata={"description": "Temps en secondes"})


class ExerciseStatsSchema(Schema):
    """Schéma pour les stats d'exercices."""
    competence_id = fields.String()
    total_exercises = fields.Integer()
    by_type = fields.Dict(keys=fields.String(), values=fields.Dict())