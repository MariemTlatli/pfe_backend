"""
Script de migration : ajoute les champs ZPD aux compétences existantes.
Usage : python scripts/migrate_competences_zpd.py

Idempotent — peut être relancé sans risque.
"""

from pymongo import MongoClient
from pymongo.uri_parser import parse_uri
from datetime import datetime
import sys
import os

# ── Ajouter le répertoire racine au path ──
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from app.config import Config
from app.models.competence import Competence


def get_db():
    """Connexion à MongoDB avec extraction correcte du nom de la DB."""
    mongo_uri = Config.MONGO_URI
    print(f"📡 URI MongoDB : {mongo_uri}")

    # Extraction fiable du nom de la DB via le parser officiel
    parsed = parse_uri(mongo_uri)
    db_name = parsed.get("database")

    # Fallback si pas de DB dans l'URI
    if not db_name:
        db_name = "adaptive_learning"
        print(f"⚠️  Pas de DB dans l'URI, fallback → '{db_name}'")

    print(f"📂 Base de données : {db_name}")

    client = MongoClient(mongo_uri)

    # Test de connexion
    try:
        client.admin.command("ping")
        print("✅ Connexion MongoDB OK")
    except Exception as e:
        print(f"❌ Connexion MongoDB échouée : {e}")
        sys.exit(1)

    return client[db_name]


def migrate():
    db = get_db()
    collection = db[Competence.collection_name]

    # ── Diagnostic ──
    total_docs = collection.count_documents({})
    print(f"\n📊 Collection '{Competence.collection_name}' : {total_docs} document(s)")

    if total_docs == 0:
        print("⚠️  Aucune compétence en base. Rien à migrer.")
        print("   → Générez d'abord un curriculum via POST /api/curriculum/generate/{subject_id}")
        return

    # Afficher un exemple de document existant
    sample = collection.find_one()
    print(f"\n🔍 Exemple de document existant :")
    print(f"   code          : {sample.get('code', 'N/A')}")
    print(f"   name          : {sample.get('name', 'N/A')}")
    print(f"   zpd_thresholds: {'✅ présent' if 'zpd_thresholds' in sample else '❌ absent'}")
    print(f"   difficulty_params: {'✅ présent' if 'difficulty_params' in sample else '❌ absent'}")

    # ── Trouver les compétences à migrer ──
    query = {
        "$or": [
            {"zpd_thresholds": {"$exists": False}},
            {"difficulty_params": {"$exists": False}},
        ]
    }
    to_migrate = collection.count_documents(query)

    if to_migrate == 0:
        print(f"\n✅ Aucune migration nécessaire — les {total_docs} document(s) ont déjà les champs ZPD.")
        return

    print(f"\n📦 {to_migrate}/{total_docs} compétences à migrer...\n")

    competences = list(collection.find(query))
    updated = 0
    errors = 0

    for comp in competences:
        try:
            update_fields = {}

            if "zpd_thresholds" not in comp:
                update_fields["zpd_thresholds"] = Competence.DEFAULT_ZPD_THRESHOLDS.copy()

            if "difficulty_params" not in comp:
                level = comp.get("level", 0)
                diff_params = Competence.DEFAULT_DIFFICULTY_PARAMS.copy()
                diff_params["base_difficulty"] = round(min(0.3 + (level * 0.1), 0.9), 2)
                update_fields["difficulty_params"] = diff_params

            if "updated_at" not in comp:
                update_fields["updated_at"] = datetime.utcnow()
            if "created_at" not in comp:
                update_fields["created_at"] = datetime.utcnow()

            if update_fields:
                result = collection.update_one(
                    {"_id": comp["_id"]},
                    {"$set": update_fields}
                )

                if result.modified_count > 0:
                    updated += 1
                    base_diff = update_fields.get("difficulty_params", {}).get("base_difficulty", "—")
                    print(f"  ✓ {comp.get('code', '???'):10s} | {comp.get('name', '???'):30s} | "
                          f"level={comp.get('level', 0)} | base_diff={base_diff}")
                else:
                    print(f"  ⚠ {comp.get('code', '???'):10s} | Pas de modification (déjà à jour ?)")

        except Exception as e:
            errors += 1
            print(f"  ✗ {comp.get('code', '???'):10s} | ERREUR : {e}")

    # ── Résultat ──
    print(f"\n{'='*60}")
    print(f"  Migrées   : {updated}")
    print(f"  Erreurs   : {errors}")
    print(f"  Total DB  : {total_docs}")
    print(f"{'='*60}")

    # ── Vérification finale ──
    remaining = collection.count_documents(query)
    if remaining == 0:
        print("✅ Vérification OK — toutes les compétences ont les champs ZPD.")
    else:
        print(f"⚠️  {remaining} document(s) restent sans champs ZPD.")

    # ── Afficher un document migré pour vérification ──
    if updated > 0:
        migrated_sample = collection.find_one({"code": competences[0].get("code")})
        print(f"\n🔍 Vérification du premier document migré ({migrated_sample.get('code')}) :")
        print(f"   zpd_thresholds  : {migrated_sample.get('zpd_thresholds')}")
        print(f"   difficulty_params: {migrated_sample.get('difficulty_params')}")


if __name__ == "__main__":
    print("=" * 60)
    print("  MIGRATION : Ajout des champs ZPD aux compétences")
    print("=" * 60)
    print()
    migrate()