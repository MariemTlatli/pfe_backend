"""
Service de gestion des domaines.
"""

from datetime import datetime
from bson.objectid import ObjectId
from app.extensions import mongo


class DomaineService:
    """Gère les opérations CRUD sur les domaines."""

    @staticmethod
    def get_all_domaines() -> list:
        """Retourne tous les domaines disponibles."""
        domaines = mongo.db.domaines.find()
        result = []

        for domaine in domaines:
            domaine["_id"] = str(domaine["_id"])
            result.append(domaine)

        return result

    @staticmethod
    def get_domaine_by_id(domaine_id: str) -> dict | None:
        """Retourne un domaine par son ID."""
        if not ObjectId.is_valid(domaine_id):
            return None

        domaine = mongo.db.domaines.find_one({"_id": ObjectId(domaine_id)})

        if domaine:
            domaine["_id"] = str(domaine["_id"])

        return domaine

    @staticmethod
    def get_user_domaines(user_id: str) -> list:
        """Retourne les domaines sélectionnés par un utilisateur."""
        user_domaines = mongo.db.user_domaines.find({"user_id": user_id})
        result = []

        for ud in user_domaines:
            domaine = mongo.db.domaines.find_one({"_id": ObjectId(ud["domaine_id"])})

            if domaine:
                result.append({
                    "_id": str(ud["_id"]),
                    "domaine_id": str(domaine["_id"]),
                    "name": domaine["name"],
                    "description": domaine["description"],
                    "icon": domaine["icon"],
                    "matieres": domaine.get("matieres", []),
                    "selected_at": ud["selected_at"].isoformat()
                })

        return result

    @staticmethod
    def select_domaines(user_id: str, domaine_ids: list) -> dict:
        """Sélectionne un ou plusieurs domaines."""
        added = 0
        skipped = 0

        for domaine_id in domaine_ids:
            if not ObjectId.is_valid(domaine_id):
                raise ValueError(f"ID invalide : {domaine_id}")

            domaine = mongo.db.domaines.find_one({"_id": ObjectId(domaine_id)})

            if not domaine:
                raise ValueError(f"Domaine introuvable : {domaine_id}")

            existing = mongo.db.user_domaines.find_one({
                "user_id": user_id,
                "domaine_id": domaine_id
            })

            if existing:
                skipped += 1
                continue

            mongo.db.user_domaines.insert_one({
                "user_id": user_id,
                "domaine_id": domaine_id,
                "selected_at": datetime.utcnow()
            })

            added += 1

        return {"added": added, "skipped": skipped}

    @staticmethod
    def deselect_domaine(user_id: str, domaine_id: str) -> bool:
        """Désélectionne un domaine."""
        result = mongo.db.user_domaines.delete_one({
            "user_id": user_id,
            "domaine_id": domaine_id
        })

        return result.deleted_count > 0