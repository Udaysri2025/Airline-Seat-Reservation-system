from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask import jsonify
import random
import os
import string
import logging
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
from flask import send_file  # Make sure this is added at the top


app = Flask(__name__)
app.config['WTF_CSRF_SECRET_KEY'] = os.urandom(24)
# Set the secret key from environment variable (better for production)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# Enable secure session cookies (only over HTTPS)
app.config['SESSION_COOKIE_SECURE'] = True  # Ensure this only works over HTTPS in production

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)  # Session expires after 2 hours

# Database configuration
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
    passenger_count = db.Column(db.Integer, nullable=False, default=1)  # Count of passengers
    pnr = db.Column(db.String(8), unique=True, nullable=False)
    passengers = db.relationship('Passenger', backref='booking', lazy=True)  # List of passenger objects

class Passenger(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    passport = db.Column(db.String(20))
    seat_number = db.Column(db.String(10))  # Added seat_number column

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
        
        # Use 'pbkdf2:sha256' instead of just 'sha256'
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
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
            return render_template('passenger_details.html', error='Invalid booking request', flight=None)

        flight = Flight.query.get(flight_id)
        if not flight:
            return render_template('passenger_details.html', error='Flight not found', flight=None)

        if flight.available_seats < num_passengers:
            return render_template('passenger_details.html', error='Not enough seats available', flight=flight)

        passengers = []
        for i in range(1, num_passengers + 1):
            first_name = request.form.get(f'first_name_{i}', '').strip()
            last_name = request.form.get(f'last_name_{i}', '').strip()
            age = request.form.get(f'age_{i}', '0').strip()
            gender = request.form.get(f'gender_{i}', '').strip()
            passport = request.form.get(f'passport_{i}', '').strip()

            if not first_name or not last_name or not age.isdigit() or int(age) <= 0 or not gender:
                return render_template('passenger_details.html', error=f'Fill all details for passenger {i}', flight=flight)

            passengers.append({
                'first_name': first_name,
                'last_name': last_name,
                'age': int(age),
                'gender': gender,
                'passport': passport if passport else None
            })

        session['pending_booking'] = {
            'flight_id': flight_id,
            'num_passengers': num_passengers,
            'passengers': passengers
        }

        return redirect(url_for('payment'))

    except Exception as e:
        print(f"[ERROR] process_booking: {e}")
        return render_template('passenger_details.html', error='Unexpected error occurred', flight=None)

@app.route('/payment')
@login_required
def payment():
    if 'pending_booking' not in session:
        return render_template('passenger_details.html', error='No booking data found', flight=None)

    try:
        booking_data = session['pending_booking']
        flight = Flight.query.get(booking_data['flight_id'])

        if not flight:
            return render_template('passenger_details.html', error='Flight not found', flight=None)

        temp_booking = {
            'flight': flight,
            'pnr': generate_pnr(),
            'total_price': flight.price * booking_data['num_passengers'],
            'passengers': booking_data['passengers']
        }

        return render_template('payment.html', booking=temp_booking, flight=flight, total_price=temp_booking['total_price'])

    except Exception as e:
        print(f"[ERROR] payment: {e}")
        return render_template('passenger_details.html', error='Failed to load payment page', flight=None)

@app.route('/complete-booking', methods=['POST'])
@login_required
def complete_booking():
    if 'pending_booking' not in session:
        flash('No booking to complete', 'error')
        return redirect(url_for('payment'))

    try:
        booking_data = session['pending_booking']
        flight = db.session.get(Flight, booking_data['flight_id'])  # Updated to session.get()
        
        if not flight:
            flash('Flight not found', 'error')
            return redirect(url_for('payment'))

        # Create the booking
        booking = Booking(
            user_id=session['user_id'],
            flight_id=flight.id,
            passenger_count=booking_data['num_passengers'],  # Use passenger_count
            pnr=generate_pnr(),
            status='Confirmed'
        )

        db.session.add(booking)
        db.session.flush()

        # Add passengers
        for passenger_data in booking_data['passengers']:
            passenger = Passenger(
                booking_id=booking.id,
                first_name=passenger_data['first_name'],
                last_name=passenger_data['last_name'],
                age=passenger_data['age'],
                gender=passenger_data['gender'],
                passport=passenger_data.get('passport')
            )
            db.session.add(passenger)

        flight.available_seats -= booking_data['num_passengers']
        db.session.commit()
        session.pop('pending_booking', None)

        # FIX APPLIED HERE: Redirect instead of render
        return redirect(url_for('view_ticket', pnr=booking.pnr))

    except Exception as e:
        db.session.rollback()
        print(f"Booking error: {str(e)}")
        flash('Failed to complete booking', 'error')
        return redirect(url_for('payment'))

@app.route('/ticket/<pnr>')
@login_required
def view_ticket(pnr):
    try:
        booking = db.session.query(Booking).options(
            db.joinedload(Booking.flight),
            db.joinedload(Booking.passengers)
        ).filter_by(pnr=pnr).first()

        if not booking or booking.user_id != session['user_id']:
            flash('Ticket not found or unauthorized', 'error')
            return redirect(url_for('my_bookings'))

        duration = booking.flight.arrival_time - booking.flight.departure_time
        total_price = booking.flight.price * booking.passenger_count  # Use passenger_count

        return render_template('ticket.html',
                            booking=booking,
                            flight=booking.flight,
                            passengers=booking.passengers,
                            duration=duration_filter(duration),
                            total_price=total_price)

    except Exception as e:
        print(f"Ticket error: {str(e)}")
        flash('Failed to load ticket', 'error')
        return redirect(url_for('my_bookings'))

@app.route('/ticket/<pnr>/download')
@login_required
def download_ticket(pnr):
    booking = db.session.query(Booking).filter_by(pnr=pnr).first()
    if not booking or booking.user_id != session['user_id']:
        flash('Unauthorized access or ticket not found', 'error')
        return redirect(url_for('my_bookings'))

    passengers = Passenger.query.filter_by(booking_id=booking.id).all()
    duration = booking.flight.arrival_time - booking.flight.departure_time
    total_price = booking.flight.price * booking.passenger_count  # Changed to passenger_count

    # Generate QR code
    import qrcode
    import base64
    from io import BytesIO

    qr_data = f"PNR:{booking.pnr}"
    qr_img = qrcode.make(qr_data)
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode('utf-8')

    rendered = render_template('ticket_pdf.html',
                               booking=booking,
                               passengers=passengers,
                               duration=duration_filter(duration),
                               total_price=total_price,
                               qr_code=qr_base64)

    from xhtml2pdf import pisa
    pdf = BytesIO()
    pisa_status = pisa.CreatePDF(rendered, dest=pdf)

    if pisa_status.err:
        return "PDF generation error", 500

    pdf.seek(0)
    return send_file(pdf, download_name=f"ticket_{pnr}.pdf", as_attachment=True)

@app.route('/checkin/<pnr>', methods=['GET', 'POST'])
@login_required
def checkin(pnr):
    # Get booking with flight and passenger data
    booking = db.session.query(Booking).options(
        db.joinedload(Booking.flight),
        db.joinedload(Booking.passengers)
    ).filter_by(pnr=pnr).first()
    
    if not booking or booking.user_id != session['user_id']:
        flash("Unauthorized access or booking not found", "error")
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            # Update booking status to Checked-In
            booking.status = 'Checked-In'
            db.session.commit()
            
            # Redirect to seats page after successful check-in
            return redirect(url_for('select_seats', pnr=pnr))
            
        except Exception as e:
            db.session.rollback()
            flash("Failed to complete check-in", "error")
            return redirect(url_for('checkin', pnr=pnr))

    # GET request - show check-in page
    return render_template('check_in.html',
                         booking=booking,
                         passengers=booking.passengers)

# ====== NEW CHECK-IN ROUTES ======
@app.route('/verify-checkin', methods=['POST'])
def verify_checkin():
    pnr = request.form.get('pnr', '').upper().strip()
    last_name = request.form.get('last_name', '').strip()
    
    if not pnr or not last_name:
        flash('Please fill all fields', 'error')
        # Pass the pnr back if it exists
        return redirect(url_for('checkin', pnr=pnr if pnr else None))
    
    booking = db.session.query(Booking).options(
        db.joinedload(Booking.passengers)
    ).filter_by(pnr=pnr).first()
    
    if not booking:
        flash('Invalid PNR number', 'error')
        return redirect(url_for('checkin', pnr=pnr))
    
    if not any(p.last_name.lower() == last_name.lower() for p in booking.passengers):
        flash('Last name does not match booking', 'error')
        return redirect(url_for('checkin', pnr=pnr))
    
    session['checkin_pnr'] = pnr
    session['checkin_last_name'] = last_name
    return redirect(url_for('select_seats', pnr=pnr))

@app.route('/select-seats/<pnr>')
@login_required
def select_seats(pnr):
    booking = db.session.query(Booking).options(
        db.joinedload(Booking.passengers)
    ).filter_by(pnr=pnr).first()
    
    if not booking or booking.user_id != session['user_id']:
        flash("Invalid booking reference", "error")
        return redirect(url_for('index'))
    
    reserved_seats = [p.seat_number for p in booking.passengers if p.seat_number]
    
    return render_template('seats.html',
                        booking=booking,
                        num_passengers=booking.passenger_count,
                        reserved_seats=reserved_seats)

@app.route('/save-seats', methods=['POST'])
def save_seats():
    try:
        data = request.get_json()
        pnr = data['pnr']
        seats = data['seats']
        
        booking = Booking.query.filter_by(pnr=pnr).first()
        if not booking:
            return jsonify({'success': False, 'error': 'Booking not found'})
        
        # Assign seats to passengers
        for i, passenger in enumerate(booking.passengers):
            if i < len(seats):
                passenger.seat_number = seats[i]
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'redirect_url': url_for('boarding_pass', pnr=pnr)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/boarding-pass/<pnr>')
@login_required
def boarding_pass(pnr):
    booking = db.session.query(Booking).options(
        db.joinedload(Booking.flight),
        db.joinedload(Booking.passengers)  # This ensures passengers are loaded
    ).filter_by(pnr=pnr).first()

    if not booking or booking.user_id != session['user_id']:
        flash("Invalid booking reference", "error")
        return redirect(url_for('index'))

    # Calculate flight duration
    duration = booking.flight.arrival_time - booking.flight.departure_time
    hours, remainder = divmod(duration.seconds, 3600)
    minutes = remainder // 60
    duration_str = f"{hours}h {minutes}m"

    # Generate random gate number
    gate = f"{random.choice(['A', 'B', 'C'])}{random.randint(1, 30)}"

    return render_template('boarding_pass.html',
                         booking=booking,
                         duration=duration_str,
                         gate=gate)

if __name__ == '__main__':
    with app.app_context():
        # Force recreate database
        db.drop_all()
        db.create_all()
        add_sample_data()
        print("Database recreated successfully!")
    
    app.run(debug=True)  # Run in debug mode to see errors