import requests

from flask import Flask, redirect, Blueprint, request, jsonify, render_template, flash, session
from flask_login import current_user, login_required, login_user, logout_user
from datetime import datetime, date, timedelta
from werkzeug.datastructures import ImmutableOrderedMultiDict

from support.config import SiteConfig
from support.models import User, Product, Pick, Orders, db
from support.extensions import paypal, aws
from support.helper import paypalify, validate_ipn

site_config = SiteConfig()

bp = Blueprint('shop', __name__)

@bp.route('/shop', methods=['POST', 'GET'])
def shop():
    db_products = Product.query.filter_by(is_stocked=True).all()
    products = [product for product in db_products]
    product_link = "/".join([aws.S3_LINK, "products"])
    return render_template('main/shop.html',
        products=products,
        product_link=product_link)

@bp.route('/shop/p.<int:id>', methods=['POST', 'GET'])
def details(id):
    product = Product.query.get_or_404(id)
    product_link = "/".join([aws.S3_LINK, "products"])
    ingredient_link = "/".join([aws.S3_LINK, "ingredients"])
    return render_template('main/details.html',
        product=product,
        product_link=product_link,
        ingredient_link=ingredient_link)

@bp.route('/shop/p.<int:id>/add')
@login_required
def add(id):
    product = Product.query.get_or_404(id)
    cart = current_user.cart

    if not product in cart.contents:
        pick_up_one = Pick(
            count=1,
            shopper_id=current_user.id,
            product_id=product.id
            )
        cart.contents.append(product)
        db.session.add(pick_up_one)
        db.session.commit()
        message = "Added to cart!"
        url = '/shop/p.{}'.format(product.id)
    else:
        pick_up_another_one = Pick.query.filter_by(shopper_id=current_user.id).filter_by(product_id=product.id).first()
        if pick_up_another_one.count < product.stock:
            pick_up_another_one.count += 1
            db.session.commit()
            message = "Another one!"
        else:
            message = "No more of this product available."
        url = '/checkout'
    flash(message)
    return redirect(url)

@bp.route('/checkout')
@login_required
def checkout():
    cart = current_user.cart
    products = [product for product in cart.contents]
    count_dict = {}
    for product in cart.contents:
        count = Pick.query.filter_by(shopper_id=current_user.id).filter_by(product_id=product.id).first().count
        count_dict[product.id] = count
    cart.bill(count_dict)
    db.session.commit()
    session['is_valid'] = paypal.PAYPAL_IPN_INACTIVE
    session['last_order_id'] = None
    product_link = "/".join([aws.S3_LINK, "products"])
    return render_template('sales/checkout.html',
        user=current_user,
        cart=cart,
        products=products,
        quantities=count_dict,
        product_link=product_link)

@bp.route('/checkout/payment')
@login_required
def payment():
    cart = current_user.cart
    new_order = Orders(
        gross=cart.total_cost,
        buyer_id=current_user.id
        )
    db.session.add(new_order)
    db.session.commit()
    return redirect('/checkout/complete')

@bp.route('/shop/p.<int:id>/drop')
@login_required
def drop(id):
    product = Product.query.get_or_404(id)
    cart = current_user.cart

    if product in cart.contents:
        drop_one = Pick.query.filter_by(shopper_id=current_user.id).filter_by(product_id=product.id).first()
        if drop_one.count > 1:
            drop_one.count -= 1
            db.session.commit()
            message = "1 {} has been deducted from you cart.".format(product.name)
        elif drop_one.count == 1:
            return redirect('/checkout/p.{}/remove'.format(product.id))
        else:
            message = "{} is not in your cart.".format(product.name)
        flash(message)
    return redirect('/checkout')

@bp.route('/checkout/p.<int:id>/remove')
@login_required
def remove(id):
    product = Product.query.get_or_404(id)
    cart = current_user.cart

    if product in cart.contents:
        pick = Pick.query.filter_by(shopper_id=current_user.id).filter_by(product_id=product.id).first()
        if pick:
            db.session.delete(pick)
        cart.contents.remove(product)
        db.session.commit()
        flash('{} has been removed from your cart.'.format(product.name))
    return redirect('/checkout')

@bp.route('/checkout/complete')
@login_required
def complete():
    is_valid_transaction = session['is_valid']
    if is_valid_transaction:
        cart = current_user.cart
        for product in cart.contents:
            purchased = Pick.query.filter_by(shopper_id=current_user.id).filter_by(product_id=product.id).first()
            product.stock -= purchased.count
            db.session.delete(purchased)
            cart.contents.remove(product)
            db.session.commit()
        message = "Your order will be processed! Thank you!"
    else:
        business_email = siteconfig.BUSINESS_EMAIL
        message = "Something went wrong. Your order was cancelled. If you were billed, contact {}".format(business_email)
    flash(message)
    return render_template('sales/complete.html')
