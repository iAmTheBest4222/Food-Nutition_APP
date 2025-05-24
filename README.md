# Food and Nutrition Apps
### About the Project
This project empowers users to make healthier food choices. By analyzing the GTIN (Global Trade Item Number) embedded in a QR code image, we provide accurate sugar content information for food products.

Simply upload a QR code image, and the system will decode it to retrieve nutritional details. It's quick, easy, and promotes informed decision-making.

--------------------------------------------------

API Used
> https://world.openfoodfacts.org/api/v0/product/{gtin}.json


### Classify -:
| Score  Range | Label | Recommendation |
|--------------|-------|----------------|
|80-100|	Excellent|	Safe for regular consumption|
|60-79|	Good	|Moderate intake recommended|
|40-59|	Caution	|Limit consumption|
|0-39|	Avoid	|Not recommended for daily use|

### Sizing -:
|Category	|Examples	|Daily Intake Guidance|
|-----------|------------|----------------------|
|Whole Foods|	Fruits, vegetables, nuts|	Unlimited (unless allergies)|
|Minimally Processed|	Whole grains, eggs|	5-7 servings/day|
|Processed	|Bread, cheese	|Limit to 2-3 servings/day|
|Ultra-Processed|	Soda, chips|	Avoid/occasional treat




#### Things Left -:
- AI-based image recognition for non-packaged foods.
- Suggested Serving Sizes
- Visualization (Prajawal)
- Tracking History: Allow users to view their scans
- AI Agent

#### for prajawal
##### home page 
 1. what this website can do
 2. its usses
 3. how to do
 4. `search bar for searching food by name`
 5. `scan to scan img` (img input)
##### visualize result 
 result will contain -:
 - serving size
 - shugar content
##### history of users previous searches
 - product name
 - result 
 - date

# GlucoseTracker

A web application for tracking and analyzing glucose levels and food nutrition information.

## Setup

1. Clone the repository
2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Fill in your OAuth credentials and secret key
   ```bash
   cp .env.example .env
   ```

5. Setup OAuth:
   - Create a project in [Google Cloud Console](https://console.cloud.google.com)
   - Create an OAuth app in [GitHub Developer Settings](https://github.com/settings/developers)
   - Add the credentials to your `.env` file

6. Initialize the database:
```bash
flask db upgrade
```

7. Run the application:
```bash
flask run
```

## Environment Variables

The following environment variables need to be set in your `.env` file:

- `SECRET_KEY`: Your Flask secret key
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `GITHUB_CLIENT_ID`: GitHub OAuth client ID
- `GITHUB_CLIENT_SECRET`: GitHub OAuth client secret

Never commit your actual `.env` file or sensitive credentials to version control!


