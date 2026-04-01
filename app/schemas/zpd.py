"""
Schémas Marshmallow pour ZPD (Zone Proximale de Développement).
"""

from marshmallow import Schema, fields, validate


class CompetenceZPDAnalysisSchema(Schema):
    """Schéma pour analyser la ZPD d'une compétence."""
    
    mastery_level = fields.Float(
        required=False,  # ← MODIFIÉ : optionnel si user_id fourni
        validate=validate.Range(min=0.0, max=1.0),
        metadata={"description": "Niveau de maîtrise de la compétence (0.0 à 1.0). Optionnel si user_id fourni."}
    )
    
    all_masteries = fields.Dict(
        keys=fields.String(),
        values=fields.Float(),
        load_default={},
        metadata={"description": "Niveaux de maîtrise de toutes les compétences (optionnel)"}
    )
    
    user_id = fields.String(  # ← NOUVEAU
        required=False,
        metadata={"description": "ID de l'utilisateur pour analyse enrichie SAINT+. Si fourni, mastery_level est calculé automatiquement."}
    )


class SubjectZPDAnalysisSchema(Schema):
    """Schéma pour analyser la ZPD d'un sujet."""
    masteries = fields.Dict(
        keys=fields.String(),
        values=fields.Float(validate=validate.Range(min=0.0, max=1.0)),
        load_default={},
        metadata={"description": "Dictionnaire des niveaux de maîtrise par compétence"}
    )


class ReadyCompetencesSchema(Schema):
    """Schéma pour récupérer les compétences prêtes."""
    masteries = fields.Dict(
        keys=fields.String(),
        values=fields.Float(validate=validate.Range(min=0.0, max=1.0)),
        load_default={},
        metadata={"description": "Niveaux de maîtrise actuels"}
    )


class NextCompetenceSchema(Schema):
    """Schéma pour récupérer la prochaine compétence recommandée."""
    masteries = fields.Dict(
        keys=fields.String(),
        values=fields.Float(validate=validate.Range(min=0.0, max=1.0)),
        load_default={},
        metadata={"description": "Niveaux de maîtrise actuels"}
    )


class LearningPathSchema(Schema):
    """Schéma pour récupérer le chemin d'apprentissage avec ZPD."""
    masteries = fields.Dict(
        keys=fields.String(),
        values=fields.Float(validate=validate.Range(min=0.0, max=1.0)),
        load_default={},
        metadata={"description": "Niveaux de maîtrise actuels"}
    )
