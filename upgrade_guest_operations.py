
from database import get_connection


def upgrade_database():
    conn = get_connection()

    try:
        columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(bookings)"
            ).fetchall()
        }

        if "checked_in_at" not in columns:
            conn.execute("""
                ALTER TABLE bookings
                ADD COLUMN checked_in_at TEXT
            """)

        if "checked_out_at" not in columns:
            conn.execute("""
                ALTER TABLE bookings
                ADD COLUMN checked_out_at TEXT
            """)

        conn.commit()
        print("Guest operations upgrade successful!")

    finally:
        conn.close()


if __name__ == "__main__":
    upgrade_database()
