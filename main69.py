from datetime import date
from typing import List
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from werkzeug.security import generate_password_hash, check_password_hash
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
import os
from dotenv import load_dotenv
import bleach

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
ckeditor = CKEditor(app)
Bootstrap5(app)

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

# TODO: Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['SQLALCHEMY_DATABASE_URI']
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(250), nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("User Details.id"))
    user: Mapped["User"] = relationship(back_populates="blogs")
    commenter: Mapped[List["Comment"]] = relationship(back_populates="blogs")

# TODO: Create a User table for all your registered users.
class User(UserMixin,db.Model):
    __tablename__ = "User Details"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String, nullable=False)
    blogs: Mapped[List["BlogPost"]] = relationship(back_populates='user')
    commenter: Mapped[List["Comment"]] = relationship( back_populates="user")

class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("User Details.id"))
    blog_id: Mapped[int] = mapped_column(ForeignKey("blog_posts.id"))
    user: Mapped["User"] = relationship(back_populates="commenter")
    blogs: Mapped["BlogPost"] = relationship(back_populates="commenter")

with app.app_context():
    db.create_all()

def admin_only(function):
    def decorator_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)

        function(*args, **kwargs)
    return decorator_function


# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods= ['POST', 'GET'])
def register():
    register_form = RegisterForm()
    if request.method == "POST":
        all_data = db.session.execute(db.select(User).order_by(User.id)).scalars().all()
        all_emails = [user.email for user in all_data]

        name = register_form.name.data
        email = register_form.email.data
        password = register_form.password.data

        hashed_password = generate_password_hash(password, 'pbkdf2', 8)

        if email in all_emails:
            flash('An account with the entered email already exists. Login instead.')
            return redirect(url_for("login"))

        new_user = User(name= name, email=email, password= hashed_password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("get_all_posts"))
    return render_template("register.html", form = register_form)


# TODO: Retrieve a user from the database based on their email.
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == "POST":
        email = form.email.data
        password = form.password.data

        user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if user is None:
            flash("Email not registered. Enter a registered Email!")
            return redirect(url_for("login"))
        if check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("get_all_posts"))
        else:
            flash("Password Incorrect. Try again")

    return render_template("login.html", form= form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>", methods=['POST', 'GET'])
def show_post(post_id):
    form = CommentForm()
    requested_post = db.get_or_404(BlogPost, post_id)

    comments = db.session.execute(db.select(Comment).where(Comment.blog_id == post_id)).scalars().all()

    if request.method == "POST":
        if current_user.is_authenticated:
            data = form.comment.data
            data = data.split('>')[1]
            data= data.split("<")[0]

            current_blog = db.get_or_404(BlogPost, post_id)
            comment = Comment(text=data, user=current_user, blogs=current_blog)
            db.session.add(comment)
            db.session.commit()
            return redirect(url_for("show_post"))
        else:
            flash("Only Logged in users are allowed to make comments. Please log in.")
            return redirect(url_for("login"))


    return render_template("post.html", post=requested_post, form=form, comments=comments)


# TODO: Use a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
@login_required
def add_new_post():
    if current_user.id != 1:
        return abort(403)
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            author= current_user.name,
            body=form.body.data,
            img_url=form.img_url.data,
            date=date.today().strftime("%B %d, %Y"),
            user = current_user,
        )

        db.session.add(new_post)
        db.session.commit()

        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@login_required
# @admin_only
def edit_post(post_id):
    if current_user.id != 1:
        return abort(403)
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()

        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@login_required
# @admin_only
def delete_post(post_id):
    if current_user.id != 1:
        return abort(403)
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=False, port=5002)
