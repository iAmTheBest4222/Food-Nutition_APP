from flask import render_template, request, redirect, url_for, flash, session, jsonify
import os
import cv2
import numpy as np
import requests
import time
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
import json
import secrets
from urllib.parse import quote, urlencode
from werkzeug.utils import secure_filename
from pyzbar.pyzbar import decode

# Import the app instance and models
from main import app, UPLOAD_FOLDER, cache
from modules import db, User, Food, SearchedFood
from functools import wraps
from sqlalchemy import or_

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Configuration for file uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize OAuth
oauth = OAuth(app)

# OAuth Configuration - Get from environment variables
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')

# OAuth Providers Configuration
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile',
        'redirect_uri': os.environ.get('GOOGLE_REDIRECT_URI', 'http://127.0.0.1:5000/login/google/callback')
    }
)

oauth.register(
    name='github',
    client_id=GITHUB_CLIENT_ID,
    client_secret=GITHUB_CLIENT_SECRET,
    access_token_url='https://github.com/login/oauth/access_token',
    access_token_params=None,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={
        'scope': 'user:email',
        'redirect_uri': os.environ.get('GITHUB_REDIRECT_URI', 'http://127.0.0.1:5000/login/github/callback')
    }
)

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

def detect_barcode_regions(image):
    """Detect potential barcode regions in an image"""
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Compute gradients
    gradX = cv2.Sobel(gray, ddepth=cv2.CV_32F, dx=1, dy=0, ksize=-1)
    gradY = cv2.Sobel(gray, ddepth=cv2.CV_32F, dx=0, dy=1, ksize=-1)

    # Subtract the y-gradient from the x-gradient
    gradient = cv2.subtract(gradX, gradY)
    gradient = cv2.convertScaleAbs(gradient)

    # Blur and threshold the image
    blurred = cv2.blur(gradient, (9, 9))
    _, thresh = cv2.threshold(blurred, 225, 255, cv2.THRESH_BINARY)

    # Construct a closing kernel and apply it to the threshold image
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 7))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # Perform a series of erosions and dilations
    closed = cv2.erode(closed, None, iterations=4)
    closed = cv2.dilate(closed, None, iterations=4)

    # Find contours in the threshold image
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    # Sort contours by area and keep the largest one
    c = max(contours, key=cv2.contourArea)
    rect = cv2.minAreaRect(c)
    box = cv2.boxPoints(rect)
    box = np.int0(box)

    return box

def scan_qr_code(image_path):
    """Enhanced barcode and QR code detection using pyzbar"""
    try:
        # Read the image
        print(f"Debug: Reading image from {image_path}")
        image = cv2.imread(image_path)
        if image is None:
            print(f"Error: Unable to read image at {image_path}")
            return None
            
        # Create debug images directory if it doesn't exist
        debug_dir = os.path.join(os.path.dirname(image_path), 'debug_images')
        os.makedirs(debug_dir, exist_ok=True)
        
        # Save original image for debugging
        cv2.imwrite(os.path.join(debug_dir, 'original.jpg'), image)
        
        # List of preprocessing methods to try
        preprocessed_images = []
        
        # Original image
        preprocessed_images.append(('original', image))
        
        # Grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        cv2.imwrite(os.path.join(debug_dir, 'grayscale.jpg'), gray)
        preprocessed_images.append(('grayscale', gray))
        
        # Gaussian blur + threshold
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cv2.imwrite(os.path.join(debug_dir, 'threshold.jpg'), thresh)
        preprocessed_images.append(('threshold', thresh))
        
        # Adaptive threshold
        adaptive_thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                              cv2.THRESH_BINARY, 11, 2)
        cv2.imwrite(os.path.join(debug_dir, 'adaptive_thresh.jpg'), adaptive_thresh)
        preprocessed_images.append(('adaptive_thresh', adaptive_thresh))
        
        # Enhanced contrast
        contrast = cv2.convertScaleAbs(gray, alpha=2.0, beta=-100)
        cv2.imwrite(os.path.join(debug_dir, 'contrast.jpg'), contrast)
        preprocessed_images.append(('contrast', contrast))
        
        # Try barcode detection with pyzbar
        for name, img in preprocessed_images:
            try:
                # Decode barcodes
                barcodes = decode(img)
                
                if barcodes:
                    for barcode in barcodes:
                        # Get the barcode data
                        barcode_data = barcode.data.decode('utf-8')
                        barcode_type = barcode.type
                        print(f"Debug: Found {barcode_type} barcode in {name} image: {barcode_data}")
                        return barcode_data
                        
            except Exception as e:
                print(f"Error processing {name} image: {str(e)}")
                continue
                
        print("Debug: No barcode found in any preprocessed image")
        return None
        
    except Exception as e:
        print(f"Error in scan_qr_code: {str(e)}")
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
    Predicts whether the food item is suitable for regular consumption using a comprehensive
    scoring system based on multiple nutritional factors and ingredients analysis.
    Returns True if the product meets health criteria, False otherwise.
    """
    # Extract all relevant nutritional info
    nutriscore = product_info.get('nutriscore', 'E').upper()
    nutrients = product_info.get('nutrition', {})
    ingredients = product_info.get('ingredients', '').lower()

    # Get nutritional values with error handling
    def safe_float(value, default=None):
        try:
            return float(value) if value != 'N/A' else default
        except (ValueError, TypeError):
            return default

    # Extract all nutritional values
    sugar = safe_float(product_info.get('sugar_content'))
    fat = safe_float(nutrients.get('fat'))
    saturated_fat = safe_float(nutrients.get('saturated-fat_100g'))
    calories = safe_float(nutrients.get('calories'))
    protein = safe_float(nutrients.get('protein'))
    fiber = safe_float(nutrients.get('fiber_100g'))
    salt = safe_float(nutrients.get('salt_100g'))

    # Initialize score components (total 100 points)
    nutriscore_score = 0  # 30 points max
    nutritional_score = 0  # 40 points max
    ingredient_score = 0   # 30 points max

    # 1. Nutri-Score Evaluation (30 points)
    nutriscore_points = {'A': 30, 'B': 24, 'C': 18, 'D': 12, 'E': 6}
    nutriscore_score = nutriscore_points.get(nutriscore, 0)

    # 2. Nutritional Criteria Evaluation (40 points)
    # Initialize sub-scores
    sugar_score = 10
    fat_score = 10
    protein_score = 10
    other_nutrients_score = 10

    # Sugar evaluation (10 points)
    if sugar is not None:
        if sugar > 15:
            sugar_score = 0
        elif sugar > 10:
            sugar_score = 4
        elif sugar > 5:
            sugar_score = 7
        # else keep maximum score

    # Fat evaluation (10 points)
    if fat is not None:
        if fat > 20:
            fat_score = 0
        elif fat > 15:
            fat_score = 4
        elif fat > 10:
            fat_score = 7
        # else keep maximum score

    # Protein evaluation (10 points)
    if protein is not None:
        if protein < 2:
            protein_score = 0
        elif protein < 5:
            protein_score = 5
        elif protein < 8:
            protein_score = 7
        # else keep maximum score

    # Other nutrients (fiber, salt) (10 points)
    if fiber is not None and fiber >= 3:
        other_nutrients_score += 2
    if salt is not None and salt < 1.5:
        other_nutrients_score += 2

    nutritional_score = sugar_score + fat_score + protein_score + other_nutrients_score

    # 3. Ingredient Analysis (30 points)
    # List of concerning ingredients
    artificial_sweeteners = ['aspartame', 'acesulfame', 'sucralose', 'saccharin']
    preservatives = ['sodium benzoate', 'potassium sorbate', 'sulfites', 'nitrites']
    harmful_additives = ['msg', 'high fructose corn syrup', 'partially hydrogenated']
    
    # Start with maximum score and deduct for concerning ingredients
    ingredient_score = 30
    
    # Check for artificial sweeteners
    if any(sweetener in ingredients for sweetener in artificial_sweeteners):
        ingredient_score -= 10
        
    # Check for preservatives
    if any(preservative in ingredients for preservative in preservatives):
        ingredient_score -= 5
        
    # Check for harmful additives
    if any(additive in ingredients for additive in harmful_additives):
        ingredient_score -= 8

    # Calculate total score
    total_score = nutriscore_score + nutritional_score + ingredient_score

    # Logging for debugging
    print(f"Nutrition Analysis:")
    print(f"NutriScore: {nutriscore} ({nutriscore_score} pts)")
    print(f"Sugar: {sugar}g ({sugar_score} pts)")
    print(f"Fat: {fat}g ({fat_score} pts)")
    print(f"Protein: {protein}g ({protein_score} pts)")
    print(f"Other Nutrients: ({other_nutrients_score} pts)")
    print(f"Ingredient Score: {ingredient_score} pts")
    print(f"Total Score: {total_score}/100")

    # Automatic disqualification conditions
    disqualifying_conditions = [
        sugar is not None and sugar > 25,  # Extremely high sugar
        saturated_fat is not None and saturated_fat > 10,  # High saturated fat
        salt is not None and salt > 2.5,  # Very high salt
        any(harmful in ingredients for harmful in ['red 40', 'yellow 5', 'yellow 6']),  # Harmful food colors
        calories is not None and calories > 400  # Extremely high calories
    ]

    if any(disqualifying_conditions):
        print("Product disqualified due to exceeding critical thresholds")
        return False

    # Final decision threshold
    SUITABILITY_THRESHOLD = 65  # Requires scoring at least 65/100 points
    return total_score >= SUITABILITY_THRESHOLD

def clean_search_term(term):
    """Normalize search term for consistent caching"""
    return term.lower().strip()

@app.route('/search_food', methods=['POST'])
def search_food():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
            
        food_name = data.get('food_name')
        if not food_name or not isinstance(food_name, str):
            return jsonify({'error': 'Invalid or missing food name'}), 400
        
        if len(food_name) < 2:
            return jsonify({'error': 'Search term must be at least 2 characters long'}), 400
        
        search_term = clean_search_term(food_name)
        
        # Try to get results from cache first
        cached_result = cache.get(f'search_{search_term}')
        if cached_result:
            return jsonify({
                'status': 'success',
                'products': cached_result,
                'source': 'cache'
            })
        
        # Try to get results from local database using chunked approach
        db_results = []
        chunk_size = 100
        offset = 0
        
        while True:
            chunk = SearchedFood.query.filter(
                or_(
                    SearchedFood.search_term.ilike(f'%{search_term}%'),
                    SearchedFood.product_name.ilike(f'%{search_term}%'),
                    SearchedFood.brands.ilike(f'%{search_term}%')
                )
            ).filter(
                SearchedFood.last_searched > datetime.utcnow() - timedelta(days=7)
            ).order_by(SearchedFood.last_searched.desc()
            ).offset(offset).limit(chunk_size).all()
            
            if not chunk:
                break
                
            db_results.extend(chunk)
            if len(chunk) < chunk_size:
                break
                
            offset += chunk_size
        
        if db_results:
            products = [product.to_dict() for product in db_results]
            # Cache with a shorter timeout for database results
            cache.set(f'search_{search_term}', products, timeout=1800)  # 30 minutes
            return jsonify({
                'status': 'success',
                'products': products,
                'source': 'database'
            })
        
        # If not in cache or db, fetch from OpenFoodFacts API
        products = search_openfoodfacts(search_term)
        
        if not products:
            return jsonify({
                'status': 'success',
                'products': [],
                'message': 'No products found'
            })
        
        # Store results in database using bulk insert
        searched_foods = []
        for product in products:
            searched_food = SearchedFood(
                product_name=product.get('product_name', ''),
                brands=product.get('brands', ''),
                code=product.get('code', ''),
                image_front_url=product.get('image_front_url', ''),
                search_term=search_term,
                nutrition_data=product
            )
            searched_foods.append(searched_food)
        
        try:
            db.session.bulk_save_objects(searched_foods)
            db.session.commit()
            # Cache the results with a longer timeout for API results
            cache.set(f'search_{search_term}', products, timeout=3600)  # 1 hour
        except Exception as e:
            print(f"Error saving search results: {e}")
            db.session.rollback()
        
        return jsonify({
            'status': 'success',
            'products': products,
            'source': 'api'
        })
        
    except Exception as e:
        print(f"Error in search_food: {e}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'error': 'An unexpected error occurred'
        }), 500

class OpenFoodFactsAPI:
    def __init__(self):
        self.base_url = "https://world.openfoodfacts.org/cgi/search.pl"
        self.session = self._create_session()

    def _create_session(self):
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            max_retries=3,
            pool_connections=20,
            pool_maxsize=20,
            pool_block=True
        )
        session.mount('https://', adapter)
        session.headers.update({
            'User-Agent': 'Foodscan/1.0 (Educational Project)',
            'Accept': 'application/json'
        })
        return session

    def search(self, food_name):
        """Search OpenFoodFacts with caching and retry logic"""
        cache_key = f'off_search_{food_name.lower().strip()}'
        
        # Try to get from cache first
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            print(f"Cache hit for search: {food_name}")
            return cached_result

        params = {
            "search_terms": food_name,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 12,
            "fields": "code,product_name,brands,image_front_url,nutriments"
        }

        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    self.base_url,
                    params=params,
                    timeout=(3.05, 15)  # (connect timeout, read timeout)
                )
                response.raise_for_status()
                
                products = response.json().get('products', [])
                
                # Cache successful results
                if products:
                    cache.set(cache_key, products, timeout=3600)  # Cache for 1 hour
                    print(f"Cached {len(products)} products for search: {food_name}")
                
                return products
                
            except requests.exceptions.Timeout:
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                print(f"Timeout on attempt {attempt + 1}, retrying in {delay}s...")
                if attempt < max_retries - 1:
                    time.sleep(delay)
                continue
                
            except requests.exceptions.RequestException as e:
                print(f"Request error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (attempt + 1))
                continue
                
            except ValueError as e:
                print(f"JSON parsing error: {e}")
                return []

        print(f"All retries failed for search: {food_name}")
        return []

# Initialize the API client
off_api = OpenFoodFactsAPI()

def search_openfoodfacts(food_name):
    """Search OpenFoodFacts API using the robust client"""
    try:
        return off_api.search(food_name)
    except Exception as e:
        print(f"Error in search_openfoodfacts: {e}")
        return []

# Route handlers
@app.route('/')
def index():
    return render_template('UI.html')

@app.route('/', methods=['POST', 'GET'])
@login_required('upload_img')
def upload_img():
    if request.method == 'GET':
        return render_template('UI.html')
        
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
    
    try:
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
    finally:
        # Clean up the uploaded file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error removing temporary file: {e}")

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

@app.route('/get_product_details', methods=['POST'])
@login_required('search')
def get_product_details():
    data = request.get_json()
    code = data.get('code')
    if not code:
        return 'No product code provided', 400

    # Get product info
    product_info = get_product_info(code)
    if not product_info:
        return 'Product not found', 404

    try:
        health_score = calculate_health_score(product_info)
        # Process the product information
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

        # Save to database
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
        except Exception as e:
            print(f"Error saving to database: {e}")
            db.session.rollback()

        return url_for('result', a=a, b=b, c=c, d=d, 
                      e_calories=e_calories, e_fat=e_fat, 
                      e_carbs=e_carbs, e_protein=e_protein,
                      f=f, g=g, h=h, i=i)

    except Exception as e:
        print(f"Error processing product info: {e}")
        return 'Error processing product information', 500

@app.route('/result')
@login_required('result')
def result():
    return render_template('result.html', 
                         a=request.args.get('a'), 
                         b=request.args.get('b'),
                         c=request.args.get('c'),
                         d=request.args.get('d'),
                         e_calories=request.args.get('e_calories'),
                         e_fat=request.args.get('e_fat'),
                         e_carbs=request.args.get('e_carbs'),
                         e_protein=request.args.get('e_protein'),
                         f=request.args.get('f'),
                         g=request.args.get('g'),
                         h=request.args.get('h'),
                         i=request.args.get('i'))

# OAuth routes
@app.route('/login/<provider>')
def oauth_login(provider):
    if provider not in ['google', 'github']:
        flash('Invalid authentication provider', 'error')
        return redirect(url_for('login'))
    
    # Store the next URL in session
    session['next_url'] = request.args.get('next') or url_for('index')
    
    redirect_uri = url_for(f'oauth_callback', provider=provider, _external=True)
    print(f"Redirect URI: {redirect_uri}")  # Debug print
    
    client = oauth.create_client(provider)
    return client.authorize_redirect(redirect_uri)

@app.route('/login/<provider>/callback')
def oauth_callback(provider):
    if provider not in ['google', 'github']:
        flash('Invalid authentication provider', 'error')
        return redirect(url_for('login'))

    try:
        client = oauth.create_client(provider)
        token = client.authorize_access_token()
        print(f"OAuth token received: {token}")  # Debug print
        
        if provider == 'google':
            userinfo = token.get('userinfo')
            if not userinfo:
                print("No userinfo in token, fetching from endpoint")
                resp = client.get('https://www.googleapis.com/oauth2/v3/userinfo')
                if not resp.ok:
                    print(f"Google API error: {resp.text}")
                    flash('Failed to get user info from Google', 'error')
                    return redirect(url_for('login'))
                userinfo = resp.json()
            
            user_info = userinfo
            user_email = user_info.get('email')
            user_name = user_info.get('name')
            
        elif provider == 'github':
            # For GitHub, get user info
            resp = client.get('user')
            user_info = resp.json()
            user_email = user_info.get('email')
            user_name = user_info.get('name') or user_info.get('login')
            
            # If email is not public, get it from the email endpoint
            if not user_email:
                resp = client.get('user/emails')
                emails = resp.json()
                primary_email = next((email['email'] for email in emails if email['primary']), None)
                user_email = primary_email

        if not user_email:
            flash('Failed to get email from OAuth provider', 'error')
            return redirect(url_for('login'))

        print(f"OAuth user info - Email: {user_email}, Name: {user_name}")  # Debug print

        # Check if user exists
        user = User.query.filter_by(email=user_email).first()
        if not user:
            # Create new user with a secure random password
            secure_password = secrets.token_urlsafe(32)
            user = User(
                name=user_name or user_email.split('@')[0],
                email=user_email,
                password=generate_password_hash(secure_password)
            )
            db.session.add(user)
            try:
                db.session.commit()
                flash('Account created successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                print(f"Error creating user: {e}")
                flash('Error creating account', 'error')
                return redirect(url_for('login'))

        # Log in the user
        session['user_id'] = user.userid
        session['user_name'] = user.name
        session.permanent = True
        flash('Logged in successfully!', 'success')
        
        next_url = session.pop('next_url', url_for('index'))
        return redirect(next_url)

    except Exception as e:
        print(f"OAuth error: {str(e)}")  # Debug print
        flash('Authentication failed. Please try again.', 'error')
        return redirect(url_for('login'))

def delete_file(filepath):
    """Safely delete a file with error handling"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
    except Exception as e:
        print(f"Warning: Could not remove file {filepath}: {e}")
    return False

def save_uploaded_file(file, allowed_extensions=None):
    """Save an uploaded file with proper validation and error handling"""
    if not file or not file.filename:
        raise ValueError('No file provided')
        
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_EXTENSIONS
        
    if not '.' in file.filename or \
       file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        raise ValueError('Invalid file type')
    
    # Create a secure filename
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{timestamp}_{filename}"
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Generate full filepath
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    
    # Save the file
    file.save(filepath)
    
    return filepath

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def secure_save_file(file, upload_folder):
    """Securely save uploaded file and return the filepath"""
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{timestamp}_{filename}"
    filepath = os.path.join(upload_folder, unique_filename)
    
    file.save(filepath)
    return filepath