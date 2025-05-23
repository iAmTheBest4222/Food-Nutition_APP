from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    """User model for storing user details"""
    __tablename__ = 'users'

    userid = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Store hashed password
    phone_number = db.Column(db.String(15))
    dob = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with Food model
    scanned_foods = db.relationship('Food', backref='scanned_by', lazy=True)

    def __repr__(self):
        return f'<User {self.name}>'

class Food(db.Model):
    """Food model for storing scanned food information"""
    __tablename__ = 'foods'

    food_id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(100))
    serving_size = db.Column(db.String(50))
    sugar_content = db.Column(db.String(50))
    
    # Nutritional information
    calories = db.Column(db.String(20))
    fat = db.Column(db.String(20))
    carbs = db.Column(db.String(20))
    protein = db.Column(db.String(20))
    
    ingredients = db.Column(db.Text)
    recommendation = db.Column(db.String(200))
    image_url = db.Column(db.String(500))
    is_suitable = db.Column(db.Boolean)
    
    # Timestamps
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign key to User
    user_id = db.Column(db.Integer, db.ForeignKey('users.userid'), nullable=False)

    def __repr__(self):
        return f'<Food {self.product_name}>'

    @property
    def nutritional_info(self):
        """Return formatted nutritional information"""
        return {
            'calories': self.calories,
            'fat': self.fat,
            'carbs': self.carbs,
            'protein': self.protein
        }
