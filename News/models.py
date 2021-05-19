from . import db
from flask_login import UserMixin
import csv
import datetime
import os

class Permission:
    COMMENT = 1
    WRITE = 2
    MODERATE = 4
    ADMIN = 8


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    @staticmethod
    def insert_roles():
        roles = {
            'User': [Permission.COMMENT, Permission.WRITE],
            'Moderator': [Permission.COMMENT,
                          Permission.WRITE, Permission.MODERATE],
            'Administrator': [Permission.COMMENT,
                              Permission.WRITE, Permission.MODERATE,
                              Permission.ADMIN],
        }
        default_role = 'User'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm

    def __repr__(self):
        return '<Role %r>' % self.name

class User(UserMixin,db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    email = db.Column(db.String(100), unique=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    name = db.Column(db.String(1000))
    information_bio = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.utcnow)
    password = db.Column(db.String(256))
    avatar_path = db.Column(db.Text,default=os.path.join('/images/avatars/default.jpg'))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == os.getenv('ADMIN_EMAIL'):
                self.role = Role.query.filter_by(name='Administrator').first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)

    def change_role(self,new_role):
        role = Role.query.filter_by(name = new_role).first()
        self.role_id = role.id

    def get_json(self):
        return {
            'id' : self.id,
            'email' : self.email,
            'username' : self.username,
            'role' : Role.query.filter_by(id=self.role_id).first().name,
            'bio' : self.information_bio,
            'date_reg' : str(self.timestamp),
            'name' : self.name,
            'posts' : self.posts,
            'comments' : self.comments,
            'avatar_path' : self.avatar_path
        }

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text,nullable=False)
    body = db.Column(db.Text,nullable=False)
    image_path = db.Column(db.Text,nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comments = db.relationship('Comment', backref='post', lazy='dynamic')

    @staticmethod
    def get_posts_by_page(*,page = 1, count_in_page = 10):
        all_posts = Post.query.all()
        all_posts.reverse()
        return all_posts[count_in_page*(page-1):count_in_page*page]

    @staticmethod
    def check_page(page : int,*,count_in_page = 10):
        count_posts = Post.query.count()
        if page == 1 and count_posts >= 0:
            return True
        if count_posts >= page*count_in_page:
            return True
        return False

    @staticmethod
    def get_posts_for_news(page=1, count_in_page=10,max_length_main = 1500):
        posts = list(map(Post.get_json,Post.get_posts_by_page(page=page, count_in_page=count_in_page)))
        for post in posts:
            if len(post['body']) > max_length_main:
                post['body'] = post['body'][:max_length_main] + '..'
        return posts

    @staticmethod
    def get_posts_for_main_page(max_length_main = 600, max_lenght_right = 150):
        posts = list(map(Post.get_json,Post.get_posts_by_page(count_in_page=6)))
        if posts == []: return [],[]
        main_columns = posts[:3]
        right_columns = posts[3:]
        for post in main_columns:
            if len(post['body']) > max_length_main:
                post['body'] = post['body'][:max_length_main] + '..'
        for post in right_columns:
            if len(post['body']) > max_lenght_right:
                post['body'] = post['body'][:max_lenght_right] + '..'
        return main_columns,right_columns

    def get_json(self):
        comments = list(self.comments)
        comments.reverse()
        return {
            'id' : self.id,
            'title' : self.title,
            'body' : self.body,
            'date' : str(self.timestamp),
            'author' : User.query.filter_by(id=self.author_id).first().username,
            'image_path' : self.image_path,
            'comments' : list(map(Comment.get_json,comments))
        }

    def add_comment(self,user,message):
        new_comment = Comment(
            body = message,
            author_id = user.id,
            post_id = self.id
        )
        db.session.add(new_comment)
        db.session.commit()

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    def get_json(self):
        return {
            'id': self.id,
            'body': self.body,
            'date': str(self.timestamp),
            'author': User.query.filter_by(id=self.author_id).first().get_json(),
        }