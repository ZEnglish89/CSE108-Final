from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import math
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ---------- Models ----------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    saved_filters = db.Column(db.Text)

class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    origin_code = db.Column(db.String(10), nullable=False)
    origin_lat = db.Column(db.Float, nullable=False)
    origin_lng = db.Column(db.Float, nullable=False)
    
    dest_code = db.Column(db.String(10), nullable=False)
    dest_lat = db.Column(db.Float, nullable=False)
    dest_lng = db.Column(db.Float, nullable=False)
    
    distance_km = db.Column(db.Float, nullable=False)
    emissions_kg = db.Column(db.Float, nullable=False)

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    bedrooms = db.Column(db.Integer, nullable=False)
    city = db.Column(db.String(100), nullable=False)

class Airport(db.Model):
    __tablename__ = 'airport'
    
    id = db.Column(db.Integer, primary_key=True)
    iata = db.Column(db.String(3), nullable=True, index=True)
    icao = db.Column(db.String(4), nullable=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(2), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    altitude = db.Column(db.Float, nullable=True, default=0)
    type = db.Column(db.String(50), nullable=True)
    scheduled_service = db.Column(db.Boolean, default=False)
    
    @property
    def display_name(self):
        """Format for display."""
        return f"{self.iata} - {self.name} ({self.city}, {self.country})"
    
    def to_dict(self):
        """Convert to dictionary for JSON responses."""
        return {
            'iata': self.iata,
            'icao': self.icao,
            'name': self.name,
            'city': self.city,
            'country': self.country,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude': self.altitude,
            'display': self.display_name
        }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------- Helper Functions ----------
# In app.py, update the haversine function if needed:
def haversine(lat1, lon1, lat2, lon2):
    """Calculate the shortest distance between two points on Earth."""
    import math
    
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Earth radius in kilometers
    
    return c * r

def estimate_emissions(distance_km):
    """Estimate CO2 emissions for a flight."""
    return distance_km * 0.154  # kg CO2 per km.

def get_airports_dict():
    """
    Get airports in the format needed for the create_trip dropdown.
    Returns: {IATA: {"lat": latitude, "lng": longitude, "name": airport_name}}
    """
    airports = Airport.query.filter(Airport.iata.isnot(None)).all()
    airports_dict = {}
    
    for airport in airports:
        airports_dict[airport.iata] = {
            "lat": airport.latitude,
            "lng": airport.longitude,
            "name": airport.name,
            "city": airport.city,
            "country": airport.country,
            "icao": airport.icao
        }
    
    return airports_dict


# ---------- Routes ----------
@app.route("/")
@login_required
def dashboard():
    trips = Trip.query.filter_by(user_id=current_user.id).all()
    total_emissions = sum(t.emissions_kg for t in trips)
    whole_flight_emissions = total_emissions*160 #average number of passengers across all plane types.

    return render_template(
        "dashboard.html",
        trips=trips,
        total_emissions=total_emissions,
        whole_flight = whole_flight_emissions
    )

@app.route("/methodology")
@login_required
def methodology():
    return render_template("methodology.html")

@app.route("/create_trip", methods=["GET", "POST"])
@login_required
def create_trip():
    airports = get_airports_dict()
    
    if request.method == "POST":
        origin = request.form["origin"]
        dest = request.form["destination"]
        
        if origin not in airports or dest not in airports:
            return "Invalid airport selection", 400
        
        o = airports[origin]
        d = airports[dest]
        
        distance = haversine(o["lat"], o["lng"], d["lat"], d["lng"])
        emissions = estimate_emissions(distance)
        
        trip = Trip(
            user_id=current_user.id,
            origin_code=origin,
            origin_lat=o["lat"],
            origin_lng=o["lng"],
            dest_code=dest,
            dest_lat=d["lat"],
            dest_lng=d["lng"],
            distance_km=distance,
            emissions_kg=emissions
        )
        
        db.session.add(trip)
        db.session.commit()
        
        return redirect(url_for("dashboard"))
    
    return render_template("create_trip.html", airports=airports)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            return "Username already exists", 400
        
        hashed_pw = generate_password_hash(password)
        user = User(username=username, password_hash=hashed_pw)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for("dashboard"))
    
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("dashboard"))
        else:
            return "Invalid username or password", 401
    
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/api/airports/search")
def search_airports():
    """API endpoint for airport search."""
    query = request.args.get('q', '').upper().strip()
    
    if not query or len(query) < 1:
        return jsonify([])
    
    # Different search strategies
    if len(query) == 3 and query.isalpha():
        # Exact IATA code search
        results = Airport.query.filter(
            (Airport.iata == query) |
            (Airport.icao == query)
        ).limit(10).all()
    elif len(query) <= 3:
        # Partial IATA/ICAO search
        results = Airport.query.filter(
            (Airport.iata.like(f'{query}%')) |
            (Airport.icao.like(f'{query}%'))
        ).limit(15).all()
    else:
        # Search by city or name
        results = Airport.query.filter(
            (Airport.city.ilike(f'%{query}%')) |
            (Airport.name.ilike(f'%{query}%')) |
            (Airport.country.ilike(f'%{query}%'))
        ).order_by(Airport.iata.isnot(None), Airport.name).limit(20).all()
    
    airports_list = [airport.to_dict() for airport in results if airport.iata]
    return jsonify(airports_list)

@app.route("/api/airports/<iata_code>")
def get_airport(iata_code):
    """API endpoint to get specific airport details."""
    airport = Airport.query.filter_by(iata=iata_code.upper()).first()
    if not airport:
        return jsonify({"error": "Airport not found"}), 404
    
    return jsonify(airport.to_dict())


# ========== DELETE ROUTES ==========

@app.route("/delete_trip/<int:trip_id>", methods=["DELETE"])
@login_required
def delete_trip(trip_id):
    """Delete a specific trip."""
    trip = Trip.query.get_or_404(trip_id)
    
    # Ensure the trip belongs to the current user
    if trip.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        db.session.delete(trip)
        db.session.commit()
        return jsonify({"success": True, "message": "Trip deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/delete_all_trips", methods=["DELETE"])
@login_required
def delete_all_trips():
    """Delete all trips for the current user."""
    try:
        # Delete all trips for the current user
        deleted_count = Trip.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": f"Deleted {deleted_count} trips",
            "count": deleted_count
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/edit_trip/<int:trip_id>", methods=["GET", "POST"])
@login_required
def edit_trip(trip_id):
    """Edit an existing trip."""
    trip = Trip.query.get_or_404(trip_id)
    
    # Ensure the trip belongs to the current user
    if trip.user_id != current_user.id:
        return "Unauthorized", 403
    
    airports = get_airports_dict()
    
    if request.method == "POST":
        origin = request.form["origin"]
        dest = request.form["destination"]
        
        if origin not in airports or dest not in airports:
            return "Invalid airport selection", 400
        
        o = airports[origin]
        d = airports[dest]
        
        # Update trip data
        trip.origin_code = origin
        trip.origin_lat = o["lat"]
        trip.origin_lng = o["lng"]
        trip.dest_code = dest
        trip.dest_lat = d["lat"]
        trip.dest_lng = d["lng"]
        trip.distance_km = haversine(o["lat"], o["lng"], d["lat"], d["lng"])
        trip.emissions_kg = estimate_emissions(trip.distance_km)
        
        db.session.commit()
        
        return redirect(url_for("dashboard"))
    
    # Pre-select the current airports
    return render_template(
        "create_trip.html", 
        airports=airports,
        edit_mode=True,
        current_origin=trip.origin_code,
        current_dest=trip.dest_code
    )

if __name__ == "__main__":
    with app.app_context():
        # Create all database tables
        db.create_all()
        print("✅ Database tables created")
        
        # Add sample listings if none exist
        if Listing.query.count() == 0:
            print("📊 Adding sample rental listings...")
            sample_listings = [
                Listing(latitude=37.7749, longitude=-122.4194, price=3200, bedrooms=2, city="San Francisco"),
                Listing(latitude=37.7849, longitude=-122.4194, price=2800, bedrooms=1, city="San Francisco"),
                Listing(latitude=37.3382, longitude=-121.8863, price=2500, bedrooms=2, city="San Jose"),
                Listing(latitude=37.8044, longitude=-122.2712, price=2300, bedrooms=1, city="Oakland"),
                Listing(latitude=37.6879, longitude=-122.4702, price=2100, bedrooms=1, city="Daly City"),
            ]
            db.session.add_all(sample_listings)
            db.session.commit()
            print("✅ Sample listings added")
        
        # Check for airports
        airport_count = Airport.query.count()
        print(f"✈️  Airports in database: {airport_count}")
        
        if airport_count == 0:
            print("\n⚠️  WARNING: No airports found in database!")
            print("   To import airports, run:")
            print("   python import_large_airports.py import")
            print("\n   For now, adding a few default airports...")
            
            # Add default airports so the app works
            default_airports = [
                Airport(iata='LAX', icao='KLAX', name='Los Angeles International', 
                       city='Los Angeles', country='US', latitude=33.9416, longitude=-118.4085,
                       type='large_airport', scheduled_service=True),
                Airport(iata='JFK', icao='KJFK', name='John F Kennedy International',
                       city='New York', country='US', latitude=40.6413, longitude=-73.7781,
                       type='large_airport', scheduled_service=True),
                Airport(iata='LHR', icao='EGLL', name='London Heathrow',
                       city='London', country='GB', latitude=51.4700, longitude=-0.4543,
                       type='large_airport', scheduled_service=True),
                Airport(iata='DFW', icao='KDFW', name='Dallas/Fort Worth International',
                       city='Dallas', country='US', latitude=32.8998, longitude=-97.0403,
                       type='large_airport', scheduled_service=True),
                Airport(iata='SFO', icao='KSFO', name='San Francisco International',
                       city='San Francisco', country='US', latitude=37.6213, longitude=-122.3790,
                       type='large_airport', scheduled_service=True),
            ]
            db.session.add_all(default_airports)
            db.session.commit()
            print("✅ Added 5 default airports")
    
    # Start the Flask app
    print("\n🚀 Starting Flask app...")
    print("👉 Open http://localhost:5000 in your browser")
    print("👉 Press Ctrl+C to stop the server\n")
    app.run(debug=True)