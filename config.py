import os
import secrets
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)


class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    
    # 数据库配置 - 优先读取 DATABASE_URL，否则尝试 MySQL，最后回退到 SQLite
    _db_url = os.environ.get('DATABASE_URL', '')
    _mysql_password = os.environ.get('MYSQL_PASSWORD', 'cRwLGPScNejLEeBt')
    
    if not _db_url:
        if _mysql_password:
            # MySQL 模式
            _mysql_host = os.environ.get('MYSQL_HOST', 'localhost')
            _mysql_port = int(os.environ.get('MYSQL_PORT', 3306))
            _mysql_user = os.environ.get('MYSQL_USER', 'iot-platform')
            _mysql_database = os.environ.get('MYSQL_DATABASE', 'iot-platform')
            _db_url = f'mysql+pymysql://{_mysql_user}:{_mysql_password}@{_mysql_host}:{_mysql_port}/{_mysql_database}?charset=utf8mb4'
            logger.info("Using MySQL database")
        else:
            # 回退到 SQLite
            _instance_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
            os.makedirs(_instance_dir, exist_ok=True)
            _db_url = f'sqlite:///{os.path.join(_instance_dir, "database.db")}'
            logger.warning("MYSQL_PASSWORD not set, falling back to SQLite. Set MYSQL_PASSWORD environment variable for MySQL.")
    
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # MySQL 特有配置（仅 MySQL 时使用）
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'echo': False
    }
    if 'mysql' in _db_url:
        SQLALCHEMY_ENGINE_OPTIONS.update({
            'pool_size': 10,
            'pool_recycle': 3600,
            'max_overflow': 20,
        })
    
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
    
    # 管理员默认凭证（生产环境必须通过环境变量设置）
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', secrets.token_urlsafe(16))
    
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
    # SQLite doesn't support pool_size/max_overflow
    SQLALCHEMY_ENGINE_OPTIONS = {
        'echo': False
    }


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
