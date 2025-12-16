#!/usr/bin/env python3
"""
Special importer for OurAirports CSV format.
Run this to import your specific CSV file.
"""

import csv
import sys
import os
from collections import Counter

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Airport

def analyze_csv(file_path):
    """Analyze the CSV file structure."""
    print(f"Analyzing {file_path}...")
    
    total_rows = 0
    with_iata = 0
    with_scheduled = 0
    types_counter = Counter()
    country_counter = Counter()
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            total_rows += 1
            
            iata = row.get('iata_code', '').strip()
            if iata and len(iata) == 3:
                with_iata += 1
            
            scheduled = row.get('scheduled_service', '').strip().lower()
            if scheduled == 'yes':
                with_scheduled += 1
            
            airport_type = row.get('type', '').strip()
            types_counter[airport_type] += 1
            
            country = row.get('iso_country', '').strip()
            if country:
                country_counter[country] += 1
    
    print(f"\nCSV Analysis:")
    print(f"  Total rows: {total_rows:,}")
    print(f"  With IATA code: {with_iata:,} ({with_iata/total_rows*100:.1f}%)")
    print(f"  With scheduled service: {with_scheduled:,}")
    
    print(f"\n  Airport types:")
    for type_name, count in sorted(types_counter.items(), key=lambda x: x[1], reverse=True):
        percentage = count / total_rows * 100
        print(f"    {type_name}: {count:,} ({percentage:.1f}%)")
    
    print(f"\n  Top 15 countries:")
    for country, count in sorted(country_counter.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"    {country}: {count:,}")
    
    return {
        'total': total_rows,
        'with_iata': with_iata,
        'with_scheduled': with_scheduled
    }

def import_filtered_airports(file_path, output_sql=None):
    """
    Import only airports that are useful for your flight app.
    Filters out heliports, seaplane bases, closed airports, etc.
    """
    print(f"\nImporting filtered airports from {file_path}...")
    
    airports_to_import = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, 1):
            # Skip if no IATA code
            iata = row.get('iata_code', '').strip()
            if not iata or len(iata) != 3:
                continue
            
            # Skip heliports, seaplane bases, closed airports
            airport_type = row.get('type', '').strip().lower()
            if airport_type in ['heliport', 'seaplane_base', 'closed']:
                continue
            
            # Prefer airports with scheduled service
            scheduled = row.get('scheduled_service', '').strip().lower()
            has_scheduled = scheduled == 'yes'
            
            # Skip if no coordinates
            try:
                lat = float(row.get('latitude_deg', 0))
                lng = float(row.get('longitude_deg', 0))
            except (ValueError, TypeError):
                continue
            
            if lat == 0 and lng == 0:
                continue
            
            # Get ICAO code
            icao = row.get('icao_code', '').strip()
            if not icao:
                icao = row.get('gps_code', '').strip()
            
            # Convert elevation
            try:
                elevation_ft = float(row.get('elevation_ft', 0))
                altitude = elevation_ft * 0.3048
            except (ValueError, TypeError):
                altitude = 0
            
            airports_to_import.append({
                'iata': iata,
                'icao': icao,
                'ident': row.get('ident', '').strip(),
                'name': row.get('name', '').strip(),
                'city': row.get('municipality', '').strip(),
                'country': row.get('iso_country', '').strip(),
                'latitude': lat,
                'longitude': lng,
                'altitude': altitude,
                'type': airport_type,
                'scheduled_service': has_scheduled,
                'continent': row.get('continent', '').strip(),
                'region': row.get('iso_region', '').strip()
            })
            
            if row_num % 10000 == 0:
                print(f"  Processed {row_num:,} rows...")
    
    print(f"\nFound {len(airports_to_import):,} suitable airports")
    
    # Optional: Output to SQL file
    if output_sql:
        with open(output_sql, 'w') as f:
            f.write('INSERT INTO airport (iata, icao, name, city, country, latitude, longitude, altitude, type) VALUES\n')
            values = []
            for airport in airports_to_import[:1000]:  # Limit for demo
                values.append(f"('{airport['iata']}', '{airport['icao']}', '{airport['name']}', "
                            f"'{airport['city']}', '{airport['country']}', {airport['latitude']}, "
                            f"{airport['longitude']}, {airport['altitude']}, '{airport['type']}')")
            f.write(',\n'.join(values) + ';')
        print(f"SQL output saved to {output_sql}")
    
    return airports_to_import

def main():
    if len(sys.argv) < 2:
        print("Usage: python import_ourairports.py <command>")
        print("Commands:")
        print("  analyze <file.csv>    - Analyze CSV file")
        print("  import <file.csv>     - Import airports to database")
        print("  quickstart            - Set up with popular airports only")
        return
    
    command = sys.argv[1]
    
    with app.app_context():
        if command == 'analyze' and len(sys.argv) > 2:
            analyze_csv(sys.argv[2])
        
        elif command == 'import' and len(sys.argv) > 2:
            csv_file = sys.argv[2]
            
            # First, clear existing airports
            print("Clearing existing airports...")
            Airport.query.delete()
            db.session.commit()
            
            # Import filtered airports
            airports = import_filtered_airports(csv_file)
            
            # Add to database
            print("\nAdding to database...")
            batch_size = 500
            for i in range(0, len(airports), batch_size):
                batch = airports[i:i + batch_size]
                airport_objects = []
                
                for data in batch:
                    airport = Airport(**data)
                    airport_objects.append(airport)
                
                db.session.add_all(airport_objects)
                db.session.commit()
                
                print(f"  Added batch {i//batch_size + 1}: {len(batch)} airports")
            
            print(f"\n✅ Successfully imported {len(airports):,} airports")
        
        elif command == 'quickstart':
            # Import only major international airports for quick testing
            major_airports = [
                # North America
                ('LAX', 'KLAX', 'Los Angeles International', 'Los Angeles', 'US', 33.9416, -118.4085),
                ('JFK', 'KJFK', 'John F Kennedy International', 'New York', 'US', 40.6413, -73.7781),
                ('ORD', 'KORD', "Chicago O'Hare International", 'Chicago', 'US', 41.9786, -87.9048),
                ('DFW', 'KDFW', 'Dallas/Fort Worth International', 'Dallas', 'US', 32.8998, -97.0403),
                ('SFO', 'KSFO', 'San Francisco International', 'San Francisco', 'US', 37.6213, -122.3790),
                ('YYZ', 'CYYZ', 'Toronto Pearson International', 'Toronto', 'CA', 43.6777, -79.6248),
                ('MEX', 'MMMX', 'Mexico City International', 'Mexico City', 'MX', 19.4363, -99.0721),
                
                # Europe
                ('LHR', 'EGLL', 'London Heathrow', 'London', 'GB', 51.4700, -0.4543),
                ('CDG', 'LFPG', 'Paris Charles de Gaulle', 'Paris', 'FR', 49.0097, 2.5479),
                ('FRA', 'EDDF', 'Frankfurt Airport', 'Frankfurt', 'DE', 50.0379, 8.5622),
                ('AMS', 'EHAM', 'Amsterdam Schiphol', 'Amsterdam', 'NL', 52.3086, 4.7639),
                ('MAD', 'LEMD', 'Madrid Barajas', 'Madrid', 'ES', 40.4983, -3.5676),
                
                # Asia
                ('HND', 'RJTT', 'Tokyo Haneda', 'Tokyo', 'JP', 35.5494, 139.7798),
                ('PEK', 'ZBAA', 'Beijing Capital', 'Beijing', 'CN', 40.0799, 116.6031),
                ('DXB', 'OMDB', 'Dubai International', 'Dubai', 'AE', 25.2532, 55.3657),
                ('SIN', 'WSSS', 'Singapore Changi', 'Singapore', 'SG', 1.3644, 103.9915),
                ('BOM', 'VABB', 'Mumbai Chhatrapati Shivaji', 'Mumbai', 'IN', 19.0897, 72.8656),
                
                # Australia
                ('SYD', 'YSSY', 'Sydney Kingsford Smith', 'Sydney', 'AU', -33.9399, 151.1753),
            ]
            
            print("Creating quickstart database with 20 major airports...")
            
            # Clear existing
            Airport.query.delete()
            db.session.commit()
            
            for iata, icao, name, city, country, lat, lng in major_airports:
                airport = Airport(
                    iata=iata,
                    icao=icao,
                    name=name,
                    city=city,
                    country=country,
                    latitude=lat,
                    longitude=lng,
                    altitude=0,
                    type='large_airport',
                    scheduled_service=True
                )
                db.session.add(airport)
            
            db.session.commit()
            print(f"✅ Added {len(major_airports)} major airports")

if __name__ == "__main__":
    main()