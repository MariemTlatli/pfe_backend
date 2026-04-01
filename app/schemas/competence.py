# app/schemas/competence.py
from marshmallow import Schema, fields, validate


class PrerequisiteSchema(Schema):
    competence_id = fields.String(required=True)
    strength = fields.Float(validate=validate.Range(min=0.0, max=1.0), load_default=1.0)


class ZPDThresholdsSchema(Schema):
    mastered = fields.Float(
        validate=validate.Range(min=0.0, max=1.0),
        load_default=0.85,
        metadata={"description": "Seuil au-dessus duquel la compétence est maîtrisée"}
    )
    learning = fields.Float(
        validate=validate.Range(min=0.0, max=1.0),
        load_default=0.40,
        metadata={"description": "Seuil en-dessous duquel l'élève est en zone de frustration"}
    )


class DifficultyParamsSchema(Schema):
    base_difficulty = fields.Float(
        validate=validate.Range(min=0.0, max=1.0),
        load_default=0.5,
        metadata={"description": "Difficulté intrinsèque de la compétence"}
    )
    weight = fields.Float(
        validate=validate.Range(min=0.1),
        load_default=1.0,
        metadata={"description": "Poids/importance dans le curriculum"}
    )
    min_exercises = fields.Integer(
        validate=validate.Range(min=1),
        load_default=3,
        metadata={"description": "Nombre minimum d'exercices pour validation"}
    )
    mastery_exercises = fields.Integer(
        validate=validate.Range(min=1),
        load_default=5,
        metadata={"description": "Nombre d'exercices visés pour maîtrise complète"}
    )


class CompetenceSchema(Schema):
    _id = fields.String(dump_only=True, attribute="_id", data_key="id")
    subject_id = fields.String(required=True)
    code = fields.String(required=True)
    name = fields.String(required=True)
    description = fields.String(required=True)
    level = fields.Integer(load_default=0)
    graph_data = fields.Dict(load_default={"x": 0, "y": 0})
    prerequisites = fields.List(fields.Nested(PrerequisiteSchema), load_default=[])
    # ── Nouveaux champs ZPD ──
    zpd_thresholds = fields.Nested(ZPDThresholdsSchema, load_default=ZPDThresholdsSchema().load({}))
    difficulty_params = fields.Nested(DifficultyParamsSchema, load_default=DifficultyParamsSchema().load({}))
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class ZPDAnalysisSchema(Schema):
    """Schéma pour la réponse d'analyse ZPD"""
    competence_id = fields.String()
    code = fields.String()
    name = fields.String()
    level = fields.Integer()
    mastery_level = fields.Float()
    zone = fields.String(validate=validate.OneOf(["mastered", "zpd", "frustration"]))
    zone_label = fields.String()
    optimal_difficulty = fields.Float()
    recommended_exercise_types = fields.List(fields.String())
    thresholds = fields.Nested(ZPDThresholdsSchema)
    difficulty_params = fields.Nested(DifficultyParamsSchema)
    prerequisites = fields.List(fields.Dict())
    is_ready_to_learn = fields.Boolean()


class UpdateZPDThresholdsSchema(Schema):
    """Schéma pour la mise à jour des seuils ZPD"""
    mastered = fields.Float(validate=validate.Range(min=0.0, max=1.0))
    learning = fields.Float(validate=validate.Range(min=0.0, max=1.0))


class UpdateDifficultyParamsSchema(Schema):
    """Schéma pour la mise à jour des paramètres de difficulté"""
    base_difficulty = fields.Float(validate=validate.Range(min=0.0, max=1.0))
    weight = fields.Float(validate=validate.Range(min=0.1))
    min_exercises = fields.Integer(validate=validate.Range(min=1))
    mastery_exercises = fields.Integer(validate=validate.Range(min=1))


class CurriculumGenerateSchema(Schema):
    """Schéma pour les paramètres de génération de curriculum"""
    regenerate = fields.Boolean(
        load_default=False,
        metadata={"description": "Si true, régénère le curriculum existant"}
    )


class GraphStatsSchema(Schema):
    """Schéma pour les statistiques du graphe"""
    total_competences = fields.Integer()
    total_prerequisites = fields.Integer()
    average_prerequisites_per_competence = fields.Float()
    max_depth = fields.Integer()


class GraphNodeSchema(Schema):
    """Schéma pour un nœud du graphe"""
    id = fields.String()
    label = fields.String()
    x = fields.Float()
    y = fields.Float()
    level = fields.Integer()


class GraphEdgeSchema(Schema):
    """Schéma pour une arête du graphe"""
    source = fields.String()
    target = fields.String()
    strength = fields.Float()


class GraphDataSchema(Schema):
    """Schéma pour les données du graphe"""
    nodes = fields.List(fields.Nested(GraphNodeSchema))
    edges = fields.List(fields.Nested(GraphEdgeSchema))
    stats = fields.Nested(GraphStatsSchema)


class SubjectSchema(Schema):
    """Schéma pour une matière"""
    _id = fields.String(dump_only=True, attribute="_id", data_key="id")
    name = fields.String()
    description = fields.String()
    category = fields.String()


class CurriculumResponseSchema(Schema):
    """Schéma pour la réponse de génération de curriculum"""
    subject = fields.Nested(SubjectSchema)
    has_curriculum = fields.Boolean()
    competences = fields.List(fields.Nested(CompetenceSchema))
    graph = fields.Nested(GraphDataSchema)
    stats = fields.Nested(GraphStatsSchema)
    message = fields.String(dump_default="")