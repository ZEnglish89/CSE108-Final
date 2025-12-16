#!/usr/bin/env python3
"""
Add Merced Regional Airport (MCE) to the database.
Updated to match your Airport model.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Airport

def add_merced_airport():
    """Add Merced Regional Macready Field airport."""
    
    with app.app_context():
        # Check if MCE already exists
        existing = Airport.query.filter_by(iata='MCE').first()
        
        if existing:
            print("✅ MCE (Merced Regional) already exists in database:")
            print(f"   Name: {existing.name}")
            print(f"   City: {existing.city}, {existing.country}")
            return True
        
        # Create Merced airport - MATCHING YOUR MODEL
        merced = Airport(
            iata='MCE',
            icao='KMCE',
            name='Merced Regional Macready Field',
            city='Merced',
            country='US',
            latitude=37.284698,
            longitude=-120.514,
            altitude=155 * 0.3048,  # Convert feet to meters
            type='medium_airport',
            scheduled_service=True
            # Note: No 'ident', 'continent', or 'region' fields based on your model
        )
        
        try:
            db.session.add(merced)
            db.session.commit()
            print("✅ Successfully added Merced Regional Airport (MCE)")
            print(f"   IATA: MCE")
            print(f"   ICAO: KMCE")
            print(f"   Name: {merced.name}")
            print(f"   Location: {merced.city}, {merced.country}")
            print(f"   Coordinates: {merced.latitude:.6f}, {merced.longitude:.6f}")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error adding Merced airport: {e}")
            return False

def verify_airport_model():
    """Check what fields the Airport model actually has."""
    with app.app_context():
        print("\n🔍 Checking Airport model structure...")
        
        # Get column names
        import inspect
        columns = [c.key for c in inspect.getmembers(Airport) 
                  if hasattr(c, 'key') and isinstance(c, db.Column)]
        
        print(f"Airport model has {len(columns)} columns:")
        for col in columns:
            print(f"  - {col}")
        
        # Try to create a minimal airport
        try:
            test = Airport(
                iata='TEST',
                name='Test Airport',
                city='Test City',
                country='XX',
                latitude=0.0,
                longitude=0.0
            )
            print("\n✅ Airport model accepts basic fields")
        except Exception as e:
            print(f"\n❌ Error with Airport model: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("Adding Merced Regional Airport (MCE)")
    print("=" * 60)
    
    # First check the model structure
    verify_airport_model()
    
    print("\n" + "=" * 60)
    success = add_merced_airport()
    
    if success:
        print("\n✅ Merced airport added successfully!")
        print("   You can now use MCE in your flight trips.")
    else:
        print("\n❌ Failed to add Merced airport.")
    
    print("\nTo verify, run: python test_airport.py MCE")