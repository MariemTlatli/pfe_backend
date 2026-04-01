"""
Service de prédiction d'émotions.
"""

import io
import numpy as np
from PIL import Image
from app.config import Config
from app.models.emotion_model import emotion_model
import cv2

# Charger le classifieur Haar Cascade (une seule fois au démarrage)
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

def detect_and_crop_face(image: Image.Image) -> np.ndarray:
    """
    Détecte et recadre le visage principal d'une image.
    
    Returns:
        np.ndarray: Visage 48×48 en niveaux de gris, ou None si aucun visage
    """
    # Convertir PIL → OpenCV
    img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    # Détection
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    if len(faces) == 0:
        return None
    
    # Prendre le plus grand visage
    x, y, w, h = max(faces, key=lambda f: f[2]*f[3])
    
    # Recadrer et redimensionner
    face = gray[y:y+h, x:x+w]
    face = cv2.resize(face, Config.IMAGE_SIZE)
    
    return face

def preprocess_image(file_bytes: bytes) -> np.ndarray:
    """
    Transforme les bytes de l'image en tableau numpy pour le modèle.
    Inclut la détection de visage.
    """
    image = Image.open(io.BytesIO(file_bytes))
    image = image.convert('RGB')
    
    # Détecter et extraire le visage
    face = detect_and_crop_face(image)
    
    if face is None:
        raise ValueError("Aucun visage détecté dans l'image")
    
    # Préparer pour le modèle
    feature = face.reshape(1, *Config.IMAGE_SIZE, 1)
    return feature / 255.0

# def preprocess_image(file_bytes: bytes) -> np.ndarray:
#     """
#     Transforme les bytes de l'image en tableau numpy pour le modèle.
    
#     Args:
#         file_bytes: Les bytes de l'image reçue
        
#     Returns:
#         np.ndarray: Image prétraitée
#     """
#     image = Image.open(io.BytesIO(file_bytes))
#     image = image.convert('L')  # Grayscale
#     image = image.resize(Config.IMAGE_SIZE)
#     feature = np.array(image)
#     feature = feature.reshape(1, *Config.IMAGE_SIZE, 1)
#     return feature / 255.0  # Normalisation


def get_emotion_prediction(file_bytes: bytes) -> dict:
    """
    Logique complète de prédiction d'émotion.
    
    Args:
        file_bytes: Les bytes de l'image
        
    Returns:
        dict: Résultat de la prédiction
    """
    # 1. Prétraitement
    processed_image = preprocess_image(file_bytes)
    
    # 2. Prédiction via le modèle
    pred = emotion_model.predict(processed_image)
    
    # 3. Post-traitement des résultats
    pred_label = Config.LABELS[int(np.argmax(pred[0]))]
    confidence = float(np.max(pred[0]))
    
    probabilities = {
        Config.LABELS[i]: round(float(pred[0][i]), 4)
        for i in range(len(Config.LABELS))
    }
    
    return {
        "emotion": pred_label,
        "confidence": round(confidence, 4),
        "all_probabilities": probabilities
    }