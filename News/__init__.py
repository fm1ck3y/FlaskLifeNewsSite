from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
import sys

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'mysecretkey'

    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{username}:{password}@{server}/{db}'.format(
        username=os.getenv('MYSQL_DATABASE_USERNAME'),
        password=os.getenv('MYSQL_DATABASE_PASSWORD'),
        server=os.getenv('MYSQL_DATABASE_HOST'),
        db=os.getenv('MYSQL_DATABASE_DB')
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

    db = SQLAlchemy(app)

    if not os.path.exists(os.getenv('IMAGE_UPLOADS_POSTS')):
        os.makedirs(os.getenv('IMAGE_UPLOADS_POSTS'))

    if not os.path.exists(os.getenv('IMAGE_UPLOADS_USERS')):
        os.makedirs(os.getenv('IMAGE_UPLOADS_USERS'))

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app

app = create_app()

from flask_migrate import Migrate
from .models import User
migrate = Migrate(app, db)

db.create_all(app=app)
