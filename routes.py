from flask import render_template, request, redirect, url_for, flash, session, jsonify
import os
from pyzbar.pyzbar import decode
import cv2
import requests
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

# Import the app instance and models
from main import app, UPLOAD_FOLDER
from modules import db, User, Food
from functools import wraps

# Login required decorator
def login_required(route_name=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                messages = {
                    'history': 'Please login to view your scan history.',
                    'upload_img': 'Please login to scan and analyze products.',
                    None: 'Please login to access this feature.'
                }
                flash(messages.get(route_name, messages[None]), 'error')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return wrapper
    return decorator

def scan_qr_code(image_path):
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Unable to read image at {image_path}")
        return None
    qr_codes = decode(image)
    for qr_code in qr_codes:
        qr_data = qr_code.data.decode('utf-8')
        print(f"Decoded QR code data: {qr_data}")
        return qr_data
    print("No QR code found in the image.")
    return None

def get_product_info(gtin):
    """Fetch and extract product information from API"""
    url = f"https://world.openfoodfacts.org/api/v0/product/{gtin}.json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if 'product' in data:
            product_data = data['product']
            return {
                'name': product_data.get('product_name', 'N/A'),
                'brand': product_data.get('brands', 'N/A'),
                'serving_size': product_data.get('serving_size', 'N/A'),
                'sugar_content': product_data.get('nutriments', {}).get('sugars_100g', 'N/A'),
                'nutrition': {
                    'calories': product_data.get('nutriments', {}).get('energy-kcal_100g', 'N/A'),
                    'fat': product_data.get('nutriments', {}).get('fat_100g', 'N/A'),
                    'carbs': product_data.get('nutriments', {}).get('carbohydrates_100g', 'N/A'),
                    'protein': product_data.get('nutriments', {}).get('proteins_100g', 'N/A')
                },
                'ingredients': product_data.get('ingredients_text', 'N/A'),
                'nutriscore': product_data.get('nutriscore_grade', 'N/A').upper(),
                'image_front_url': product_data.get('image_front_url', 'N/A')
            }
        print("Product not found in the database.")
        return None
    print(f"Error fetching product information. Status code: {response.status_code}")
    return None

def calculate_health_score(product_info):
    """Calculate health score based on Nutri-Score"""
    score_map = {'A': 90, 'B': 75, 'C': 60, 'D': 45, 'E': 30}
    return score_map.get(product_info.get('nutriscore', 'E'), 30)

def classifier(score):
    """Classify product based on health score"""
    if score > 80:
        return "Safe for regular consumption"
    elif score > 60:
        return "Moderate intake recommended"
    elif score > 40:
        return "Limit consumption"
    else:
        return "Not recommended for daily use"

def is_suitable(product_info):
    """
    Predicts whether the food item is suitable for regular consumption.
    Criteria can be adjusted as per dietary guidelines or user needs.
    """
    # Extract relevant info
    nutriscore = product_info.get('nutriscore', 'E').upper()
    sugar = product_info.get('sugar_content', 'N/A')
    fat = product_info.get('nutrition', {}).get('fat', 'N/A')
    calories = product_info.get('nutrition', {}).get('calories', 'N/A')
    ingredients = product_info.get('ingredients', '').lower()

    # Convert to float if possible
    try:
        sugar = float(sugar)
    except:
        sugar = None
    try:
        fat = float(fat)
    except:
        fat = None
    try:
        calories = float(calories)
    except:
        calories = None

    # Example criteria (can be adjusted):
    # Nutri-Score should be A or B
    # Sugar < 5g/100g
    # Fat < 5g/100g
    # Calories < 150 kcal/100g
    # No artificial sweeteners or harmful additives in ingredients

    if nutriscore in ['A', 'B']:
        if (sugar is not None and sugar < 5) and \
           (fat is not None and fat < 5) and \
           (calories is not None and calories < 150):
            if "aspartame" not in ingredients and "acesulfame" not in ingredients:
                return True
    return False

def search_openfoodfacts(food_name):
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "search_terms": food_name,
        "search_simple": 1,
        "action": "process",
        "json": 1
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get('products', [])
    else:
        return []

# Route handlers
@app.route('/')
def index():
    return render_template('UI.html')

@app.route('/', methods=['POST', 'GET'])
@login_required('upload_img')
def upload_img():
    if 'img_file' not in request.files:
        print('no file selected')
        return 'No file part', 400

    file = request.files['img_file']
    
    # If no file is selected or uploaded
    if file.filename == '':
        return 'No selected file', 400
    
    # Save the file
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    
    # Initialize default values for all variables
    a = "No QR code found."
    b = ""
    c = "Not available"
    d = "Sugar content not available"
    e_calories = "N/A"
    e_fat = "N/A"
    e_carbs = "N/A"
    e_protein = "N/A"
    f = ""
    g = ""
    h = ""
    i = "Suitability assessment not available"
    scan_saved = False
    
    # Process QR code and get product information
    qr_data = scan_qr_code(file_path)
    if qr_data:
        product_info = get_product_info(qr_data)
        if product_info:
            try:
                health_score = calculate_health_score(product_info)
                # Basic info
                a = product_info['name']
                b = product_info['brand']
                c = product_info['serving_size'] if product_info['serving_size'] != 'N/A' else 'Not available'
                d = f"{product_info['sugar_content']}g per 100g" if product_info['sugar_content'] != 'N/A' else 'Sugar content not available'
                
                # Process nutrition info
                e_calories = f"{float(product_info['nutrition']['calories']):.0f}kcal" if product_info['nutrition']['calories'] != 'N/A' else 'N/A'
                e_fat = f"{float(product_info['nutrition']['fat']):.1f}g" if product_info['nutrition']['fat'] != 'N/A' else 'N/A'
                e_carbs = f"{float(product_info['nutrition']['carbs']):.1f}g" if product_info['nutrition']['carbs'] != 'N/A' else 'N/A'
                e_protein = f"{float(product_info['nutrition']['protein']):.1f}g" if product_info['nutrition']['protein'] != 'N/A' else 'N/A'
                
                # Other info
                f = product_info['ingredients']
                g = classifier(health_score)
                h = product_info['image_front_url']
                
                # Check suitability
                suitable = is_suitable(product_info)
                i = "Suitable for regular consumption" if suitable else "Not suitable for regular consumption"

                # Only save to database if we have valid product info
                if a != "No QR code found." and a != "Error processing product information":
                    try:
                        food_item = Food(
                            product_name=a,
                            brand=b,
                            serving_size=c,
                            sugar_content=d,
                            calories=e_calories,
                            fat=e_fat,
                            carbs=e_carbs,
                            protein=e_protein,
                            ingredients=f,
                            recommendation=g,
                            image_url=h,
                            is_suitable=suitable,
                            user_id=session['user_id']
                        )
                        db.session.add(food_item)
                        db.session.commit()
                        scan_saved = True
                    except Exception as e:
                        print(f"Error saving to database: {e}")
                        db.session.rollback()

            except Exception as e:
                print(f"Error processing product info: {e}")
                a = "Error processing product information"
        else:
            print("Unable to retrieve product information.")
            a = "No product information available."

    if scan_saved:
        flash('Product scan saved to your history!', 'success')
    
    return render_template('result.html', 
                         a=a, b=b, c=c, d=d, 
                         e_calories=e_calories, e_fat=e_fat, 
                         e_carbs=e_carbs, e_protein=e_protein,
                         f=f, g=g, h=h, i=i)

@app.route("/history")
@login_required('history')
def history():
    # Get all scanned foods for the current user, ordered by most recent first
    scanned_foods = Food.query.filter_by(user_id=session['user_id']).order_by(Food.scanned_at.desc()).all()
    return render_template('history.html', scanned_foods=scanned_foods)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.userid
            if remember:
                # Session will last for 30 days
                session.permanent = True
                app.permanent_session_lifetime = timedelta(days=30)
            session['user_name'] = user.name
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login_page.html')

@app.route("/signin", methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        dob_str = request.form.get('dob')
          # Validate required fields
        missing_fields = []
        if not name: missing_fields.append("Name")
        if not email: missing_fields.append("Email")
        if not password: missing_fields.append("Password")
        
        if missing_fields:
            flash(f'Please fill in the following required fields: {", ".join(missing_fields)}', 'error')
            return redirect(url_for('signin'))
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'error')
            return redirect(url_for('signin'))
        
        # Process DOB if provided
        try:
            dob = datetime.strptime(dob_str, '%Y-%m-%d') if dob_str else None
        except ValueError:
            dob = None
        
        # Create new user
        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            phone_number=phone,
            dob=dob
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating your account.', 'error')
            print(f"Error creating user: {e}")
    
    return render_template('sign_up_page.html')

@app.route("/logout")
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/search_food', methods=['POST'])
def search_food():
    data = request.get_json()
    food_name = data.get('food_name')
    if not food_name:
        return jsonify({'error': 'No food name provided'}), 400
    
    products = search_openfoodfacts(food_name)
    return jsonify({'products': products})