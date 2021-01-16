import boto3

from flask import Flask, render_template
from flask_bootstrap import Bootstrap

from support.config import DevelopmentConfig, ProductionConfig, TestingConfig
from support.extensions import aws

def page_not_found(e):
  return render_template('error/404.html'), 404

def internal_server(e):
  return render_template('error/500.html'), 500

#Create Flask object
def create_app(config_object=DevelopmentConfig()):
    app = Flask(__name__)
    app.config.from_object(config_object)

    s3 = boto3.client('s3',
                aws_access_key_id=aws.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=aws.AWS_SECRET_ACCESS_KEY)

    from flask_bootstrap import Bootstrap
    Bootstrap(app)

    from support.login import login_manager
    login_manager.init_app(app)

    from support.models import db
    db.init_app(app)

    from views.auth import bp as auth
    from views.shop import bp as shop
    from views.admin import bp as admin
    from views.splash import bp as splash
    app.register_blueprint(auth)
    app.register_blueprint(shop)
    app.register_blueprint(admin)
    app.register_blueprint(splash)

    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, internal_server)
    return app
