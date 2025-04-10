from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import random
import os
import string
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///airline.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    bookings = db.relationship('Booking', backref='user', lazy=True)

class Flight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flight_number = db.Column(db.String(10), nullable=False)
    airline = db.Column(db.String(50), nullable=False)
    departure = db.Column(db.String(50), nullable=False)
    destination = db.Column(db.String(50), nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)
    arrival_time = db.Column(db.DateTime, nullable=False)
    price = db.Column(db.Float, nullable=False)
    total_seats = db.Column(db.Integer, nullable=False, default=180)
    available_seats = db.Column(db.Integer, nullable=False)
    bookings = db.relationship('Booking', backref='flight', lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    flight_id = db.Column(db.Integer, db.ForeignKey('flight.id'), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Confirmed')
    passengers = db.Column(db.Integer, nullable=False, default=1)
    pnr = db.Column(db.String(8), unique=True, nullable=False)

class Passenger(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    passport = db.Column(db.String(20))

# Template filters and context processors
@app.template_filter('duration')
def duration_filter(delta):
    if isinstance(delta, timedelta):
        total_seconds = delta.total_seconds()
    else:
        total_seconds = delta.seconds
    
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    return f"{hours}h {minutes}m"

@app.context_processor
def inject_datetime():
    return {
        'datetime': datetime,
        'today': datetime.now().strftime('%Y-%m-%d')
    }

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Helper functions
def generate_flight_number():
    airlines = ['AI', 'UA', 'DL', 'AA', 'BA']
    return f"{random.choice(airlines)}{random.randint(100, 999)}"

def generate_flight_price():
    return round(random.uniform(5000, 15000), 2)

def generate_pnr():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def init_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
        add_sample_data()

def add_sample_data():
    cities = ['DEL', 'BOM', 'BLR', 'HYD', 'MAA', 'CCU', 'JFK', 'LAX', 'ORD', 'LHR']
    airlines = ['AirIndia', 'United', 'Delta', 'American', 'British Airways']
    
    # Add sample flights for next 30 days
    for _ in range(50):
        departure, destination = random.sample(cities, 2)
        dep_time = datetime.now() + timedelta(
            days=random.randint(1, 30),
            hours=random.randint(0, 23),
            minutes=random.choice([0, 15, 30, 45])
        )
        duration = timedelta(hours=random.randint(1, 6), minutes=random.randint(0, 59))
        
        flight = Flight(
            flight_number=generate_flight_number(),
            airline=random.choice(airlines),
            departure=departure,
            destination=destination,
            departure_time=dep_time,
            arrival_time=dep_time + duration,
            price=generate_flight_price(),
            available_seats=random.randint(5, 180)
        )
        db.session.add(flight)
    
    # Add test user only if it doesn't exist
    if not User.query.filter_by(email='test@example.com').first():
        hashed_password = generate_password_hash('test123', method='scrypt')  # Updated method
        test_user = User(
            username='testuser',
            email='test@example.com',
            password=hashed_password
        )
        db.session.add(test_user)
    
    db.session.commit()

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if not all([username, email, password]):
            flash('All fields are required', 'error')
            return redirect(url_for('signup'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('signup'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('signup'))
        
        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password, password):
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))
        
        session['user_id'] = user.id
        session['username'] = user.username
        flash('Logged in successfully!', 'success')
        return redirect(url_for('home'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

@app.route('/search-flights', methods=['GET', 'POST'])
@login_required
def search_flights():
    if request.method == 'POST':
        try:
            departure = request.form.get('departure')
            destination = request.form.get('destination')
            travel_date = request.form.get('travel_date')
            passengers = int(request.form.get('passengers', 1))
            
            # Validate inputs
            if not all([departure, destination, travel_date]):
                flash('Please fill all fields', 'error')
                return redirect(url_for('home'))
            
            if departure == destination:
                flash('Departure and destination cannot be same', 'error')
                return redirect(url_for('home'))
            
            date_obj = datetime.strptime(travel_date, '%Y-%m-%d').date()
            if date_obj < datetime.now().date():
                flash('Please select today or a future date', 'error')
                return redirect(url_for('home'))
            
            # Search for flights in database
            flights = Flight.query.filter(
                Flight.departure == departure,
                Flight.destination == destination,
                db.func.date(Flight.departure_time) == date_obj,
                Flight.available_seats >= passengers
            ).order_by(Flight.departure_time).all()
        
            # If no flights found, generate 3 sample flights
            if not flights:
                flights = []
                for i in range(3):
                    dep_time = datetime.combine(
                        date_obj,
                        datetime.strptime(f"{6+i*6}:00", "%H:%M").time()
                    )
                    duration = timedelta(hours=random.randint(1,3))
                    
                    flight = Flight(
                        flight_number=generate_flight_number(),
                        airline=random.choice(['AirIndia', 'United', 'Delta']),
                        departure=departure,
                        destination=destination,
                        departure_time=dep_time,
                        arrival_time=dep_time + duration,
                        price=generate_flight_price(),
                        available_seats=random.randint(5,50)
                    )
                    db.session.add(flight)
                    flights.append(flight)
                db.session.commit()
            
            return render_template('flights.html', 
                                flights=flights, 
                                passengers=passengers)
        
        except ValueError as e:
            flash('Invalid date format', 'error')
            return redirect(url_for('home'))
        except Exception as e:
            flash('An error occurred while searching for flights', 'error')
            return redirect(url_for('home'))
    
    return redirect(url_for('home'))

@app.route('/book-flight/<int:flight_id>')
@login_required
def book_flight(flight_id):
    try:
        flight = Flight.query.get_or_404(flight_id)
        passengers = int(request.args.get('passengers', 1))
        
        if flight.available_seats < passengers:
            flash('Not enough seats available', 'error')
            return redirect(url_for('search_flights'))
        
        return render_template('passenger_details.html', 
                            flight=flight, 
                            passengers=passengers)
    except Exception as e:
        flash('Error loading booking page', 'error')
        return redirect(url_for('home'))

@app.route('/process-booking', methods=['POST'])
@login_required
def process_booking():
    try:
        flight_id = request.form.get('flight_id')
        num_passengers = int(request.form.get('num_passengers', 0))
        
        if not flight_id or num_passengers <= 0:
            flash('Invalid booking request', 'error')
            return redirect(url_for('home'))
            
        # Check flight exists and has enough seats
        flight = Flight.query.get(flight_id)
        if not flight:
            flash('Flight not found', 'error')
            return redirect(url_for('home'))
            
        if flight.available_seats < num_passengers:
            flash('Not enough seats available', 'error')
            return redirect(url_for('flight_details', flight_id=flight_id))
        
        # Store booking details in session for payment page
        session['pending_booking'] = {
            'flight_id': flight_id,
            'num_passengers': num_passengers,
            'passengers': []
        }
        
        # Collect passenger details from form
        for i in range(1, num_passengers + 1):
            first_name = request.form.get(f'first_name_{i}', '').strip()
            last_name = request.form.get(f'last_name_{i}', '').strip()
            age = int(request.form.get(f'age_{i}', 0))
            gender = request.form.get(f'gender_{i}', '').strip()
            passport = request.form.get(f'passport_{i}', '').strip()
            
            if not first_name or not last_name or age <= 0 or not gender:
                flash('Please fill all required passenger details', 'error')
                return redirect(url_for('passenger_details', flight_id=flight_id))
                
            passenger = {
                'first_name': first_name,
                'last_name': last_name,
                'age': age,
                'gender': gender,
                'passport': passport if passport else None
            }
            session['pending_booking']['passengers'].append(passenger)
        
        return redirect(url_for('payment'))
        
    except ValueError:
        flash('Invalid input data', 'error')
        return redirect(url_for('home'))
    except Exception as e:
        flash('An error occurred while processing your booking', 'error')
        return redirect(url_for('home'))

@app.route('/payment')
@login_required
def payment():
    if 'pending_booking' not in session:
        flash('No booking to pay for', 'error')
        return redirect(url_for('home'))
    
    try:
        flight = Flight.query.get(session['pending_booking']['flight_id'])
        if not flight:
            flash('Invalid flight', 'error')
            return redirect(url_for('home'))
        
        # Create a temporary booking object for the template
        temp_booking = {
            'flight': flight,
            'pnr': generate_pnr(),  # Generate a temporary PNR for display
            'total_price': flight.price * session['pending_booking']['num_passengers']
        }
        
        return render_template('payment.html', 
                            booking=temp_booking,
                            passengers=session['pending_booking']['passengers'])
    except Exception as e:
        app.logger.error(f"Payment error: {str(e)}")
        flash('An error occurred while loading payment page', 'error')
        return redirect(url_for('home'))

@app.route('/complete-booking', methods=['POST'])
@login_required
def complete_booking():
    if 'pending_booking' not in session:
        flash('No booking to complete', 'error')
        return redirect(url_for('home'))
    
    try:
        # Start a transaction
        db.session.begin()
        
        # Check flight availability again (in case seats were taken since payment page)
        flight = Flight.query.get(session['pending_booking']['flight_id'])
        if not flight:
            flash('Flight not found', 'error')
            return redirect(url_for('home'))
            
        if flight.available_seats < session['pending_booking']['num_passengers']:
            flash('Not enough seats available', 'error')
            return redirect(url_for('flight_details', flight_id=flight.id))
        
        # Create the booking
        booking = Booking(
            user_id=session['user_id'],
            flight_id=session['pending_booking']['flight_id'],
            passengers=session['pending_booking']['num_passengers'],
            pnr=generate_pnr(),
            status='Confirmed'
        )
        
        # Add passengers
        for passenger_data in session['pending_booking']['passengers']:
            passenger = Passenger(
                booking=booking,
                first_name=passenger_data['first_name'],
                last_name=passenger_data['last_name'],
                age=passenger_data['age'],
                gender=passenger_data['gender'],
                passport=passenger_data.get('passport')
            )
            db.session.add(passenger)
        
        # Update flight seats
        flight.available_seats -= session['pending_booking']['num_passengers']
        
        db.session.add(booking)
        db.session.commit()
        
        # Clear pending booking
        session.pop('pending_booking', None)
        
        flash('Booking completed successfully!', 'success')
        return redirect(url_for('view_ticket', pnr=booking.pnr))
        
    except SQLAlchemyError as e:
        db.session.rollback()
        flash('An error occurred while completing your booking', 'error')
        return redirect(url_for('home'))
    except Exception as e:
        db.session.rollback()
        flash('An unexpected error occurred', 'error')
        return redirect(url_for('home'))

@app.route('/ticket/<pnr>')
@login_required
def view_ticket(pnr):
    booking = Booking.query.filter_by(pnr=pnr).first_or_404()
    if booking.user_id != session['user_id']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('home'))
    
    duration = booking.flight.arrival_time - booking.flight.departure_time
    return render_template('ticket.html', 
                         booking=booking,
                         duration=duration_filter(duration))

@app.route('/my-bookings')
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=session['user_id']).order_by(Booking.booking_date.desc()).all()
    return render_template('bookings.html', bookings=bookings)

@app.route('/cancel-booking/<int:booking_id>')
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != session['user_id']:
        flash('Unauthorized action', 'error')
        return redirect(url_for('my_bookings'))
    
    flight = booking.flight
    flight.available_seats += booking.passengers
    booking.status = 'Cancelled'
    
    db.session.commit()
    flash('Booking cancelled successfully', 'success')
    return redirect(url_for('my_bookings'))

if __name__ == '__main__':
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Add sample data only if database is empty
        if not Flight.query.first() and not User.query.first():
            add_sample_data()
    
    app.run(debug=True)