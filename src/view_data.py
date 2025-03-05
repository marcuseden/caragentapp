import asyncio
import motor.motor_asyncio
from config import MONGODB_URI, DB_NAME, COLLECTION_NAME
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich import box

def format_number(value, suffix=''):
    """Format number with thousand separators and optional suffix"""
    if isinstance(value, (int, float)):
        return f"{value:,}{suffix}"
    return 'N/A'

async def view_car_listings():
    # Connect to MongoDB
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    
    # Get all documents
    cursor = collection.find({})
    documents = await cursor.to_list(length=None)
    
    console = Console()
    
    if documents:
        for idx, car in enumerate(documents, 1):
            console.print(f"\n[bold cyan]Car #{idx}: {car.get('brand', 'N/A')} {car.get('model', 'N/A')}[/bold cyan]")
            
            # Basic Information Table
            basic_table = Table(title="Basic Information", box=box.ROUNDED, show_header=True)
            basic_table.add_column("Field", style="cyan")
            basic_table.add_column("Value", style="green")
            
            basic_info = [
                ("Brand", car.get('brand', 'N/A')),
                ("Model", car.get('model', 'N/A')),
                ("Year", car.get('year', 'N/A')),
                ("First Registration", car.get('first_registration', 'N/A')),
                ("Mileage", format_number(car.get('mileage'), ' km')),
                ("Color", car.get('color', 'N/A')),
                ("Fuel Type", car.get('fuel_type', 'N/A'))
            ]
            
            for field, value in basic_info:
                basic_table.add_row(field, str(value))
            
            console.print(basic_table)
            
            # Price Information Table
            price_table = Table(title="Price Information", box=box.ROUNDED, show_header=True)
            price_table.add_column("Field", style="cyan")
            price_table.add_column("Value", style="green")
            
            price_info = [
                ("Cash Price", format_number(car.get('cash_price'), ' DKK')),
                ("Annual Tax", format_number(car.get('annual_tax'), ' DKK/year'))
            ]
            
            for field, value in price_info:
                price_table.add_row(field, str(value))
            
            console.print(price_table)
            
            # Technical Specifications Table
            tech_table = Table(title="Technical Specifications", box=box.ROUNDED, show_header=True)
            tech_table.add_column("Field", style="cyan")
            tech_table.add_column("Value", style="green")
            
            tech_info = [
                ("Power", f"{car.get('horsepower', 'N/A')} hp / {car.get('torque_nm', 'N/A')} Nm"),
                ("Acceleration (0-100)", f"{car.get('acceleration', 'N/A')} seconds"),
                ("Top Speed", f"{car.get('top_speed', 'N/A')} km/h"),
                ("Weight", format_number(car.get('weight'), ' kg')),
                ("Trunk Size", format_number(car.get('trunk_size'), ' liters')),
                ("Towing Capacity", format_number(car.get('towing_capacity'), ' kg'))
            ]
            
            for field, value in tech_info:
                tech_table.add_row(field, str(value))
            
            console.print(tech_table)
            
            # EV Specific Information (if applicable)
            if car.get('fuel_type') == 'El':
                ev_table = Table(title="EV Specifications", box=box.ROUNDED, show_header=True)
                ev_table.add_column("Field", style="cyan")
                ev_table.add_column("Value", style="green")
                
                ev_info = [
                    ("Range (WLTP)", format_number(car.get('range_km'), ' km')),
                    ("Battery Capacity", f"{car.get('battery_capacity', 'N/A')} kWh"),
                    ("Energy Consumption", f"{car.get('energy_consumption', 'N/A')} Wh/km"),
                    ("AC Charging", car.get('charging_ac', 'N/A')),
                    ("DC Charging", car.get('charging_dc', 'N/A')),
                    ("DC Charging Time (10-80%)", car.get('charging_time', 'N/A'))
                ]
                
                for field, value in ev_info:
                    ev_table.add_row(field, str(value))
                
                console.print(ev_table)
            
            # Equipment Table
            if car.get('equipment'):
                equip_table = Table(title="Equipment and Features", box=box.ROUNDED, show_header=True)
                equip_table.add_column("Equipment", style="green")
                
                # Split equipment into chunks for better display
                chunk_size = 3
                equipment = sorted(set(car.get('equipment', [])))  # Remove duplicates and sort
                for i in range(0, len(equipment), chunk_size):
                    chunk = equipment[i:i + chunk_size]
                    equip_table.add_row("\n".join(f"• {item}" for item in chunk))
                
                console.print(equip_table)
            
            console.print("\n" + "="*100 + "\n")
        
        console.print(f"[bold]Total listings: {len(documents)}[/bold]")
        console.print(f"[italic]Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/italic]")
    else:
        console.print("\n[red]No car listings found in database.[/red]")
    
    # Close connection
    client.close()

if __name__ == "__main__":
    # First install rich if not installed
    try:
        import rich
    except ImportError:
        print("Installing required package: rich")
        import subprocess
        subprocess.check_call(["pip", "install", "rich"])
        
    asyncio.run(view_car_listings()) 