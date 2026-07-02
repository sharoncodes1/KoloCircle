# import os

# class Config:
#     SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
#     SQLALCHEMY_TRACK_MODIFICATIONS = False
#     WTF_CSRF_SECRET_KEY = os.environ.get('CSRF_SECRET_KEY') or 'csrf-secret'

# class DevelopmentConfig(Config):
#     DEBUG = True
#     # Read from instance/config.py
#     DATABASE_PASS = os.environ.get('DATABASE_PASS') or '1234'
#     DATABASE_NAME = os.environ.get('DATABASE_NAME') or 'kolo_circle'
#     SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://root:{DATABASE_PASS}@localhost/{DATABASE_NAME}'
#     SESSION_COOKIE_SECURE = False

# class ProductionConfig(Config):
#     DEBUG = False
#     SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
#     SESSION_COOKIE_SECURE = True

# LiveConfig = DevelopmentConfig

class GeneralConfig(object):
    SECRET_KEY="sample-secret-key"
    SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://root@localhost/kolo_circle'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class LiveConfig(GeneralConfig):
    SECRET_KEY="difficult-to-guess"