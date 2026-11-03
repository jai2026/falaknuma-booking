
import os
import re
import secrets

from admin import admin_bp

from datetime import date, datetime


from flask import (
    Flask,
    render_template,
    abort,
    request,
    redirect,
    url_for,
    flash,
    session
)


from database import (
    get_all_rooms,
    get_room_by_id,
    get_room_amenities,
    get_available_rooms,
    create_booking,
    get_booking_by_reference,
    find_booking,
    cancel_booking
)



app = Flask(__name__)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "local-development-only-change-before-deployment"
)

# Secure cookies when running on HTTPS in production.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = (
    os.environ.get("RENDER") == "true"
)

if os.environ.get("RENDER") == "true":
    if not os.environ.get("FLASK_SECRET_KEY"):
        raise RuntimeError(
            "FLASK_SECRET_KEY must be configured in production."
        )

app.register_blueprint(admin_bp)


def validate_search(checkin, checkout, guests_text):
    try:
        checkin_date = datetime.strptime(
            checkin, "%Y-%m-%d"
        ).date()

        checkout_date = datetime.strptime(
            checkout, "%Y-%m-%d"
        ).date()

        guests = int(guests_text)

    except (ValueError, TypeError):
        return None, "Enter valid dates and guests."

    if checkin_date < date.today():
        return None, "Check-in cannot be in the past."

    if checkout_date <= checkin_date:
        return None, "Check-out must be after check-in."

    if not 1 <= guests <= 6:
        return None, "Choose between 1 and 6 guests."

    nights = (checkout_date - checkin_date).days

    return (guests, nights), None


@app.route("/")
def home():
    rooms = get_all_rooms()

    return render_template(
        "index.html",
        rooms=rooms
    )


@app.route("/room/<int:room_id>")
def room_details(room_id):
    room = get_room_by_id(room_id)

    if room is None:
        abort(404)

    room["amenities"] = get_room_amenities(room_id)

    return render_template(
        "room_details.html",
        room=room
    )






@app.route("/book/<int:room_id>", methods=["GET", "POST"])
def book_room(room_id):
    room = get_room_by_id(room_id)

    if room is None:
        abort(404)

    if request.method == "POST":
        data = request.form
    else:
        data = request.args

    checkin = data.get("checkin", "").strip()
    checkout = data.get("checkout", "").strip()
    guests_text = data.get("guests", "2").strip()

    result, error = validate_search(
        checkin, checkout, guests_text
    )

    if error:
        flash(error)
        return redirect(url_for("home") + "#reservation")

    guests, nights = result

    if guests > room["guests"]:
        flash("This room cannot accommodate your party.")
        return redirect(url_for("home") + "#reservation")

    available_rooms = get_available_rooms(
        checkin, checkout, guests
    )

    available_room = next(
        (r for r in available_rooms if r["id"] == room_id),
        None
    )

    if available_room is None:
        flash("This room is no longer available.")
        return redirect(
            url_for(
                "availability",
                checkin=checkin,
                checkout=checkout,
                guests=guests
            )
        )

    total_price = room["price"] * nights

    if request.method == "POST":
        submitted_token = request.form.get(
            "csrf_token", ""
        )

        expected_token = session.get("booking_csrf")

        if (
            not expected_token
            or not secrets.compare_digest(
                submitted_token,
                expected_token
            )
        ):
            abort(400)

        guest_name = data.get(
            "guest_name", ""
        ).strip()

        guest_email = data.get(
            "guest_email", ""
        ).strip()

        guest_phone = data.get(
            "guest_phone", ""
        ).strip()

        if not 2 <= len(guest_name) <= 100:
            flash("Enter a valid guest name.")

        elif (
            len(guest_email) > 254
            or not re.fullmatch(
                r"[^@\s]+@[^@\s]+\.[^@\s]+",
                guest_email
            )
        ):
            flash("Enter a valid email address.")

        elif not re.fullmatch(
            r"\+?[0-9]{10,15}",
            guest_phone
        ):
            flash(
                "Enter a valid phone number "
                "with 10 to 15 digits."
            )

        else:
            reference, booking_error = create_booking(
                room_id=room_id,
                guest_name=guest_name,
                guest_email=guest_email,
                guest_phone=guest_phone,
                checkin=checkin,
                checkout=checkout,
                guests=guests
            )

            if reference:
                session.pop("booking_csrf", None)
                session["confirmed_booking"] = reference
                return redirect(
                    url_for(
                        "booking_confirmation",
                        reference=reference
                    )
                )

            flash(booking_error)

    if "booking_csrf" not in session:
        session["booking_csrf"] = secrets.token_urlsafe(32)

    return render_template(
        "booking.html",
        room=room,
        checkin=checkin,
        checkout=checkout,
        guests=guests,
        nights=nights,
        total_price=total_price,
        csrf_token=session["booking_csrf"]
    )


@app.route("/confirmation/<reference>")
def booking_confirmation(reference):
    booking = get_booking_by_reference(reference)

    if booking is None:
        abort(404)

    checkin_date = date.fromisoformat(
        booking["checkin"]
    )

    checkout_date = date.fromisoformat(
        booking["checkout"]
    )

    nights = (checkout_date - checkin_date).days

    total_price = booking["room_price"] * nights

    return render_template(
        "confirmation.html",
        booking=booking,
        nights=nights,
        total_price=total_price
    )


@app.route("/manage-booking", methods=["GET", "POST"])
def manage_booking():

    if request.method == "POST":

        reference = request.form.get(
            "booking_reference", ""
        ).strip().upper()

        email = request.form.get(
            "guest_email", ""
        ).strip()

        token = request.form.get("csrf_token", "")
        expected = session.get("manage_csrf", "")

        if not expected or not secrets.compare_digest(
            token, expected
        ):
            abort(400)

        booking = find_booking(reference, email)

        if booking is None:
            flash(
                "Booking not found. Please check "
                "your reference and email."
            )
        else:
            session["managed_booking"] = reference
            session["managed_email"] = email

            return redirect(
                url_for("booking_details")
            )

    if "manage_csrf" not in session:
        session["manage_csrf"] = secrets.token_urlsafe(32)

    return render_template(
        "manage_booking.html",
        csrf_token=session["manage_csrf"]
    )

@app.route("/my-booking")
def booking_details():

    reference = session.get("managed_booking")
    email = session.get("managed_email")

    if not reference or not email:
        return redirect(url_for("manage_booking"))

    booking = find_booking(reference, email)

    if booking is None:
        session.pop("managed_booking", None)
        session.pop("managed_email", None)
        return redirect(url_for("manage_booking"))

    checkin_date = date.fromisoformat(
        booking["checkin"]
    )

    checkout_date = date.fromisoformat(
        booking["checkout"]
    )

    nights = (checkout_date - checkin_date).days

    total_price = booking["room_price"] * nights

    can_cancel = (
        booking["status"] == "confirmed"
        and checkin_date > date.today()
    )

    if "cancel_csrf" not in session:
        session["cancel_csrf"] = secrets.token_urlsafe(32)

    return render_template(
        "booking_details.html",
        booking=booking,
        nights=nights,
        total_price=total_price,
        can_cancel=can_cancel,
        csrf_token=session["cancel_csrf"]
    )

@app.route("/cancel-booking", methods=["POST"])
def cancel_reservation():

    reference = session.get("managed_booking")
    email = session.get("managed_email")

    if not reference or not email:
        return redirect(url_for("manage_booking"))

    submitted_token = request.form.get(
        "csrf_token", ""
    )

    expected_token = session.get(
        "cancel_csrf", ""
    )

    if (
        not expected_token
        or not secrets.compare_digest(
            submitted_token,
            expected_token
        )
    ):
        abort(400)

    success = cancel_booking(reference, email)

    session.pop("cancel_csrf", None)

    if success:
        flash(
            "Your reservation has been "
            "cancelled successfully."
        )
    else:
        flash(
            "Cancellation was not possible. "
            "The booking may already be cancelled "
            "or the check-in date has arrived."
        )

    return redirect(url_for("booking_details"))


@app.route("/availability", methods=["GET"])
def availability():

    checkin = request.args.get("checkin", "").strip()
    checkout = request.args.get("checkout", "").strip()
    guests_text = request.args.get("guests", "2").strip()

    result, error = validate_search(
        checkin, checkout, guests_text
    )

    if error:
        flash(error)
        return redirect(url_for("home") + "#reservation")

    guests, nights = result

    rooms = get_available_rooms(
        checkin,
        checkout,
        guests
    )

    for room in rooms:
        room["total_price"] = room["price"] * nights

    return render_template(
        "availability.html",
        rooms=rooms,
        checkin=checkin,
        checkout=checkout,
        guests=guests,
        nights=nights
    )


if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLASK_DEBUG") == "1"
    )