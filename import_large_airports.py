#!/usr/bin/env python3
"""
Import ONLY large airports from OurAirports CSV.
Specifically for airports like LAX (row 3632 in your example).
"""

import csv
import sys
import os
from collections import Counter

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Airport

def import_large_airports(csv_file='airports.csv'):
    """
    Import only LARGE airports with IATA codes and scheduled service.
    """
    print(f"🔍 Searching for LARGE airports in {csv_file}...")
    
    airports_to_import = []
    total_rows = 0
    large_found = 0
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, 1):
            total_rows += 1
            
            # Skip if not a large airport
            if row.get('type', '').strip().lower() != 'large_airport':
                continue
            
            # Skip if no scheduled service
            if row.get('scheduled_service', '').strip().lower() != 'yes':
                continue
            
            # Skip if no IATA code
            iata = row.get('iata_code', '').strip()
            if not iata or len(iata) != 3:
                continue
            
            large_found += 1
            
            # Get ICAO code
            icao = row.get('icao_code', '').strip()
            if not icao:
                icao = row.get('gps_code', '').strip()
            
            # Get coordinates
            try:
                lat = float(row.get('latitude_deg', 0))
                lng = float(row.get('longitude_deg', 0))
            except (ValueError, TypeError):
                continue
            
            # Convert elevation
            try:
                elevation_ft = float(row.get('elevation_ft', 0))
                altitude = elevation_ft * 0.3048
            except (ValueError, TypeError):
                altitude = 0
            
            # Get city
            city = row.get('municipality', '').strip()
            if not city:
                city = 'Unknown'
            
            airports_to_import.append({
                'iata': iata,
                'icao': icao,
                'ident': row.get('ident', '').strip(),
                'name': row.get('name', '').strip(),
                'city': city,
                'country': row.get('iso_country', '').strip(),
                'latitude': lat,
                'longitude': lng,
                'altitude': altitude,
                'type': 'large_airport',
                'scheduled_service': True,
                'continent': row.get('continent', '').strip(),
                'region': row.get('iso_region', '').strip()
            })
            
            # Show progress
            if large_found % 10 == 0:
                print(f"  Found {large_found} large airports...")
    
    print(f"\n📊 Analysis:")
    print(f"  Total rows in CSV: {total_rows:,}")
    print(f"  Large airports found: {large_found:,}")
    
    if large_found == 0:
        print("\n❌ No large airports found!")
        print("   Check that your CSV has rows with:")
        print("   - type: 'large_airport'")
        print("   - scheduled_service: 'yes'")
        print("   - iata_code: 3-letter code (e.g., 'LAX')")
        return []
    
    # Show first 10 examples
    print(f"\n🏙️  First {min(10, len(airports_to_import))} large airports found:")
    for i, airport in enumerate(airports_to_import[:10]):
        print(f"  {i+1:2d}. {airport['iata']} - {airport['name']} ({airport['city']}, {airport['country']})")
    
    return airports_to_import

def count_airport_types(csv_file='airports.csv'):
    """Count how many airports of each type exist."""
    print(f"\n📈 Counting airport types in {csv_file}...")
    
    type_counter = Counter()
    iata_counter = Counter()
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            airport_type = row.get('type', '').strip()
            type_counter[airport_type] += 1
            
            iata = row.get('iata_code', '').strip()
            if iata and len(iata) == 3:
                iata_counter[airport_type] = iata_counter.get(airport_type, 0) + 1
    
    print("\nAirport Types:")
    for type_name, count in sorted(type_counter.items(), key=lambda x: x[1], reverse=True):
        iata_count = iata_counter.get(type_name, 0)
        print(f"  {type_name:20s}: {count:6,} total, {iata_count:6,} with IATA codes")

def main():
    if len(sys.argv) < 2:
        print("Usage: python import_large_airports.py <command>")
        print("\nCommands:")
        print("  import       - Import large airports from airports.csv")
        print("  analyze      - Analyze CSV file content")
        print("  quick        - Quick import (no analysis)")
        print("  sample       - Show sample large airports without importing")
        return
    
    command = sys.argv[1]
    
    with app.app_context():
        if command == 'analyze':
            count_airport_types('airports.csv')
            
            # Also show large airport examples
            airports = import_large_airports('airports.csv')
            if airports:
                print(f"\n✅ Found {len(airports)} large airports total")
                
                # Group by country
                from collections import Counter
                country_counts = Counter([a['country'] for a in airports])
                print(f"\n🌍 By country:")
                for country, count in sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:15]:
                    print(f"  {country}: {count}")
        
        elif command == 'sample':
            print("Looking for sample large airports...")
            with open('airports.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                found = 0
                
                for row in reader:
                    if (row.get('type', '').strip().lower() == 'large_airport' and
                        row.get('scheduled_service', '').strip().lower() == 'yes' and
                        row.get('iata_code', '').strip()):
                        
                        found += 1
                        print(f"\n{found}. {row.get('iata_code')} - {row.get('name')}")
                        print(f"   City: {row.get('municipality')}")
                        print(f"   Country: {row.get('iso_country')}")
                        print(f"   ICAO: {row.get('icao_code') or row.get('gps_code')}")
                        
                        if found >= 20:
                            break
        
        elif command in ['import', 'quick']:
            # Create tables if needed
            db.create_all()
            
            # Clear existing airports
            print("🗑️  Clearing existing airports...")
            try:
                Airport.query.delete()
                db.session.commit()
                print("✅ Existing airports cleared")
            except Exception as e:
                print(f"Note: {e}")
                db.session.rollback()
            
            # Import large airports
            airports = import_large_airports('airports.csv')
            
            if not airports:
                print("❌ No airports to import")
                return
            
            # Add to database
            print(f"\n💾 Adding {len(airports)} large airports to database...")
            batch_size = 100
            total_added = 0
            
            for i in range(0, len(airports), batch_size):
                batch = airports[i:i + batch_size]
                airport_objects = []
                
                for data in batch:
                    airport = Airport(
                        iata=data['iata'],
                        icao=data['icao'] or None,
                        ident=data['ident'] or None,
                        name=data['name'],
                        city=data['city'],
                        country=data['country'],
                        latitude=data['latitude'],
                        longitude=data['longitude'],
                        altitude=data['altitude'],
                        type=data['type'],
                        scheduled_service=data['scheduled_service'],
                        continent=data['continent'] or None,
                        region=data['region'] or None
                    )
                    airport_objects.append(airport)
                
                try:
                    db.session.add_all(airport_objects)
                    db.session.commit()
                    total_added += len(batch)
                    print(f"  Added batch {i//batch_size + 1}: {len(batch)} airports")
                except Exception as e:
                    db.session.rollback()
                    print(f"  Error with batch: {e}")
            
            print(f"\n🎉 Successfully imported {total_added} large airports!")
            
            # Show summary
            print(f"\n📊 Database Summary:")
            all_airports = Airport.query.all()
            print(f"  Total in database: {len(all_airports)}")
            
            # Count by country
            from collections import Counter
            country_counts = Counter([a.country for a in all_airports])
            print(f"\n  Top 10 countries:")
            for country, count in sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"    {country}: {count} airports")
            
            # List all airports
            print(f"\n  All airports imported:")
            for airport in sorted(all_airports, key=lambda x: x.iata):
                print(f"    {airport.iata} - {airport.name}")

if __name__ == "__main__":
    main()