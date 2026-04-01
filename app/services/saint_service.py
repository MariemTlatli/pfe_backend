"""
Service SAINT+ Enrichi — Remplace le BKT Service.

Ce service :
1. Charge le modèle SAINT+ entraîné
2. Construit la séquence d'un élève depuis MongoDB
3. Prédit P(correct) pour le prochain exercice
4. Dérive toutes les métriques enrichies :
   - Maîtrise par compétence
   - Zone ZPD
   - Tentatives estimées
   - Probabilité de besoin d'indice
   - Score d'engagement
   - Détection d'anomalies / triche
   - Poids d'attention (explicabilité)
   - Difficulté recommandée
"""

import os
import math
import numpy as np
import torch
import torch.nn as nn
from datetime import datetime
from collections import defaultdict
from bson import ObjectId
from app.models.user_response import UserResponse
from app.models.user_progress import UserProgress
from app.models.competence import Competence
from app.config import Config


# ═══════════════════════════════════════════════════════════
# 1. MODÈLE SAINT+ (même architecture que train_saint.py)
# ═══════════════════════════════════════════════════════════

class SAINTPlus(nn.Module):
    """Architecture SAINT+ pour inférence."""

    def __init__(self, n_exercises, n_skills, d_model=64,
                 n_heads=8, n_blocks=4, dropout=0.1, max_seq_len=200):
        super().__init__()
        self.d_model = d_model

        # Encoder embeddings
        self.exercise_emb = nn.Embedding(n_exercises + 1, d_model, padding_idx=0)
        self.skill_emb = nn.Embedding(n_skills + 1, d_model, padding_idx=0)

        # Decoder embeddings
        self.response_emb = nn.Embedding(3, d_model)

        # Temporal features (SAINT+)
        self.elapsed_linear = nn.Linear(1, d_model)
        self.lag_linear = nn.Linear(1, d_model)

        # Position
        self.pos_emb = nn.Embedding(max_seq_len, d_model)

        # Encoder
        enc_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads,
            dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True,
            norm_first=True
        )
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers=n_blocks)

        # Decoder (on garde les cross-attention accessibles)
        dec_layer = nn.TransformerDecoderLayer(
            d_model=d_model, nhead=n_heads,
            dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True,
            norm_first=True
        )
        self.decoder = nn.TransformerDecoder(dec_layer, num_layers=n_blocks)

        # Output
        self.fc_out = nn.Linear(d_model, 1)
        self.dropout_layer = nn.Dropout(dropout)

    def forward(self, exercises, skills, responses,
                elapsed_time=None, lag_time=None, mask=None):
        batch_size, seq_len = exercises.size()
        device = exercises.device

        pos = torch.arange(seq_len, device=device).unsqueeze(0).expand(batch_size, -1)

        # Encoder
        enc_in = (self.exercise_emb(exercises) +
                  self.skill_emb(skills) +
                  self.pos_emb(pos))
        enc_in = self.dropout_layer(enc_in)

        # Decoder (shifted responses)
        shifted = torch.full_like(responses, 2)
        shifted[:, 1:] = responses[:, :-1]

        dec_in = self.response_emb(shifted) + self.pos_emb(pos)
        if elapsed_time is not None:
            dec_in = dec_in + self.elapsed_linear(elapsed_time.unsqueeze(-1))
        if lag_time is not None:
            dec_in = dec_in + self.lag_linear(lag_time.unsqueeze(-1))
        dec_in = self.dropout_layer(dec_in)

        # Masks
        padding_mask = (mask == 0) if mask is not None else None
        causal_mask = torch.triu(
            torch.ones(seq_len, seq_len, device=device), diagonal=1
        ).bool()

        # Forward
        enc_out = self.encoder(enc_in, src_key_padding_mask=padding_mask)
        dec_out = self.decoder(
            dec_in, enc_out,
            tgt_mask=causal_mask,
            tgt_key_padding_mask=padding_mask,
            memory_key_padding_mask=padding_mask
        )

        output = torch.sigmoid(self.fc_out(dec_out).squeeze(-1))
        return output

    def forward_with_attention(self, exercises, skills, responses,
                                elapsed_time=None, lag_time=None, mask=None):
        """
        Forward pass qui retourne AUSSI les poids d'attention.
        Utilisé pour l'explicabilité.
        """
        batch_size, seq_len = exercises.size()
        device = exercises.device
        pos = torch.arange(seq_len, device=device).unsqueeze(0).expand(batch_size, -1)

        # Encoder
        enc_in = (self.exercise_emb(exercises) +
                  self.skill_emb(skills) +
                  self.pos_emb(pos))

        # Decoder
        shifted = torch.full_like(responses, 2)
        shifted[:, 1:] = responses[:, :-1]
        dec_in = self.response_emb(shifted) + self.pos_emb(pos)
        if elapsed_time is not None:
            dec_in = dec_in + self.elapsed_linear(elapsed_time.unsqueeze(-1))
        if lag_time is not None:
            dec_in = dec_in + self.lag_linear(lag_time.unsqueeze(-1))

        padding_mask = (mask == 0) if mask is not None else None
        causal_mask = torch.triu(
            torch.ones(seq_len, seq_len, device=device), diagonal=1
        ).bool()

        enc_out = self.encoder(enc_in, src_key_padding_mask=padding_mask)

        # Extraire l'attention du dernier bloc decoder manuellement
        attention_weights = []
        x = dec_in
        for layer in self.decoder.layers:
            # Self-attention
            x2 = layer.norm1(x)
            x = x + layer.self_attn(x2, x2, x2, attn_mask=causal_mask,
                                     key_padding_mask=padding_mask)[0]

            # Cross-attention (avec l'encoder) → ON CAPTURE ÇA
            x2 = layer.norm2(x)
            attn_out, attn_w = layer.multihead_attn(
                x2, enc_out, enc_out,
                key_padding_mask=padding_mask,
                need_weights=True
            )
            attention_weights.append(attn_w.detach())
            x = x + attn_out

            # FFN
            x2 = layer.norm3(x)
            x = x + layer.linear2(layer.dropout(layer.activation(layer.linear1(x2))))

        output = torch.sigmoid(self.fc_out(x).squeeze(-1))

        return output, attention_weights


# ═══════════════════════════════════════════════════════════
# 2. SERVICE PRINCIPAL
# ═══════════════════════════════════════════════════════════

class SAINTService:
    """
    Service SAINT+ Enrichi.
    Remplace BKTService avec des prédictions Deep Learning.
    """

    _model = None
    _config = None
    _data_info = None
    _device = None

    # ──────────────────────────────────────────────
    # Chargement du modèle
    # ──────────────────────────────────────────────

    @classmethod
    def load_model(cls, model_path=None):
        """
        Charge le modèle SAINT+ entraîné.
        Appelé une seule fois au démarrage de l'app.
        """
        if cls._model is not None:
            return  # Déjà chargé

        if model_path is None:
            model_path = os.path.join("models", "saint_full", "best_model.pt")

        if not os.path.exists(model_path):
            print(f"⚠️ Modèle SAINT+ non trouvé : {model_path}")
            print("   Utilisation du mode fallback (prédiction par défaut)")
            return

        cls._device = torch.device("cpu")

        checkpoint = torch.load(model_path, map_location=cls._device,
                                weights_only=False)
        cls._config = checkpoint["config"]
        cls._data_info = checkpoint["data_info"]

        cls._model = SAINTPlus(
            n_exercises=cls._data_info["n_exercises"],
            n_skills=cls._data_info["n_skills"],
            d_model=cls._config["d_model"],
            n_heads=cls._config["n_heads"],
            n_blocks=cls._config["n_blocks"],
            dropout=0.0,  # Pas de dropout en inférence
            max_seq_len=cls._config["max_seq_len"]
        ).to(cls._device)

        cls._model.load_state_dict(checkpoint["model_state_dict"])
        cls._model.eval()

        print(f"✅ Modèle SAINT+ chargé depuis {model_path}")
        print(f"   AUC entraînement : {checkpoint.get('best_auc', 'N/A')}")

    @classmethod
    def is_loaded(cls):
        """Vérifie si le modèle est chargé."""
        return cls._model is not None

    # ──────────────────────────────────────────────
    # Construction de la séquence depuis MongoDB
    # ──────────────────────────────────────────────

    @classmethod
    def _build_sequence(cls, db, user_id, limit=200):
        """
        Construit la séquence d'interactions d'un élève
        depuis MongoDB pour la passer au modèle.

        Returns:
            dict avec les tenseurs prêts pour le modèle
            + les données brutes pour le post-traitement
        """
        collection = db[UserResponse.collection_name]
        uid = user_id if not isinstance(user_id, str) else user_id
        # uid = ObjectId(uid)

        # Récupérer les réponses triées par date
        responses = list(
            collection.find({"user_id": uid})
            .sort("created_at", 1)
            .limit(limit)
        )
        print("responses count:", len(responses))
        print("responses:", responses)
        # print("responses", responses.count)
        if not responses:
            return None

        max_seq = cls._config["max_seq_len"] if cls._config else 200
        n = min(len(responses), max_seq)
        responses = responses[-n:]  # Garder les plus récentes

        # Construire les arrays
        questions = np.zeros(max_seq, dtype=np.int64)
        concepts = np.zeros(max_seq, dtype=np.int64)
        resp_arr = np.zeros(max_seq, dtype=np.int64)
        elapsed = np.zeros(max_seq, dtype=np.float32)
        lag = np.zeros(max_seq, dtype=np.float32)
        mask = np.zeros(max_seq, dtype=np.float32)

        raw_data = []

        for i, r in enumerate(responses):
            # Mapper les IDs MongoDB vers des entiers
            # (hash simple pour rester dans la plage)
            ex_id = hash(str(r["exercise_id"])) % cls._data_info["n_exercises"] + 1
            sk_id = hash(str(r["competence_id"])) % cls._data_info["n_skills"] + 1

            questions[i] = ex_id
            concepts[i] = sk_id
            resp_arr[i] = 1 if r["is_correct"] else 0
            mask[i] = 1.0

            # Temps de réponse normalisé
            time_spent = r.get("time_spent", 30)
            elapsed[i] = math.log1p(max(time_spent, 0)) / 7.0

            # Lag time
            if i > 0:
                prev_time = responses[i - 1].get("created_at", r["created_at"])
                curr_time = r.get("created_at", prev_time)
                if isinstance(prev_time, datetime) and isinstance(curr_time, datetime):
                    lag_seconds = (curr_time - prev_time).total_seconds()
                else:
                    lag_seconds = 60
                lag[i] = math.log1p(max(lag_seconds, 0)) / 12.0

            raw_data.append({
                "exercise_id": str(r["exercise_id"]),
                "competence_id": str(r["competence_id"]),
                "is_correct": r["is_correct"],
                "time_spent": r.get("time_spent", 0),
                "created_at": r.get("created_at"),
            })

        return {
            "questions": torch.LongTensor(questions).unsqueeze(0),
            "concepts": torch.LongTensor(concepts).unsqueeze(0),
            "responses": torch.LongTensor(resp_arr).unsqueeze(0),
            "elapsed_time": torch.FloatTensor(elapsed).unsqueeze(0),
            "lag_time": torch.FloatTensor(lag).unsqueeze(0),
            "mask": torch.FloatTensor(mask).unsqueeze(0),
            "seq_len": n,
            "raw_data": raw_data,
        }

    # ──────────────────────────────────────────────
    # Prédiction principale
    # ──────────────────────────────────────────────

    @classmethod
    def predict(cls, db, user_id, competence_id=None):
        """
        Prédiction ENRICHIE complète.

        Args:
            db: connexion MongoDB
            user_id: ID de l'utilisateur
            competence_id: ID de la compétence (optionnel, pour filtrer)

        Returns:
            dict: résultat enrichi complet
        """
        # Fallback si modèle non chargé
        if not cls.is_loaded():
            return cls._fallback_predict(db, user_id, competence_id)

        # Construire la séquence
        seq = cls._build_sequence(db, user_id)
        if seq is None:
            return cls._empty_result(competence_id)

        # Inférence
        with torch.no_grad():
            predictions, attention_weights = cls._model.forward_with_attention(
                seq["questions"].to(cls._device),
                seq["concepts"].to(cls._device),
                seq["responses"].to(cls._device),
                seq["elapsed_time"].to(cls._device),
                seq["lag_time"].to(cls._device),
                seq["mask"].to(cls._device),
            )

        # Extraire P(correct) à la dernière position valide
        last_pos = seq["seq_len"] - 1
        p_correct = float(predictions[0, last_pos].cpu())

        # Post-traitement enrichi
        result = cls._enrich_prediction(
            p_correct=p_correct,
            raw_data=seq["raw_data"],
            attention_weights=attention_weights,
            seq_len=seq["seq_len"],
            competence_id=competence_id,
            db=db
        )

        return result

    # ──────────────────────────────────────────────
    # Post-traitement enrichi
    # ──────────────────────────────────────────────

    @classmethod
    def _enrich_prediction(cls, p_correct, raw_data, attention_weights,
                            seq_len, competence_id, db):
        """
        Calcule TOUTES les métriques dérivées.
        """
        result = {}

        # ── 1. P(correct) natif ──
        result["p_correct"] = round(p_correct, 4)

        # ── 2. Mastery (= P(correct) pour cette compétence) ──
        mastery = cls._compute_mastery(p_correct, raw_data, competence_id)
        result["mastery"] = round(mastery, 4)

        # ── 3. Zone ZPD ──
        zone_info = cls._classify_zpd(mastery, competence_id, db)
        result["zone"] = zone_info["zone"]
        result["zone_label"] = zone_info["label"]
        result["is_ready_to_learn"] = zone_info["is_ready"]

        # ── 4. Tentatives estimées ──
        estimated_attempts = cls._estimate_attempts(p_correct)
        result["estimated_attempts"] = estimated_attempts

        # ── 5. Probabilité de besoin d'indice ──
        hint_info = cls._compute_hint_probability(p_correct, raw_data)
        result["hint_probability"] = hint_info


        # ── 6. Score d'engagement ──
        engagement = cls._compute_engagement(raw_data)
        result["engagement"] = engagement

        # ── 7. Détection d'anomalies ──
        anomalies = cls._detect_anomalies(p_correct, raw_data)
        result["anomaly"] = anomalies

        # ── 8. Attention (top interactions influentes) ──
        top_interactions = cls._extract_attention_insights(
            attention_weights, raw_data, seq_len
        )
        result["influential_interactions"] = top_interactions

        # ── 9. Difficulté recommandée ──
        recommended_diff = cls._recommend_difficulty(mastery, p_correct)
        result["recommended_difficulty"] = recommended_diff

        # ── 10. Nombre d'exercices recommandés ──
        result["recommended_exercises_count"] = cls._recommend_exercise_count(mastery)

        # ── 11. Confiance du modèle ──
        result["confidence"] = cls._compute_confidence(p_correct, len(raw_data))

        return result

    # ──────────────────────────────────────────────
    # MÉTRIQUE 1 : Mastery par compétence
    # ──────────────────────────────────────────────

    @classmethod
    def _compute_mastery(cls, p_correct, raw_data, competence_id):
        """
        Calcule la maîtrise pour une compétence spécifique.

        Si competence_id donné : moyenne pondérée des P(correct)
        sur les interactions récentes de cette compétence.
        Sinon : utilise P(correct) global.
        """
        if not competence_id or not raw_data:
            return p_correct

        # Filtrer les interactions de cette compétence
        comp_interactions = [
            r for r in raw_data
            if r["competence_id"] == str(competence_id)
        ]

        if not comp_interactions:
            return p_correct

        # Taux de réussite récent (pondéré récence)
        n = len(comp_interactions)
        weights = np.array([0.5 + 0.5 * (i / max(n - 1, 1)) for i in range(n)])
        corrects = np.array([1.0 if r["is_correct"] else 0.0 for r in comp_interactions])

        weighted_rate = np.average(corrects, weights=weights)

        # Combiner avec P(correct) du modèle (70% modèle, 30% historique)
        mastery = 0.7 * p_correct + 0.3 * weighted_rate

        return mastery

    # ──────────────────────────────────────────────
    # MÉTRIQUE 2 : Zone ZPD
    # ──────────────────────────────────────────────

    @classmethod
    def _classify_zpd(cls, mastery, competence_id, db):
        """Classifie dans la zone ZPD appropriée."""
        # Récupérer les seuils personnalisés si disponibles
        thresholds = Competence.DEFAULT_ZPD_THRESHOLDS

        if competence_id and db is not None:
            comp = Competence.get_by_id(competence_id)
            if comp:
                thresholds = comp.get("zpd_thresholds", thresholds)

        zone = Competence.classify_zone(mastery, thresholds)

        labels = {
            Competence.ZONE_MASTERED: "Maîtrisé — Prêt pour la compétence suivante",
            Competence.ZONE_ZPD: "Zone Proximale — Moment idéal pour apprendre",
            Competence.ZONE_FRUSTRATION: "En difficulté — Renforcer les bases d'abord",
        }

        return {
            "zone": zone,
            "label": labels[zone],
            "is_ready": zone != Competence.ZONE_FRUSTRATION,
        }

    # ──────────────────────────────────────────────
    # MÉTRIQUE 3 : Tentatives estimées
    # ──────────────────────────────────────────────

    @classmethod
    def _estimate_attempts(cls, p_correct):
        """
        Estime le nombre de tentatives pour réussir.

        Modèle géométrique : E[tentatives] = 1 / P(correct)
        Borné entre 1 et 10.
        """
        if p_correct >= 0.95:
            return {"value": 1, "label": "Réussira du premier coup"}
        elif p_correct <= 0.05:
            return {"value": 10, "label": "Exercice beaucoup trop difficile"}

        expected = min(10, max(1, round(1.0 / p_correct)))

        labels = {
            1: "Réussira probablement du premier coup",
            2: "1 à 2 tentatives nécessaires",
            3: "2 à 3 tentatives nécessaires",
            4: "Plusieurs tentatives nécessaires",
            5: "Exercice difficile pour cet élève",
        }
        label = labels.get(expected, f"Environ {expected} tentatives nécessaires")

        return {"value": expected, "label": label}

    # ──────────────────────────────────────────────
    # MÉTRIQUE 4 : Besoin d'indice
    # ──────────────────────────────────────────────

    @classmethod
    def _compute_hint_probability(cls, p_correct, raw_data):
        """
        Estime la probabilité que l'élève ait besoin d'un indice.

        Facteurs :
        - P(correct) faible → besoin d'indice élevé
        - Série d'échecs récents → besoin accru
        - Temps de réponse élevé → hésitation
        """
        # Base : inverse de P(correct)
        base_hint = 1.0 - p_correct

        # Bonus si série d'échecs récents
        streak_bonus = 0.0
        if raw_data:
            recent = raw_data[-5:]  # 5 dernières interactions
            fails = sum(1 for r in recent if not r["is_correct"])
            if fails >= 4:
                streak_bonus = 0.20
            elif fails >= 3:
                streak_bonus = 0.10
            elif fails >= 2:
                streak_bonus = 0.05

        # Bonus si temps de réponse élevé (hésitation)
        time_bonus = 0.0
        if raw_data:
            recent_times = [r["time_spent"] for r in raw_data[-3:] if r["time_spent"] > 0]
            if recent_times:
                avg_time = sum(recent_times) / len(recent_times)
                if avg_time > 120:  # Plus de 2 minutes
                    time_bonus = 0.10
                elif avg_time > 60:
                    time_bonus = 0.05

        probability = min(1.0, base_hint + streak_bonus + time_bonus)

        # Niveau
        if probability >= 0.7:
            level = "fort"
            description = "Indice fortement recommandé"
        elif probability >= 0.4:
            level = "moyen"
            description = "Un indice pourrait aider"
        else:
            level = "faible"
            description = "L'élève devrait y arriver seul"

        return {
            "probability": round(probability, 3),
            "level": level,
            "description": description,
        }

    # ──────────────────────────────────────────────
    # MÉTRIQUE 5 : Engagement
    # ──────────────────────────────────────────────

    @classmethod
    def _compute_engagement(cls, raw_data):
        """
        Score d'engagement basé sur les patterns temporels.

        Facteurs analysés :
        - Régularité des sessions (écart-type des lag times)
        - Temps de réponse raisonnable (ni trop court ni trop long)
        - Persévérance après échecs
        - Volume d'interactions récentes
        """
        if not raw_data or len(raw_data) < 2:
            return {
                "score": 0.5,
                "level": "inconnu",
                "description": "Pas assez de données",
                "factors": {}
            }

        scores = {}

        # ── A. Régularité des sessions ──
        timestamps = [r["created_at"] for r in raw_data
                      if r.get("created_at") and isinstance(r["created_at"], datetime)]
        if len(timestamps) >= 2:
            gaps = [(timestamps[i+1] - timestamps[i]).total_seconds()
                    for i in range(len(timestamps) - 1)]
            # Exclure les très longs gaps (> 1 jour)
            short_gaps = [g for g in gaps if g < 86400]
            if short_gaps:
                cv = np.std(short_gaps) / max(np.mean(short_gaps), 1)
                # CV faible = régulier = bon engagement
                scores["regularity"] = max(0, min(1, 1.0 - cv * 0.3))
            else:
                scores["regularity"] = 0.3
        else:
            scores["regularity"] = 0.5

        # ── B. Temps de réponse raisonnable ──
        times = [r["time_spent"] for r in raw_data if r["time_spent"] > 0]
        if times:
            avg_time = np.mean(times)
            # Trop rapide (<5s) = rushing, Trop lent (>300s) = distrait
            if 10 <= avg_time <= 120:
                scores["response_quality"] = 1.0
            elif 5 <= avg_time <= 180:
                scores["response_quality"] = 0.7
            else:
                scores["response_quality"] = 0.3
        else:
            scores["response_quality"] = 0.5

        # ── C. Persévérance après échecs ──
        if len(raw_data) >= 3:
            continued_after_fail = 0
            fail_count = 0
            for i in range(len(raw_data) - 1):
                if not raw_data[i]["is_correct"]:
                    fail_count += 1
                    continued_after_fail += 1  # Il a continué (puisqu'il y a i+1)
            if fail_count > 0:
                scores["perseverance"] = min(1.0, continued_after_fail / fail_count)
            else:
                scores["perseverance"] = 1.0  # Pas d'échec = persévérant par défaut
        else:
            scores["perseverance"] = 0.5

        # ── D. Volume récent ──
        recent_count = len(raw_data[-20:])  # 20 dernières
        scores["activity"] = min(1.0, recent_count / 15.0)

        # Score global (moyenne pondérée)
        weights = {
            "regularity": 0.25,
            "response_quality": 0.25,
            "perseverance": 0.30,
            "activity": 0.20
        }
        global_score = sum(scores[k] * weights[k] for k in weights)
        global_score = round(global_score, 3)

        # Niveau
        if global_score >= 0.75:
            level = "élevé"
            description = "L'élève est très engagé et régulier"
        elif global_score >= 0.50:
            level = "moyen"
            description = "Engagement correct, peut être amélioré"
        elif global_score >= 0.25:
            level = "faible"
            description = "L'élève montre des signes de désengagement"
        else:
            level = "critique"
            description = "Risque d'abandon — intervention recommandée"

        return {
            "score": global_score,
            "level": level,
            "description": description,
            "factors": {k: round(v, 3) for k, v in scores.items()},
        }

    # ──────────────────────────────────────────────
    # MÉTRIQUE 6 : Détection d'anomalies
    # ──────────────────────────────────────────────

    @classmethod
    def _detect_anomalies(cls, p_correct, raw_data):
        """
        Détecte les comportements suspects.

        Types d'anomalies :
        - Triche : réponse correcte improbable + temps très court
        - Rushing : temps de réponse anormalement bas
        - Guessing : pattern aléatoire de réponses
        - Inactivité : longs gaps entre interactions
        """
        if not raw_data or len(raw_data) < 3:
            return {
                "has_anomaly": False,
                "flags": [],
                "severity": "none"
            }

        flags = []

        # ── A. Détection de triche ──
        recent = raw_data[-5:]
        for r in recent:
            if r["is_correct"] and r["time_spent"] > 0 and r["time_spent"] < 3:
                # Correct en moins de 3 secondes = suspect
                flags.append({
                    "type": "possible_cheating",
                    "description": "Réponse correcte en moins de 3 secondes",
                    "exercise_id": r["exercise_id"],
                    "severity": "high"
                })

        # ── B. Détection de rushing ──
        times = [r["time_spent"] for r in recent if r["time_spent"] > 0]
        if times and np.mean(times) < 5:
            flags.append({
                "type": "rushing",
                "description": f"Temps moyen très bas ({np.mean(times):.0f}s) "
                               f"sur les dernières interactions",
                "severity": "medium"
            })

        # ── C. Détection de guessing (pattern aléatoire) ──
        if len(raw_data) >= 10:
            recent_10 = raw_data[-10:]
            corrects = [r["is_correct"] for r in recent_10]
            rate = sum(corrects) / len(corrects)
            # Si le taux est proche de 50% et le temps est court
            avg_time = np.mean([r["time_spent"] for r in recent_10 if r["time_spent"] > 0]) \
                if any(r["time_spent"] > 0 for r in recent_10) else 30
            if 0.35 <= rate <= 0.65 and avg_time < 10:
                flags.append({
                    "type": "random_guessing",
                    "description": "Pattern de réponses aléatoires détecté "
                                   "(taux ~50% + temps très courts)",
                    "severity": "medium"
                })

        # ── D. Détection d'inactivité ──
        timestamps = [r["created_at"] for r in raw_data
                      if isinstance(r.get("created_at"), datetime)]
        if len(timestamps) >= 2:
            last_gap = (timestamps[-1] - timestamps[-2]).total_seconds()
            if last_gap > 7 * 86400:  # Plus de 7 jours
                flags.append({
                    "type": "long_inactivity",
                    "description": f"Inactif depuis {last_gap / 86400:.0f} jours",
                    "severity": "low"
                })

        # Sévérité globale
        if any(f["severity"] == "high" for f in flags):
            severity = "high"
        elif any(f["severity"] == "medium" for f in flags):
            severity = "medium"
        elif flags:
            severity = "low"
        else:
            severity = "none"

        return {
            "has_anomaly": len(flags) > 0,
            "flags": flags,
            "severity": severity,
            "count": len(flags),
        }

    # ──────────────────────────────────────────────
    # MÉTRIQUE 7 : Attention (explicabilité)
    # ──────────────────────────────────────────────

    @classmethod
    def _extract_attention_insights(cls, attention_weights, raw_data, seq_len):
        """
        Extrait les interactions passées les plus influentes.

        Utilise les poids de cross-attention du dernier bloc
        pour identifier quelles interactions passées ont le plus
        influencé la prédiction courante.
        """
        if not attention_weights or not raw_data:
            return []

        try:
            # Prendre le dernier bloc d'attention
            last_attn = attention_weights[-1]  # (1, seq_len, seq_len)

            # Attention de la dernière position valide
            last_pos = min(seq_len - 1, last_attn.size(1) - 1)
            attn_scores = last_attn[0, last_pos, :seq_len].cpu().numpy()

            # Top 5 interactions les plus influentes
            top_indices = np.argsort(attn_scores)[::-1][:5]

            insights = []
            for idx in top_indices:
                if idx < len(raw_data):
                    r = raw_data[idx]
                    insights.append({
                        "position": int(idx),
                        "attention_weight": round(float(attn_scores[idx]), 4),
                        "exercise_id": r["exercise_id"],
                        "competence_id": r["competence_id"],
                        "was_correct": r["is_correct"],
                        "time_spent": r["time_spent"],
                    })

            return insights

        except Exception:
            return []

    # ──────────────────────────────────────────────
    # MÉTRIQUE 8 : Difficulté recommandée
    # ──────────────────────────────────────────────

    @classmethod
    def _recommend_difficulty(cls, mastery, p_correct):
        """
        Recommande la difficulté optimale du prochain exercice.

        Principe ZPD : légèrement au-dessus du niveau actuel.
        """
        zone = Competence.classify_zone(mastery)

        stretch_map = {
            Competence.ZONE_FRUSTRATION: 0.05,   # Petit stretch
            Competence.ZONE_ZPD: 0.15,            # Stretch optimal
            Competence.ZONE_MASTERED: 0.20,       # Challenge
        }
        stretch = stretch_map[zone]

        difficulty = min(1.0, max(0.1, mastery + stretch))

        return {
            "value": round(difficulty, 3),
            "range_min": round(max(0.1, difficulty - 0.1), 3),
            "range_max": round(min(1.0, difficulty + 0.1), 3),
        }

    # ──────────────────────────────────────────────
    # MÉTRIQUE 9 : Exercices recommandés
    # ──────────────────────────────────────────────

    @classmethod
    def _recommend_exercise_count(cls, mastery):
        """Recommande le nombre d'exercices à faire."""
        if mastery >= 0.95:
            return {"count": 0, "label": "Compétence maîtrisée"}
        elif mastery >= 0.85:
            return {"count": 2, "label": "Révision légère"}
        elif mastery >= 0.70:
            return {"count": 3, "label": "Consolidation"}
        elif mastery >= 0.50:
            return {"count": 5, "label": "Pratique régulière"}
        elif mastery >= 0.30:
            return {"count": 7, "label": "Entraînement intensif"}
        else:
            return {"count": 10, "label": "Remise à niveau nécessaire"}

    # ──────────────────────────────────────────────
    # MÉTRIQUE 10 : Confiance du modèle
    # ──────────────────────────────────────────────

    @classmethod
    def _compute_confidence(cls, p_correct, n_interactions):
        """
        Estime la confiance dans la prédiction.

        Facteurs :
        - P(correct) extrême (proche de 0 ou 1) = plus confiant
        - Plus d'interactions = plus confiant
        """
        # Confiance basée sur la certitude
        certainty = abs(p_correct - 0.5) * 2  # 0 à 1

        # Confiance basée sur le volume de données
        data_confidence = min(1.0, n_interactions / 30)

        # Combinaison
        confidence = 0.4 * certainty + 0.6 * data_confidence

        if confidence >= 0.75:
            level = "haute"
        elif confidence >= 0.45:
            level = "moyenne"
        else:
            level = "faible"

        return {
            "score": round(confidence, 3),
            "level": level,
            "n_interactions": n_interactions,
        }

    # ──────────────────────────────────────────────
    # Méthode publique : update après réponse
    # (Remplace BKTService.update_knowledge)
    # ──────────────────────────────────────────────

    @classmethod
    def update_knowledge(cls, db, user_id, competence_id, is_correct):
        """
        Met à jour la connaissance après un exercice.
        Remplace directement BKTService.update_knowledge().

        Returns:
            dict: résultat enrichi complet
        """
        # Prédire avec tout l'historique (incluant la nouvelle réponse)
        result = cls.predict(db, user_id, competence_id)

        # Mettre à jour UserProgress
        mastery = result.get("mastery", 0.0)

        UserProgress.update_mastery(
            user_id=user_id,
            competence_id=competence_id,
            mastery=float(mastery),
            source="saint+"
        )

        result["is_mastered"] = bool(mastery >= 0.85)
        return result

    # ──────────────────────────────────────────────
    # Méthode publique : prédire la performance
    # (Remplace BKTService.predict_performance)
    # ──────────────────────────────────────────────

    @classmethod
    def predict_performance(cls, db, user_id, competence_id):
        """
        Prédit la performance au prochain exercice.
        Remplace directement BKTService.predict_performance().
        """
        result = cls.predict(db, user_id, competence_id)

        return {
            "probability_correct": result["p_correct"],
            "mastery": result["mastery"],
            "zone": result["zone"],
            "confidence": result["confidence"]["level"],
            "engagement": result["engagement"]["level"],
            "hint_needed": result["hint_probability"],
            "estimated_attempts": result["estimated_attempts"],
            "anomaly": result["anomaly"],
        }

    # ──────────────────────────────────────────────
    # Fallback & Empty
    # ──────────────────────────────────────────────

    @classmethod
    def _fallback_predict(cls, db, user_id, competence_id):
        """Prédiction basique si le modèle n'est pas chargé."""
        responses = UserResponse.get_by_user_and_competence(
            db, user_id, competence_id
        ) if competence_id else UserResponse.get_by_user(db, user_id)

        if not responses:
            return cls._empty_result(competence_id)

        # Taux de réussite simple
        corrects = sum(1 for r in responses if r["is_correct"])
        p_correct = corrects / len(responses)

        return cls._enrich_prediction(
            p_correct=p_correct,
            raw_data=[{
                "exercise_id": str(r.get("exercise_id", "")),
                "competence_id": str(r.get("competence_id", "")),
                "is_correct": r["is_correct"],
                "time_spent": r.get("time_spent", 0),
                "created_at": r.get("created_at"),
            } for r in responses],
            attention_weights=[],
            seq_len=len(responses),
            competence_id=competence_id,
            db=db
        )

    @classmethod
    def _empty_result(cls, competence_id=None):
        """Résultat par défaut quand pas de données."""
        return {
            "p_correct": 0.5,
            "mastery": 0.0,
            "zone": "frustration",
            "zone_label": "Pas encore de données",
            "is_ready_to_learn": True,
            "estimated_attempts": {"value": 3, "label": "Estimation par défaut"},
            "hint_probability": {"probability": 0.5, "level": "moyen",
                                  "description": "Pas assez de données"},
            "engagement": {"score": 0.5, "level": "inconnu",
                           "description": "Pas de données", "factors": {}},
            "anomaly": {"has_anomaly": False, "flags": [], "severity": "none"},
            "influential_interactions": [],
            "recommended_difficulty": {"value": 0.3, "range_min": 0.2, "range_max": 0.4},
            "recommended_exercises_count": {"count": 5, "label": "Commencer l'apprentissage"},
            "confidence": {"score": 0.0, "level": "faible", "n_interactions": 0},
        }

        