from flask import Flask, render_template, request, redirect, url_for, session
from flask import flash
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import check_password_hash

from werkzeug.utils import secure_filename
import os


app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['MONGO_URI'] = 'mongodb://localhost:27017/reservetable'
mongo = PyMongo(app)

# Home page showing restaurants..................................................
@app.route('/')
def home():
    restaurants = mongo.db.restaurants.find()
    return render_template('home.html', restaurants=restaurants)
#Customer Home.....................................................................
@app.route('/customer_home')
def customer_home():
    restaurants = mongo.db.restaurants.find()
    return render_template('customer_home.html', restaurants=restaurants)

# Login Page......................................................................
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('role')  # Get role (customer/restaurant) from the form
        username = request.form['username']  # Get the username from the form
        password = request.form['password']  # Get the password from the form

        if role == "restaurant":
            # Check if restaurant exists with the provided username and password
            user = mongo.db.restaurants.find_one({"username": username, "password": password})
            if user:
                # Set session for the restaurant user and redirect to the admin dashboard
                session['username'] = user['username']
                session['role'] = 'restaurant'
                flash("login successfull", "success")
                return redirect(url_for('admin_homepage'))  # Redirect to restaurant dashboard
            else:
                flash("invalid credentials", "danger")
                return redirect(url_for('login'))  # Invalid credentials message for restaurant
        elif role == "customer":
            # Check if customer exists with the provided username and password
            user2 = mongo.db.customers.find_one({"username": username, "password": password})
            if user2:
                # Set session for the customer user and redirect to the customer dashboard
                session['username'] = user2['username']
                session['role'] = 'customer'
                flash("login successfull", "success")
                return redirect(url_for('customer_home'))  # Redirect to customer dashboard
            else:
                flash("invalid credentials", "danger")
                return redirect(url_for('login'))  # Invalid credentials message for customer
        else:
            return "Invalid role selected!"  # Role not selected or incorrect

    # Render the login page if the request is GET
    return render_template('login.html')

# Register Page for customers......................................................................................
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        number = request.form['number']

        # Check if the username or email already exists in the database
        existing_user = mongo.db.customers.find_one({"$or": [{"username": username}, {"email": email}]})

        if existing_user:
            # If the username or email is already taken, show an error message
            flash("Username or email already registered. Please try again with different credentials.", "danger")
            return redirect(url_for('register'))

        # If no existing user is found, proceed with registration
        if mongo.db.customers.insert_one({"username": username, "password": password, "email": email, "number": number}):
            flash("Registration successful", "success")
            return redirect(url_for('login'))

    return render_template('register.html')


# Register restaurant Page.................................................................................
@app.route('/register_rest', methods=['GET', 'POST'])
def register_rest():
    if request.method == 'POST':
        restname = request.form['restname']
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        number = request.form['number']
        tables = request.form['tables']  # Number of tables field

        # Check if the restaurant (email or username) is already registered
        existing_restaurant = mongo.db.restaurants.find_one({
            "$or": [
                {"email": email},
                {"username": username}
            ]
        })

        if existing_restaurant:
            flash("Restaurant with this email or username is already registered!", "danger")
            return redirect(url_for('register_rest'))

        # If not registered, proceed with the registration
        mongo.db.restaurants.insert_one({
            "restname": restname,
            "username": username,
            "password": password,
            "email": email,
            "number": number,
            "tables": tables  # Storing number of tables
        })

        flash("Registration successful!", "success")
        return redirect(url_for('login'))

    return render_template('register_rest.html')


# Admin Homepage (for restaurants)......................................................................
@app.route('/admin_homepage')
def admin_homepage():
    if session.get('role') == 'restaurant':
        restaurant = mongo.db.restaurants.find_one({"owner": session['username']})
        return render_template('admin_homepage.html', restaurant=restaurant)
    else:
        return redirect(url_for('login'))

# Admin Dashboard (for viewing bookings)..................................................................
@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') == 'restaurant':
        booking = mongo.db.bookings.find({"restaurant_owner": session['username']})
        return render_template('admin_dashboard.html', bookings=booking)
    else:
        return redirect(url_for('login'))

# deallocate table.........................................................................................
@app.route('/deallocate/<booking_id>', methods=['POST', 'GET'])
def deallocate_table(booking_id):
    if session.get('role') == 'restaurant':
        # Remove the booking from the bookings collection by its ID
        mongo.db.bookings.delete_one({"_id": ObjectId(booking_id)})
        flash("Table deallocated successfully", "success")
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('login'))

# Customer Dashboard.........................................................................................
@app.route('/customer_dashboard', methods=['GET', 'POST'])
def customer_dashboard():
    if request.method == 'POST':
        booking_id = request.form.get('booking_id')
        # Remove the booking from the bookings collection based on the ID
        mongo.db.bookings.delete_one({"_id": ObjectId(booking_id)})
        flash("Booking canceled successfully", "success")
        return redirect(url_for('customer_dashboard'))

    # Retrieve bookings for the logged-in customer
    bookings = mongo.db.bookings.find({"customer": session['username']})
    return render_template('customer_dashboard.html', bookings=bookings)


# Reserve a Table................................................................................................
@app.route('/reserve_table/<restaurants_id>', methods=['GET', 'POST'])
def reserve_table(restaurants_id):
    restaurant = mongo.db.restaurants.find_one({"_id": ObjectId(restaurants_id)})

    if request.method == 'POST':
        table_number = request.form['table_number']
        date = request.form['date']
        time = request.form['time']
        persons = request.form['persons']

        # Check if the selected table is already booked at the given date and time
        existing_booking = mongo.db.bookings.find_one({
            "restaurant_name": restaurant['restname'],
            "table_number": table_number,
            "date": date,
            "time": time
        })

        if existing_booking:
            flash("This table is already booked for the selected date and time.", "danger")
            return redirect(url_for('reserve_table', restaurants_id=restaurants_id))

        # Proceed with booking if table is available
        mongo.db.bookings.insert_one({
            "restaurant_owner": restaurant['username'],
            "restaurant_name": restaurant['restname'],
            "table_number": table_number,
            "date": date,
            "time": time,
            "persons": persons,
            "customer": session['username']
        })
        flash("Table booked successfully", "success")
        return redirect(url_for('customer_home'))

    # Fetch available tables by checking the restaurant's total tables and filtering out booked ones
    total_tables = int(restaurant.get('tables', 0))
    booked_tables = mongo.db.bookings.find({
        "restaurant_name": restaurant['restname'],
        "date": request.args.get('date', ''),  # Get the selected date if available
        "time": request.args.get('time', '')  # Get the selected time if available
    })

    # Create a list of booked table numbers
    booked_table_numbers = [booking['table_number'] for booking in booked_tables]

    # Generate a list of available tables
    available_tables = [str(i) for i in range(1, total_tables + 1) if str(i) not in booked_table_numbers]

    return render_template('reserve_table.html', restaurant=restaurant, available_tables=available_tables)


# MENU.........................................................................................................
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/menu', methods=['GET', 'POST'])
def manage_menu():
    if session.get('role') == 'restaurant':
        menu_items = mongo.db.menu.find({"restaurant_owner": session['username']})
        return render_template('menu.html', menu=menu_items)
    return redirect(url_for('login'))

@app.route('/add_menu', methods=['POST'])
def add_menu():
    if 'image' not in request.files:
        return 'No file part'
    file = request.files['image']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image_url = f"/static/uploads/{filename}"

        # Insert new menu item into the database
        mongo.db.menu.insert_one({
            "restaurant_owner": session['username'],
            "name": request.form['name'],
            "description": request.form['description'],
            "price": request.form['price'],
            "image_url": image_url
        })
        flash("menu item added successfully", "success")
        return redirect(url_for('manage_menu'))
    else:
        return 'Invalid image file'

@app.route('/edit_menu/<menu_id>', methods=['GET', 'POST'])
def edit_menu(menu_id):
    if request.method == 'POST':
        file = request.files['image']
        image_url = request.form['current_image']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = f"/static/uploads/{filename}"

        mongo.db.menu.update_one(
            {"_id": ObjectId(menu_id)},
            {"$set": {
                "name": request.form['name'],
                "description": request.form['description'],
                "price": request.form['price'],
                "image_url": image_url
            }}
        )
        flash("menu item updated successfully", "success")
        return redirect(url_for('manage_menu'))

    menu_item = mongo.db.menu.find_one({"_id": ObjectId(menu_id)})
    return render_template('edit_menu.html', menu_item=menu_item)

@app.route('/delete_menu/<menu_id>', methods=['GET'])
def delete_menu(menu_id):
    mongo.db.menu.delete_one({"_id": ObjectId(menu_id)})
    flash("menu item deleted successfully", "success")
    return redirect(url_for('manage_menu'))


#customer view of menu....................................................
@app.route('/view_menu/<restaurant_id>', methods=['GET'])
def view_menu(restaurant_id):
    restaurant = mongo.db.restaurants.find_one({"_id": ObjectId(restaurant_id)})
    if restaurant:
        menu_items = mongo.db.menu.find({"restaurant_owner": restaurant['username']})
        return render_template('restaurant_menu.html', restaurant=restaurant, menu_items=menu_items)
    else:
        flash("Restaurant not found", "danger")
        return redirect(url_for('customer_dashboard'))

# About Page.....................................................................
@app.route('/about')
def about():
    return render_template('about.html')

# Contact Us Page................................................................
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Extract form data
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        
        # Insert data into MongoDB
        contact_data = {
            'name': name,
            'email': email,
            'message': message
        }
        mongo.db.contact_queries.insert_one(contact_data)
        
        # Flash a success message
        flash("Your query has been submitted successfully! Please be patient, our team is working on it.", "success")
        return redirect(url_for('contact'))
    
    return render_template('contact.html')








if __name__ == '__main__':
    app.run(debug=True)
