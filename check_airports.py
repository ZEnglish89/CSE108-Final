# check_airports.py
from app import app, db, Airport

with app.app_context():
    # Count airports
    count = Airport.query.count()
    print(f"✅ Total airports in database: {count}")
    
    # List first 20 airports
    print("\n📋 First 20 airports:")
    airports = Airport.query.order_by(Airport.iata).limit(20).all()
    
    for airport in airports:
        print(f"{airport.iata} - {airport.name} ({airport.city}, {airport.country})")
    
    # Show some statistics
    print(f"\n📊 Statistics:")
    print(f"  - USA airports: {Airport.query.filter_by(country='US').count()}")
    print(f"  - UK airports: {Airport.query.filter_by(country='GB').count()}")
    print(f"  - Canadian airports: {Airport.query.filter_by(country='CA').count()}")