from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///bus_booking.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ─── Models ───────────────────────────────────────────────────────────────────

class User(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(100), nullable=False)
    email    = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role     = db.Column(db.String(10), default='user')   # 'user' | 'admin'
    bookings = db.relationship('Booking', backref='user', lazy=True)

class Bus(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    origin      = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    departure   = db.Column(db.String(50),  nullable=False)
    seats       = db.Column(db.Integer, default=40)
    price       = db.Column(db.Float,   nullable=False)
    bookings    = db.relationship('Booking', backref='bus', lazy=True)

class Booking(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bus_id     = db.Column(db.Integer, db.ForeignKey('bus.id'),  nullable=False)
    seats      = db.Column(db.Integer, nullable=False)
    booked_at  = db.Column(db.DateTime, default=datetime.utcnow)
    status     = db.Column(db.String(20), default='confirmed')

# ─── Helpers ──────────────────────────────────────────────────────────────────

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated

# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name     = request.form['name'].strip()
        email    = request.form['email'].strip().lower()
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
        hashed = generate_password_hash(password)
        db.session.add(User(name=name, email=email, password=hashed))
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email'].strip().lower()
        password = request.form['password']
        user     = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['name']    = user.name
            session['role']    = user.role
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('admin_dashboard') if user.role == 'admin' else url_for('home'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

# ─── User Routes ──────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def home():
    origin      = request.args.get('origin', '').strip()
    destination = request.args.get('destination', '').strip()
    buses = Bus.query
    if origin:
        buses = buses.filter(Bus.origin.ilike(f'%{origin}%'))
    if destination:
        buses = buses.filter(Bus.destination.ilike(f'%{destination}%'))
    buses = buses.all()
    return render_template('home.html', buses=buses, origin=origin, destination=destination)

@app.route('/book/<int:bus_id>', methods=['GET', 'POST'])
@login_required
def book(bus_id):
    bus = Bus.query.get_or_404(bus_id)
    booked_seats = sum(b.seats for b in bus.bookings if b.status == 'confirmed')
    available    = bus.seats - booked_seats
    if request.method == 'POST':
        seats = int(request.form['seats'])
        if seats < 1 or seats > available:
            flash(f'Only {available} seats available.', 'danger')
            return redirect(url_for('book', bus_id=bus_id))
        db.session.add(Booking(user_id=session['user_id'], bus_id=bus_id, seats=seats))
        db.session.commit()
        flash('Booking confirmed!', 'success')
        return redirect(url_for('my_bookings'))
    return render_template('book.html', bus=bus, available=available)

@app.route('/my-bookings')
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=session['user_id']).order_by(Booking.booked_at.desc()).all()
    return render_template('my_bookings.html', bookings=bookings)

@app.route('/cancel/<int:booking_id>', methods=['POST'])
@login_required
def cancel(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != session['user_id']:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('my_bookings'))
    booking.status = 'cancelled'
    db.session.commit()
    flash('Booking cancelled.', 'info')
    return redirect(url_for('my_bookings'))

# ─── Admin Routes ─────────────────────────────────────────────────────────────

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    users    = User.query.count()
    bookings = Booking.query.count()
    buses    = Bus.query.count()
    recent   = Booking.query.order_by(Booking.booked_at.desc()).limit(10).all()
    return render_template('admin_dashboard.html', users=users, bookings=bookings, buses=buses, recent=recent)

@app.route('/admin/buses', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_buses():
    if request.method == 'POST':
        db.session.add(Bus(
            name        = request.form['name'],
            origin      = request.form['origin'],
            destination = request.form['destination'],
            departure   = request.form['departure'],
            seats       = int(request.form['seats']),
            price       = float(request.form['price'])
        ))
        db.session.commit()
        flash('Bus added successfully.', 'success')
        return redirect(url_for('admin_buses'))
    buses = Bus.query.all()
    return render_template('admin_buses.html', buses=buses)

@app.route('/admin/buses/delete/<int:bus_id>', methods=['POST'])
@login_required
@admin_required
def delete_bus(bus_id):
    bus = Bus.query.get_or_404(bus_id)
    db.session.delete(bus)
    db.session.commit()
    flash('Bus deleted.', 'info')
    return redirect(url_for('admin_buses'))

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin_users.html', users=users)

# ─── Init ─────────────────────────────────────────────────────────────────────

def seed():
    """Add a default admin and sample buses if DB is empty."""
    if not User.query.filter_by(role='admin').first():
        db.session.add(User(
            name     = 'Admin',
            email    = 'admin@busbooking.com',
            password = generate_password_hash('Admin@123'),
            role     = 'admin'
        ))
    if Bus.query.count() == 0:
        sample = [
            Bus(name='Kerala Express',  origin='Kochi',      destination='Trivandrum', departure='08:00 AM', seats=40, price=250),
            Bus(name='Malabar Travels', origin='Kozhikode',  destination='Kochi',      departure='10:30 AM', seats=35, price=180),
            Bus(name='City Liner',      origin='Trivandrum', destination='Thrissur',   departure='06:00 AM', seats=45, price=320),
        ]
        db.session.add_all(sample)
    db.session.commit()

with app.app_context():
    db.create_all()
    seed()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
