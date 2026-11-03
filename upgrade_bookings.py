
from database import get_connection

conn = get_connection()

try:
    columns = [
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(bookings)"
        ).fetchall()
    ]

    if "guest_phone" not in columns:
        conn.execute("""
            ALTER TABLE bookings
            ADD COLUMN guest_phone TEXT
        """)

    if "booking_reference" not in columns:
        conn.execute("""
            ALTER TABLE bookings
            ADD COLUMN booking_reference TEXT
        """)

    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_booking_reference
        ON bookings (booking_reference)
    """)

    conn.commit()

    print("Phase 5 database upgrade successful!")

finally:
    conn.close()
