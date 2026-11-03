
import os
import secrets
import sqlite3

from database import (
    get_admin_booking_details,
    update_guest_operation
)
from database import get_admin_rooms, update_room_details
from datetime import date
from functools import wraps

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    abort
)

from werkzeug.security import check_password_hash
from database import get_connection


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)


def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin.login"))

        return function(*args, **kwargs)

    return wrapper


def verify_admin_token():
    supplied = request.form.get("csrf_token", "")
    expected = session.get("admin_csrf", "")

    return bool(
        expected
        and secrets.compare_digest(supplied, expected)
    )


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        if not verify_admin_token():
            abort(400)

        username = request.form.get(
            "username", ""
        ).strip()

        password = request.form.get(
            "password", ""
        )

        admin_username = os.environ.get(
            "ADMIN_USERNAME", ""
        )

        password_hash = os.environ.get(
            "ADMIN_PASSWORD_HASH", ""
        )

        valid_password = bool(
            password_hash
            and check_password_hash(
                password_hash,
                password
            )
        )

        if (
            username == admin_username
            and admin_username
            and valid_password
        ):
            session.clear()
            session["admin_logged_in"] = True
            session["admin_csrf"] = secrets.token_urlsafe(32)

            return redirect(
                url_for("admin.dashboard")
            )

        flash("Invalid admin credentials.")

    if "admin_csrf" not in session:
        session["admin_csrf"] = secrets.token_urlsafe(32)

    return render_template(
        "admin/login.html",
        csrf_token=session["admin_csrf"]
    )


@admin_bp.route("/logout", methods=["POST"])
@admin_required
def logout():
    if not verify_admin_token():
        abort(400)

    session.clear()

    return redirect(url_for("admin.login"))


@admin_bp.route("/")
@admin_required
def dashboard():
    conn = get_connection()

    try:
        total_rooms = conn.execute("""
            SELECT COALESCE(SUM(total_rooms), 0)
            FROM rooms
        """).fetchone()[0]

        total_bookings = conn.execute("""
            SELECT COUNT(*) FROM bookings
        """).fetchone()[0]

        confirmed = conn.execute("""
            SELECT COUNT(*) FROM bookings
            WHERE status = 'confirmed'
        """).fetchone()[0]

        cancelled = conn.execute("""
            SELECT COUNT(*) FROM bookings
            WHERE status = 'cancelled'
        """).fetchone()[0]

        today = date.today().isoformat()

        occupied = conn.execute("""
            SELECT COUNT(*)
            FROM bookings
            WHERE status = 'confirmed'
              AND checkin <= ?
              AND checkout > ?
        """, (today, today)).fetchone()[0]

        checked_in = conn.execute("""
        SELECT COUNT(*)
        FROM bookings
        WHERE status = 'confirmed'
        AND checked_in_at IS NOT NULL
        AND checked_out_at IS NULL
        """).fetchone()[0]
        checked_out = conn.execute("""
        SELECT COUNT(*)
        FROM bookings
        WHERE status = 'confirmed'
        AND checked_out_at IS NOT NULL
        """).fetchone()[0]

        recent_rows = conn.execute("""
            SELECT
                b.booking_reference,
                b.guest_name,
                b.checkin,
                b.checkout,
                b.status,
                r.name AS room_name
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
            ORDER BY b.id DESC
            LIMIT 8
        """).fetchall()

        recent = [dict(row) for row in recent_rows]

    finally:
        conn.close()

    stats = {
        "total_rooms": total_rooms,
        "total_bookings": total_bookings,
        "confirmed": confirmed,
        "cancelled": cancelled,
        "occupied": occupied,
        "available_today": max(
            0, total_rooms - occupied
        ),
        "checked_in": checked_in,
"checked_out": checked_out
    }

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent=recent,
        csrf_token=session["admin_csrf"]
    )


@admin_bp.route("/reservations")
@admin_required
def reservations():
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "all").strip()

    if status not in ("all", "confirmed", "cancelled"):
        status = "all"

    query = """
        SELECT
            b.id,
            b.booking_reference,
            b.guest_name,
            b.guest_email,
            b.checkin,
            b.checkout,
            b.guests,
            b.status,
            r.name AS room_name
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        WHERE 1 = 1
    """

    params = []

    if search:
        query += """
            AND (
                b.booking_reference LIKE ?
                OR b.guest_name LIKE ?
                OR b.guest_email LIKE ?
            )
        """

        pattern = f"%{search}%"
        params.extend([pattern, pattern, pattern])

    if status != "all":
        query += " AND b.status = ?"
        params.append(status)

    query += " ORDER BY b.id DESC LIMIT 200"

    conn = get_connection()

    try:
        rows = conn.execute(query, params).fetchall()
        bookings = [dict(row) for row in rows]

    finally:
        conn.close()

    return render_template(
        "admin/reservations.html",
        bookings=bookings,
        search=search,
        status=status,
        csrf_token=session["admin_csrf"]
    )



@admin_bp.route("/rooms")
@admin_required
def rooms():
    room_list = get_admin_rooms()

    return render_template(
        "admin/rooms.html",
        rooms=room_list,
        csrf_token=session["admin_csrf"]
    )


@admin_bp.route(
    "/rooms/<int:room_id>/edit",
    methods=["GET", "POST"]
)
@admin_required
def edit_room(room_id):
    conn = get_connection()

    try:
        row = conn.execute(
            "SELECT * FROM rooms WHERE id = ?",
            (room_id,)
        ).fetchone()

        room = dict(row) if row else None

    finally:
        conn.close()

    if room is None:
        abort(404)

    if request.method == "POST":
        if not verify_admin_token():
            abort(400)

        try:
            price = int(request.form.get("price", ""))
            total_rooms = int(
                request.form.get("total_rooms", "")
            )

        except (ValueError, TypeError):
            flash("Enter valid whole numbers.")
            return redirect(
                url_for("admin.edit_room", room_id=room_id)
            )

        if price > 10000000 or total_rooms > 10000:
            flash("The entered value is too large.")
            return redirect(
                url_for("admin.edit_room", room_id=room_id)
            )

        success, message = update_room_details(
            room_id,
            price,
            total_rooms
        )

        flash(message)

        if success:
            return redirect(url_for("admin.rooms"))

        return redirect(
            url_for("admin.edit_room", room_id=room_id)
        )

    return render_template(
        "admin/edit_room.html",
        room=room,
        csrf_token=session["admin_csrf"]
    )


@admin_bp.route("/reservations/<int:booking_id>")
@admin_required
def reservation_details(booking_id):
    booking = get_admin_booking_details(booking_id)

    if booking is None:
        abort(404)

    checkin_allowed = (
        booking["status"] == "confirmed"
        and not booking["checked_in_at"]
        and booking["checkin"] <= date.today().isoformat()
        < booking["checkout"]
    )

    checkout_allowed = (
        booking["status"] == "confirmed"
        and bool(booking["checked_in_at"])
        and not booking["checked_out_at"]
    )

    return render_template(
        "admin/reservation_details.html",
        booking=booking,
        checkin_allowed=checkin_allowed,
        checkout_allowed=checkout_allowed,
        csrf_token=session["admin_csrf"]
    )


@admin_bp.route(
    "/reservations/<int:booking_id>/<action>",
    methods=["POST"]
)
@admin_required
def guest_operation(booking_id, action):
    if not verify_admin_token():
        abort(400)

    if action not in ("checkin", "checkout"):
        abort(404)

    success, message = update_guest_operation(
        booking_id, action
    )

    flash(message)

    return redirect(
        url_for(
            "admin.reservation_details",
            booking_id=booking_id
        )
    )
