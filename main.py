from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash,request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text,ForeignKey
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Import your forms from the forms.py
from forms import CreatePostForm,CreateRegisterForm,CreateLoginForm,CreateCommentForm
import os



app = Flask(__name__,template_folder="templates")

app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'

ckeditor = CKEditor(app)
app.config["CKEDITOR_SERVE_LOCAL"] = True

Bootstrap5(app)

# TODO: Configure Flask-Login


# CREATE DATABASE
class Base(DeclarativeBase):
    pass
import os

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
db = SQLAlchemy(model_class=Base)
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)

# Create a user_loader callback
@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

class Comment(db.Model):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    text: Mapped[str] = mapped_column(Text, nullable=False)

    # foreign key → which user wrote the comment
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # foreign key → which post the comment belongs to
    post_id: Mapped[int] = mapped_column(ForeignKey("blog_posts.id"))

    # relationships
    author = relationship("User", back_populates="comments")
    post = relationship("BlogPost", back_populates="comments")

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))

    posts = relationship("BlogPost", back_populates="author")

    comments = relationship("Comment", back_populates="author")

class BlogPost(db.Model):
    __tablename__ = "blog_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)

    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    author = relationship("User", back_populates="posts")

    comments = relationship("Comment", back_populates="post")


with app.app_context():
    db.create_all()

@app.route('/')
def home():
    if current_user.is_authenticated:
      return redirect(url_for("get_all_posts"))
    else:
        return render_template("home.html")

@app.route('/register',methods=['GET','POST'])
def register():
    form= CreateRegisterForm()
    if form.validate_on_submit():
        hash_and_salted_password = generate_password_hash(
            request.form.get('Password'),
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=request.form.get('Email'),
            name=request.form.get('Name'),
            password=hash_and_salted_password,)
        result = db.session.execute(
            db.select(User).where(User.email == new_user.email)
        )
        user = result.scalar()
        
        if user:
            flash("You are already registered with us please login ")
            return redirect(url_for("login"))
        else: 
           db.session.add(new_user)
           db.session.commit()

        # Log in and authenticate user after adding details to database.
           flash("Registration successful")
           login_user(new_user)
           return redirect(url_for("get_all_posts"))

    
    return render_template("register.html",form=form)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login',methods=['GET','POST'])
def login():
    form = CreateLoginForm()
    if form.validate_on_submit():
        email = request.form.get("Email")
        password = request.form.get("Password")

        result = db.session.execute(
            db.select(User).where(User.email == email)
        )
        user = result.scalar()

        if not user:
            flash("The Email entered is incorrect, please try again")

        elif not check_password_hash(user.password, password):
            flash("Incorrect password, please check the password")

        else:
            login_user(user)
            return redirect(url_for("get_all_posts"))
    return render_template("login.html",form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.route('/logged')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts)


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    form = CreateCommentForm()
    requested_post = db.get_or_404(BlogPost, post_id)

    if form.validate_on_submit():

        if not current_user.is_authenticated:
            flash("You must login to comment")
            return redirect(url_for("login"))

        new_comment = Comment(
            text=form.body.data,
            author=current_user,
            post=requested_post
        )

        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for("show_post", post_id=post_id))
    return render_template(
        "post.html",
        post=requested_post,
        form=form
    )


# TODO: Use a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
           title=form.title.data,
           subtitle=form.subtitle.data,
           body=form.body.data,
           img_url=form.img_url.data,
           date=date.today().strftime("%B %d, %Y"),
           author=current_user      
        )
        
        
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):
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
def delete_post(post_id):
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
    app.run(debug=True, port=5002)
