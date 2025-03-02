from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.fields.simple import PasswordField
from wtforms.validators import DataRequired, URL, Length, Email
from flask_ckeditor import CKEditorField
import email_validator

# WTForm for creating a blog post
class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    img_url = StringField("Blog Image URL", validators=[DataRequired(), URL()])
    body = CKEditorField("Blog Content", validators=[DataRequired()])
    submit = SubmitField("Submit Post")


# TODO: Create a RegisterForm to register new users
class RegisterForm(FlaskForm):
    name = StringField(label="Name", validators=[DataRequired(), Length(max=20)])
    email = StringField(label="Email", validators=[DataRequired(), Email()])
    password = PasswordField(label="Password", validators=[DataRequired(), Length(min=8)])
    submit = SubmitField(label="Register")

# TODO: Create a LoginForm to login existing users
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField(label='Password', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField(label='Log in')

# TODO: Create a CommentForm so users can leave comments below posts
class CommentForm(FlaskForm):
    comment = CKEditorField("Comment")
    submit = SubmitField("Submit Comment")