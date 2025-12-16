# csv_airport_manager.py
import csv
import sys
from app import app, db, Airport

def inspect_csv(file_path):
    """Inspect CSV file structure."""
    print(f"\nInspecting CSV file: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Try to read as DictReader first
            try:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                print(f"Headers: {headers}")
                
                # Show first few rows
                print("\nFirst 3 rows:")
                for i, row in enumerate(reader):
                    print(f"Row {i+1}: {dict(row)}")
                    if i >= 2:
                        break
                
            except:
                # Try as regular CSV
                f.seek(0)
                reader = csv.reader(f)
                headers = next(reader)
                print(f"Headers: {headers}")
                
                print("\nFirst 3 rows:")
                for i, row in enumerate(reader):
                    print(f"Row {i+1}: {row}")
                    if i >= 2:
                        break
                        
    except Exception as e:
        print(f"Error inspecting CSV: {e}")

def export_airports_to_csv(output_file='airports_export.csv'):
    """Export database airports to a clean CSV."""
    with app.app_context():
        airports = Airport.query.all()
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write headers
            writer.writerow(['IATA', 'ICAO', 'Name', 'City', 'Country', 'Latitude', 'Longitude', 'Altitude'])
            
            for airport in airports:
                writer.writerow([
                    airport.iata,
                    airport.icao,
                    airport.name,
                    airport.city,
                    airport.country,
                    airport.latitude,
                    airport.longitude,
                    airport.altitude or 0
                ])
        
        print(f"Exported {len(airports)} airports to {output_file}")

def clean_database():
    """Remove duplicate or invalid airports."""
    with app.app_context():
        # Find duplicates by IATA
        from sqlalchemy import func
        duplicates = db.session.query(
            Airport.iata,
            func.count(Airport.iata)
        ).group_by(Airport.iata).having(func.count(Airport.iata) > 1).all()
        
        print(f"Found {len(duplicates)} duplicate IATA codes")
        
        for iata, count in duplicates:
            print(f"  {iata}: {count} duplicates")
            # Keep the first, delete others
            airports = Airport.query.filter_by(iata=iata).all()
            for airport in airports[1:]:
                db.session.delete(airport)
        
        # Delete airports with invalid coordinates
        invalid = Airport.query.filter(
            (Airport.latitude == 0) & (Airport.longitude == 0)
        ).all()
        
        print(f"Found {len(invalid)} airports with invalid coordinates")
        for airport in invalid:
            db.session.delete(airport)
        
        db.session.commit()
        print("Database cleaned")

def main():
    """Command-line interface for airport management."""
    if len(sys.argv) < 2:
        print("Usage: python csv_airport_manager.py [command]")
        print("Commands:")
        print("  inspect <file.csv>    - Inspect CSV file structure")
        print("  export                - Export airports to CSV")
        print("  clean                 - Clean database (remove duplicates)")
        print("  count                 - Count airports in database")
        return
    
    command = sys.argv[1]
    
    with app.app_context():
        if command == 'inspect' and len(sys.argv) > 2:
            inspect_csv(sys.argv[2])
        elif command == 'export':
            export_airports_to_csv()
        elif command == 'clean':
            clean_database()
        elif command == 'count':
            count = Airport.query.count()
            print(f"Total airports in database: {count}")
        else:
            print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()