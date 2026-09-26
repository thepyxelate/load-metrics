import base64

from flask import Flask, json, render_template, request, jsonify
from flask_cors import CORS

from models import db, Load 

app = Flask(__name__)
CORS(app) # CORS 

#SQLAlchemy config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///relay_loads.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def encode_cursor(extracted_at, load_id):
    data = {"t": extracted_at, "l": load_id}
    json_str = json.dumps(data)
    encoded = base64.b64encode(json_str.encode())
    
    return encoded.decode()


def decode_cursor(cursor_str):
    try:
        decoded = base64.b64decode(cursor_str)
        data = json.loads(decoded)
        return data["t"], data["l"]
    except Exception:
        return None

@app.route('/')
def dashboard():
    """Main dashboard Page"""
    return render_template('index.html')

@app.route('/api/v1/collect', methods=['POST'])
def collect_data():
    try:
        content = request.get_json()
        if not content or 'data' not in content:
            return jsonify({"status": "error", "message": "No valid data received"}), 400

        incoming_data = content['data']
        if not incoming_data:
            return jsonify({"status": "success", "new_items": 0}), 200

        # Собираем все load_id, которые пришли
        incoming_ids = [item.get('load_id') for item in incoming_data if item.get('load_id')]
        existing_loads = db.session.query(Load.load_id).filter(Load.load_id.in_(incoming_ids)).all()
        existing_ids = {load[0] for load in existing_loads}

        new_loads_to_add = []
        for item in incoming_data:
            load_id = item.get('load_id')
            if not load_id or load_id in existing_ids:
                continue

            # Безопасно получаем all_stops
            all_stops = item.get('all_stops')
            if all_stops is None:
                stops_data = json.dumps([])
            elif isinstance(all_stops, (list, dict)):
                stops_data = json.dumps(all_stops)
            else:
                stops_data = all_stops  # уже строка

            new_load = Load(
                load_id=load_id,
                payout=item.get('payout'),
                rate_per_mile=item.get('rate_per_mile'),
                total_stops=item.get('total_stops'),
                start_time=item.get('start_time'),
                end_time=item.get('end_time'),
                trip_duration=item.get('trip_duration'),
                total_distance=item.get('total_distance'),
                all_stops_json=stops_data,
                extracted_at=item.get('extracted_at')
            )
            new_loads_to_add.append(new_load)
            existing_ids.add(load_id)

        if new_loads_to_add:
            db.session.add_all(new_loads_to_add)
            db.session.commit()

        return jsonify({"status": "success", "new_items": len(new_loads_to_add)}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in collect_data: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/v1/loads', methods=['GET'])
def get_loads():
    """Bazadagi data-ni frontend-ga berish"""
    # 1. limit and cursor
    limit = request.args.get('limit', 20, type=int)
    limit = min(limit,100)
    cursor_str = request.args.get('cursor')

    # filter
    city = request.args.get('city', '').strip().lower()
    min_rpm = request.args.get('min_rpm', type=float)
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    # 2. statement query (+1 trick)
    stmt = db.select(Load).order_by(
        Load.extracted_at.desc(),
        Load.load_id.desc()
    ).limit(limit + 1)

    # 3. add Where if a cursor is present
    # Filter WHERE shartlari
    if city:
        stmt = stmt.where(Load.all_stops_json.ilike(f"%{city}%"))

    if min_rpm:
        rpm_clean = db.func.replace(
            db.func.replace(Load.rate_per_mile, '$', ''),
            '/mi', ''
        )
        stmt = stmt.where(db.cast(rpm_clean, db.Float) >= min_rpm)   # ← shu yerga

    if cursor_str:
        decoded = decode_cursor(cursor_str)
        if decoded is None:
            return jsonify({"error": "invalid cursor"}), 400

        cursor_time, cursor_load_id = decoded

        older_time = Load.extracted_at < cursor_time

        same_time_but_lower_id = db.and_(Load.extracted_at == cursor_time, Load.load_id < cursor_load_id)

        cursor_condition = db.or_(older_time, same_time_but_lower_id)

        stmt = stmt.where(cursor_condition)

    # 4. Execute
    result = db.session.execute(stmt)
    scalars = result.scalars()
    items = scalars.all()

    # 5. has_next va next_cursor
    has_next = len(items) > limit
    items = items[:limit]
    if has_next:
        next_cursor = encode_cursor(items[-1].extracted_at, items[-1].load_id) 
    else:
        next_cursor = None

    # 6. JSON
    items_data = [load.to_dict() for load in items]

    return jsonify({
        "items":items_data,
        "next_cursor":next_cursor,
        "has_next":has_next,
    })

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
        db.create_all()
        print("Bazadagi jadvallar yaratildi yoki tekshirildi.")
    app.run(port=5000, debug=True)

