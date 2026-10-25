from app import app, db
from models import Load
import json

# FACILITY_MAP ni ham app.py dan import qilish kerak (yoki nusxalash)
from app import FACILITY_MAP 

def migrate_data():
    # 3. Bazadagi barcha eski yuklarni olamiz
    with app.app_context():
        loads = Load.query.all()
        print(f"Jami yuklar soni: {len(loads)}")
        
        updated_count = 0
        
        for load in loads:
            
            # 1. J  SONni ochamiz
            if not load.all_stops_json:
                continue
                
            try:
                stops_list = json.loads(load.all_stops_json)
            except:
                continue # Agar JSON buzuq bo'lsa, tashlab ketamiz

            if not stops_list:
                continue

            # 5. JSON ichidan origin va destination kodlarini ajratib olamiz
            pickup_code = stops_list[0].get("location")
            dropoff_code = stops_list[-1].get("location")

            # 6. Kodlarni FACILITY_MAP orqali shahar/shtatga aylantiramiz
            # (Sizning oldingi kodingizdan foydalanamiz)
            pickup_loc = FACILITY_MAP.get(pickup_code, {"city": "UNKNOWN", "state": "UNKNOWN"})
            dropoff_loc = FACILITY_MAP.get(dropoff_code, {"city": "UNKNOWN", "state": "UNKNOWN"})

            # 4. Yangi topilgan ma'lumotlarni yozamiz
            load.origin_city = pickup_loc["city"]
            load.origin_state = pickup_loc["state"]
            load.destination_city = dropoff_loc["city"]
            load.destination_state = dropoff_loc["state"]
            
            updated_count += 1
            
        # 2. O'zgarishlarni saqlaymiz
        db.session.commit()
        print(f"Yangilangan yuklar soni: {updated_count}")

if __name__ == "__main__":
    migrate_data()