from flask import Flask, json, render_template, request, jsonify
from flask_cors import CORS

from models import db, Load 

app = Flask(__name__)
CORS(app) # CORS 

#SQLAlchemy config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///relay_loads.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/')
def dashboard():
    """Main dashboard Page"""
    return render_template('index.html')

@app.route('/api/v1/collect', methods = ['POST'])
def collect_data():
    try:
        # Extension yuborgan ma'lumotni olish
        content = request.get_json()

        if not content or 'data' not in content:
            return jsonify({"status": "error", "message": "No valid data received "}), 400
        
        incoming_data = content['data']
        if not incoming_data:
            return jsonify({"status": "success", "new_items": 0}), 200

        incoming_ids = [item['load_id'] for item in incoming_data if 'load_id' in item ]

        existing_loads = db.session.query(Load.load_id).filter(Load.load_id.in_(incoming_ids)).all()
        existing_ids = {load[0] for load in existing_loads}

        new_loads_to_add = []
        for item in incoming_data:
            if item['load_id'] not in existing_ids:

                stops_data = json.dumps(item['all_stops']) if isinstance(item['all_stops'], (list, dict)) else item['all_stops']
            
                new_load = Load(
                    load_id=item['load_id'],
                    payout=item['payout'],
                    rate_per_mile=item['rate_per_mile'],
                    total_stops=item['total_stops'],
                    start_time=item['start_time'],
                    end_time=item['end_time'],
                    trip_duration=item['trip_duration'],
                    total_distance=item['total_distance'],
                    all_stops_json=stops_data,
                    extracted_at=item['extracted_at']
                )
                new_loads_to_add.append(new_load)
                existing_ids.add(item['load_id'])
            
        if new_loads_to_add:
            db.session.add_all(new_loads_to_add)
            db.session.commit()
        
        return jsonify({"status": "success", "new_items": len(new_loads_to_add)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/v1/loads', methods=['GET'])
def get_loads():
    """Bazadagi data-ni frontend-ga berish"""
    # Eng yangi olingan yukni birinchi chiqarish
    all_loads = Load.query.order_by(Load.extracted_at.desc()).all()
    return jsonify([load.to_dict()for load in all_loads])

# delete
@app.route("/delete/load/<string:id>", methods=["DELETE"])
def delete_load(id):
    load = db.session.get(Load, id)

    if not load:
        return jsonify({"status": "error", "message": "Load not found"}), 404
    
    db.session.delete(load)
    db.session.commit()
    return jsonify({"status": "success", "message": "load is deleted"} ),200
    


if __name__ == '__main__':
    with app.app_context():
        print(f"DEBUG: Baza manzili: {app.config['SQLALCHEMY_DATABASE_URI']}")
        db.create_all() # Database va Columnlarni yaratish
        print("Bazadagi jadvallar yaratildi yoki tekshirildi.")
    app.run(port=5000)

