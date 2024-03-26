from flask import Flask, request, jsonify, redirect, url_for,send_from_directory,make_response
from flask import render_template
import hashlib
from werkzeug.utils import secure_filename
import os
import base64
from mutagen.mp3 import MP3
from mutagen.wavpack import WavPack
import numpy as np
import io 
import PIL.Image
from moviepy.editor import ImageSequenceClip, AudioFileClip, concatenate_audioclips,vfx
import tempfile
from sqlalchemy import create_engine, Column, Integer, String, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import cv2
import numpy as np
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.mysql import BLOB
import datetime
import jwt
import secrets
import string

current_user=-1
app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['DISPLAY_FOLDER'] = 'display'

engine = create_engine(os.environ["DATABASE_URL"])
Base = declarative_base()
Session = sessionmaker(bind=engine)



# Secret key for JWT
app.config['SECRET_KEY'] = secrets.token_urlsafe(32)

def generate_token(username):
    expiry_date = datetime.datetime.utcnow() + datetime.timedelta(days=1)
    payload = {'username': username, 'exp': expiry_date}
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    return token

def verify_token(token):
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload['username']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None



def delete_files_in_directory(directory_path):
    try:
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"Deleted file: {filename}")
    except Exception as e:
        print(f"Error deleting files: {e}")



def get_image_format(image_data):
    # Extract the image format from the base64-encoded data
    return image_data[:image_data.find(b';')].decode('utf-8').split('/')[1]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

class UserDetails(Base):
    __tablename__ = 'user_details'

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(1000))
    user_name = Column(String(1000))
    email = Column(String(1000))
    password = Column(String(1000))

class Image(Base):
    __tablename__ = 'images'

    image_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    image = Column(BLOB)
    image_metadata = Column(String(1000))
    extension = Column(String(20))


class Audio(Base):
    __tablename__ = 'audio'

    audio_id = Column(Integer, primary_key=True, autoincrement=True)
    audio_data = Column(BLOB)
    audio_metadata = Column(String(1000))



def create_tables():
    Base.metadata.create_all(engine)
def insert_data(name1, username1, email1, password1):
    session = Session()
    try:
        user = UserDetails(name=name1, user_name=username1, email=email1, password=password1)
        session.add(user)
        session.commit()
        print("Data inserted successfully!")
    except SQLAlchemyError as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()
        print("Session closed")



def search_for_JUST_username(username_user):
    session = Session()
    try:
        # Query the user_details table for a specific username
        user = session.query(UserDetails).filter(UserDetails.user_name == username_user).first()
        
        if user:
            return user.user_id
        else:
            return 0
    except Exception as e:
        print(f"Error: {e}")
        return 0
    finally:
        session.close()
        print("Session closed")


def search_for_user(username_user, password_user):
    try:
        session = Session()

        user = session.query(UserDetails).filter_by(user_name=username_user, password=password_user).first()

        if user:
            user_id = user.user_id
            session.close()
            print("MySQL connection closed")
            return user_id
        else:
            session.close()
            print("MySQL connection closed")
            return 0
    
    except SQLAlchemyError as e:
        print(f"Error: {e}")
        return 0

def get_user_details(user_id):
    try:
        session = Session()

        user = session.query(UserDetails).filter_by(user_id=user_id).first()

        if user:
            user_details = {
                'name': user.name,
                'user_name': user.user_name,
                'email': user.email,
                'password': user.password,
                'user_id': user.user_id
            }
            session.close()
            print("MySQL connection closed")
            return user_details
        else:
            session.close()
            print("MySQL connection closed")
            return None

    except SQLAlchemyError as e:
        print(f"Error: {e}")
        return None
def save_to_database(file_path, user_id, extension):
    try:
        session = Session()
        with PIL.Image.open(file_path) as img:
            image_metadata = {
                'format': img.format,
                'size': img.size,
                'mode': img.mode,
                'dpi': img.info.get('dpi'),  # Extract DPI if available
                # Add more metadata fields as needed
            }
        with open(file_path, 'rb') as file:
            image_data = file.read()

        # Create an Image object and add it to the session
        image = Image(image=image_data, user_id=user_id, extension=extension,image_metadata=str(image_metadata))
        session.add(image)
        session.commit()

    except Exception as e:
        print(f"Error: {e}")
        session.rollback()  # Rollback the transaction in case of error

    finally:
        session.close()


def get_audio():
    try:
        session = Session()

        # Retrieve audio data from the database
        audios = session.query(Audio.audio_data).all()

        audio_data_list = []
        for audio_data in audios:
            # Convert audio_data to base64 for embedding in HTML
            encoded_audio = base64.b64encode(audio_data[0]).decode('utf-8')
            audio_data_list.append(f"data:audio/mp3;base64,{encoded_audio}")

        return audio_data_list

    except Exception as e:
        print(f"Error: {e}")

    finally:
        session.close()
def get_images(user_id):
    try:
        session = Session()

        # Retrieve images for the specified user_id from the database
        images = session.query(Image.image, Image.extension).filter_by(user_id=user_id).all()

        image_data_list = []
        for image_data, image_extension in images:
            # Convert image_data to base64 for embedding in HTML
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            image_data_list.append(f"data:image/{image_extension};base64,{encoded_image}")

        return image_data_list

    except Exception as e:
        print(f"Error: {e}")

    finally:
        session.close()


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html',target="_self")


@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        username_login=request.form['username']
        password_login=request.form['password']
        if username_login=='admin' and password_login=='admin':
            
            token = generate_token(0)
            response = make_response(redirect(url_for('admin')))
            response.set_cookie('jwtToken', token)
            return response
        hashed_password_login = hashlib.sha256(password_login.encode()).hexdigest()
        a=search_for_user(username_login,hashed_password_login)
        delete_files_in_directory(app.config['UPLOAD_FOLDER'])
        if a==0:
            return render_template('login.html', login_failed=True)
        else:
            global current_user
            current_user = a
            token = generate_token(current_user)
            response = make_response(redirect(url_for('home', user_id=a)))
            response.set_cookie('jwtToken', token)
            return response
        
    return render_template('login.html',target="_self")

@app.route('/logout')
def logout():
    response = make_response(redirect(url_for('index')))
    response.set_cookie('jwtToken', '', max_age=0)
    return response

@app.route('/signup',methods=['GET','POST'])
def signup():
    
    if request.method=='POST':
        delete_files_in_directory(app.config['UPLOAD_FOLDER'])
        username_user=request.form['username']
        name_user=request.form['name']
        email_user=request.form['email']
        password_user=request.form['password']
        confirmed_password_user=request.form['confirm-password']
        a=search_for_JUST_username(username_user)
        print(a)
        if(a!=0 and password_user!=confirmed_password_user):
            return render_template('signup.html', password_mismatch=True,user_found=True)
        elif(a!=0):
            return render_template('signup.html', password_mismatch=False,user_found=True)
        elif(password_user!=confirmed_password_user):
            return render_template('signup.html', password_mismatch=True,user_found=False)
        else:
            hashed_password = hashlib.sha256(password_user.encode()).hexdigest()
            insert_data(name_user, username_user, email_user, hashed_password)
            return redirect(url_for('login'))


    return render_template('signup.html', password_mismatch=False,user_found=False,target="_self")
    
@app.route('/home/user/<int:user_id>', methods=['GET', 'POST'])
def home(user_id):
    token = request.cookies.get('jwtToken')

    if not token:
        return jsonify({'message': 'Token is missing'}), 401

    username = verify_token(token)

    if username:
        # User is authenticated, continue with the request
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
                save_to_database(file_path,user_id,image_extension)
                

                return jsonify({"status": "success"})

            return jsonify({"status": "failed"})
        else:
            
            image_data_list = get_images(user_id)
            row = get_user_details(user_id)
            # Render HTML to display images
            return render_template('home.html', user_id=user_id, image_data_list=image_data_list, row=row)
    else:
        # Token is invalid, return unauthorized response
        return jsonify({'message': 'Invalid token'}), 401



@app.route('/admin')
def admin():
    token = request.cookies.get('jwtToken')

    if not token:
        return jsonify({'message': 'Token is missing'}), 401

    username = verify_token(token)

    if username==0:
        return render_template('admin.html',target="_self")
    else:
        return jsonify({'message': 'Invalid token'}), 401

@app.route('/get_user_details_admin')
def get_user_details_admin():
    session = Session()
    users = session.query(UserDetails).all()
    user_details = [{
        'user_id': user.user_id,
        'name': user.name,
        'user_name': user.user_name,
        'email': user.email
    } for user in users]
    session.close()
    return jsonify(user_details)

@app.route('/delete_user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    session = Session()
    try:
        user = session.query(UserDetails).filter_by(user_id=user_id).first()
        if user:
            session.delete(user)
            session.commit()
            session.close()
            return jsonify({'status': 'success', 'message': 'User deleted successfully'})
        else:
            session.close()
            return jsonify({'status': 'failed', 'message': 'User not found'})
    except Exception as e:
        session.rollback()
        session.close()
        return jsonify({'status': 'failed', 'message': f'Error deleting user: {e}'})


@app.route('/videopage/user')
def videopage():
    token = request.cookies.get('jwtToken')

    if not token:
        return jsonify({'message': 'Token is missing'}), 401

    username = verify_token(token)

    if username:
        global current_user
        user_id=current_user
        image_data_list = get_images(user_id)
        audio_data_list=get_audio()
        print(len(image_data_list))
        return render_template('videopage.html',user_id=user_id,image_data_list=image_data_list,audio_data_list=audio_data_list)

    else:
        # Token is invalid, return unauthorized response
        return jsonify({'message': 'Invalid token'}), 401

@app.route('/create_video', methods=['POST'])
def create_video():
    data = request.get_json()
    images = data['images']  
    fps = 1/int(data['fps'])
    width = int(data['width'])
    height = int(data['height'])
    audios=data['audios']
    quality_val=int(data['quality'])

    try:

        video_clips = []

        # Iterate through the image URLs
        for image_url in images:
            # Decode the base64 encoded image
            image_data = base64.b64decode(image_url.split(',')[1])

            img = PIL.Image.open(io.BytesIO(image_data))

            if img.mode != 'RGB':
                img = img.convert('RGB')

            img = img.resize((width, height), resample=PIL.Image.BICUBIC)
            
            img_io = io.BytesIO()
            img.save(img_io, 'JPEG', quality=quality_val)
            img = PIL.Image.open(img_io)

            img_array = np.array(img)

            video_clips.append(img_array)

        if video_clips:
            final_clip = ImageSequenceClip(video_clips, fps=fps)
        else:
            print("No valid images provided.")
            return jsonify({"status": "failed", "message": "No valid images provided."})

       
        if audios != []:
            audio_clips = []

            for audio in audios:
                
                audio_data = base64.b64decode(audio['src'].split(',')[1])

                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio_file:
                    temp_audio_file.write(audio_data)
                    temp_audio_path = temp_audio_file.name

                audio_clip = AudioFileClip(temp_audio_path)

                audio_clips.append(audio_clip)

            concatenated_audio = concatenate_audioclips(audio_clips)

            looped_audio = concatenated_audio.fx(vfx.loop, duration=final_clip.duration)

            final_clip = final_clip.set_audio(looped_audio)

        output_path = os.path.join('static', 'output_video.mp4')

        final_clip.write_videofile(output_path, codec='libx264')

        return jsonify({"status": "success", "output": output_path})

    except Exception as e:
        print(f"Error creating video: {e}")
        return jsonify({"status": "failed"})
    
@app.route('/videodisplay')
def videodisplay():
    return render_template('videodisplay.html',target="_blank")
    
    
if __name__ == '__main__':
    create_tables()
    app.run(debug=True)
