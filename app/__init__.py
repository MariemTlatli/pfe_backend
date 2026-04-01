"""
Factory Flask pour l'application d'apprentissage adaptatif.
"""

from flask import Flask
from app.config import get_config
from app.extensions import mongo, jwt, bcrypt, cors, api

# Ajouter APRÈS la création de l'app Flask
from app.models import emotion_model
from app.services.saint_service import SAINTService

def create_app(config_class=None):
    """Factory pour créer l'application Flask."""
    
    app = Flask(__name__)
    
    # Configuration
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)
    
    # Initialisation des extensions
    mongo.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app)
    api.init_app(app)
    

        # Chargement du modèle ML avant de lancer l'app
    emotion_model.load()

    
    
    # Charger le modèle SAINT+ au démarrage
    SAINTService.load_model()
    # ═══════════════════════════════════════════════════════════════════════
    #  ENREGISTREMENT DES ROUTES
    # ═══════════════════════════════════════════════════════════════════════
    # ── auth_blp Check ──
    try:
      from app.routes.user_subject_routes import blp as user_subject_blp
      api.register_blueprint(user_subject_blp)
      
    except ImportError:
        print("⚠️  Route user_subject_blp non trouvée, ignorée")
    from app.routes.emotion_detection import blp as emotion_blp
    api.register_blueprint(emotion_blp)

    from app.routes.zpd_routes import zpd_bp
    api.register_blueprint(zpd_bp)
    from app.routes.exercise_routes import exercise_bp       
    api.register_blueprint(exercise_bp)

    from app.routes.response_routes import response_bp       
    api.register_blueprint(response_bp)
    
    # ── auth_blp Check ──
    try:
       from app.routes.auth import auth_blp
       api.register_blueprint(auth_blp)
    except ImportError:
        print("⚠️  Route auth_blp non trouvée, ignorée")
    
    # ── Health Check ──
    try:
        from app.routes.health import blp
        api.register_blueprint(blp)
    except ImportError:
        print("⚠️  Route health non trouvée, ignorée")
    
    # ── Domains ──
    try:
        from app.routes.domains import blp
        api.register_blueprint(blp)
    except ImportError:
        print("⚠️  Route domains non trouvée, ignorée")
    
    # ── Subjects ──
    try:
        from app.routes.subjects import blp
        api.register_blueprint(blp)
    except ImportError:
        print("⚠️  Route subjects non trouvée, ignorée")
    
    # ── Curriculum ──
    try:
        from app.routes.curriculum import blp
        api.register_blueprint(blp)
    except ImportError:
        print("⚠️  Route curriculum non trouvée, ignorée")
    
    # ── Lessons ──
    try:
        from app.routes.lessons import blp
        api.register_blueprint(blp)
    except ImportError:
        print("⚠️  Route lessons non trouvée, ignorée")
    
    print("✅ Blueprints enregistrés")
    
    # ═══════════════════════════════════════════════════════════════════════
    #  INITIALISATION BASE DE DONNÉES
    # ═══════════════════════════════════════════════════════════════════════
    
    if app.config.get('DEBUG'):
        with app.app_context():
            _create_indexes()
            _seed_initial_data()
    
    return app


def _create_indexes():
    """Crée les index MongoDB pour optimiser les requêtes."""
    from app.extensions import mongo
    
    try:
        # Index pour users
        mongo.db.users.create_index('email', unique=True)
        mongo.db.users.create_index('username', unique=True)
        
        # Index pour domains
        mongo.db.domains.create_index('name', unique=True)
        
        # Index pour subjects
        mongo.db.subjects.create_index([('domain_id', 1), ('name', 1)])
        
        # Index pour competences
        mongo.db.competences.create_index('code', unique=True)
        mongo.db.competences.create_index('subject_id')
        
        # Index pour lessons
        mongo.db.lessons.create_index([('competence_id', 1), ('order_index', 1)])
        
        # Index pour user_progress (BKT)
        mongo.db.user_progress.create_index(
            [('user_id', 1), ('competence_id', 1)], 
            unique=True
        )
        
        print("✅ Index MongoDB créés avec succès")
    
    except Exception as e:
        print(f"⚠️  Erreur lors de la création des index : {e}")


def _seed_initial_data():
    """Initialise les données de base (domaines + matières)."""
    try:
        from app.seeds.seed_data import seed_initial_data
        seed_initial_data()
    except ImportError:
        print("⚠️  Fichier de seed introuvable, ignoré")
    except Exception as e:
        print(f"⚠️  Erreur lors du seed : {e}")