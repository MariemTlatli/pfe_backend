"""
Routes Domains - CRUD des domaines de connaissance.
"""

from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.models.domain import Domain
from app.schemas.domain import DomainSchema, DomainCreateSchema, DomainUpdateSchema
from app.schemas.common import MessageSchema


blp = Blueprint(
    "Domains",
    __name__,
    url_prefix="/api/domains",
    description="Gestion des domaines de connaissance"
)


@blp.route("")
class DomainList(MethodView):
    """Liste et création de domaines."""
    
    @blp.response(200, DomainSchema(many=True))
    def get(self):
        """Récupérer tous les domaines."""
        domains = Domain.find_all()
        return [Domain.to_dict(d) for d in domains]
    
    @blp.arguments(DomainCreateSchema)
    @blp.response(201, DomainSchema)
    def post(self, data):
        """Créer un nouveau domaine."""
        try:
            domain = Domain.create(
                name=data['name'],
                description=data.get('description')
            )
            return Domain.to_dict(domain)
        except ValueError as e:
            abort(409, message=str(e))
        except Exception as e:
            abort(500, message=f"Erreur serveur: {str(e)}")


@blp.route("/<string:domain_id>")
class DomainDetail(MethodView):
    """Opérations sur un domaine spécifique."""
    
    @blp.response(200, DomainSchema)
    def get(self, domain_id):
        """Récupérer un domaine par ID."""
        domain = Domain.find_by_id(domain_id)
        if not domain:
            abort(404, message=f"Domaine {domain_id} introuvable")
        return Domain.to_dict(domain)
    
    @blp.arguments(DomainUpdateSchema)
    @blp.response(200, DomainSchema)
    def put(self, data, domain_id):
        """Mettre à jour un domaine."""
        domain = Domain.find_by_id(domain_id)
        if not domain:
            abort(404, message=f"Domaine {domain_id} introuvable")
        
        updates = {k: v for k, v in data.items() if v is not None}
        if updates:
            Domain.update(domain_id, updates)
        
        domain = Domain.find_by_id(domain_id)
        return Domain.to_dict(domain)
    
    @blp.response(200, MessageSchema)
    def delete(self, domain_id):
        """Supprimer un domaine et ses matières."""
        domain = Domain.find_by_id(domain_id)
        if not domain:
            abort(404, message=f"Domaine {domain_id} introuvable")
        
        Domain.delete(domain_id)
        return {"message": f"Domaine '{domain['name']}' supprimé avec succès"}


@blp.route("/<string:domain_id>/subjects")
class DomainSubjects(MethodView):
    """Matières d'un domaine."""
    
    @blp.response(200)
    def get(self, domain_id):
        """Récupérer les matières d'un domaine."""
        from app.models.subject import Subject
        
        domain = Domain.find_by_id(domain_id)
        if not domain:
            abort(404, message=f"Domaine {domain_id} introuvable")
        
        subjects = Subject.find_by_domain(domain_id)
        
        return {
            "domain": Domain.to_dict(domain),
            "subjects": [Subject.to_dict(s) for s in subjects],
            "count": len(subjects)
        }