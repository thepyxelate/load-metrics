import json
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Load(db.Model):
    __tablename__ = 'loads'
    load_id = db.Column(db.String, primary_key=True)
    payout = db.Column(db.String)
    rate_per_mile = db.Column(db.String)
    total_stops = db.Column(db.Integer)
    start_time = db.Column(db.String)
    end_time = db.Column(db.String)
    trip_duration = db.Column(db.String)
    total_distance = db.Column(db.String)
    all_stops_json = db.Column(db.Text)
    extracted_at = db.Column(db.String)

    def to_dict(self):
        """Modelni (dict) korinishiga otkazish"""
        return {
            "load_id": self.load_id,
            "payout": self.payout,
            "rate_per_mile": self.rate_per_mile,
            "total_stops": self.total_stops,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "trip_duration": self.trip_duration,
            "total_distance": self.total_distance,
            # Xavfsiz yuklash: agar NULL bo'lsa, bo'sh list [] qaytaradi
            "all_stops": json.loads(self.all_stops_json) if self.all_stops_json else [],
            "extracted_at": self.extracted_at
        }
