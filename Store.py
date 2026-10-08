from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'real_ecommerce_super_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///real_store.db'
db = SQLAlchemy(app)

# ----------------1. قواعد البيانات (Database Models) ----------------
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
    status = db.Column(db.String(50), default='مكتمل')

# ---------------- 2. الهيكل العام للواجهة (HTML Layout) ----------------
HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>متجري الحقيقي</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">
</head>
<body class="bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark sticky-top">
      <div class="container">
        <a class="navbar-brand fw-bold" href="/">🛍️ متجري المتكامل</a>
        <div class="d-flex align-items-center">
          <a href="/cart" class="btn btn-outline-warning btn-sm me-2">
             🛒 السلة <span class="badge bg-danger">{{ session.get('cart', {})|length }}</span>
          </a>
          {% if session.get('user_id') %}
            {% if session.get('is_admin') %}
                <a href="/admin" class="btn btn-warning btn-sm me-2">لوحة التحكم</a>
            {% endif %}
            <span class="text-white me-2">أهلاً، {{ session['username'] }}</span>
            <a href="/logout" class="btn btn-outline-danger btn-sm">خروج</a>
          {% else %}
            <a href="/login" class="btn btn-outline-light btn-sm me-1">دخول</a>
            <a href="/register" class="btn btn-primary btn-sm">حساب جديد</a>
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

# ---------------- 3. الصفحات والواجهات (Routes) ----------------

# الصفحة الرئيسية
@app.route('/')
def home():
    products = Product.query.all()
    template = HTML_LAYOUT + """
    <h2 class="mb-4 text-center fw-bold">المنتجات المميزة</h2>
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
                    <a href="/add_to_cart/{{ p.id }}" class="btn btn-primary w-100 mt-2">إضافة للسلة 🛒</a>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    """
    return render_template_string(template, products=products)

# سلة التسوق
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
    <h3 class="mb-4">سلة التسوق</h3>
    {% if cart_items %}
    <div class="table-responsive bg-white p-3 rounded shadow-sm">
        <table class="table align-middle">
            <thead>
                <tr>
                    <th>المنتج</th>
                    <th>السعر</th>
                    <th>الكمية</th>
                    <th>المجموع</th>
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
            <h4>الإجمالي: <span class="text-success">${{ total }}</span></h4>
            <a href="/checkout" class="btn btn-success btn-lg">الانتقال للدفع 💳</a>
        </div>
    </div>
    {% else %}
    <div class="alert alert-warning text-center">السلة فارغة حالياً! <a href="/">تصفح المنتجات</a></div>
    {% endif %}
    """
    return render_template_string(template, cart_items=cart_items, total=total)

# إضافة منتج للسلة
@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    cart = session.get('cart', {})
    str_id = str(product_id)
    cart[str_id] = cart.get(str_id, 0) + 1
    session['cart'] = cart
    flash('تم إضافة المنتج إلى السلة!')
    return redirect(url_for('home'))

# صفحة الدفع
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash('يرجى تسجيل الدخول أولاً لإتمام عملية الشراء.')
        return redirect(url_for('login'))
        
    cart = session.get('cart', {})
    total = sum(Product.query.get(int(pid)).price * qty for pid, qty in cart.items() if Product.query.get(int(pid)))
    
    if request.method == 'POST':
        # إنشاء طلب جديد في قاعدة البيانات
        new_order = Order(user_id=session['user_id'], total_amount=total)
        db.session.add(new_order)
        db.session.commit()
        
        session['cart'] = {} # تفريغ السلة بعد الشراء
        flash('تمت عملية الدفع وتأكيد الطلب بنجاح!')
        return redirect(url_for('home'))
        
    template = HTML_LAYOUT + """
    <div class="row justify-content-center">
        <div class="col-md-6 bg-white p-4 rounded shadow-sm">
            <h3 class="mb-3">إتمام الشراء والدفع</h3>
            <p class="fs-5">المبلغ الإجمالي المطلوبة دفعها: <strong class="text-success">${{ total }}</strong></p>
            <hr>
            <form method="POST">
                <div class="mb-3">
                    <label class="form-label">الاسم على البطاقة</label>
                    <input type="text" class="form-control" required placeholder="Maryam ...">
                </div>
                <div class="mb-3">
                    <label class="form-label">رقم البطاقة (Stripe / Test Card)</label>
                    <input type="text" class="form-control" placeholder="4242 4242 4242 4242" required>
                </div>
                <div class="row mb-3">
                    <div class="col"><input type="text" class="form-control" placeholder="MM/YY" required></div>
                    <div class="col"><input type="text" class="form-control" placeholder="CVC" required></div>
                </div>
                <button type="submit" class="btn btn-success w-100 btn-lg">تأكيد الدفع الفوري</button>
            </form>
        </div>
    </div>
    """
    return render_template_string(template, total=total)

# لوحة تحكم الأدمن (إضافة منتج جديد)
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('is_admin'):
        flash('عذراً، هذه الصفحة مخصصة لمدير المتجر فقط!')
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        image_url = request.form['image_url']
        
        new_prod = Product(name=name, price=price, description=description, image_url=image_url)
        db.session.add(new_prod)
        db.session.commit()
        flash('تم إضافة المنتج الجديد للمتجر بنجاح!')
        return redirect(url_for('admin'))
        
    orders = Order.query.all()
    template = HTML_LAYOUT + """
    <h2 class="mb-4">لوحة تحكم الأدمن</h2>
    <div class="row mb-5">
        <div class="col-md-6 bg-white p-4 rounded shadow-sm">
            <h4>إضافة منتج جديد للمتجر</h4>
            <form method="POST">
                <input type="text" name="name" class="form-control mb-2" placeholder="اسم المنتج" required>
                <input type="number" step="0.01" name="price" class="form-control mb-2" placeholder="السعر ($)" required>
                <textarea name="description" class="form-control mb-2" placeholder="وصف المنتج"></textarea>
                <input type="url" name="image_url" class="form-control mb-3" placeholder="رابط صورة المنتج" required>
                <button type="submit" class="btn btn-warning w-100">نشر المنتج في المتجر</button>
            </form>
        </div>
        <div class="col-md-6">
            <h4>سجل الطلبات الواردة</h4>
            <ul class="list-group">
                {% for o in orders %}
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    طلب رقم #{{ o.id }} - المستخدم ID: {{ o.user_id }}
                    <span class="badge bg-success fs-6">${{ o.total_amount }}</span>
                </li>
                {% else %}
                <li class="list-group-item text-muted">لا يوجد طلبات حتى الآن</li>
                {% endfor %}
            </ul>
        </div>
    </div>
    """
    return render_template_string(template, orders=orders)

# الحسابات (تسجيل ودخول وخروج)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form['password'])
        # أول حساب يتم إنشاؤه يصبح مديراً تلقائياً (Admin)
        is_admin = True if User.query.count() == 0 else False
        new_user = User(username=request.form['username'], email=request.form['email'], password=hashed_pw, is_admin=is_admin)
        db.session.add(new_user)
        db.session.commit()
        flash('تم إنشاء الحساب بنجاح! يمكنك الدخول الآن.')
        return redirect(url_for('login'))
        
    template = HTML_LAYOUT + """
    <div class="row justify-content-center">
        <div class="col-md-6 bg-white p-4 rounded shadow-sm">
            <h3 class="mb-3">تسجيل حساب جديد</h3>
            <form method="POST">
                <input type="text" name="username" class="form-control mb-2" placeholder="اسم المستخدم" required>
                <input type="email" name="email" class="form-control mb-2" placeholder="البريد الإلكتروني" required>
                <input type="password" name="password" class="form-control mb-3" placeholder="كلمة السر" required>
                <button type="submit" class="btn btn-primary w-100">إنشاء الحساب</button>
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
            flash('تم تسجيل الدخول بنجاح!')
            return redirect(url_for('home'))
        flash('بيانات الدخول غير صحيحة!')
        
    template = HTML_LAYOUT + """
    <div class="row justify-content-center">
        <div class="col-md-6 bg-white p-4 rounded shadow-sm">
            <h3 class="mb-3">تسجيل الدخول</h3>
            <form method="POST">
                <input type="text" name="username" class="form-control mb-2" placeholder="اسم المستخدم" required>
                <input type="password" name="password" class="form-control mb-3" placeholder="كلمة السر" required>
                <button type="submit" class="btn btn-success w-100">دخول</button>
            </form>
        </div>
    </div>
    """
    return render_template_string(template)

@app.route('/logout')
def logout():
    session.clear()
    flash('تم تسجيل الخروج.')
    return redirect(url_for('home'))

# ---------------- 4. البدء وإضافة بيانات مبدئية ----------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Product.query.first():
            p1 = Product(name="ساعة ذكية متطورة", price=120.00, description="ساعة مقاومة للماء مع تتبع اللياقة البدنية", image_url="https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500")
            p2 = Product(name="سماعات بلوتوث", price=55.50, description="سماعات ذات جودة صوت عالية وعزل ضوضاء", image_url="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500")
            db.session.add_all([p1, p2])
            db.session.commit()
            
    app.run(host='127.0.0.1', port=8080, debug=False)
