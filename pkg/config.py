import os

class GeneralConfig(object):
    SECRET_KEY="sample-secret-key"
    SQLALCHEMY_DATABASE_URI='mysql+pymysql://root@localhost:3306/kolo_circle'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class LiveConfig(GeneralConfig):
    SECRET_KEY="difficult-to-guess"