from flask import Flask, request, redirect, url_for, send_from_directory, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename
import os
import base64
from mutagen.mp3 import MP3
from mutagen.wavpack import WavPack
from prettytable import PrettyTable

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:bhuvan2904@localhost/iss_project'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['DISPLAY_FOLDER'] = 'display'

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))
    username = db.Column(db.String(1000), unique=True)
    email = db.Column(db.String(1000))
    password = db.Column(db.String(1000))

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('images', lazy=True))
    image = db.Column(db.LargeBinary)
    metadata = db.Column(db.String(1000))
    extension = db.Column(db.String(20))

class Audio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    audio_data = db.Column(db.LargeBinary)
    audio_metadata = db.Column(db.String(1000))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

current_user=-1

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', target="_self")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_login = request.form['username']
        password_login = request.form['password']
        user = User.query.filter_by(username=username_login, password=password_login).first()
        if user:
            return redirect(url_for('home', user_id=user.id))
        else:
            return render_template('login.html', login_failed=True)
    return render_template('login.html', target="_self")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username_user = request.form['username']
        name_user = request.form['name']
        email_user = request.form['email']
        password_user = request.form['password']
        confirmed_password_user = request.form['confirm-password']

        existing_user = User.query.filter_by(username=username_user).first()
        if existing_user:
            return render_template('signup.html', user_found=True)

        if password_user != confirmed_password_user:
            return render_template('signup.html', password_mismatch=True)

        new_user = User(name=name_user, username=username_user, email=email_user, password=password_user)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('signup.html', password_mismatch=False, user_found=False, target="_self")

@app.route('/home/user/<int:user_id>', methods=['GET', 'POST'])
def home(user_id):
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            image_extension = file.filename.rsplit('.', 1)[1].lower()

            # Save the file path to the database along with metadata
            with open(file_path, 'rb') as f:
                image_data = f.read()

            new_image = Image(user_id=user_id, image=image_data, extension=image_extension)
            db.session.add(new_image)
            db.session.commit()

            return redirect(url_for('home', user_id=user_id))

        return redirect(url_for('home', user_id=user_id))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('index'))

    images = Image.query.filter_by(user_id=user_id).all()
    image_data_list = [f"data:image/{image.extension};base64,{base64.b64encode(image.image).decode('utf-8')}" for image in images]

    return render_template('home.html', user_id=user_id, image_data_list=image_data_list)

@app.route('/display/<int:user_id>/<int:image_id>', methods=['GET', 'POST'])
def display_image(user_id, image_id):
    image = Image.query.filter_by(user_id=user_id, id=image_id).first()
    if not image:
        return redirect(url_for('index'))
    return send_from_directory(app.config['DISPLAY_FOLDER'], str(image_id))

@app.route('/admin')
def admin():
    return render_template('admin.html', target="_self")

@app.route('/videopage/user')
def videopage():
    user_id = 1  # Assuming there's a logged-in user
    images = Image.query.filter_by(user_id=user_id).all()
    image_data_list = [f"data:image/{image.extension};base64,{base64.b64encode(image.image).decode('utf-8')}" for image in images]

    audios = Audio.query.all()
    audio_data_list = [f"data:audio/mp3;base64,{base64.b64encode(audio.audio_data).decode('utf-8')}" for audio in audios]

    return render_template('videopage.html', user_id=user_id, image_data_list=image_data_list, audio_data_list=audio_data_list)

if __name__ == '__main__':
    app.run(debug=True)
