from app.extensions import mongo
from bson import ObjectId
from datetime import datetime
from app.services.ollama_service import OllamaService
import math
import random

COLLECTION_GAME = "game"
COULEURS = ["j", "b", "v", "r"]
COLLECTION_USERS = "users"


class GamificationServiceV2:

    # ─────────────────────────────────────────────
    # CARTES PÉDAGOGIQUES
    # ─────────────────────────────────────────────

    @staticmethod
    def get_user_special_cards(user_id):
        """Récupère toutes les infos de gamification d'un utilisateur."""
        user_id_obj = ObjectId(user_id) if isinstance(user_id, str) else user_id
        # ERREUR: GamificationService.COLLECTION_USERS -> COLLECTION_USERS (variable globale)
        user = mongo.db[COLLECTION_USERS].find_one({"_id": user_id_obj})

        if not user:
            return {
                "joker_cards": 0,
                "plus4_cards": 0,
                "reverse_cards": 0,
                "skip_cards": 0,
                "plus2_cards": 0,
            }

        return {
            "plus2_cards": user.get("plus2_cards", 0),
            "joker_cards": user.get("joker_cards", 0),
            "plus4_cards": user.get("plus4_cards", 0),
            "reverse_cards": user.get("reverse_cards", 0),
            "skip_cards": user.get("skip_cards", 0),
        }

    @staticmethod
    def distribuer_les_cartes_deterministe(user_id, difficulty, nb_cartes=7):
        """Distribue les valeurs des cartes selon la difficulté."""
        difficulty = max(0, min(1, difficulty))
        somme_cible = round(difficulty * 10)

        cartes = [0] * nb_cartes
        for i in range(somme_cible):
            cartes[i % nb_cartes] += 1

        return cartes

    @staticmethod
    def get_couleur_dominante(difficulty):
        """Retourne la couleur dominante en fonction de la difficulté."""
        difficulty = max(0, min(1, difficulty))

        if difficulty <= 0.2:
            return "j"
        elif difficulty <= 0.4:
            return "b"
        elif difficulty <= 0.8:
            return "v"
        else:  # ERREUR: "elif difficulty > 0.8 or difficulty >= 1" redondant -> else
            return "r"

    @staticmethod
    def generer_couleurs_cartes(difficulty, nb_cartes=7):
        """Génère une liste de couleurs pour les cartes avec une couleur dominante."""
        couleur_dominante = GamificationServiceV2.get_couleur_dominante(difficulty)

        nb_dominantes = math.ceil(nb_cartes / 2)
        nb_autres = nb_cartes - nb_dominantes

        autres_couleurs = [c for c in COULEURS if c != couleur_dominante]
        couleurs = [couleur_dominante] * nb_dominantes

        for _ in range(nb_autres):
            couleurs.append(random.choice(autres_couleurs))

        random.shuffle(couleurs)
        return couleurs

    @staticmethod
    def attribuer_les_cartes(user_id, difficulty, nb_cartes=7):
        """Attribue 7 cartes avec une valeur et une couleur dominante."""
        valeurs = GamificationServiceV2.distribuer_les_cartes_deterministe(
            user_id, difficulty, nb_cartes
        )
        couleurs = GamificationServiceV2.generer_couleurs_cartes(difficulty, nb_cartes)

        cartes = [
            {
                "user_id": user_id,
                "valeur": valeurs[i],
                "couleur": couleurs[i],
            }
            for i in range(nb_cartes)
        ]
        return cartes

    @staticmethod
    def vider_la_main(user_id):
        """Supprime toutes les cartes associées à un utilisateur."""
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)

            collection = mongo.db[COLLECTION_GAME]  # ERREUR: mongo.db.cartes -> COLLECTION_GAME
            result = collection.delete_many({"user_id": user_id})

            return {
                "success": True,
                "deleted_count": result.deleted_count,
                "message": f"{result.deleted_count} carte(s) supprimée(s)."
            }
        except Exception as e:
            return {
                "success": False,
                "deleted_count": 0,
                "message": str(e)
            }

    @staticmethod
    def mettre_a_jour_cartes_existantes(user_id, difficulty):
        """Met à jour les cartes existantes sans les supprimer."""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        collection = mongo.db[COLLECTION_GAME]

        # ERREUR: attribuer_les_cartes() -> GamificationServiceV2.attribuer_les_cartes()
        nouvelles_cartes = GamificationServiceV2.attribuer_les_cartes(str(user_id), difficulty)
        anciennes_cartes = list(collection.find({"user_id": user_id}))

        for ancienne, nouvelle in zip(anciennes_cartes, nouvelles_cartes):
            collection.update_one(
                {"_id": ancienne["_id"]},
                {
                    "$set": {
                        "valeur": nouvelle["valeur"],
                        "couleur": nouvelle["couleur"],
                    }
                }
            )

        return {
            "success": True,
            "message": "Cartes mises à jour.",
            "couleur_dominante": GamificationServiceV2.get_couleur_dominante(difficulty)
        }

    # ─────────────────────────────────────────────
    # CARTES SPÉCIALES
    # ─────────────────────────────────────────────

    @staticmethod
    def initialiser_les_cartes_special(user_id):  # ERREUR: caractère spécial "é" dans le nom
        """Initialise les champs des cartes spéciales pour un utilisateur."""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        result = mongo.db[COLLECTION_USERS].update_one(
            {"_id": user_id},
            {
                "$set": {
                    "joker_cards": 0,
                    "plus4_cards": 0,
                    "reverse_cards": 0,
                    "skip_cards": 0,
                    "plus2_cards": 0,
                    "nb_exercices_imposes": 0,
                    "reverse_shield": False,
                    "emotion_counters": {},
                    "difficulty": 0.5,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count

    # ─────────────────────────────────────────────
    # CARTE +2
    # ─────────────────────────────────────────────

    @staticmethod
    def attribuer_carte_plus2(user_id):
        """Attribue une carte +2 à l'utilisateur."""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        result = mongo.db[COLLECTION_USERS].update_one(
            {"_id": user_id},
            {
                "$inc": {"plus2_cards": 1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return {
            "success": result.modified_count > 0,
            "message": "Carte +2 attribuée."
        }

    @staticmethod
    def proposer_utilisateurs_cibles(user_id, nombre=4):
        """Propose des utilisateurs cibles aléatoires."""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        utilisateurs = list(
            mongo.db[COLLECTION_USERS].aggregate([
                {"$match": {"_id": {"$ne": user_id}}},
                {"$sample": {"size": nombre}},
                {"$project": {"username": 1}}
            ])
        )

        for user in utilisateurs:
            user["_id"] = str(user["_id"])

        return utilisateurs

    @staticmethod
    def utiliser_carte_plus2(from_user_id, to_user_id, nb_exercices=2):
        """
        Utilise une carte +2 contre un utilisateur.
        Si la cible possède un bouclier d'inversion, l'effet est renvoyé à l'expéditeur.
        """
        if isinstance(from_user_id, str):
            from_user_id = ObjectId(from_user_id)
        if isinstance(to_user_id, str):
            to_user_id = ObjectId(to_user_id)

        users_collection = mongo.db[COLLECTION_USERS]
        history_collection = mongo.db.actions_plus2

        from_user = users_collection.find_one({"_id": from_user_id})
        to_user = users_collection.find_one({"_id": to_user_id})

        if not from_user or not to_user:
            return {"success": False, "message": "Utilisateur introuvable."}

        if from_user.get("plus2_cards", 0) <= 0:
            return {"success": False, "message": "Aucune carte +2 disponible."}

        # Vérifier le bouclier d'inversion
        if to_user.get("reverse_shield", False):
            users_collection.update_one(
                {"_id": to_user_id},
                {"$set": {"reverse_shield": False, "updated_at": datetime.utcnow()}}
            )
            users_collection.update_one(
                {"_id": from_user_id},
                {
                    "$inc": {"plus2_cards": -1, "nb_exercices_imposes": nb_exercices},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )

            history_collection.insert_one({
                "from_user_id": from_user_id,
                "to_user_id": to_user_id,
                "action": "plus2_reversed",
                "nb_exercices": nb_exercices,
                "created_at": datetime.utcnow()
            })

            return {
                "success": True,
                "message": "Attaque +2 renvoyée à l'expéditeur grâce au bouclier d'inversion."
            }

        # Cas normal
        users_collection.update_one(
            {"_id": from_user_id},
            {
                "$inc": {"plus2_cards": -1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        users_collection.update_one(
            {"_id": to_user_id},
            {
                "$inc": {"nb_exercices_imposes": nb_exercices},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        history_collection.insert_one({
            "from_user_id": from_user_id,
            "to_user_id": to_user_id,
            "action": "plus2_used",
            "nb_exercices": nb_exercices,
            "created_at": datetime.utcnow()
        })

        return {"success": True, "message": "Carte +2 appliquée avec succès."}
        # ERREUR: code mort supprimé (instructions après return)

    @staticmethod
    def enregistrer_historique_plus2(from_user_id, to_user_id):
        """Enregistre l'historique d'utilisation d'une carte +2."""
        mongo.db.actions_plus2.insert_one({
            "from_user_id": from_user_id,
            "to_user_id": to_user_id,
            "nb_exercices": 2,
            "used_at": datetime.utcnow()
        })

    # ─────────────────────────────────────────────
    # CARTE SKIP
    # ─────────────────────────────────────────────

    @staticmethod
    def attribuer_carte_skip(user_id):
        """Attribue une carte Skip à l'utilisateur."""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        result = mongo.db[COLLECTION_USERS].update_one(
            {"_id": user_id},
            {
                "$inc": {"skip_cards": 1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return {
            "success": result.modified_count > 0,
            "message": "Carte Skip attribuée."
        }

    @staticmethod
    def utiliser_carte_skip(user_id, nb_exercices_a_annuler=2):
        """Permet à un utilisateur d'utiliser une carte Skip."""
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)

            users_collection = mongo.db[COLLECTION_USERS]
            history_collection = mongo.db.actions_skip

            user = users_collection.find_one({"_id": user_id})
            if not user:
                return {"success": False, "message": "Utilisateur introuvable."}

            if user.get("skip_cards", 0) <= 0:
                return {"success": False, "message": "Aucune carte Skip disponible."}

            nb_imposes = user.get("nb_exercices_imposes", 0)
            if nb_imposes <= 0:
                return {"success": False, "message": "Aucun exercice imposé à annuler."}

            nb_annules = min(nb_exercices_a_annuler, nb_imposes)

            users_collection.update_one(
                {"_id": user_id},
                {
                    "$inc": {
                        "skip_cards": -1,
                        "nb_exercices_imposes": -nb_annules
                    },
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )

            history_collection.insert_one({
                "user_id": user_id,
                "action": "skip_used",
                "nb_exercices_annules": nb_annules,
                "used_at": datetime.utcnow()
            })

            return {
                "success": True,
                "message": f"{nb_annules} exercice(s) imposé(s) annulé(s).",
                "skip_cards_restantes": user.get("skip_cards", 1) - 1
            }

        except Exception as e:
            return {"success": False, "message": str(e)}

    # ─────────────────────────────────────────────
    # CARTE INVERSION
    # ─────────────────────────────────────────────

    @staticmethod
    def activer_carte_inversion(user_id):
        """Active le bouclier d'inversion pour la prochaine attaque +2."""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        users_collection = mongo.db[COLLECTION_USERS]
        user = users_collection.find_one({"_id": user_id})

        if not user:
            return {"success": False, "message": "Utilisateur introuvable."}
        if user.get("reverse_cards", 0) <= 0:
            return {"success": False, "message": "Aucune carte Inversion disponible."}
        if user.get("reverse_shield", False):
            return {"success": False, "message": "Le bouclier est déjà actif."}

        users_collection.update_one(
            {"_id": user_id},
            {
                "$inc": {"reverse_cards": -1},
                "$set": {
                    "reverse_shield": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        mongo.db.actions_reverse.insert_one({
            "user_id": user_id,
            "action": "reverse_shield_activated",
            "created_at": datetime.utcnow()
        })

        return {"success": True, "message": "Bouclier d'inversion activé."}

    @staticmethod
    def attribuer_carte_inversion_par_emotion(user_id, emotion_type, seuil=12):
        """Attribue une carte Inversion quand une émotion dominante atteint le seuil."""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        users_collection = mongo.db[COLLECTION_USERS]
        history_collection = mongo.db.actions_reverse

        user = users_collection.find_one({"_id": user_id})
        if not user:
            return {"success": False, "message": "Utilisateur introuvable."}

        emotions = user.get("emotion_counters", {})
        current_value = emotions.get(emotion_type, 0)

        if current_value < seuil:
            return {
                "success": False,
                "message": f"Seuil non atteint ({current_value}/{seuil})."
            }

        users_collection.update_one(
            {"_id": user_id},
            {
                "$inc": {"reverse_cards": 1},
                "$set": {
                    f"emotion_counters.{emotion_type}": 0,
                    "updated_at": datetime.utcnow()
                }
                # ERREUR: deux update_one séparés fusionnés en un seul
            }
        )

        history_collection.insert_one({
            "user_id": user_id,
            "action": "reverse_card_awarded",
            "emotion_type": emotion_type,
            "emotion_value": current_value,
            "threshold": seuil,
            "created_at": datetime.utcnow()
        })

        return {
            "success": True,
            "message": "Carte Inversion attribuée grâce à l'engagement émotionnel.",
            "emotion": emotion_type,
            "value": current_value
        }

    @staticmethod
    def increment_emotion(user_id, emotion_type):
        """Incrémente le compteur d'une émotion pour un utilisateur."""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        mongo.db[COLLECTION_USERS].update_one(
            {"_id": user_id},
            {"$inc": {f"emotion_counters.{emotion_type}": 1}}
        )

    # ─────────────────────────────────────────────
    # CARTE +4 / FIN MAÎTRISE
    # ─────────────────────────────────────────────

    @staticmethod
    def attribuer_carte_plus4(user_id, competence_id):
        """Attribue une carte +4 lorsqu'une compétence est maîtrisée."""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        if isinstance(competence_id, str):
            competence_id = ObjectId(competence_id)

        users_collection = mongo.db[COLLECTION_USERS]
        
        # Attribution de la carte +4
        result = users_collection.update_one(
            {"_id": user_id},
            {
                "$inc": {"plus4_cards": 1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        return {
            "success": result.modified_count > 0,
            "message": "Carte +4 attribuée suite à la maîtrise de la compétence.",
            "reward": "+4"
        }

    # ─────────────────────────────────────────────
    # UTILISER CARTE +4
    # ─────────────────────────────────────────────

    @staticmethod
    def utiliser_carte_plus4(user_id, exercise_id):
        """
        Utilise une carte +4 pour obtenir 4 indices dans l'exercice en cours.
        """
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        if isinstance(exercise_id, str):
            exercise_id = ObjectId(exercise_id)

        users_collection = mongo.db[COLLECTION_USERS]
        exercises_collection = mongo.db.exercises

        # 1. Vérifier si l'utilisateur a une carte +4
        user = users_collection.find_one({"_id": user_id})
        if not user or user.get("plus4_cards", 0) <= 0:
            return {"success": False, "message": "Aucune carte +4 disponible."}

        # 2. Récupérer l'exercice
        exercise = exercises_collection.find_one({"_id": exercise_id})
        if not exercise:
            return {"success": False, "message": "Exercice introuvable."}

        # 2b. Générer 4 NOUVEAUX indices via Ollama (llama3.2)
        prompt = f"""
        Tu es un tuteur pédagogique expert. Ta mission est de générer EXACTEMENT 4 indices progressifs pour aider un élève à résoudre l'exercice suivant sans donner directement la réponse.

        EXERCICE:
        Question: {exercise.get('question', '')}
        Réponse correcte (pour ton information): {exercise.get('correct_answer', '')}

        CONSIGNES:
        1. Les indices doivent être de plus en plus révélateurs.
        2. Le premier doit être subtil, le dernier doit être une aide majeure.
        3. Ne donne PAS la réponse finale.
        4. Réponds UNIQUEMENT par un tableau JSON de 4 chaînes de caractères.
        Assure-toi que la liste 'indices' contient exactement 4 éléments.
        FORMAT ATTENDU:
        ["Indice 1", "Indice 2", "Indice 3", "Indice 4"]
        """
        try:
            generated_hints = OllamaService.generate_json(prompt, temperature=0.7)
            print("+++++++++++++++++++++++++++++++++++")
            print("generated_hints")
            print(generated_hints)
            list_indices = list(generated_hints.values())
            print(list_indices)
            print("+++++++++++++++++++++++++++++++++++")
        except Exception as e:
            print(f"Erreur OllamaService: {e}")
            return {"success": False, "message": "Erreur lors de la génération des indices par Ollama."}

        if not list_indices or not isinstance(list_indices, list) or len(list_indices) < 4:
            return {"success": False, "message": "Format d'indices invalide reçu d'Ollama."}

        # 2c. Ajouter les indices à l'exercice en DB
        exercises_collection.update_one(
            {"_id": exercise_id},
            {"$push": {"hints": {"$each": list_indices}}}
        )

        # 3. Consommer la carte
        users_collection.update_one(
            {"_id": user_id},
            {
                "$inc": {"plus4_cards": -1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        # 4. Enregistrer l'action
        mongo.db.actions_plus4.insert_one({
            "user_id": user_id,
            "exercise_id": exercise_id,
            "action": "plus4_used",
            "hints_count": len(list_indices),
            "generated_hints": list_indices,
            "created_at": datetime.utcnow()
        })

        return {
            "success": True,
            "message": f"Carte +4 utilisée. 4 nouveaux indices ont été générés.",
            "hints": list_indices,
            "plus4_cards_restantes": user.get("plus4_cards", 1) - 1
        }

    # ─────────────────────────────────────────────
    # CARTE JOKER
    # ─────────────────────────────────────────────

    @staticmethod
    def utiliser_carte_joker(user_id, new_difficulty):
        """Permet à un utilisateur de changer la difficulté via une carte Joker."""
        new_difficulty = max(0, min(1, new_difficulty))

        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        users_collection = mongo.db[COLLECTION_USERS]
        user = users_collection.find_one({"_id": user_id})

        if not user:
            return {"success": False, "message": "Utilisateur introuvable."}

        if user.get("joker_cards", 0) <= 0:
            return {"success": False, "message": "Aucune carte Joker disponible."}

        old_difficulty = user.get("difficulty", 0.5)

        users_collection.update_one(
            {"_id": user_id},
            {
                "$inc": {"joker_cards": -1},
                "$set": {
                    "difficulty": new_difficulty,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        mongo.db.actions_joker.insert_one({
            "user_id": user_id,
            "old_difficulty": old_difficulty,
            "new_difficulty": new_difficulty,
            "action": "joker_used",
            "created_at": datetime.utcnow()
        })

        return {
            "success": True,
            "message": f"Difficulté changée de {old_difficulty} → {new_difficulty}",
            "old_difficulty": old_difficulty,
            "new_difficulty": new_difficulty
        }

    @staticmethod
    def attribuer_joker_par_emotion(user_id, seuil_sad=5):
        """Attribue une carte Joker si l'utilisateur a >= seuil_sad émotions 'sad'."""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        user_response_collection = mongo.db.user_response
        users_collection = mongo.db[COLLECTION_USERS]

        responses = list(user_response_collection.find({"user_id": user_id}))

        sad_count = sum(
            r.get("emotion_data", []).count("sad") for r in responses
        )

        if sad_count < seuil_sad:
            return {
                "success": False,
                "message": f"Seuil non atteint ({sad_count}/{seuil_sad})"
            }

        users_collection.update_one(
            {"_id": user_id},
            {
                "$inc": {"joker_cards": 1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        user_response_collection.update_many(
            {"user_id": user_id},
            {"$set": {"emotion_data": []}}
        )

        mongo.db.actions_joker.insert_one({
            "user_id": user_id,
            "action": "joker_awarded",
            "reason": "5_sad_emotions",
            "sad_count": sad_count,
            "created_at": datetime.utcnow()
        })

        return {
            "success": True,
            "message": f"Carte Joker attribuée ({sad_count} émotions sad détectées)",
            "sad_count": sad_count
        }

    # ─────────────────────────────────────────────
    # UNO
    # ─────────────────────────────────────────────

    @staticmethod
    def verifier_condition_uno(cartes_main, nb_exercices_restants):
        """Détermine si on doit afficher UNO."""
        total_cartes_main = sum(cartes_main)
        return nb_exercices_restants == 1 and total_cartes_main == 1

    @staticmethod  # ERREUR: méthode non statique -> ajout @staticmethod
    def get_uno_state(user_id, difficulty, nb_exercices_restants):
        """Retourne l'état UNO pour affichage frontend."""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        # ERREUR: appel sans GamificationServiceV2.
        cartes_main = GamificationServiceV2.distribuer_les_cartes_deterministe(
            user_id, difficulty
        )
        is_uno = GamificationServiceV2.verifier_condition_uno(
            cartes_main, nb_exercices_restants
        )

        return {
            "cartes_main": cartes_main,
            "total_cartes": sum(cartes_main),
            "nb_exercices_restants": nb_exercices_restants,
            "uno": is_uno
        }