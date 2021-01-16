#Reference: https://realpython.com/flask-google-login/
import os

from flask import Flask, redirect, Blueprint, request, url_for, render_template, flash
from flask_login import current_user, login_required, login_user, logout_user

from support.models import Waitlist, db

bp = Blueprint('splash', __name__)

@bp.route("/")
def index():
    return render_template('main/index.html')

@bp.route("/get-access", methods=["POST", "GET"])
def access():
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")

        new_waitlist = Waitlist(
            first_name=first_name,
            last_name=last_name,
            email=email
            )
        db.session.add(new_waitlist)
        db.session.commit()
        flash("Thanks for your interest in our product!")
        return redirect("/")
    return render_template("main/access.html")

@bp.route("/about")
def about():
    return render_template('main/about.html')
