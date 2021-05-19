from flask import Flask, jsonify, make_response, request,flash,url_for
import News.models as models
import logging
from flask import Blueprint, render_template,redirect
from functools import wraps
from . import db
from flask_login import login_required, current_user
import os

main = Blueprint('main', __name__)

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission):
                return render_template('404.html')
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@main.route('/')
def index():
    main_columns, right_columns = models.Post.get_posts_for_main_page()
    return render_template('index.html', main_columns=main_columns, right_columns=right_columns)


@main.route('/profile',methods=['GET'])
@login_required
def profile():
    return render_template('profile.html', user=current_user.get_json())

@main.route('/profile',methods=['POST'])
@login_required
def profile_update():
    email = request.form.get('email')
    name = request.form.get('name')
    username = request.form.get('username')
    bio = request.form.get('bio')

    user = models.User.query.filter_by(
        email=email).first()  # if this returns a user, then the email already exists in database

    if user and user.id != current_user.id:  # if a user is found, we want to redirect back to signup page so user can try again
        flash('Данный email адрес уже используется другим пользователем',category='warning')
        return redirect(url_for('main.profile'))

    user = models.User.query.filter_by(
        username=username).first()  # if this returns a user, then the email already exists in database

    if user and user.id != current_user.id:  # if a user is found, we want to redirect back to signup page so user can try again
        flash('Данный никнейм уже используется другим пользователем',category='warning')
        return redirect(url_for('main.profile'))

    if request.files['image'].filename != '':
        image = request.files['image']
        avatar_path = os.path.join(os.getenv('IMAGE_UPLOADS_USERS'), image.filename)
        image.save(avatar_path)

        current_user.avatar_path = '/images/avatars/' + image.filename

    current_user.email = email
    current_user.name = name
    current_user.username = username
    current_user.information_bio = bio
    db.session.commit()

    flash('Вы успешно изменили данные профиля!',category='good')
    return redirect(url_for('main.profile'))


@main.route('/news/page=<page>')
def news(page = 1):
    page = int(page)
    main_columns = models.Post.get_posts_for_news(page=page,count_in_page=6)
    next_page = page+1
    previous_page = 1
    if not models.Post.check_page(page=next_page,count_in_page=6):
        next_page -= 1
    if page != 1:
        previous_page = page-1
    return render_template('news.html', main_columns=main_columns,previous_page = previous_page,page = next_page, this_page = page)

@main.route('/post/id=<post_id>')
def page_post(post_id):
    post = models.Post.query.filter_by(id = post_id).first()
    right_columns, _ = models.Post.get_posts_for_main_page()
    if post:
        return render_template('post.html',post = post.get_json() ,right_columns = right_columns)
    return render_template('404.html')


@main.route('/add_post',methods=['GET'])
@login_required
@permission_required(4)
def add_post_get():
    return render_template('add_post.html')

@main.route('/add_post',methods=['POST'])
@login_required
@permission_required(4)
def add_post():
    title = request.form.get('title')
    text = request.form.get('text')
    if request.files['image'].filename == '':
        flash('Пожалуйста, добавьте фотографию к посту!',category='warning')
        return redirect(url_for('main.add_post'))

    image = request.files['image']
    image_path = os.path.join(os.getenv('IMAGE_UPLOADS_POSTS'), image.filename)
    image.save(image_path)

    new_post = models.Post(
        title = title,
        body = text,
        author_id = current_user.id,
        image_path = '/images/posts/' + image.filename
    )
    db.session.add(new_post)
    db.session.commit()
    flash('Вы успешно добавили пост!',category="good")
    return redirect(url_for('main.add_post_get'))

@main.route('/comment',methods=['POST'])
@login_required
@permission_required(2)
def comment():
    post_id = request.form.get('post_id')
    message = request.form.get('message')
    post = models.Post.query.filter_by(id = post_id).first()
    if post:
        post.add_comment(message=message,user=current_user)
    return redirect(url_for('main.page_post',post_id=post_id))

@main.route('/delete_post/post_id=<post_id>')
@login_required
@permission_required(8)
def delete_post(post_id):
    post = models.Post.query.filter_by(id=post_id).first()
    if post:
        db.session.delete(post)
        db.session.commit()
    return redirect(url_for('main.index'))

@main.route('/delete_comment/comment_id=<comment_id>&post_id=<post_id>')
@login_required
@permission_required(4)
def delete_comment(comment_id,post_id):
    comment = models.Comment.query.filter_by(id=comment_id).first()
    if comment:
        db.session.delete(comment)
        db.session.commit()
    return redirect(url_for('main.page_post',post_id=post_id))


@main.route('/control_users')
@login_required
@permission_required(8)
def control_users():
    users = map(models.User.get_json,models.User.query.all())
    return render_template('control_users.html',users = users, admin_email = os.getenv('ADMIN_EMAIL'))


@main.route('/update_role_user',methods = ['POST'])
@login_required
@permission_required(8)
def update_role_user():
    id = request.form.get('user_id')
    role = request.form.get('roles')
    models.User.query.filter_by(id = id).first().change_role(role)
    db.session.commit()
    return redirect(url_for('main.control_users'))