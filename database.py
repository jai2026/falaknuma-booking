

import os
import sqlite3
from pathlib import Path

# Local development: C:\Falakunuma-Booking\hotel.db
# Render production: /var/data/hotel.db

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = Path(
    os.environ.get(
        "DATABASE_PATH",
        str(BASE_DIR / "hotel.db")
    )
)

DB_PATH.parent.mkdir(parents=True, exist_ok=True)



def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_all_rooms():
    conn = get_connection()

    try:
        rows = conn.execute(
            "SELECT * FROM rooms ORDER BY id"
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


def get_room_by_id(room_id):
    conn = get_connection()

    try:
        row = conn.execute(
            "SELECT * FROM rooms WHERE id = ?",
            (room_id,)
        ).fetchone()

        return dict(row) if row else None

    finally:
        conn.close()


def get_room_amenities(room_id):
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT amenity_name
            FROM room_amenities
            WHERE room_id = ?
            ORDER BY id
            """,
            (room_id,)
        ).fetchall()

        return [row["amenity_name"] for row in rows]

    finally:
        conn.close()

def get_available_rooms(checkin, checkout, guests):
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT
                r.*,
                (
                    r.total_rooms -
                    (
                        SELECT COUNT(*)
                        FROM bookings b
                        WHERE b.room_id = r.id
                          AND b.status = 'confirmed'
                          AND b.checkin < ?
                          AND b.checkout > ?
                    )
                ) AS available_count
            FROM rooms r
            WHERE r.guests >= ?
            ORDER BY r.price ASC
            """,
            (checkout, checkin, guests)
        ).fetchall()

        return [
            dict(row)
            for row in rows
            if row["available_count"] > 0
        ]

    finally:
        conn.close()

import secrets

def create_booking(
    room_id,
    guest_name,
    guest_email,
    guest_phone,
    checkin,
    checkout,
    guests
):
    conn = get_connection()

    try:
        # Lock before checking inventory and inserting.
        conn.execute("BEGIN IMMEDIATE")

        room = conn.execute(
            "SELECT * FROM rooms WHERE id = ?",
            (room_id,)
        ).fetchone()

        if room is None:
            conn.rollback()
            return None, "Room not found."

        if guests > room["guests"]:
            conn.rollback()
            return None, "Too many guests for this room."

        booked = conn.execute("""
            SELECT COUNT(*)
            FROM bookings
            WHERE room_id = ?
              AND status = 'confirmed'
              AND checkin < ?
              AND checkout > ?
        """, (
            room_id,
            checkout,
            checkin
        )).fetchone()[0]

        if booked >= room["total_rooms"]:
            conn.rollback()
            return None, "This room is no longer available."

        # Random reference rather than a predictable ID.
        reference = "FP-" + secrets.token_hex(12).upper()

        conn.execute("""
            INSERT INTO bookings (
                room_id,
                guest_name,
                guest_email,
                guest_phone,
                checkin,
                checkout,
                guests,
                status,
                booking_reference
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            room_id,
            guest_name,
            guest_email,
            guest_phone,
            checkin,
            checkout,
            guests,
            "confirmed",
            reference
        ))

        conn.commit()

        return reference, None

    except sqlite3.Error:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_booking_by_reference(reference):
    conn = get_connection()

    try:
        row = conn.execute("""
            SELECT
                b.*,
                r.name AS room_name,
                r.category AS room_category,
                r.image AS room_image,
                r.price AS room_price
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
            WHERE b.booking_reference = ?
        """, (reference,)).fetchone()

        return dict(row) if row else None

    finally:
        conn.close()

def find_booking(reference, email):
    conn = get_connection()

    try:
        row = conn.execute("""
            SELECT
                b.*,
                r.name AS room_name,
                r.category AS room_category,
                r.image AS room_image,
                r.price AS room_price
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
            WHERE b.booking_reference = ?
              AND LOWER(b.guest_email) = LOWER(?)
        """, (
            reference,
            email
        )).fetchone()

        return dict(row) if row else None

    finally:
        conn.close()


def cancel_booking(reference, email):
    from datetime import date

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        cursor = conn.execute("""
            UPDATE bookings
            SET status = 'cancelled'
            WHERE booking_reference = ?
              AND LOWER(guest_email) = LOWER(?)
              AND status = 'confirmed'
              AND checkin > ?
        """, (
            reference,
            email,
            date.today().isoformat()
        ))

        if cursor.rowcount == 1:
            conn.commit()
            return True

        conn.rollback()
        return False

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()



def get_admin_rooms():
    conn = get_connection()

    try:
        rows = conn.execute("""
            SELECT
                r.*,
                (
                    SELECT COUNT(*)
                    FROM bookings b
                    WHERE b.room_id = r.id
                      AND b.status = 'confirmed'
                      AND b.checkin <= date('now', 'localtime')
                      AND b.checkout > date('now', 'localtime')
                ) AS occupied_today
            FROM rooms r
            ORDER BY r.id
        """).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


def update_room_details(room_id, price, total_rooms):
    if price <= 0:
        return False, "Room price must be greater than zero."

    if total_rooms < 1:
        return False, "Room inventory must be at least one."

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        room = conn.execute(
            "SELECT id FROM rooms WHERE id = ?",
            (room_id,)
        ).fetchone()

        if room is None:
            conn.rollback()
            return False, "Room not found."

        # Find the maximum number of overlapping confirmed
        # reservations for this room category.
        rows = conn.execute("""
            SELECT checkin, checkout
            FROM bookings
            WHERE room_id = ?
              AND status = 'confirmed'
              AND checkout > date('now', 'localtime')
        """, (room_id,)).fetchall()

        events = []

        for booking in rows:
            events.append((booking["checkin"], 1))
            events.append((booking["checkout"], -1))

        # Checkout happens before check-in on the same date.
        events.sort(key=lambda event: (event[0], event[1]))

        active = 0
        peak = 0

        for _, change in events:
            active += change
            peak = max(peak, active)

        if total_rooms < peak:
            conn.rollback()
            return (
                False,
                f"Inventory cannot be below {peak}; "
                "existing confirmed reservations overlap."
            )

        conn.execute("""
            UPDATE rooms
            SET price = ?,
                total_rooms = ?
            WHERE id = ?
        """, (price, total_rooms, room_id))

        conn.commit()

        return True, "Room details updated successfully."

    except sqlite3.Error:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_admin_booking_details(booking_id):
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT b.*, r.name AS room_name,
                   r.category AS room_category,
                   r.price AS room_price,
                   r.image AS room_image
            FROM bookings b
            JOIN rooms r ON r.id = b.room_id
            WHERE b.id = ?
        """, (booking_id,)).fetchone()

        return dict(row) if row else None
    finally:
        conn.close()


def update_guest_operation(booking_id, action):
    from datetime import date, datetime

    if action not in ("checkin", "checkout"):
        return False, "Invalid operation."

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        booking = conn.execute("""
            SELECT status, checkin, checkout,
                   checked_in_at, checked_out_at
            FROM bookings
            WHERE id = ?
        """, (booking_id,)).fetchone()

        if booking is None:
            conn.rollback()
            return False, "Booking not found."

        if booking["status"] != "confirmed":
            conn.rollback()
            return False, "Cancelled bookings cannot be processed."

        today = date.today().isoformat()
        timestamp = datetime.now().astimezone().isoformat(
            timespec="seconds"
        )

        if action == "checkin":
            if booking["checked_in_at"]:
                conn.rollback()
                return False, "Guest is already checked in."

            if not (
                booking["checkin"] <= today
                < booking["checkout"]
            ):
                conn.rollback()
                return False, "Check-in is only allowed during the scheduled stay."

            conn.execute("""
                UPDATE bookings
                SET checked_in_at = ?
                WHERE id = ?
            """, (timestamp, booking_id))

            message = "Guest checked in successfully."

        else:
            if not booking["checked_in_at"]:
                conn.rollback()
                return False, "Guest must check in first."

            if booking["checked_out_at"]:
                conn.rollback()
                return False, "Guest is already checked out."

            conn.execute("""
                UPDATE bookings
                SET checked_out_at = ?
                WHERE id = ?
            """, (timestamp, booking_id))

            message = "Guest checked out successfully."

        conn.commit()
        return True, message

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
