# pkg/__init__.py
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# Initialize db at module level BEFORE importing models
db = SQLAlchemy()
csrf = CSRFProtect()
migrate = Migrate()  


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile('config.py')  # the config in instance
    app.config.from_object('pkg.config.GeneralConfig')    
    db.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)     
    return app

app = create_app()

# Import models AFTER db is initialized
from .models import User, Group, GroupMember, GroupAdmin, Saving, Contribution, Cycle, Member, Activity, Transaction, Notification

# Ensure the new group membership tables exist if the database is empty
with app.app_context():
    db.create_all()

# Import routes AFTER models
from . import user_routes, admin_routes, forms

app.register_blueprint(admin_routes.admin_bp)

# Start background scheduler
from .scheduler import start_scheduler
import os
# Avoid running scheduler twice in debug mode reloader
if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    start_scheduler(app)