
# from app.extensions import mongo
# from bson import ObjectId
# from datetime import datetime
# import math
# import random
# COLLECTION_GAME = "game"
# COULEURS = ["j", "b", "v", "r"]
# class GamificationServiceV2:

#     @staticmethod
#     def get_user_special_cards(user_id):
#         """Récupère toutes les infos de gamification d'un utilisateur."""
#         user_id_obj = ObjectId(user_id) if isinstance(user_id, str) else user_id
#         user = mongo.db[GamificationService.COLLECTION_USERS].find_one({"_id": user_id_obj})
#         print("user", user)
#         if not user:
#             return {
#                 "joker_cards": 0,
#                 "plus4_cards": 0,
#                 "reverse_cards": 0,
#                 "skip_cards": 0,
#             }

#         joker_cards = user.get("joker_cards", 0)
#         plus4_cards = user.get("plus4_cards", 0)
#         reverse_cards = user.get("reverse_cards", 0)
#         skip_cards = user.get("skip_cards", 0)  
        
#         return {
#             "joker_cards": joker_cards,
#             "plus4_cards": plus4_cards,
#             "reverse_cards": reverse_cards,
#             "skip_cards": skip_cards,
#         }


#     @staticmethod
#     def distribuer_les_cartes_deterministe(user_id,difficulty, nb_cartes=7):
        
#         difficulty = max(0, min(1, difficulty))
#         somme_cible = round(difficulty * 10)
        
#         cartes = [0] * nb_cartes
#         for i in range(somme_cible):
#             cartes[i % nb_cartes] += 1
        
#         return cartes
#     @staticmethod    
#     def get_couleur_dominante(difficulty):
#         """
#         Retourne la couleur dominante en fonction de la difficulté.
        
#         :param difficulty: Niveau de difficulté entre 0 et 1
#         :return: Couleur dominante (str)
#         """
#         difficulty = max(0, min(1, difficulty))  # Assurer que la valeur est bornée

#         if difficulty <= 0.2:
#             return "j"
#         elif difficulty <= 0.4:
#             return "b"
#         elif difficulty <= 0.8:
#             return "v"
#         elif difficulty > 0.8 or difficulty >= 1:
#             return "r"
        

#     @staticmethod
#     def generer_couleurs_cartes(difficulty, nb_cartes=7):
#         """
#         Génère une liste de couleurs pour les cartes avec une couleur dominante.
#         """
#         couleur_dominante = GamificationServiceV2.get_couleur_dominante(difficulty)
        
#         # Nombre de cartes dominantes (majorité)
#         nb_dominantes = math.ceil(nb_cartes / 2)  # ex: 7 -> 4
#         nb_autres = nb_cartes - nb_dominantes

#         # Couleurs secondaires
#         autres_couleurs = [c for c in COULEURS if c != couleur_dominante]

#         couleurs = [couleur_dominante] * nb_dominantes

#         # Répartition aléatoire des autres couleurs
#         for _ in range(nb_autres):
#             couleurs.append(random.choice(autres_couleurs))

#         # Mélange pour éviter que les cartes dominantes soient groupées
#         random.shuffle(couleurs)

#         return couleurs
#     @staticmethod
#     def attribuer_les_cartes(user_id, difficulty, nb_cartes=7):
#         """
#         Attribue 7 cartes avec une valeur et une couleur dominante.
#         """
#         # Valeurs des cartes
#         valeurs = GamificationServiceV2.distribuer_les_cartes_deterministe(user_id, difficulty, nb_cartes)
        
#         # Couleurs des cartes
#         couleurs = GamificationServiceV2.generer_couleurs_cartes(difficulty, nb_cartes)

#         # Combinaison valeur + couleur
#         cartes = [
#             {
#                 "user_id": user_id,
#                 "valeur": valeurs[i],
#                 "couleur": couleurs[i],
#             }
#             for i in range(nb_cartes)
#         ]

#         return cartes    
#     @staticmethod
#     def vider_la_main(user_id):
#         """
#         Supprime toutes les cartes associées à un utilisateur.

#         :param user_id: Identifiant de l'utilisateur (str ou ObjectId)
#         :return: Nombre de cartes supprimées
#         """
#         try:
#             # Conversion en ObjectId si nécessaire
#             if isinstance(user_id, str):
#                 user_id = ObjectId(user_id)

#             # Accès à la collection des cartes
#             collection = mongo.db.cartes

#             # Suppression des cartes de l'utilisateur
#             result = collection.delete_many({"user_id": user_id})

#             return {
#                 "success": True,
#                 "deleted_count": result.deleted_count,
#                 "message": f"{result.deleted_count} carte(s) supprimée(s)."
#             }

#         except Exception as e:
#             return {
#                 "success": False,
#                 "deleted_count": 0,
#                 "message": str(e)
#             }
#     @staticmethod
#     def mettre_a_jour_cartes_existantes(user_id, difficulty):
#         """
#         Met à jour les cartes existantes sans les supprimer.
#         """
#         if isinstance(user_id, str):
#             user_id = ObjectId(user_id)

#         collection = mongo.db[COLLECTION_GAME]

#         # Générer les nouvelles cartes
#         nouvelles_cartes = attribuer_les_cartes(str(user_id), difficulty)

#         # Récupérer les cartes existantes
#         anciennes_cartes = list(collection.find({"user_id": user_id}))

#         # Mise à jour carte par carte
#         for ancienne, nouvelle in zip(anciennes_cartes, nouvelles_cartes):
#             collection.update_one(
#                 {"_id": ancienne["_id"]},
#                 {
#                     "$set": {
#                         "valeur": nouvelle["valeur"],
#                         "couleur": nouvelle["couleur"],
#                     }
#                 }
#             )

#         return {
#             "success": True,
#             "message": "Cartes mises à jour.",
#             "couleur_dominante": GamificationServiceV2.get_couleur_dominante(difficulty)
#         } 

#     from app.extensions import mongo
#     from datetime import datetime
#     @staticmethod
#     def initialiser_les_cartes_spécial(user_id):
#         """
#         Initialise les champs des cartes spéciales pour un utilisateur spécifique.
#         :param user_id: Identifiant de l'utilisateur (string ou ObjectId)
#         :return: Nombre de documents modifiés (0 ou 1)
#         """

#         # Conversion en ObjectId si nécessaire
#         if isinstance(user_id, str):
#             user_id = ObjectId(user_id)

#         result = mongo.db.users.update_one(
#             {"_id": user_id},
#             {
#                 "$set": {
#                     "joker_cards": 0,
#                     "plus4_cards": 0,
#                     "reverse_cards": 0,
#                     "skip_cards": 0,
#                     "plus2_cards": 0,
#                     "nb_exercices_imposes": 0,
#                     "updated_at": datetime.utcnow()
#                 }
#             }
#         )

#         return result.modified_count

#     from bson import ObjectId
#     from datetime import datetime
#     @staticmethod
#     def attribuer_carte_plus2(user_id):
#         if isinstance(user_id, str):
#             user_id = ObjectId(user_id)

#         result = mongo.db.users.update_one(
#             {"_id": user_id},
#             {
#                 "$inc": {"plus2_cards": 1},
#                 "$set": {"updated_at": datetime.utcnow()}
#             }
#         )

#         return {
#             "success": result.modified_count > 0,
#             "message": "Carte +2 attribuée."
#         }
#     @staticmethod
#     def proposer_utilisateurs_cibles(user_id, nombre=4):
#         from bson import ObjectId

#         if isinstance(user_id, str):
#             user_id = ObjectId(user_id)

#         utilisateurs = list(
#             mongo.db.users.aggregate([
#                 {"$match": {"_id": {"$ne": user_id}}},
#                 {"$sample": {"size": nombre}},
#                 {"$project": {"username": 1}}
#             ])
#         )

#         # Conversion des ObjectId en string pour l'API
#         for user in utilisateurs:
#             user["_id"] = str(user["_id"])

#         return utilisateurs
#     @staticmethod
#     def utiliser_carte_plus2(from_user_id, to_user_id, nb_exercices=2):
#         """
#         Utilise une carte +2 contre un utilisateur.
#         Si la cible possède un bouclier d'inversion, l'effet est renvoyé à l'expéditeur.
#         """
#         if isinstance(from_user_id, str):
#             from_user_id = ObjectId(from_user_id)
#         if isinstance(to_user_id, str):
#             to_user_id = ObjectId(to_user_id)

#         users_collection = mongo.db.users
#         history_collection = mongo.db.actions_plus2

#         from_user = users_collection.find_one({"_id": from_user_id})
#         to_user = users_collection.find_one({"_id": to_user_id})

#         if not from_user or not to_user:
#             return {"success": False, "message": "Utilisateur introuvable."}

#         if from_user.get("plus2_cards", 0) <= 0:
#             return {"success": False, "message": "Aucune carte +2 disponible."}

#         # 🔁 Vérifier le bouclier d'inversion
#         if to_user.get("reverse_shield", False):
#             # Désactiver le bouclier
#             users_collection.update_one(
#                 {"_id": to_user_id},
#                 {
#                     "$set": {
#                         "reverse_shield": False,
#                         "updated_at": datetime.utcnow()
#                     }
#                 }
#             )

#             # Décrémenter la carte +2 de l'expéditeur
#             users_collection.update_one(
#                 {"_id": from_user_id},
#                 {
#                     "$inc": {"plus2_cards": -1},
#                     "$set": {"updated_at": datetime.utcnow()}
#                 }
#             )

#             # Appliquer l'effet à l'expéditeur
#             users_collection.update_one(
#                 {"_id": from_user_id},
#                 {
#                     "$inc": {"nb_exercices_imposes": nb_exercices},
#                     "$set": {"updated_at": datetime.utcnow()}
#                 }
#             )

#             # Historique
#             history_collection.insert_one({
#                 "from_user_id": from_user_id,
#                 "to_user_id": to_user_id,
#                 "action": "plus2_reversed",
#                 "nb_exercices": nb_exercices,
#                 "created_at": datetime.utcnow()
#             })

#             return {
#                 "success": True,
#                 "message": "Attaque +2 renvoyée à l'expéditeur grâce au bouclier d'inversion."
#             }

#         # ✅ Cas normal : appliquer le +2 à la cible
#         users_collection.update_one(
#             {"_id": from_user_id},
#             {
#                 "$inc": {"plus2_cards": -1},
#                 "$set": {"updated_at": datetime.utcnow()}
#             }
#         )

#         users_collection.update_one(
#             {"_id": to_user_id},
#             {
#                 "$inc": {"nb_exercices_imposes": nb_exercices},
#                 "$set": {"updated_at": datetime.utcnow()}
#             }
#         )

#         # Historique
#         history_collection.insert_one({
#             "from_user_id": from_user_id,
#             "to_user_id": to_user_id,
#             "action": "plus2_used",
#             "nb_exercices": nb_exercices,
#             "created_at": datetime.utcnow()
#         })

#         return {
#             "success": True,
#             "message": "Carte +2 appliquée avec succès."
#         }

#         # Ajouter deux exercices imposés à l'utilisateur cible
#         users_collection.update_one(
#             {"_id": to_user_id},
#             {
#                 "$inc": {"nb_exercices_imposes": 2},
#                 "$set": {"updated_at": datetime.utcnow()}
#             }
#         )

#         return {
#             "success": True,
#             "message": "Carte +2 utilisée avec succès."
#         }
#     @staticmethod
#     def enregistrer_historique_plus2(from_user_id, to_user_id):
#         mongo.db.actions_plus2.insert_one({
#             "from_user_id": from_user_id,
#             "to_user_id": to_user_id,
#             "nb_exercices": 2,
#             "used_at": datetime.utcnow()
#         })

#     from app.extensions import mongo
#     from bson import ObjectId
#     from datetime import datetime
#     @staticmethod
#     def utiliser_carte_skip(user_id, nb_exercices_a_annuler=2):
#         """
#         Permet à un utilisateur d'utiliser une carte Skip pour annuler
#         des exercices imposés suite à une carte +2.

#         :param user_id: Identifiant de l'utilisateur (str ou ObjectId)
#         :param nb_exercices_a_annuler: Nombre d'exercices à annuler (par défaut 2)
#         :return: Dictionnaire contenant le résultat de l'opération
#         """
#         try:
#             # Conversion en ObjectId si nécessaire
#             if isinstance(user_id, str):
#                 user_id = ObjectId(user_id)

#             users_collection = mongo.db.users
#             history_collection = mongo.db.actions_skip

#             # Récupération de l'utilisateur
#             user = users_collection.find_one({"_id": user_id})
#             if not user:
#                 return {
#                     "success": False,
#                     "message": "Utilisateur introuvable."
#                 }

#             # Vérifier la disponibilité d'une carte Skip
#             if user.get("skip_cards", 0) <= 0:
#                 return {
#                     "success": False,
#                     "message": "Aucune carte Skip disponible."
#                 }

#             # Nombre actuel d'exercices imposés
#             nb_imposes = user.get("nb_exercices_imposes", 0)
#             if nb_imposes <= 0:
#                 return {
#                     "success": False,
#                     "message": "Aucun exercice imposé à annuler."
#                 }

#             # Calcul du nombre réel d'exercices à annuler
#             nb_annules = min(nb_exercices_a_annuler, nb_imposes)

#             # Mise à jour de l'utilisateur
#             users_collection.update_one(
#                 {"_id": user_id},
#                 {
#                     "$inc": {
#                         "skip_cards": -1,
#                         "nb_exercices_imposes": -nb_annules
#                     },
#                     "$set": {
#                         "updated_at": datetime.utcnow()
#                     }
#                 }
#             )

#             # Enregistrement dans l'historique
#             history_collection.insert_one({
#                 "user_id": user_id,
#                 "action": "skip_used",
#                 "nb_exercices_annules": nb_annules,
#                 "used_at": datetime.utcnow()
#             })

#             return {
#                 "success": True,
#                 "message": f"{nb_annules} exercice(s) imposé(s) annulé(s).",
#                 "skip_cards_restantes": user.get("skip_cards", 1) - 1
#             }

#         except Exception as e:
#             return {
#                 "success": False,
#                 "message": str(e)
#             }    
#     @staticmethod
#     def attribuer_carte_skip(user_id):
#         if isinstance(user_id, str):
#             user_id = ObjectId(user_id)

#         result = mongo.db.users.update_one(
#             {"_id": user_id},
#             {
#                 "$inc": {"skip_cards": 1},
#                 "$set": {"updated_at": datetime.utcnow()}
#             }
#         )

#         return {
#             "success": result.modified_count > 0,
#             "message": "Carte Skip attribuée."
#         }

#     from app.extensions import mongo
#     from bson import ObjectId
#     from datetime import datetime
#     @staticmethod
#     def activer_carte_inversion(user_id):
#         """
#         Active le bouclier d'inversion pour la prochaine attaque +2.
#         """
#         if isinstance(user_id, str):
#             user_id = ObjectId(user_id)

#         users_collection = mongo.db.users

#         user = users_collection.find_one({"_id": user_id})
#         if not user:
#             return {"success": False, "message": "Utilisateur introuvable."}

#         if user.get("reverse_cards", 0) <= 0:
#             return {"success": False, "message": "Aucune carte Inversion disponible."}

#         if user.get("reverse_shield", False):
#             return {"success": False, "message": "Le bouclier est déjà actif."}

#         users_collection.update_one(
#             {"_id": user_id},
#             {
#                 "$inc": {"reverse_cards": -1},
#                 "$set": {
#                     "reverse_shield": True,
#                     "updated_at": datetime.utcnow()
#                 }
#             }
#         )

#         # Historique
#         mongo.db.actions_reverse.insert_one({
#             "user_id": user_id,
#             "action": "reverse_shield_activated",
#             "created_at": datetime.utcnow()
#         })

#         return {
#             "success": True,
#             "message": "Bouclier d'inversion activé."
#         }
#     from app.extensions import mongo
#     from bson import ObjectId
#     from datetime import datetime
#     @staticmethod
#     def attribuer_carte_inversion_par_emotion(user_id, emotion_type, seuil=12):
#         """
#         Attribue une carte Inversion lorsque une émotion dominante atteint 12 occurrences.
#         """

#         if isinstance(user_id, str):
#             user_id = ObjectId(user_id)

#         users_collection = mongo.db.users
#         history_collection = mongo.db.actions_reverse

#         user = users_collection.find_one({"_id": user_id})

#         if not user:
#             return {
#                 "success": False,
#                 "message": "Utilisateur introuvable."
#             }

#         # Récupération du compteur émotionnel
#         emotions = user.get("emotion_counters", {})
#         current_value = emotions.get(emotion_type, 0)

#         # Vérification du seuil
#         if current_value < seuil:
#             return {
#                 "success": False,
#                 "message": f"Seuil non atteint ({current_value}/{seuil})."
#             }

#         # Attribution de la carte Inversion
#         users_collection.update_one(
#             {"_id": user_id},
#             {
#                 "$inc": {"reverse_cards": 1},
#                 "$set": {"updated_at": datetime.utcnow()}
#             }
#         )

#         # Optionnel : reset ou réduction du compteur émotionnel
#         users_collection.update_one(
#             {"_id": user_id},
#             {
#                 "$set": {f"emotion_counters.{emotion_type}": 0}
#             }
#         )

#         # Historique
#         history_collection.insert_one({
#             "user_id": user_id,
#             "action": "reverse_card_awarded",
#             "emotion_type": emotion_type,
#             "emotion_value": current_value,
#             "threshold": seuil,
#             "created_at": datetime.utcnow()
#         })

#         return {
#             "success": True,
#             "message": "Carte Inversion attribuée grâce à l’engagement émotionnel.",
#             "emotion": emotion_type,
#             "value": current_value
#         }        
#     @staticmethod
#     def increment_emotion(user_id, emotion_type):
#         if isinstance(user_id, str):
#             user_id = ObjectId(user_id)

#         mongo.db.users.update_one(
#             {"_id": user_id},
#             {
#                 "$inc": {f"emotion_counters.{emotion_type}": 1}
#             }
#         )
#     from app.extensions import mongo
#     from bson import ObjectId
#     from datetime import datetime
#     @staticmethod
#     def attribuer_carte_fin_maitrise(user_id, competence):
#         """
#         Attribue une carte +2 ou +4 lorsqu'une compétence est maîtrisée.
        
#         :param user_id: utilisateur
#         :param competence: dict compétence avec is_mastered
#         """

#         if isinstance(user_id, str):
#             user_id = ObjectId(user_id)

#         users_collection = mongo.db.users
#         competence_collection = mongo.db.competences

#         # Vérification compétence
#         comp = competence_collection.find_one({"_id": competence})
#         if not comp:
#             return {
#                 "success": False,
#                 "message": "Compétence introuvable."
#             }

#         if not comp.get("is_mastered", False):
#             return {
#                 "success": False,
#                 "message": "Compétence non maîtrisée."
#             }

#         # 🎯 logique de récompense
#         mastery_level = comp.get("mastery_level", 0)

#         # seuil simple (modifiable)
#         if mastery_level >= 0.85:
#             reward = "+4"
#             field = "plus4_cards"
#         else:
#             reward = "+2"
#             field = "plus2_cards"

#         # 🔥 attribution carte
#         users_collection.update_one(
#             {"_id": user_id},
#             {
#                 "$inc": {field: 1},
#                 "$set": {"updated_at": datetime.utcnow()}
#             }
#         )

#         return {
#             "success": True,
#             "message": f"Carte {reward} attribuée suite à la maîtrise de la compétence.",
#             "reward": reward
#         }


#     from app.extensions import mongo
#     from bson import ObjectId
#     from datetime import datetime
#     @staticmethod
#     def utiliser_carte_joker(user_id, new_difficulty):
#         """
#         Permet à un utilisateur de changer la difficulté du système
#         en utilisant une carte Joker.
        
#         :param user_id: utilisateur
#         :param new_difficulty: nouvelle difficulté (0 à 1)
#         """

#         # 🔒 sécurité borne difficulté
#         new_difficulty = max(0, min(1, new_difficulty))

#         if isinstance(user_id, str):
#             user_id = ObjectId(user_id)

#         users_collection = mongo.db.users

#         user = users_collection.find_one({"_id": user_id})

#         if not user:
#             return {
#                 "success": False,
#                 "message": "Utilisateur introuvable."
#             }

#         # 🎴 vérifier carte joker
#         if user.get("joker_cards", 0) <= 0:
#             return {
#                 "success": False,
#                 "message": "Aucune carte Joker disponible."
#             }

#         old_difficulty = user.get("difficulty", 0.5)

#         # 🔁 mise à jour
#         users_collection.update_one(
#             {"_id": user_id},
#             {
#                 "$inc": {"joker_cards": -1},
#                 "$set": {
#                     "difficulty": new_difficulty,
#                     "updated_at": datetime.utcnow()
#                 }
#             }
#         )

#         # 🗂️ historique
#         mongo.db.actions_joker.insert_one({
#             "user_id": user_id,
#             "old_difficulty": old_difficulty,
#             "new_difficulty": new_difficulty,
#             "action": "joker_used",
#             "created_at": datetime.utcnow()
#         })

#         return {
#             "success": True,
#             "message": f"Difficulté changée de {old_difficulty} → {new_difficulty}",
#             "old_difficulty": old_difficulty,
#             "new_difficulty": new_difficulty
#         }

#     from app.extensions import mongo
#     from bson import ObjectId
#     from datetime import datetime
#     @staticmethod
#     def attribuer_joker_par_emotion(user_id, seuil_sad=5):
#         """
#         Attribue une carte Joker si l'utilisateur a >= 5 émotions 'sad'
#         dans l'historique user_response.emotion_data.
#         """

#         if isinstance(user_id, str):
#             user_id = ObjectId(user_id)

#         user_response_collection = mongo.db.user_response
#         users_collection = mongo.db.users

#         # 🔍 récupérer toutes les réponses utilisateur
#         responses = list(user_response_collection.find({"user_id": user_id}))

#         # 📊 compter les émotions sad
#         sad_count = 0

#         for r in responses:
#             emotions = r.get("emotion_data", [])
#             sad_count += emotions.count("sad")

#         # ❌ condition non atteinte
#         if sad_count < seuil_sad:
#             return {
#                 "success": False,
#                 "message": f"Seuil non atteint ({sad_count}/{seuil_sad})"
#             }

#         # 🎴 attribution Joker
#         users_collection.update_one(
#             {"_id": user_id},
#             {
#                 "$inc": {"joker_cards": 1},
#                 "$set": {"updated_at": datetime.utcnow()}
#             }
#         )

#         # 🗂️ reset optionnel (éviter double récompense)
#         user_response_collection.update_many(
#             {"user_id": user_id},
#             {
#                 "$set": {"emotion_data": []}
#             }
#         )

#         # 🧾 historique
#         mongo.db.actions_joker.insert_one({
#             "user_id": user_id,
#             "action": "joker_awarded",
#             "reason": "5_sad_emotions",
#             "sad_count": sad_count,
#             "created_at": datetime.utcnow()
#         })

#         return {
#             "success": True,
#             "message": f"Carte Joker attribuée ({sad_count} émotions sad détectées)",
#             "sad_count": sad_count
#         }

#     @staticmethod
#     def verifier_condition_uno(cartes_main, nb_exercices_restants):
#         """
#         Détermine si on doit afficher UNO.

#         Condition :
#         - 1 seul exercice restant
#         - 1 seule carte dans la main pédagogique
#         """

#         total_cartes_main = sum(cartes_main)

#         if nb_exercices_restants == 1 and total_cartes_main == 1:
#             return True

#         return False
#     from app.extensions import mongo
#     from bson import ObjectId

#     def get_uno_state(user_id, difficulty, nb_exercices_restants):
#         """
#         Retourne l'état UNO pour affichage frontend.
#         """

#         if isinstance(user_id, str):
#             user_id = ObjectId(user_id)

#         # 🎴 génération main pédagogique
#         cartes_main = attribuer_les_cartes_deterministe(user_id, difficulty)

#         # 🧠 check UNO
#         is_uno = verifier_condition_uno(cartes_main, nb_exercices_restants)

#         return {
#             "cartes_main": cartes_main,
#             "total_cartes": sum(cartes_main),
#             "nb_exercices_restants": nb_exercices_restants,
#             "uno": is_uno
#         }                        
#     @staticmethod
#     def executer_toutes_les_fonctions():
#         user_id = "69d78b6e9c8ffb339eb0ced2"
#         difficulty = 0.5

#         cartes = attribuer_les_cartes(user_id, difficulty)

#         print("Couleur dominante :", GamificationServiceV2.get_couleur_dominante(difficulty))
#         print("Cartes générées :")
#         for carte in cartes:
#             print(carte)

#         # Vider la main de l'utilisateur
#         # resultat = vider_la_main(user_id)  
#         # print(resultat)
#         # resultat = mettre_a_jour_cartes_existantes(user_id, difficulty)
#         # print(resultat)
#         # if difficulty > 0.8 or difficulty >= 1:
#         # # 1. Attribution d'une carte +2
#         #     attribuer_carte_plus2(user_source)

#         # # 2. Proposition de cibles
#         #     propositions = proposer_utilisateurs_cibles(user_source)
#         #     print("Utilisateurs proposés :", propositions)

#         # # 3. Utilisation de la carte +2
#         # resultat = utiliser_carte_plus2(user_source, user_cible)
#         # print(resultat)

#         # resultat = utiliser_carte_skip(user_id)
#         # print(resultat)
#         # if difficulty > 0.4 and difficulty < 0.8:
#         #     attribuer_carte_skip(user_id)

#         # user_A = "ID_USER_A"
#         # user_B = "ID_USER_B"

#         # # B active le bouclier
#         # print(activer_carte_inversion(user_B))

#         # # A tente d'utiliser une carte +2 contre B
#         # print(utiliser_carte_plus2(user_A, user_B))

#         # result = utiliser_carte_joker(user_id, 0.8)
#         # print(result)


#     if __name__ == "__main__":
#         executer_toutes_les_fonctions()






class GamificationService:
    """
    Service gérant le système de gamification :
    - Calcul des points (XP)
    - Gestion des niveaux
    - Attribution des badges
    - Suivi des séries (streaks)
    """

    COLLECTION_USERS = "users"
    COLLECTION_BADGES = "badges"

    @staticmethod
    def award_points(user_id, is_correct, difficulty, time_spent, hints_used, emotion_data=None):
        """
        Calcule et attribue les points XP à l'utilisateur après un exercice.
        """
        # 1. Calcul de l'XP de base
        xp_gain = 10 if is_correct else 2
        
        # 2. Bonus de difficulté (1.0 à 2.0x)
        difficulty_multiplier = 1.0 + (float(difficulty) * 0.5)
        xp_gain = int(xp_gain * difficulty_multiplier)
        
        # 3. Bonus de performance
        if is_correct:
            # Bonus sans indices
            if hints_used == 0:
                xp_gain += 5
            
            # Bonus de rapidité (si < 30s)
            if time_spent < 30:
                xp_gain += 10
        
        # 4. Bonus d'engagement (émotionnel)
        if emotion_data:
            engagement = emotion_data.get("engagement_score", 0.5)
            if engagement > 0.8:
                xp_gain += 5

        # 5. Mise à jour en base de données
        user_id_obj = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        # Récupérer l'utilisateur actuel pour calculer le passage de niveau
        user = mongo.db[GamificationService.COLLECTION_USERS].find_one({"_id": user_id_obj})
        if not user:
            return {"xp_earned": 0, "new_level": 1, "level_up": False}

        old_xp = user.get("xp", 0)
        new_xp = old_xp + xp_gain
        
        old_level = GamificationService._calculate_level(old_xp)
        new_level = GamificationService._calculate_level(new_xp)
        level_up = new_level > old_level

        # Mettre à jour l'utilisateur
        mongo.db[GamificationService.COLLECTION_USERS].update_one(
            {"_id": user_id_obj},
            {
                "$set": {
                    "xp": new_xp,
                    "level": new_level,
                    "last_activity": datetime.utcnow()
                }
            },
            upsert=True
        )

        return {
            "xp_earned": xp_gain,
            "total_xp": new_xp,
            "level": new_level,
            "level_up": level_up
        }

    @staticmethod
    def _calculate_level(xp):
        """
        Calcule le niveau en fonction de l'XP.
        Formule : Level = floor(sqrt(XP / 50)) + 1
        """
        if xp <= 0: return 1
        return int(math.sqrt(xp / 50)) + 1

    @staticmethod
    def check_and_award_badges(user_id, stats, mastery_level):
        """
        Vérifie si l'utilisateur a débloqué de nouveaux badges.
        """
        new_badges = []
        user_id_obj = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        # Récupérer les badges déjà possédés
        user = mongo.db[GamificationService.COLLECTION_USERS].find_one({"_id": user_id_obj})
        current_badges = user.get("badges", []) if user else []
        
        badge_definitions = [
            {"id": "first_step", "name": "Premier Pas", "criteria": lambda s, m: s['total'] >= 1},
            {"id": "starter", "name": "Débutant Sérieux", "criteria": lambda s, m: s['total'] >= 10},
            {"id": "perfectionist", "name": "Perfectionniste", "criteria": lambda s, m: s['streak'] >= 5},
            {"id": "streak_master", "name": "Maître de la Série", "criteria": lambda s, m: s['streak'] >= 10},
            {"id": "quick_thinker", "name": "Cerveau Agile", "criteria": lambda s, m: s['avg_time'] < 20 and s['total'] >= 5},
            {"id": "competence_master", "name": "Maître de Compétence", "criteria": lambda s, m: m >= 0.9},
        ]

        for badge in badge_definitions:
            if badge["id"] not in [b["id"] for b in current_badges]:
                if badge["criteria"](stats, mastery_level):
                    badge_data = {
                        "id": badge["id"],
                        "name": badge["name"],
                        "earned_at": datetime.utcnow()
                    }
                    new_badges.append(badge_data)

        if new_badges:
            mongo.db[GamificationService.COLLECTION_USERS].update_one(
                {"_id": user_id_obj},
                {"$push": {"badges": {"$each": new_badges}}}
            )

        return new_badges

    