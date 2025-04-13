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


