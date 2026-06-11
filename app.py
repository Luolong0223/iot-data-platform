import os
import logging
from flask import Flask
from flask_login import LoginManager

from config import config
from models.database import db, User
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.devices import devices_bp
from routes.data import data_bp
from routes.tcp import tcp_bp
from routes.pages import pages_bp

logging.basicConfig(level=logging.INFO)

login_manager = LoginManager()


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config.get(config_name, config['default']))

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(devices_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(tcp_bp)
    app.register_blueprint(pages_bp)

    with app.app_context():
        db.create_all()
        create_default_admin()

    return app


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_default_admin():
    admin_username = os.environ.get('ADMIN_USERNAME') or 'admin'
    admin_password = os.environ.get('ADMIN_PASSWORD') or 'admin123'

    admin = User.query.filter_by(username=admin_username).first()
    if not admin:
        admin = User(
            username=admin_username,
            is_admin=True,
            tcp_port=9000,
            storage_enabled=True
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        logging.info(f"Default admin user '{admin_username}' created")
