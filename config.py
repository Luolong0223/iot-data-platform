import os
from datetime import timedelta


class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'iot-data-platform-secret-key-2024-optimized'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'max_overflow': 20,
        'echo': False
    }
    
    # 会话配置
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # TCP Server 配置
    TCP_HOST = os.environ.get('TCP_HOST') or '0.0.0.0'
    TCP_BASE_PORT = int(os.environ.get('TCP_BASE_PORT') or 9105)
    TCP_BUFFER_SIZE = 4096
    TCP_TIMEOUT = 30
    TCP_MAX_CONNECTIONS = 100
    
    # 管理员默认凭证
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin123'
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32MB
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'csv', 'json', 'txt'}
    
    # 地图配置
    MAP_DEFAULT_LAT = 26.5933  # 贵阳默认纬度
    MAP_DEFAULT_LNG = 106.7135  # 贵阳默认经度
    MAP_DEFAULT_ZOOM = 12
    BAIDU_MAP_AK = os.environ.get('BAIDU_MAP_AK') or ''
    
    # API 限流配置
    RATELIMIT_STORAGE_URL = 'memory://'
    RATELIMIT_DEFAULT = '200/hour;50/minute'
    RATELIMIT_LOGIN = '10/hour;5/minute'
    RATELIMIT_API = '1000/hour;200/minute'
    
    # 数据导出配置
    EXPORT_MAX_ROWS = 100000  # 最大导出行数
    EXPORT_CHUNK_SIZE = 1000  # 分批查询大小
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # 安全配置
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = False
    PASSWORD_REQUIRE_LOWERCASE = False
    PASSWORD_REQUIRE_DIGIT = False
    PASSWORD_REQUIRE_SPECIAL = False
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_DURATION = 300  # 5分钟
    
    # 邮件配置（可选）
    MAIL_SERVER = os.environ.get('MAIL_SERVER', '')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 465))
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'true').lower() == 'true'
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', '')
    
    # 钉钉机器人配置
    DINGTALK_WEBHOOK = os.environ.get('DINGTALK_WEBHOOK', '')
    DINGTALK_SECRET = os.environ.get('DINGTALK_SECRET', '')
    
    # 企业微信机器人配置
    WECOM_WEBHOOK = os.environ.get('WECOM_WEBHOOK', '')
    
    # 告警通知配置
    ALARM_NOTIFICATION_CHANNELS = ['email', 'dingtalk']  # 可选: email, dingtalk, wecom
    ALARM_EMAIL_RECIPIENTS = os.environ.get('ALARM_EMAIL_RECIPIENTS', '').split(',')


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    
    # 生产环境使用更严格的限流
    RATELIMIT_DEFAULT = '100/hour;30/minute'
    RATELIMIT_LOGIN = '5/hour;3/minute'


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
