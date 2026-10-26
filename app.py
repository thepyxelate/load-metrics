import base64

from flask import Flask, json, render_template, request, jsonify
from flask_cors import CORS
from flask_migrate import Migrate

from facilities import FACILITY_MAP
from models import db, Load 

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///relay_loads.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

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

        incoming_ids = [item.get('load_id') for item in incoming_data if item.get('load_id')]
        existing_loads = db.session.query(Load.load_id).filter(Load.load_id.in_(incoming_ids)).all()
        existing_ids = {load[0] for load in existing_loads}

        new_loads_to_add = []
        for item in incoming_data:
            load_id = item.get('load_id')
            if not load_id or load_id in existing_ids:
                continue

            all_stops = item.get('all_stops')
            if all_stops is None:
                stops_data = json.dumps([])
            elif isinstance(all_stops, (list, dict)):
                stops_data = json.dumps(all_stops)
            else:
                stops_data = all_stops

            if not all_stops:
                continue
            pickup_code = all_stops[0].get("location")
            dropoff_code = all_stops[-1].get("location")

            pickup_location = FACILITY_MAP.get(pickup_code, {"city": "UNKNOWN", "state": "UNKNOWN"})
            dropoff_location = FACILITY_MAP.get(dropoff_code, {"city":"UNKNOWN", "state": "UNKNOWN"})
            print(f"pickup: {pickup_location}")
            print(f"dropoff: {dropoff_location}")

            new_load = Load(
                load_id=load_id,
                origin_city=pickup_location.get('city'),
                origin_state=pickup_location.get('state'),
                destination_city=dropoff_location.get('city'),
                destination_state=dropoff_location.get('state'),
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
    limit = request.args.get('limit', 20, type=int)
    limit = min(limit,100)
    cursor_str = request.args.get('cursor')

    city = request.args.get('city', '').strip().lower()
    min_rpm = request.args.get('min_rpm', type=float)

    stmt = db.select(Load).order_by(
        Load.extracted_at.desc(),
        Load.load_id.desc()
    ).limit(limit + 1)

    if city:
        stmt = stmt.where(
            db.or_(
                Load.origin_city.ilike(f"%{city}%"),
                Load.destination_city.ilike(f"%{city}%")
            )
        )

    if min_rpm:
        stmt = stmt.where(Load.rate_per_mile >= min_rpm)

    if cursor_str:
        decoded = decode_cursor(cursor_str)
        if decoded is None:
            return jsonify({"error": "invalid cursor"}), 400

        cursor_time, cursor_load_id = decoded

        older_time = Load.extracted_at < cursor_time

        same_time_but_lower_id = db.and_(Load.extracted_at == cursor_time, Load.load_id < cursor_load_id)

        cursor_condition = db.or_(older_time, same_time_but_lower_id)

        stmt = stmt.where(cursor_condition)

    result = db.session.execute(stmt)
    scalars = result.scalars()
    items = scalars.all()

    has_next = len(items) > limit
    items = items[:limit]
    if has_next:
        next_cursor = encode_cursor(items[-1].extracted_at, items[-1].load_id) 
    else:
        next_cursor = None

    items_data = [load.to_dict() for load in items]

    return jsonify({
        "items":items_data,
        "next_cursor":next_cursor,
        "has_next":has_next,
    })

@app.route("/api/v1/delete/load/<string:id>", methods=["DELETE"])
def delete_load(id):
    print(f"load: ")
    load = db.session.get(Load, id)

    if not load:
        return jsonify({"status": "error", "message": "Load not found"}), 404
    
    db.session.delete(load)
    db.session.commit()
    return jsonify({"status": "success", "message": "load is deleted"} ),200
    
@app.route("/api/v1/analytics/summary", methods=['GET'])
def get_analytics_summary():
    try:
        averages = db.session.query(
            db.func.avg(Load.payout),
            db.func.avg(Load.rate_per_mile)
        ).first()

        avg_payout = averages[0] if averages[0] is not None else 0
        avg_rpm = averages[1] if averages[1] is not None else 0

        top_origin_data = db.session.query(
            Load.origin_city,
            Load.origin_state,
            db.func.count(Load.load_id).label('count')
        ).filter(
            Load.origin_city != "UNKNOWN"
        ).group_by(
            Load.origin_city,
            Load.origin_state
        ).order_by(
            db.func.count(Load.load_id).desc()
        ).first()

        top_destination_data = db.session.query(
            Load.destination_city,
            Load.destination_state,
            db.func.count(Load.load_id).label('count')
        ).filter(
            Load.destination_city != "UNKNOWN"
        ).group_by(
            Load.destination_city,
            Load.destination_state,
        ).order_by(
            db.func.count(Load.load_id).desc()
        ).first()

        top_origin_json = {"city": "N/A", "state": "N/A", "count": 0}
        top_dest_json = {"city": "N/A", "state": "N/A", "count": 0}

        if top_origin_data:
            top_origin_json = {
                "city": top_origin_data[0],   
                "state": top_origin_data[1], 
                "count": top_origin_data[2]
            }

        if top_destination_data:
            top_dest_json = {
                "city": top_destination_data[0],   
                "state": top_destination_data[1], 
                "count": top_destination_data[2]   
            }

        trend_data = db.session.query(
            db.func.substr(Load.extracted_at,1,10).label('date'),
            db.func.avg(Load.rate_per_mile).label('avg_rpm')
        ).filter(
            Load.rate_per_mile.isnot(None)
        ).group_by(
            'date'
        ).order_by(
            'date'
        ).all()

        trend_json = []
        for row in trend_data:
            trend_json.append({
                "date": row[0],
                "avg_rpm": round(row[1], 2) if row[1] is not None else 0
            })


        top_origin_city_data = db.session.query(
            Load.origin_city,
            db.func.count(Load.load_id).label('count')
        ).filter(
            Load.origin_city != "UNKNOWN",
            Load.origin_city.isnot(None),
        ).group_by(
            Load.origin_city
        ).order_by(
            db.func.count(Load.load_id).desc()
        ).limit(
            5
        ).all()

        top_destination_city_data = db.session.query(
            Load.destination_city,
            db.func.count(Load.load_id).label('count')
        ).filter(
            Load.destination_city != "UNKNOWN",
            Load.destination_city.isnot(None),
        ).group_by(
            Load.destination_city
        ).order_by(
            db.func.count(Load.load_id).desc()
        ).limit(
            5
        ).all()

        origin_cities_json = []
        for r in top_origin_city_data:
            origin_cities_json.append({
                "city": r.origin_city,
                "count": r.count
            })

        dest_cities_json = []
        for r in top_destination_city_data:
            dest_cities_json.append({
                "city": r.destination_city,
                "count": r.count
            })
        # KPI
        return jsonify({
            "avg_payout": round(avg_payout, 2),
            "avg_rpm": round(avg_rpm, 2),
            "top_origin": top_origin_json,
            "top_destination": top_dest_json,
            "market_trend": trend_json,
            "top_origin_cities": origin_cities_json,
            "top_destination_cities": dest_cities_json
        }), 200


    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    with app.app_context():
        print(f"DEBUG: Baza manzili: {app.config['SQLALCHEMY_DATABASE_URI']}")
        db.create_all()
        print("Bazadagi jadvallar yaratildi yoki tekshirildi.")
    app.run(port=5000, debug=True)

