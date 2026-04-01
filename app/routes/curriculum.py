"""
Routes Curriculum - Génération du graphe de compétences avec Ollama.
"""

from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask import jsonify, send_file
from app.models.subject import Subject
from app.models.competence import Competence
from app.services.curriculum_service import CurriculumService
from app.services.graph_service import GraphService
from app.services.ollama_service import OllamaService
from app.schemas.competence import (
    CompetenceSchema, 
    CurriculumGenerateSchema, 
    CurriculumResponseSchema
)
from app.schemas.common import MessageSchema


blp = Blueprint(
    "Curriculum",
    __name__,
    url_prefix="/api/curriculum",
    description="Génération de graphes de compétences avec IA"
)


@blp.route("/generate/<string:subject_id>")
class CurriculumGenerate(MethodView):
    """Génération du curriculum pour une matière."""
    
    @blp.arguments(CurriculumGenerateSchema, location="query")
    @blp.response(201, CurriculumResponseSchema)
    def post(self, args, subject_id):
        """
        Générer le curriculum (graphe de compétences) pour une matière.
        
        APPROCHE EN 3 ÉTAPES :
        1. Génération des compétences (sans prérequis)
        2. Génération des prérequis (avec tous les codes disponibles)
        3. Construction du graphe et validation
        
        Utilise Ollama pour analyser la matière et créer automatiquement :
        - Les compétences à maîtriser
        - Les prérequis entre compétences (graphe DAG)
        - Les niveaux de difficulté
        """
        # Vérifier que la matière existe
        subject = Subject.find_by_id(subject_id)
        if not subject:
            abort(404, message=f"Matière {subject_id} introuvable")
        
        # Vérifier qu'Ollama est disponible
        if not OllamaService.is_available():
            abort(503, message="Service Ollama indisponible. Vérifiez que Ollama est lancé.")
        
        # Régénérer si demandé
        regenerate = args.get('regenerate', False)
        
        try:
            if regenerate:
                result = CurriculumService.regenerate_for_subject(subject_id)
            else:
                result = CurriculumService.generate_for_subject(subject_id)
            
            return result
        
        except ValueError as e:
            abort(409, message=str(e))
        except Exception as e:
            abort(500, message=f"Erreur de génération: {str(e)}")


@blp.route("/regenerate-prerequisites/<string:subject_id>")
class CurriculumRegeneratePrerequisites(MethodView):
    """Régénérer seulement les prérequis."""
    
    @blp.response(200)
    def post(self, subject_id):
        """
        Régénérer seulement les prérequis (garde les compétences).
        Utile si le graphe généré n'est pas satisfaisant.
        """
        try:
            result = CurriculumService.regenerate_prerequisites_only(subject_id)
            return result
        except ValueError as e:
            abort(400, message=str(e))
        except Exception as e:
            abort(500, message=f"Erreur: {str(e)}")


@blp.route("/subject/<string:subject_id>")
class CurriculumBySubject(MethodView):
    """Récupérer le curriculum d'une matière."""
    
    @blp.response(200)
    def get(self, subject_id):
        """Récupérer le curriculum existant d'une matière."""
        subject = Subject.find_by_id(subject_id)
        if not subject:
            abort(404, message=f"Matière {subject_id} introuvable")
        
        competences = Competence.find_by_subject(subject_id)
        
        if not competences:
            return {
                "subject": Subject.to_dict(subject),
                "has_curriculum": False,
                "competences": [],
                "graph": {"nodes": [], "edges": [], "stats": {}},
                "message": "Curriculum non généré. Utilisez POST /api/curriculum/generate/{subject_id}"
            }
        
        return {
            "subject": Subject.to_dict(subject),
            "has_curriculum": True,
            "competences": [Competence.to_dict(c, include_prerequisites=True) for c in competences],
            "graph": GraphService.build_graph_data(competences),
            "stats": GraphService.get_graph_stats(competences)
        }


@blp.route("/graph/<string:subject_id>")
class CurriculumGraph(MethodView):
    """Récupérer uniquement le graphe (pour visualisation frontend)."""
    
    @blp.response(200)
    def get(self, subject_id):
        """Récupérer le graphe de compétences pour visualisation."""
        subject = Subject.find_by_id(subject_id)
        if not subject:
            abort(404, message=f"Matière {subject_id} introuvable")
        
        competences = Competence.find_by_subject(subject_id)
        
        if not competences:
            abort(404, message="Curriculum non généré pour cette matière")
        
        return GraphService.build_graph_data(competences)


@blp.route("/visualize/<string:subject_id>")
class CurriculumVisualize(MethodView):
    """Générer et retourner l'image du graphe."""
    
    @blp.response(200, description="Image PNG du graphe")
    def get(self, subject_id):
        """Visualiser le graphe de compétences (retourne une image PNG)."""
        from pathlib import Path
        
        # Vérifier matière
        subject = Subject.find_by_id(subject_id)
        if not subject:
            abort(404, message=f"Matière {subject_id} introuvable")
        
        # Récupérer compétences
        competences = Competence.find_by_subject(subject_id)
        if not competences:
            abort(404, message="Aucun curriculum généré")
        
        # Générer l'image
        try:
            file_path = GraphService.visualize_graph(
                competences,
                subject_name=subject['name'],
                subject_id=subject_id
            )
            
            # Vérifier que le fichier existe
            if not Path(file_path).exists():
                abort(500, message=f"Fichier non créé: {file_path}")
            
            # Retourner l'image
            return send_file(
                file_path,
                mimetype='image/png',
                as_attachment=False,
                download_name=f"curriculum_{subject_id}.png"
            )
        
        except Exception as e:
            abort(500, message=f"Erreur génération: {str(e)}")


@blp.route("/validate/<string:subject_id>")
class CurriculumValidate(MethodView):
    """Valider le graphe de compétences."""
    
    @blp.response(200)
    def get(self, subject_id):
        """Valider que le graphe est un DAG valide."""
        subject = Subject.find_by_id(subject_id)
        if not subject:
            abort(404, message=f"Matière {subject_id} introuvable")
        
        competences = Competence.find_by_subject(subject_id)
        
        if not competences:
            return {"valid": True, "message": "Aucune compétence (graphe vide)"}
        
        is_valid, message = GraphService.validate_dag(competences)
        
        return {
            "valid": is_valid,
            "message": message,
            "competences_count": len(competences)
        }

@blp.route("/stats/<string:subject_id>")
class CurriculumStats(MethodView):
    """Statistiques du curriculum."""
    
    @blp.response(200)
    def get(self, subject_id):
        """Obtenir les statistiques complètes du curriculum."""
        subject = Subject.find_by_id(subject_id)
        if not subject:
            abort(404, message=f"Matière {subject_id} introuvable")
        
        competences = Competence.find_by_subject(subject_id)
        
        if not competences:
            return {
                "subject": Subject.to_dict(subject),
                "has_curriculum": False,
                "stats": {}
            }
        
        stats = GraphService.get_graph_stats(competences)
        
        # Ajouter des détails supplémentaires
        root_nodes = GraphService.get_root_nodes(competences)
        leaf_nodes = GraphService.get_leaf_nodes(competences)
        longest_path = GraphService.get_longest_path(competences)
        
        # Compétences racines avec détails
        root_details = []
        for node_id in root_nodes:
            comp = Competence.find_by_id(node_id)
            if comp:
                root_details.append({
                    "id": str(comp['_id']),
                    "code": comp['code'],
                    "name": comp['name']
                })
        
        # Compétences terminales avec détails
        leaf_details = []
        for node_id in leaf_nodes:
            comp = Competence.find_by_id(node_id)
            if comp:
                leaf_details.append({
                    "id": str(comp['_id']),
                    "code": comp['code'],
                    "name": comp['name']
                })
        
        return {
            "subject": Subject.to_dict(subject),
            "has_curriculum": True,
            "stats": stats,
            "root_nodes_details": root_details,
            "leaf_nodes_details": leaf_details,
            "longest_path_length": len(longest_path)
        }