from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, EmailField, PasswordField
from wtforms.validators import DataRequired, Email, Length


class ContactForm(FlaskForm):
    firstname = StringField("Enter Firstname: ", validators=[DataRequired(message="Your Firstname must be supplied")])
    lastname = StringField("Enter Lastname: ", validators=[DataRequired(message="Your Lastname must be supplied")])
    email = EmailField("Your Email: ", validators=[Email(message="Are you sure this email is correct?")])
    message = TextAreaField("Message: ", validators=[DataRequired(message="How can your message be empty"), Length(min=10, max=100, message="Too Short!")])
    submit = SubmitField("Submit")
    
class RegisterForm(FlaskForm):
    firstname = StringField('First Name', validators=[DataRequired(message='This field cannot be empty')])
    lastname = StringField('Last Name', validators=[DataRequired(message='This field cannot be empty')])
    email = EmailField('Last Name', validators=[Email()])
    phone = StringField('Phone', validators=[DataRequired(message='This field cannot be empty')])
    password = PasswordField('Password', validators=[DataRequired(message='This field cannot be empty')])
    confirm_pass = PasswordField('Confirm Password', validators=[DataRequired(message='This field cannot be empty')])
    
    
class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required')])
    submit = SubmitField('Login')
    
    
    