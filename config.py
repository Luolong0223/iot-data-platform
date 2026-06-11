import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'iot-data-platform-secret-key-2024'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # TCP Server Config
    TCP_HOST = os.environ.get('TCP_HOST') or '0.0.0.0'
    TCP_BASE_PORT = int(os.environ.get('TCP_BASE_PORT') or 9000)
    TCP_BUFFER_SIZE = 4096
    TCP_TIMEOUT = 30
    
    # Admin default credentials
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin123'
    
    # Upload Config
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = 'uploads'
    
    # Map Config
    MAP_DEFAULT_LAT = 26.5933  # 贵阳默认纬度
    MAP_DEFAULT_LNG = 106.7135  # 贵阳默认经度
    MAP_DEFAULT_ZOOM = 12

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
