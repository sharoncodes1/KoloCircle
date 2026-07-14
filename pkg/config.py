# config.py

import os

try:
    from config_local import *
except ImportError:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-default-key-change-me')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    PAYSTACK_PUBLIC_KEY = os.environ.get('PAYSTACK_PUBLIC_KEY')
    PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY')
    COWRYWISE_CLIENT_ID = os.environ.get('COWRYWISE_CLIENT_ID')
    COWRYWISE_CLIENT_SECRET = os.environ.get('COWRYWISE_CLIENT_SECRET')

class GeneralConfig(object):
    """Base configuration - safe defaults"""
    SECRET_KEY = SECRET_KEY
    SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = SQLALCHEMY_TRACK_MODIFICATIONS
    DEBUG = DEBUG
    
    PAYSTACK_PUBLIC_KEY = PAYSTACK_PUBLIC_KEY
    PAYSTACK_SECRET_KEY = PAYSTACK_SECRET_KEY
    
    COWRYWISE_CLIENT_ID = COWRYWISE_CLIENT_ID
    COWRYWISE_CLIENT_SECRET = COWRYWISE_CLIENT_SECRET
    COWRYWISE_BASE_URL = os.environ.get('COWRYWISE_BASE_URL', 'https://sandbox.embed.cowrywise.com')
    
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    REMEMBER_COOKIE_SECURE = os.environ.get('REMEMBER_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'pkg/static/uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@kolocircle.com')

class DevelopmentConfig(GeneralConfig):
    """Development configuration - override defaults"""
    DEBUG = True
    SQLALCHEMY_ECHO = False  
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False

class TestingConfig(GeneralConfig):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL', 'sqlite:///test.db')
    WTF_CSRF_ENABLED = False  
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False

class ProductionConfig(GeneralConfig):
    """Production configuration - uses ONLY environment variables"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    
    @classmethod
    def init_app(cls, app):
        required_vars = ['SECRET_KEY', 'DATABASE_URL', 'PAYSTACK_SECRET_KEY']
        for var in required_vars:
            if not os.environ.get(var):
                raise ValueError(f"Environment variable {var} is required in production!")

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on FLASK_ENV"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, DevelopmentConfig)