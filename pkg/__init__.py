from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from pkg.config import LiveConfig

# Create db instance HERE (outside the function)
db = SQLAlchemy()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    
    # Load config
    app.config.from_pyfile("config.py")
    app.config.from_object(LiveConfig)
    
    # Initialize extensions with app
    db.init_app(app)
    migrate = Migrate(app, db)
    csrf.init_app(app)
    
    return app

# Create app instance
app = create_app()

# Import routes AFTER app is created (to avoid circular imports)
from pkg import routes  # If you have other routes

# Register blueprints if you're using them
# app.register_blueprint(user_routes.bp)
# app.register_blueprint(admin_routes.bp)