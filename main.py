from flask import Flask, render_template, request
import os
from pyzbar.pyzbar import decode
import cv2
import requests

app = Flask(__name__)

# Define where uploaded PDFs will be saved
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Route to display the upload form
@app.route('/')
def index():
    return render_template('UI.html')

# Route to handle file upload
@app.route('/', methods=['POST','GET'])
def upload_img():
    if 'img_file' not in request.files:
        print('no file selected')
        return 'No file part', 400

    file = request.files['img_file']
    
    # If no file is selected or uploaded
    if file.filename == '':
        return 'No selected file', 400
    
    # Save the file
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)
    
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

    # Process QR code and get product information
    qr_data = scan_qr_code(file_path)
    
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
    
    if qr_data:
        product_info = get_product_info(qr_data)
        if product_info:
            health_score = calculate_health_score(product_info)
            a = product_info['name']
            b = product_info['brand']
            c = product_info['serving_size'] if product_info['serving_size'] != 'N/A' else 'Not available'
            d = f"{product_info['sugar_content']}g per 100g" if product_info['sugar_content'] != 'N/A' else 'Sugar content not available'
            # Split nutrition info into separate variables with proper formatting
            e_calories = f"{float(product_info['nutrition']['calories']):.0f}kcal" if product_info['nutrition']['calories'] != 'N/A' else 'N/A'
            e_fat = f"{float(product_info['nutrition']['fat']):.1f}g" if product_info['nutrition']['fat'] != 'N/A' else 'N/A'
            e_carbs = f"{float(product_info['nutrition']['carbs']):.1f}g" if product_info['nutrition']['carbs'] != 'N/A' else 'N/A'
            e_protein = f"{float(product_info['nutrition']['protein']):.1f}g" if product_info['nutrition']['protein'] != 'N/A' else 'N/A'
            f = product_info['ingredients']
            g = classifier(health_score)
            h = product_info['image_front_url']
        else:
            print("Unable to retrieve product information.")
            a = "No product information available."

    return render_template('result.html', 
                           a=a, b=b, c=c, d=d, 
                           e_calories=e_calories, e_fat=e_fat, 
                           e_carbs=e_carbs, e_protein=e_protein,
                           f=f, g=g, h=h)

if __name__ == '__main__':
    app.run(debug=True)
