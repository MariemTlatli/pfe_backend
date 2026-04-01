"""
Modèle Domain - Domaine de connaissance (ex: Programmation, Mathématiques).
"""

from app.extensions import mongo
from bson import ObjectId
from datetime import datetime


class Domain:
    """Gestion des domaines de connaissance."""
    
    COLLECTION = 'domains'
    
    @staticmethod
    def create(name, description=None):
        """
        Créer un nouveau domaine.
        
        Args:
            name (str): Nom du domaine
            description (str, optional): Description
            
        Returns:
            dict: Document créé avec _id
            
        Raises:
            ValueError: Si le nom existe déjà
        """
        # Vérifier si existe déjà
        if mongo.db[Domain.COLLECTION].find_one({'name': name}):
            raise ValueError(f"Le domaine '{name}' existe déjà")
        
        domain = {
            'name': name,
            'description': description,
            'created_at': datetime.utcnow()
        }
        
        result = mongo.db[Domain.COLLECTION].insert_one(domain)
        domain['_id'] = result.inserted_id
        
        return domain
    
    @staticmethod
    def find_all():
        """
        Récupérer tous les domaines.
        
        Returns:
            list: Liste de tous les domaines
        """
        return list(mongo.db[Domain.COLLECTION].find().sort('name', 1))
    
    @staticmethod
    def find_by_id(domain_id):
        """
        Trouver un domaine par ID.
        
        Args:
            domain_id (str|ObjectId): ID du domaine
            
        Returns:
            dict|None: Document du domaine ou None
        """
        try:
            return mongo.db[Domain.COLLECTION].find_one({'_id': ObjectId(domain_id)})
        except Exception:
            return None
    
    @staticmethod
    def find_by_name(name):
        """
        Trouver un domaine par nom.
        
        Args:
            name (str): Nom du domaine
            
        Returns:
            dict|None: Document du domaine ou None
        """
        return mongo.db[Domain.COLLECTION].find_one({'name': name})
    
    @staticmethod
    def update(domain_id, updates):
        """
        Mettre à jour un domaine.
        
        Args:
            domain_id (str|ObjectId): ID du domaine
            updates (dict): Champs à mettre à jour
            
        Returns:
            bool: True si mis à jour
        """
        result = mongo.db[Domain.COLLECTION].update_one(
            {'_id': ObjectId(domain_id)},
            {'$set': updates}
        )
        return result.modified_count > 0
    
    @staticmethod
    def delete(domain_id):
        """
        Supprimer un domaine et ses matières associées.
        
        Args:
            domain_id (str|ObjectId): ID du domaine
            
        Returns:
            bool: True si supprimé
        """
        from app.models.subject import Subject
        
        # Supprimer toutes les matières du domaine
        subjects = Subject.find_by_domain(domain_id)
        for subject in subjects:
            Subject.delete(subject['_id'])
        
        # Supprimer le domaine
        result = mongo.db[Domain.COLLECTION].delete_one({'_id': ObjectId(domain_id)})
        return result.deleted_count > 0
    
    @staticmethod
    def count_subjects(domain_id):
        """
        Compter le nombre de matières dans un domaine.
        
        Args:
            domain_id (str|ObjectId): ID du domaine
            
        Returns:
            int: Nombre de matières
        """
        from app.models.subject import Subject
        return mongo.db[Subject.COLLECTION].count_documents({'domain_id': ObjectId(domain_id)})
    
    @staticmethod
    def to_dict(domain, include_subjects_count=True):
        """
        Convertir un document MongoDB en dict JSON-friendly.
        
        Args:
            domain (dict): Document MongoDB
            include_subjects_count (bool): Inclure le nombre de matières
            
        Returns:
            dict|None: Dictionnaire formaté ou None
        """
        if not domain:
            return None
        
        data = {
            'id': str(domain['_id']),
            'name': domain['name'],
            'description': domain.get('description'),
            'created_at': domain['created_at'].isoformat()
        }
        
        if include_subjects_count:
            data['subjects_count'] = Domain.count_subjects(domain['_id'])
        
        return data