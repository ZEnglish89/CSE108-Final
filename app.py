from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import math

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

#temp airport data
AIRPORTS = {
    "DFW": {"lat": 32.8998, "lng": -97.0403},
    "SFO": {"lat": 37.6213, "lng": -122.3790},
    "LAX": {"lat": 33.9416, "lng": -118.4085},
    "JFK": {"lat": 40.6413, "lng": -73.7781},
    "BCN": {"lat": 41.2974, "lng": 2.0833},
    "LHR": {"lat": 51.4700, "lng": -0.4543},
}


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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def seed_listings():
    if Listing.query.first():
        return

    sample_listings = [
        Listing(latitude=37.7749, longitude=-122.4194, price=3200, bedrooms=2, city="San Francisco"),
        Listing(latitude=37.7849, longitude=-122.4094, price=2800, bedrooms=1, city="San Francisco"),
        Listing(latitude=37.3382, longitude=-121.8863, price=2500, bedrooms=2, city="San Jose"),
        Listing(latitude=37.8044, longitude=-122.2712, price=2300, bedrooms=1, city="Oakland"),
        Listing(latitude=37.6879, longitude=-122.4702, price=2100, bedrooms=1, city="Daly City"),
    ]

    db.session.add_all(sample_listings)
    db.session.commit()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2

    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def estimate_emissions(distance_km):
    return distance_km * 0.115  # kg CO2 per km (simple, defensible)

# ---------- Routes ----------
@app.route("/")
@login_required
def dashboard():
    trips = Trip.query.filter_by(user_id=current_user.id).all()
    total_emissions = sum(t.emissions_kg for t in trips)

    return render_template(
        "dashboard.html",
        trips=trips,
        total_emissions=total_emissions
    )

@app.route("/create_trip", methods=["GET", "POST"])
@login_required
def create_trip():
    if request.method == "POST":
        origin = request.form["origin"]
        dest = request.form["destination"]

        o = AIRPORTS[origin]
        d = AIRPORTS[dest]

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

    return render_template("create_trip.html", airports=AIRPORTS)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        hashed_pw = generate_password_hash(password)
        user = User(username=username, password_hash=hashed_pw)
        db.session.add(user)
        db.session.commit()

        return redirect(url_for("login"))

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

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_listings()
    app.run(debug=True)