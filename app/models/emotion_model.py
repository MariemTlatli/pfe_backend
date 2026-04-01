"""
Gestion du modèle de détection d'émotions.
"""

import os
import threading
from tensorflow.keras.models import load_model
from app.config import Config


class EmotionModel:
    """Gestionnaire du modèle Keras."""
    
    def __init__(self):
        self.model = None
        self.lock = threading.Lock()
        self.is_loaded = False
    
    def load(self):
        """Charge le modèle au démarrage."""
        if os.path.exists(Config.MODEL_PATH):
            try:
                print(f"✅ Chargement du modèle depuis {Config.MODEL_PATH}...")
                self.model = load_model(Config.MODEL_PATH)
                self.is_loaded = True
                print("✅ Modèle chargé avec succès !")
            except Exception as e:
                print(f"❌ Erreur chargement modèle : {e}")
                self.is_loaded = False
        else:
            print(f"❌ Fichier {Config.MODEL_PATH} introuvable !")
            self.is_loaded = False
    
    def predict(self, processed_image):
        """Effectue une prédiction thread-safe."""
        if not self.is_loaded or self.model is None:
            raise RuntimeError("Le modèle n'est pas chargé.")
        
        with self.lock:
            pred = self.model.predict(processed_image, verbose=0)
        return pred


# Instance globale du modèle
emotion_model = EmotionModel()