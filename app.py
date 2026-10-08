from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_fallback_secret_key_12345')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///real_store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------- 1. Database Models ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(200), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='Completed')

# Auto-initialize DB before handling the first request
@app.before_request
def initialize_database_once():
    if not getattr(app, '_got_first_request', False):
        db.create_all()
        if not Product.query.first():
            p1 = Product(
                name="Smart Watch Pro", 
                price=120.00, 
                description="Water-resistant smartwatch with fitness tracking.", 
                image_url="https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500"
            )
            p2 = Product(
                name="Wireless Headphones", 
                price=55.50, 
                description="High-quality noise-canceling bluetooth headphones.", 
                image_url="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500"
            )
            db.session.add_all([p1, p2])
            db.session.commit()
        app._got_first_request = True

# ---------------- 2. HTML Base Layout ----------------
HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>E-Commerce MVP</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark sticky-top">
      <div class="container">
        <a class="navbar-brand fw-bold" href="/">🛍️ TechStore</a>
        <div class="d-flex align-items-center">
          <a href="/cart" class="btn btn-outline-warning btn-sm me-2">
             🛒 Cart <span class="badge bg-danger">{{ session.get('cart', {})|length }}</span>
          </a>
          {% if session.get('user_id') %}
            {% if session.get('is_admin') %}
                <a href="/admin" class="btn btn-warning btn-sm me-2">Admin Panel</a>
            {% endif %}
            <span class="text-white me-2">Welcome, {{ session['username'] }}</span>
            <a href="/logout" class="btn btn-outline-danger btn-sm">Logout</a>
          {% else %}
            <a href="/login" class="btn btn-outline-light btn-sm me-1">Login</a>
            <a href="/register" class="btn btn-primary btn-sm">Register</a>
          {% endif %}
        </div>
      </div>
    </nav>

    <div class="container my-4">
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for msg in messages %}
              <div class="alert alert-info alert-dismissible fade show" role="alert">
                {{ msg }}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

# ---------------- 3. Routes ----------------
@app.route('/')
def home():
    products = Product.query.all()
    template = HTML_LAYOUT + """
    <h2 class="mb-4 text-center fw-bold">Featured Products</h2>
    <div class="row">
        {% for p in products %}
        <div class="col-12 col-md-4 mb-4">
            <div class="card shadow-sm h-100 border-0">
                <img src="{{ p.image_url }}" class="card-img-top" style="height: 220px; object-fit: cover;">
                <div class="card-body d-flex flex-column justify-content-between">
                    <div>
                        <h5 class="card-title fw-bold">{{ p.name }}</h5>
                        <p class="card-text text-muted small">{{ p.description }}</p>
                        <p class="card-text text-success fs-5 fw-bold">${{ p.price }}</p>
                    </div>
                    <a href="/add_to_cart/{{ p.id }}" class="btn btn-primary w-100 mt-2">Add to Cart 🛒</a>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    """
    return render_template_string(template, products=products)

@app.route('/cart')
def view_cart():
    cart = session.get('cart', {})
    cart_items = []
    total = 0
    for product_id, quantity in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            item_total = product.price * quantity
            total += item_total
            cart_items.append({'product': product, 'quantity': quantity, 'item_total': item_total})
            
    template = HTML_LAYOUT + """
    <h3 class="mb-4">Your Shopping Cart</h3>
    {% if cart_items %}
    <div class="table-responsive bg-white p-3 rounded shadow-sm">
        <table class="table align-middle">
            <thead>
                <tr>
                    <th>Product</th>
                    <th>Price</th>
                    <th>Quantity</th>
                    <th>Subtotal</th>
                </tr>
            </thead>
            <tbody>
                {% for item in cart_items %}
                <tr>
                    <td>{{ item.product.name }}</td>
                    <td>${{ item.product.price }}</td>
                    <td>{{ item.quantity }}</td>
                    <td>${{ item.item_total }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <hr>
        <div class="d-flex justify-content-between align-items-center">
            <h4>Total: <span class="text-success">${{ total }}</span></h4>
            <a href="/checkout" class="btn btn-success btn-lg">Proceed to Checkout 💳</a>
        </div>
    </div>
    {% else %}
    <div class="alert alert-warning text-center">Your cart is currently empty! <a href="/">Browse Products</a></div>
    {% endif %}
    """
    return render_template_string(template, cart_items=cart_items, total=total)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    cart = session.get('cart', {})
    str_id = str(product_id)
    cart[str_id] = cart.get(str_id, 0) + 1
    session['cart'] = cart
    flash('Item added to cart successfully!')
    return redirect(url_for('home'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash('Please login to complete your purchase.')
        return redirect(url_for('login'))
        
    cart = session.get('cart', {})
    total = sum(Product.query.get(int(pid)).price * qty for pid, qty in cart.items() if Product.query.get(int(pid)))
    
    if request.method == 'POST':
        new_order = Order(user_id=session['user_id'], total_amount=total)
        db.session.add(new_order)
        db.session.commit()
        
        session['cart'] = {}
        flash('Payment successful! Your order has been placed.')
        return redirect(url_for('home'))
        
    template = HTML_LAYOUT + """
    <div class="row justify-content-center">
        <div class="col-md-6 bg-white p-4 rounded shadow-sm">
            <h3 class="mb-3">Checkout & Payment</h3>
            <p class="fs-5">Total Amount Due: <strong class="text-success">${{ total }}</strong></p>
            <hr>
            <form method="POST">
                <div class="mb-3">
                    <label class="form-label">Name on Card</label>
                    <input type="text" class="form-control" required placeholder="John Doe">
                </div>
                <div class="mb-3">
                    <label class="form-label">Card Number (Test / Mock)</label>
                    <input type="text" class="form-control" placeholder="4242 4242 4242 4242" required>
                </div>
                <div class="row mb-3">
                    <div class="col"><input type="text" class="form-control" placeholder="MM/YY" required></div>
                    <div class="col"><input type="text" class="form-control" placeholder="CVC" required></div>
                </div>
                <button type="submit" class="btn btn-success w-100 btn-lg">Complete Payment</button>
            </form>
        </div>
    </div>
    """
    return render_template_string(template, total=total)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('is_admin'):
        flash('Access restricted to administrators only!')
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        image_url = request.form['image_url']
        
        new_prod = Product(name=name, price=price, description=description, image_url=image_url)
        db.session.add(new_prod)
        db.session.commit()
        flash('New product published successfully!')
        return redirect(url_for('admin'))
        
    orders = Order.query.all()
    template = HTML_LAYOUT + """
    <h2 class="mb-4">Admin Dashboard</h2>
    <div class="row mb-5">
        <div class="col-md-6 bg-white p-4 rounded shadow-sm">
            <h4>Add New Product</h4>
            <form method="POST">
                <input type="text" name="name" class="form-control mb-2" placeholder="Product Name" required>
                <input type="number" step="0.01" name="price" class="form-control mb-2" placeholder="Price ($)" required>
                <textarea name="description" class="form-control mb-2" placeholder="Product Description"></textarea>
                <input type="url" name="image_url" class="form-control mb-3" placeholder="Image URL" required>
                <button type="submit" class="btn btn-warning w-100">Publish Product</button>
            </form>
        </div>
        <div class="col-md-6">
            <h4>Recent Customer Orders</h4>
            <ul class="list-group">
                {% for o in orders %}
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    Order #{{ o.id }} - User ID: {{ o.user_id }}
                    <span class="badge bg-success fs-6">${{ o.total_amount }}</span>
                </li>
                {% else %}
                <li class="list-group-item text-muted">No orders found yet.</li>
                {% endfor %}
            </ul>
        </div>
    </div>
    """
    return render_template_string(template, orders=orders)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form['password'])
        is_admin = True if User.query.count() == 0 else False
        new_user = User(username=request.form['username'], email=request.form['email'], password=hashed_pw, is_admin=is_admin)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully! Please log in.')
        return redirect(url_for('login'))
        
    template = HTML_LAYOUT + """
    <div class="row justify-content-center">
        <div class="col-md-6 bg-white p-4 rounded shadow-sm">
            <h3 class="mb-3">Create an Account</h3>
            <form method="POST">
                <input type="text" name="username" class="form-control mb-2" placeholder="Username" required>
                <input type="email" name="email" class="form-control mb-2" placeholder="Email Address" required>
                <input type="password" name="password" class="form-control mb-3" placeholder="Password" required>
                <button type="submit" class="btn btn-primary w-100">Register</button>
            </form>
        </div>
    </div>
    """
    return render_template_string(template)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            flash('Logged in successfully!')
            return redirect(url_for('home'))
        flash('Invalid username or password!')
        
    template = HTML_LAYOUT + """
    <div class="row justify-content-center">
        <div class="col-md-6 bg-white p-4 rounded shadow-sm">
            <h3 class="mb-3">Account Login</h3>
            <form method="POST">
                <input type="text" name="username" class="form-control mb-2" placeholder="Username" required>
                <input type="password" name="password" class="form-control mb-3" placeholder="Password" required>
                <button type="submit" class="btn btn-success w-100">Login</button>
            </form>
        </div>
    </div>
    """
    return render_template_string(template)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=False)
