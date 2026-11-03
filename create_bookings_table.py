
from database import get_connection

conn = get_connection()

try:
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            guest_name TEXT NOT NULL,
            guest_email TEXT NOT NULL,
            checkin TEXT NOT NULL,
            checkout TEXT NOT NULL,
            guests INTEGER NOT NULL CHECK(guests > 0),
            status TEXT NOT NULL DEFAULT 'confirmed'
                CHECK(status IN ('confirmed', 'cancelled')),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_id) REFERENCES rooms(id),
            CHECK(checkout > checkin)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_bookings_room_dates
        ON bookings (
            room_id,
            checkin,
            checkout,
            status
        )
    """)

    conn.commit()

    print("Bookings table created successfully!")

finally:
    conn.close()
