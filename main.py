
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
    return render_template('INDEX2.HTML')

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
    
    # Save the PDF file
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
        print("No QR code found in the image. 1")
        return None
    
    qr_data = scan_qr_code(file_path)
    
    def get_product_info(gtin):
        url = f"https://world.openfoodfacts.org/api/v0/product/{gtin}.json"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if 'product' in data:
                return data['product']
            else:
                print("Product not found in the database.")
                return None
        else:
            print(f"Error fetching product information. Status code: {response.status_code}")
            return None
    def calculate_health_score(product_data):
        # Base Score
        score = 100
        
        # Deductions
        # 1. Nutri-Score Penalty
        nutri_score_penalty = {"a":0, "b":10, "c":20, "d":30, "e":40}
        score -= nutri_score_penalty.get(product_data["nutriscore_grade"].lower(), 40)
        
        # 2. Nova Group Penalty
        score -= product_data["nova_group"] * 10  # 40 points for group 4
        
        # 3. Sugar Content
        if product_data["nutriments"]["sugars_value"] > 5:
            score -= (product_data["nutriments"]["sugars_value"] -5) * 2
        
        # 4. Additives
        score -= len(product_data["additives_tags"]) * 5
        
        # 5. Caffeine Content
        if product_data["nutriments"].get("caffeine_value",0) > 50:
            score -= 15
            
        # Bonuses
        if "en:organic" in product_data["labels_tags"]:
            score += 20
            
        return max(0, min(100, score))
    def classifier(score):
        if score > 80:
            return "Safe for regular consumption"
        elif score > 60:
            return "Moderate intake recommended"
        elif score > 40:
            return "Limit consumption"
        else:
            return "Not recommended for daily use"

    
    if qr_data:
        product_info = get_product_info(qr_data)
        if product_info:
            # Extract relevant information from the product data
            classify=calculate_health_score(product_info)
            c=classifier(classify)
            # nut=extract_nutrition(product_info)
            # print("Product Information:")
            # print(nut)
            ingredients = product_info.get('ingredients', 'N/A')
            sugar_content = product_info.get('nutriments', {}).get('sugars_100g', 'N/A')
            a = f"Estimated Sugar: {ingredients[1]['percent_estimate']}%"
            b = f"Sugar Content: {sugar_content}g per 100g"
        else:
            print("Unable to retrieve product information.")
            a = "No product information available."
            b = ""
    else:
        a = "No QR code found."
        b = ""
        c=""
    
    return render_template('INDEX2.HTML', a=a, b=b,c=c)


if __name__ == '__main__':
    app.run(debug=True)
