import json
import pandas as pd

# Load the JSON file
with open("api.json", "r") as file:
    data = json.load(file)

# Extract product information
product = data.get("product", {})
product_name = product.get("product_name", "Unknown")
quantity = product.get("quantity", "Unknown")
brands = product.get("brands", "Unknown")
categories = product.get("categories", "Unknown")
labels = product.get("labels", "Unknown")
allergens = product.get("allergens", "None")
nutriments = product.get("nutriments", {})
ingredients = product.get("ingredients", [])

# Extract nutritional values
nutrition_data = {
    "Energy (kJ)": nutriments.get("energy-kj_100g", "N/A"),
    "Energy (kcal)": nutriments.get("energy-kcal_100g", "N/A"),
    "Sugars (g)": nutriments.get("sugars_100g", "N/A"),
    "Fat (g)": nutriments.get("fat_100g", "N/A"),
    "Saturated Fat (g)": nutriments.get("saturated-fat_100g", "N/A"),
    "Salt (g)": nutriments.get("salt_100g", "N/A"),
    "Proteins (g)": nutriments.get("proteins_100g", "N/A"),
}

# Extract ingredient details
ingredient_details = []
for ingredient in ingredients:
    ingredient_details.append({
        "Ingredient": ingredient.get("text", "Unknown"),
        "Percent Estimate": ingredient.get("percent_estimate", "N/A"),
        "Vegan": ingredient.get("vegan", "Unknown"),
        "Vegetarian": ingredient.get("vegetarian", "Unknown"),
    })

# Create a DataFrame for ingredients
ingredients_df = pd.DataFrame(ingredient_details)

# Create a summary table
summary_data = {
    "Product Name": product_name,
    "Quantity": quantity,
    "Brands": brands,
    "Categories": categories,
    "Labels": labels,
    "Allergens": allergens,
    **nutrition_data,
}
summary_df = pd.DataFrame([summary_data])

# Save the data to CSV files
summary_df.to_csv("product_summary.csv", index=False)
ingredients_df.to_csv("ingredients_details.csv", index=False)

print("Data extracted and saved to product_summary.csv and ingredients_details.csv")
