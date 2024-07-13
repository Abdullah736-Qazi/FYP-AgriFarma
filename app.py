from flask import Flask, render_template, flash, request, redirect, url_for, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import secrets
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import pandas as pd
import requests
import warnings
import os
import random
from sklearn.exceptions import UndefinedMetricWarning, DataConversionWarning

warnings.filterwarnings("ignore", category=DataConversionWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=UndefinedMetricWarning)

API_KEY = 'cadedcb58343421c899172349241801'
secret_key = secrets.token_hex(32)

app = Flask(__name__, template_folder='templates')
app.secret_key = secret_key
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}  # Allowed image file extensions
UPLOAD_FOLDER_PATH = os.path.join(os.getcwd(), UPLOAD_FOLDER)
print(UPLOAD_FOLDER_PATH)




def connect_db():
    return sqlite3.connect('AGRI-FARMA.db')


def init_db():
    with connect_db() as db:
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS farmer(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                password TEXT NOT NULL,
                phone_number TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customer(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                password TEXT NOT NULL,
                phone_number TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                image_filename TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES farmer(id)
            )
        ''')
        db.commit()


def insert_user(name, password, phone_number):
    with connect_db() as db:
        cursor = db.cursor()
        cursor.execute('INSERT INTO farmer (name, password, phone_number) VALUES (?, ?, ?)',
                       (name, generate_password_hash(password), phone_number))
        db.commit()


def insert_customer(name, password, phone_number):
    with connect_db() as db:
        cursor = db.cursor()
        cursor.execute('INSERT INTO customer (name, password, phone_number) VALUES (?, ?, ?)',
                       (name, generate_password_hash(password), phone_number))
        db.commit()


def insert_crop(user_id, name, price, quantity, image_filename):
    try:
        with connect_db() as db:
            cursor = db.cursor()
            cursor.execute('INSERT INTO crops (user_id, name, price, quantity, image_filename) VALUES (?, ?, ?, ?, ?)',
                           (user_id, name, price, quantity, image_filename))
            db.commit()
            return True
    except Exception as e:
        print(f"Error adding crop: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def user_exists(phone_number):
    with connect_db() as db:
        cursor = db.cursor()
        cursor.execute('SELECT * FROM farmer WHERE phone_number=?', (phone_number,))
        return cursor.fetchone()


def customer_exists(phone_number):
    with connect_db() as db:
        cursor = db.cursor()
        cursor.execute('SELECT * FROM customer WHERE phone_number=?', (phone_number,))
        return cursor.fetchone()


def fetch_crops(user_id):
    try:
        with connect_db() as db:
            cursor = db.cursor()
            cursor.execute('SELECT * FROM crops WHERE user_id=?', (user_id,))
            crops = cursor.fetchall()
            crop_list = []
            for crop in crops:
                crop_dict = {
                    'id': crop[0],
                    'user_id': crop[1],
                    'name': crop[2],
                    'price': crop[3],
                    'quantity': crop[4],
                    'image_filename': crop[5]
                }
                crop_list.append(crop_dict)
            return crop_list
    except Exception as e:
        print(f"Error fetching crops: {e}")
        return None

def fetch_crops_by_category(category):
    crops = []  # Initialize an empty list to store crop data

    try:
        with sqlite3.connect('AGRI-FARMA.db') as conn:
            cursor = conn.cursor()

            # Case-insensitive comparison using LOWER()
            cursor.execute("SELECT name, user_id, price, quantity, image_filename FROM crops WHERE LOWER(name) = ?", (category.lower(),))

            rows = cursor.fetchall()  # Fetch all matching rows

            # Iterate through rows and create crop dictionaries
            for row in rows:
                crop = {
                    'name': row[0],
                    'phone_number': "+92" + str(row[1]),
                    'price': row[2],
                    'quantity': row[3],
                    'image_url': url_for('static', filename='uploads/' + row[4])  # Construct image URL
                }

                # Check if all required properties are present
                if all(key in crop for key in ['name', 'phone_number', 'price', 'quantity', 'image_url']):
                    crops.append(crop)  # Add crop to the list
                else:
                    print("Skipping crop due to missing properties:", crop)

    except sqlite3.Error as e:
        print("Error fetching crops by category:", e)

    return crops  # Return the list of crop dictionaries


def verify_login(phone_number, password):
    user = user_exists(phone_number)
    if user and check_password_hash(user[2], password):
        return True
    return False


def verify_customer(phone_number, password):
    user = customer_exists(phone_number)
    if user and check_password_hash(user[2], password):
        return True
    return False


def get_user_name(phone_number):
    with connect_db() as db:
        cursor = db.cursor()
        cursor.execute('SELECT name FROM farmer WHERE phone_number=?', (phone_number,))
        user = cursor.fetchone()
        if user:
            return user[0]
    return None


df = pd.read_csv('crop.csv')
features = ['humidity', 'temperature', 'rainfall']
target = 'label'
X = df[features]
y = df[target]
X.columns = features

model = RandomForestClassifier(random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model.fit(X_train, y_train)


def get_prediction(city):
    try:
        base_url = f'http://api.weatherapi.com/v1/forecast.json?key={API_KEY}&q={city}&days=30'
        response = requests.get(base_url)

        if response.status_code == 200:
            weather_data = response.json()

            rainfall_data = [day['day']['totalprecip_mm'] for day in weather_data['forecast']['forecastday']]

            total_rainfall = sum(rainfall_data)

            predicted_label = model.predict(
                [[weather_data['current']['humidity'], weather_data['current']['temp_c'], total_rainfall]])[0]

            return predicted_label

    except Exception as e:
        print(f"Error getting prediction: {e}")

    return None


def update_profile(phone_number, name, password):
    try:
        with connect_db() as db:
            cursor = db.cursor()
            if password:
                cursor.execute('UPDATE farmer SET name=?, password=? WHERE phone_number=?',
                               (name, generate_password_hash(password), phone_number))
            else:
                cursor.execute('UPDATE farmer SET name=? WHERE phone_number=?',
                               (name, phone_number))
            db.commit()
            return True
    except Exception as e:
        print(f"Error updating profile: {e}")
        db.rollback()
        return False
    finally:
        db.close()


generated_otp = None


def generate_otp():
    return random.randint(1000, 9999)


hash_key = '531b4c9aa92f2f84881c161d1766e678'
base_url = 'https://api.veevotech.com/v3/sendsms'


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/landing')
def landing():
    return render_template('landing.html')


@app.route('/verification', methods=['GET', 'POST'])
def verification():
    global generated_otp

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'send_otp':
            phone_number = request.form.get('phone_number')
            if phone_number:
                generated_otp = generate_otp()

                payload = {
                    'hash': hash_key,
                    'receivernum': phone_number,
                    'medium': 1,
                    'sendernum': 'Default',
                    'textmessage': 'Your OTP is: ' + str(generated_otp),
                }

                response = requests.post(base_url, json=payload)
                response_data = response.json()

                if response_data['STATUS'] == 'SUCCESSFUL':
                    return jsonify({'success': True})
                else:
                    return jsonify({'success': False, 'error': 'Failed to send OTP'})

        if action == 'verify_otp':
            entered_otp = request.form.get('otp')
            if entered_otp == str(generated_otp):
                phone_number = request.form.get('phone_number')
                if phone_number:
                    return jsonify({'success': True, 'phone_number': phone_number})  # Pass phone number to the next route
            else:
                return jsonify({'success': False, 'error': 'Invalid OTP'})

    return render_template('verification.html')


@app.route('/verification2', methods=['GET', 'POST'])
def verification2():
    global generated_otp

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'send_otp':
            phone_number = request.form.get('phone_number')
            if phone_number:
                generated_otp = generate_otp()

                payload = {
                    'hash': hash_key,
                    'receivernum': phone_number,
                    'medium': 1,
                    'sendernum': 'Default',
                    'textmessage': 'Your OTP is: ' + str(generated_otp),
                }

                response = requests.post(base_url, json=payload)
                response_data = response.json()

                if response_data['STATUS'] == 'SUCCESSFUL':
                    return jsonify({'success': True})
                else:
                    return jsonify({'success': False, 'error': 'Failed to send OTP'})

        if action == 'verify_otp':
            entered_otp = request.form.get('otp')
            if entered_otp == str(generated_otp):
                phone_number = request.form.get('phone_number')
                if phone_number:
                    return jsonify({'success': True, 'phone_number': phone_number})  # Pass phone number to the next route
            else:
                return jsonify({'success': False, 'error': 'Invalid OTP'})

    return render_template('verification2.html')


@app.route('/verification-forgetpass', methods=['GET', 'POST'])
def verification_forgetpass():
    global generated_otp

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'send_otp':
            phone_number = request.form.get('phone_number')
            if user_exists(phone_number):
                generated_otp = generate_otp()

                payload = {
                    'hash': hash_key,
                    'receivernum': phone_number,
                    'medium': 1,
                    'sendernum': 'Default',
                    'textmessage': 'Your OTP is: ' + str(generated_otp),
                }

                response = requests.post(base_url, json=payload)
                response_data = response.json()

                if response_data['STATUS'] == 'SUCCESSFUL':
                    return jsonify({'success': True})
                else:
                    return jsonify({'success': False, 'error': 'Failed to send OTP'})

        elif action == 'verify_otp':
            entered_otp = request.form.get('otp')
            if entered_otp == str(generated_otp):
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Invalid OTP'})

    return render_template('verification-forgetpass.html')


@app.route('/verification-forgetpassC', methods=['GET', 'POST'])
def verification_forgetpassC():
    global generated_otp

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'send_otp':
            phone_number = request.form.get('phone_number')
            if customer_exists(phone_number):
                generated_otp = generate_otp()
                payload = {
                    'hash': hash_key,
                    'receivernum': phone_number,
                    'medium': 1,
                    'sendernum': 'Default',
                    'textmessage': 'Your OTP is: ' + str(generated_otp),
                }

                response = requests.post(base_url, json=payload)
                response_data = response.json()

                if response_data['STATUS'] == 'SUCCESSFUL':
                    return jsonify({'success': True})
                else:
                    return jsonify({'success': False, 'error': 'Failed to send OTP'})

        elif action == 'verify_otp':
            entered_otp = request.form.get('otp')
            if entered_otp == str(generated_otp):
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Invalid OTP'})

    return render_template('verification-forgetpassC.html')


@app.route('/farmer-register', methods=['GET', 'POST'])
def farmer_register():
    if request.method == 'POST':
        init_db()
        name = request.form['name']
        password = request.form['password']
        phone_number = request.form['phone_number']

        if user_exists(phone_number):
            return jsonify({"success": False, "error": "Phone number is already registered."})

        insert_user(name, password, phone_number)
        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for('farmer_login'))
    return render_template('farmer-register.html')


@app.route('/customer-register', methods=['GET', 'POST'])
def customer_register():
    if request.method == 'POST':
        init_db()
        name = request.form['name']
        password = request.form['password']
        phone_number = request.form['phone_number']

        if customer_exists(phone_number):
            return jsonify({"success": False, "error": "Phone number is already registered."})

        insert_customer(name, password, phone_number)
        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for('customer_login'))
    elif request.method == 'GET':
        phone_number = request.args.get('phone_number')
        return render_template('customer-register.html', phone_number=phone_number)


@app.route('/farmer-login', methods=['GET', 'POST'])
def farmer_login():
    if request.method == 'POST':
        phone_number = request.form['phone_number']
        password = request.form['password']
        if verify_login(phone_number, password):
            session['user'] = phone_number
            return redirect(url_for('dashboard'))

    return render_template('farmer-login.html')


@app.route('/customer-login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        phone_number = request.form['phone_number']
        password = request.form['password']
        if verify_customer(phone_number, password):
            session['user'] = phone_number
            return redirect(url_for('market'))

    return render_template('customer-login.html')


@app.route('/dashboard')
def dashboard():
    new_crop_data = request.args.get('new_crop')

    if 'user' in session:
        phone_number = session['user']
        user_name = get_user_name(phone_number)
        if user_name:
            user_info = {'name': user_name, 'phone': phone_number}
            return render_template('dashboard.html', user_info=user_info, new_crop=new_crop_data)
        else:
            flash("User not found.", "error")
            return redirect(url_for('farmer_login'))
    return redirect(url_for('farmer_login'))


@app.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user' in session:
        if request.method == 'GET':
            return render_template('edit-profile.html')

        if request.method == 'POST':
            phone_number = session['user']
            name = request.form.get('name')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm-password')

            if password != confirm_password:
                return jsonify({'success': False, 'error': 'Passwords do not match'})

            if update_profile(phone_number, name, password):
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Failed to update profile'})

    return redirect(url_for('farmer_login'))


@app.route('/add-crop', methods=['GET', 'POST'])
def add_crop():
    if request.method == 'POST':
        crop_name = request.form.get('crop-name')
        crop_price = request.form.get('crop-price')
        crop_quantity = request.form.get('crop-quantity')
        crop_image = request.files.get('crop-image')

        # Check if all required fields are filled
        if not all([crop_name, crop_price, crop_quantity, crop_image]):
            flash("Please fill out all fields.", "error")
            return redirect(url_for('add_crop'))

        # Check if the uploaded file is an allowed image type
        if crop_image.filename == '':
            flash("No selected file.", "error")
            return redirect(request.url)
        if not allowed_file(crop_image.filename):
            flash("Invalid file type.", "error")
            return redirect(request.url)

        # Save the uploaded image file
        filename = secure_filename(crop_image.filename)
        crop_image.save(os.path.join(UPLOAD_FOLDER_PATH, filename))
        # Insert crop data into the database
        user_id = session.get('user')
        if insert_crop(user_id, crop_name, crop_price, crop_quantity, filename):
            # Fetch the newly added crop data
            new_crop = {
                'name': crop_name,
                'price': crop_price,
                'quantity': crop_quantity,
                'image_filename': filename
            }
            return jsonify(new_crop)  # Return the new crop data in JSON format
        else:
            flash("Failed to add crop. Please try again.", "error")
            return redirect(url_for('dashboard'))

    # Fetch crops data from the database
    user_id = session.get('user')
    crops = fetch_crops(user_id)

    return render_template('add-crop.html', cropsData=crops)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/get-prediction', methods=['GET', 'POST'])
def get_prediction_route():
    if request.method == 'GET':
        city = request.args.get('city')
        predicted_label = get_prediction(city)
        if predicted_label is not None:
            return render_template('ai.html', predicted_label=predicted_label)
        else:
            return jsonify({"error": "Failed to get weather data or make a prediction."}), 500

    return jsonify({"error": "Invalid request method."})


@app.route('/market')
def market():
    return render_template('market.html')


@app.route('/categories')
def categories():
    category = request.args.get('category')

    if not category:
        return redirect(url_for('market'))  

    # Convert category to lowercase for comparison
    category = category.lower()  

    crops = fetch_crops_by_category(category)

    # Capitalize category for display in template (if needed)
    category_display = category.capitalize() 

    return render_template('categories.html', category=category_display, crops=crops)

@app.route('/error')
def error():
    return render_template('error.html')
