import csv
import os
import sys

from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for
)


# ============================================================
# PROJECT PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


# ============================================================
# DATABASE
# ============================================================

from database import DatabaseManager


db = DatabaseManager()


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "CLINIC_SECRET_KEY",
    "clinic-management-secret-key"
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

if not db.connect():
    raise RuntimeError(
        "Unable to connect to the clinic_management database."
    )


# ============================================================
# REPORT DIRECTORY
# ============================================================

REPORT_DIR = BASE_DIR


# ============================================================
# AUTHENTICATION DECORATORS
# ============================================================

def login_required(view_function):
    """
    Allow access only to authenticated users.
    """

    @wraps(view_function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            flash(
                "Please login to continue.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        return view_function(*args, **kwargs)

    return wrapper


def role_required(*allowed_roles):
    """
    Allow access only to users having one of
    the specified roles.
    """

    @wraps(role_required)
    def decorator(view_function):

        @wraps(view_function)
        def wrapper(*args, **kwargs):

            if "user_id" not in session:
                flash(
                    "Please login to continue.",
                    "error"
                )

                return redirect(
                    url_for("login")
                )


            if session.get("role") not in allowed_roles:

                flash(
                    "You are not authorized to access this page.",
                    "error"
                )

                return redirect(
                    url_for("dashboard")
                )


            return view_function(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_doctor_id_for_user(user_id):
    """
    Return the active doctor_id belonging to a user.
    """

    doctor = db.fetch_one(
        """
        SELECT doctor_id
        FROM doctors
        WHERE user_id = %s
          AND status = 'Active'
        """,
        (user_id,)
    )

    if doctor:
        return doctor[0]

    return None


def parse_date(value):
    """
    Convert YYYY-MM-DD string into a date object.
    """

    try:
        return datetime.strptime(
            value,
            "%Y-%m-%d"
        ).date()

    except (ValueError, TypeError):
        return None


def parse_time(value):
    """
    Convert HH:MM string into a time object.
    """

    try:
        return datetime.strptime(
            value,
            "%H:%M"
        ).time()

    except (ValueError, TypeError):
        return None


def validate_name(value, field_name):
    """
    Basic validation for required text fields.
    """

    value = (value or "").strip()

    if not value:
        return f"{field_name} is required."

    return None


def parse_fee(value):
    """
    Convert consultation fee to Decimal.
    """

    try:

        fee = Decimal(
            str(value).strip()
        )

        if fee < 0:
            return None

        return fee

    except (
        InvalidOperation,
        TypeError,
        ValueError
    ):
        return None


def write_csv(filename, headers, rows):
    """
    Write a report CSV file and return its path.
    """

    path = REPORT_DIR / filename

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        writer = csv.writer(csv_file)

        writer.writerow(headers)

        for row in rows:
            writer.writerow(row)

    return path


def send_csv(filename, headers, rows):
    """
    Generate and download a CSV report.
    """

    path = write_csv(
        filename,
        headers,
        rows
    )

    return send_file(
        path,
        as_attachment=True,
        download_name=filename,
        mimetype="text/csv"
    )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    if "user_id" in session:
        return redirect(
            url_for("dashboard")
        )

    return redirect(
        url_for("login")
    )


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect(
            url_for("dashboard")
        )


    if request.method == "POST":

        username = (
            request.form.get("username")
            or ""
        ).strip()

        password = (
            request.form.get("password")
            or ""
        )


        if not username or not password:

            flash(
                "Username and password are required.",
                "error"
            )

            return render_template(
                "login.html"
            )


        user = db.fetch_one(
            """
            SELECT
                user_id,
                username,
                password,
                full_name,
                role,
                status
            FROM users
            WHERE username = %s
            """,
            (username,)
        )


        if not user:

            flash(
                "Invalid username or password.",
                "error"
            )

            return render_template(
                "login.html"
            )


        user_id = user[0]
        db_username = user[1]
        db_password = user[2]
        full_name = user[3]
        role = user[4]
        status = user[5]


        if status != "Active":

            flash(
                "Your account is inactive. Please contact the Admin.",
                "error"
            )

            return render_template(
                "login.html"
            )


        # Current schema stores plaintext passwords.
        # This comparison matches the existing database design.

        if password != db_password:

            flash(
                "Invalid username or password.",
                "error"
            )

            return render_template(
                "login.html"
            )


        session.clear()

        session["user_id"] = user_id
        session["username"] = db_username
        session["full_name"] = full_name
        session["role"] = role


        flash(
            f"Welcome, {full_name}!",
            "success"
        )


        return redirect(
            url_for("dashboard")
        )


    return render_template(
        "login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("login")
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():

    # --------------------------------------------------------
    # Common statistics
    # --------------------------------------------------------

    active_doctors = db.fetch_one(
        """
        SELECT COUNT(*)
        FROM doctors d
        JOIN users u
            ON d.user_id = u.user_id
        WHERE d.status = 'Active'
          AND u.status = 'Active'
        """
    )[0]


    total_patients = db.fetch_one(
        """
        SELECT COUNT(*)
        FROM patients
        """
    )[0]


    total_appointments = 0
    today_appointments = 0
    total_revenue = Decimal("0.00")
    doctor_appointments = 0
    doctor_revenue = Decimal("0.00")


    # --------------------------------------------------------
    # ADMIN
    # --------------------------------------------------------

    if session["role"] == "Admin":

        total_appointments = db.fetch_one(
            """
            SELECT COUNT(*)
            FROM appointments
            """
        )[0]


        revenue_result = db.fetch_one(
            """
            SELECT COALESCE(
                SUM(amount),
                0
            )
            FROM payments
            """
        )

        total_revenue = (
            revenue_result[0]
            if revenue_result and revenue_result[0] is not None
            else Decimal("0.00")
        )


    # --------------------------------------------------------
    # RECEPTIONIST
    # --------------------------------------------------------

    elif session["role"] == "Receptionist":

        total_appointments = db.fetch_one(
            """
            SELECT COUNT(*)
            FROM appointments
            """
        )[0]


        today_appointments = db.fetch_one(
            """
            SELECT COUNT(*)
            FROM appointments
            WHERE appointment_date = CURDATE()
            """
        )[0]


    # --------------------------------------------------------
    # DOCTOR
    # --------------------------------------------------------

    elif session["role"] == "Doctor":

        doctor_id = get_doctor_id_for_user(
            session["user_id"]
        )


        if doctor_id:

            doctor_appointments = db.fetch_one(
                """
                SELECT COUNT(*)
                FROM appointments
                WHERE doctor_id = %s
                """,
                (doctor_id,)
            )[0]


            doctor_revenue_result = db.fetch_one(
                """
                SELECT COALESCE(
                    SUM(p.amount),
                    0
                )
                FROM payments p
                JOIN appointments a
                    ON p.appointment_id = a.appointment_id
                WHERE a.doctor_id = %s
                """,
                (doctor_id,)
            )


            doctor_revenue = (
                doctor_revenue_result[0]
                if doctor_revenue_result
                and doctor_revenue_result[0] is not None
                else Decimal("0.00")
            )


    return render_template(
        "dashboard.html",

        active_doctors=active_doctors,

        total_patients=total_patients,

        total_appointments=total_appointments,

        today_appointments=today_appointments,

        total_revenue=total_revenue,

        doctor_appointments=doctor_appointments,

        doctor_revenue=doctor_revenue
    )


# ============================================================
# ADMIN HOME
# ============================================================

@app.route("/admin")
@role_required("Admin")
def admin():

    return redirect(
        url_for("dashboard")
    )


# ============================================================
# DOCTOR MANAGEMENT
# ============================================================

@app.route("/doctors")
@role_required(
    "Admin",
    "Receptionist"
)
def doctors():

    if session["role"] == "Admin":

        doctors = db.fetch_all(
            """
            SELECT
                d.doctor_id,
                d.user_id,
                u.username,
                u.full_name,
                d.specialization,
                d.consultation_fee,
                d.status,
                u.status
            FROM doctors d
            JOIN users u
                ON d.user_id = u.user_id
            ORDER BY d.doctor_id
            """
        )

    else:

        doctors = db.fetch_all(
            """
            SELECT
                d.doctor_id,
                d.user_id,
                u.username,
                u.full_name,
                d.specialization,
                d.consultation_fee,
                d.status,
                u.status
            FROM doctors d
            JOIN users u
                ON d.user_id = u.user_id
            WHERE d.status = 'Active'
              AND u.status = 'Active'
            ORDER BY u.full_name
            """
        )


    return render_template(
        "doctors.html",
        doctors=doctors
    )


# ============================================================
# ADD DOCTOR
# ============================================================

@app.route(
    "/doctors/add",
    methods=["GET", "POST"]
)
@role_required("Admin")
def add_doctor():

    if request.method == "POST":

        username = (
            request.form.get("username")
            or ""
        ).strip()

        password = (
            request.form.get("password")
            or ""
        )

        full_name = (
            request.form.get("full_name")
            or ""
        ).strip()

        specialization = (
            request.form.get("specialization")
            or ""
        ).strip()

        consultation_fee = parse_fee(
            request.form.get("consultation_fee")
        )


        if not username:

            flash(
                "Username is required.",
                "error"
            )

            return render_template(
                "add_doctor.html"
            )


        if not password:

            flash(
                "Password is required.",
                "error"
            )

            return render_template(
                "add_doctor.html"
            )


        if not full_name:

            flash(
                "Doctor full name is required.",
                "error"
            )

            return render_template(
                "add_doctor.html"
            )


        if not specialization:

            flash(
                "Specialization is required.",
                "error"
            )

            return render_template(
                "add_doctor.html"
            )


        if consultation_fee is None:

            flash(
                "Please enter a valid non-negative consultation fee.",
                "error"
            )

            return render_template(
                "add_doctor.html"
            )


        # ----------------------------------------------------
        # Check duplicate username
        # ----------------------------------------------------

        existing_user = db.fetch_one(
            """
            SELECT user_id
            FROM users
            WHERE username = %s
            """,
            (username,)
        )


        if existing_user:

            flash(
                "Username already exists.",
                "error"
            )

            return render_template(
                "add_doctor.html"
            )


        # ----------------------------------------------------
        # Create user account
        # ----------------------------------------------------

        result = db.execute(
            """
            INSERT INTO users
            (
                username,
                password,
                full_name,
                role,
                status
            )
            VALUES
            (
                %s,
                %s,
                %s,
                'Doctor',
                'Active'
            )
            """,
            (
                username,
                password,
                full_name
            )
        )


        if result != 1:

            flash(
                "Unable to create doctor account.",
                "error"
            )

            return render_template(
                "add_doctor.html"
            )


        # DatabaseManager.execute() returns rowcount,
        # so retrieve the generated user_id separately.

        user = db.fetch_one(
            """
            SELECT user_id
            FROM users
            WHERE username = %s
            """,
            (username,)
        )


        if not user:

            flash(
                "Doctor account was created but user information could not be retrieved.",
                "error"
            )

            return render_template(
                "add_doctor.html"
            )


        user_id = user[0]


        # ----------------------------------------------------
        # Create doctor profile
        # ----------------------------------------------------

        doctor_result = db.execute(
            """
            INSERT INTO doctors
            (
                user_id,
                specialization,
                consultation_fee,
                status
            )
            VALUES
            (
                %s,
                %s,
                %s,
                'Active'
            )
            """,
            (
                user_id,
                specialization,
                consultation_fee
            )
        )


        if doctor_result != 1:

            # Roll back the logical operation by removing
            # the user account because the doctor profile
            # could not be created.

            db.execute(
                """
                DELETE FROM users
                WHERE user_id = %s
                """,
                (user_id,)
            )


            flash(
                "Unable to create doctor profile.",
                "error"
            )

            return render_template(
                "add_doctor.html"
            )


        flash(
            "Doctor added successfully.",
            "success"
        )


        return redirect(
            url_for("doctors")
        )


    return render_template(
        "add_doctor.html"
    )


# ============================================================
# EDIT DOCTOR
# ============================================================

@app.route(
    "/doctors/<int:doctor_id>/edit",
    methods=["GET", "POST"]
)
@role_required("Admin")
def edit_doctor(doctor_id):

    doctor = db.fetch_one(
        """
        SELECT
            d.doctor_id,
            d.user_id,
            u.username,
            u.full_name,
            d.specialization,
            d.consultation_fee,
            d.status,
            u.status
        FROM doctors d
        JOIN users u
            ON d.user_id = u.user_id
        WHERE d.doctor_id = %s
        """,
        (doctor_id,)
    )


    if not doctor:

        flash(
            "Doctor not found.",
            "error"
        )

        return redirect(
            url_for("doctors")
        )


    if request.method == "POST":

        full_name = (
            request.form.get("full_name")
            or ""
        ).strip()

        specialization = (
            request.form.get("specialization")
            or ""
        ).strip()

        consultation_fee = parse_fee(
            request.form.get("consultation_fee")
        )


        if not full_name:

            flash(
                "Doctor full name is required.",
                "error"
            )

            return render_template(
                "edit_doctor.html",
                doctor=doctor
            )


        if not specialization:

            flash(
                "Specialization is required.",
                "error"
            )

            return render_template(
                "edit_doctor.html",
                doctor=doctor
            )


        if consultation_fee is None:

            flash(
                "Please enter a valid non-negative consultation fee.",
                "error"
            )

            return render_template(
                "edit_doctor.html",
                doctor=doctor
            )


        # ----------------------------------------------------
        # Update users
        # ----------------------------------------------------

        user_result = db.execute(
            """
            UPDATE users
            SET full_name = %s
            WHERE user_id = %s
            """,
            (
                full_name,
                doctor[1]
            )
        )


        # ----------------------------------------------------
        # Update doctors
        # ----------------------------------------------------

        doctor_result = db.execute(
            """
            UPDATE doctors
            SET
                specialization = %s,
                consultation_fee = %s
            WHERE doctor_id = %s
            """,
            (
                specialization,
                consultation_fee,
                doctor_id
            )
        )


        if user_result < 0 or doctor_result < 0:

            flash(
                "Unable to update doctor.",
                "error"
            )

            return render_template(
                "edit_doctor.html",
                doctor=doctor
            )


        flash(
            "Doctor details updated successfully.",
            "success"
        )


        return redirect(
            url_for("doctors")
        )


    return render_template(
        "edit_doctor.html",
        doctor=doctor
    )


# ============================================================
# ACTIVATE DOCTOR
# ============================================================

@app.route(
    "/doctors/<int:doctor_id>/activate",
    methods=["POST"]
)
@role_required("Admin")
def activate_doctor(doctor_id):

    doctor = db.fetch_one(
        """
        SELECT
            doctor_id,
            user_id
        FROM doctors
        WHERE doctor_id = %s
        """,
        (doctor_id,)
    )


    if not doctor:

        flash(
            "Doctor not found.",
            "error"
        )

        return redirect(
            url_for("doctors")
        )


    db.execute(
        """
        UPDATE doctors
        SET status = 'Active'
        WHERE doctor_id = %s
        """,
        (doctor_id,)
    )


    db.execute(
        """
        UPDATE users
        SET status = 'Active'
        WHERE user_id = %s
        """,
        (doctor[1],)
    )


    flash(
        "Doctor activated successfully.",
        "success"
    )


    return redirect(
        url_for("doctors")
    )


# ============================================================
# DEACTIVATE DOCTOR
# ============================================================

@app.route(
    "/doctors/<int:doctor_id>/deactivate",
    methods=["POST"]
)
@role_required("Admin")
def deactivate_doctor(doctor_id):

    doctor = db.fetch_one(
        """
        SELECT
            doctor_id,
            user_id
        FROM doctors
        WHERE doctor_id = %s
        """,
        (doctor_id,)
    )


    if not doctor:

        flash(
            "Doctor not found.",
            "error"
        )

        return redirect(
            url_for("doctors")
        )


    # --------------------------------------------------------
    # Do not deactivate a doctor who still has
    # future scheduled appointments.
    # --------------------------------------------------------

    future_appointment = db.fetch_one(
        """
        SELECT appointment_id
        FROM appointments
        WHERE doctor_id = %s
          AND status = 'Scheduled'
          AND (
                appointment_date > CURDATE()
                OR (
                    appointment_date = CURDATE()
                    AND appointment_time > CURTIME()
                )
              )
        LIMIT 1
        """,
        (doctor_id,)
    )


    if future_appointment:

        flash(
            "Doctor cannot be deactivated because future scheduled appointments exist.",
            "error"
        )

        return redirect(
            url_for("doctors")
        )


    db.execute(
        """
        UPDATE doctors
        SET status = 'Inactive'
        WHERE doctor_id = %s
        """,
        (doctor_id,)
    )


    db.execute(
        """
        UPDATE users
        SET status = 'Inactive'
        WHERE user_id = %s
        """,
        (doctor[1],)
    )


    flash(
        "Doctor deactivated successfully.",
        "success"
    )


    return redirect(
        url_for("doctors")
    )


# ============================================================
# DELETE DOCTOR
# ============================================================

@app.route(
    "/doctors/<int:doctor_id>/delete",
    methods=["POST"]
)
@role_required("Admin")
def delete_doctor(doctor_id):

    doctor = db.fetch_one(
        """
        SELECT
            doctor_id,
            user_id
        FROM doctors
        WHERE doctor_id = %s
        """,
        (doctor_id,)
    )


    if not doctor:

        flash(
            "Doctor not found.",
            "error"
        )

        return redirect(
            url_for("doctors")
        )


    # --------------------------------------------------------
    # Protect appointment history.
    # --------------------------------------------------------

    appointment_history = db.fetch_one(
        """
        SELECT appointment_id
        FROM appointments
        WHERE doctor_id = %s
        LIMIT 1
        """,
        (doctor_id,)
    )


    if appointment_history:

        flash(
            "Doctor cannot be deleted because appointment history exists.",
            "error"
        )

        return redirect(
            url_for("doctors")
        )


    # --------------------------------------------------------
    # Delete doctor profile first because it references users.
    # --------------------------------------------------------

    doctor_result = db.execute(
        """
        DELETE FROM doctors
        WHERE doctor_id = %s
        """,
        (doctor_id,)
    )


    if doctor_result != 1:

        flash(
            "Unable to delete doctor.",
            "error"
        )

        return redirect(
            url_for("doctors")
        )


    # --------------------------------------------------------
    # Delete corresponding user account.
    # --------------------------------------------------------

    db.execute(
        """
        DELETE FROM users
        WHERE user_id = %s
        """,
        (doctor[1],)
    )


    flash(
        "Doctor deleted successfully.",
        "success"
    )


    return redirect(
        url_for("doctors")
    )


# ============================================================
# PATIENT MANAGEMENT
# ============================================================

@app.route("/patients")
@role_required(
    "Admin",
    "Receptionist"
)
def patients():

    patients = db.fetch_all(
        """
        SELECT
            patient_id,
            patient_name,
            phone,
            gender
        FROM patients
        ORDER BY patient_id
        """
    )


    return render_template(
        "patients.html",
        patients=patients
    )


# ============================================================
# ADD PATIENT
# ============================================================

@app.route(
    "/patients/add",
    methods=["GET", "POST"]
)
@role_required("Receptionist")
def add_patient():

    if request.method == "POST":

        patient_name = (
            request.form.get("patient_name")
            or ""
        ).strip()

        phone = (
            request.form.get("phone")
            or ""
        ).strip()

        gender = (
            request.form.get("gender")
            or ""
        ).strip()


        if not patient_name:

            flash(
                "Patient name is required.",
                "error"
            )

            return render_template(
                "add_patient.html"
            )


        if not phone:

            flash(
                "Phone number is required.",
                "error"
            )

            return render_template(
                "add_patient.html"
            )


        if not gender:

            flash(
                "Gender is required.",
                "error"
            )

            return render_template(
                "add_patient.html"
            )


        # ----------------------------------------------------
        # Duplicate phone
        # ----------------------------------------------------

        existing = db.fetch_one(
            """
            SELECT patient_id
            FROM patients
            WHERE phone = %s
            """,
            (phone,)
        )


        if existing:

            flash(
                "A patient with this phone number already exists.",
                "error"
            )

            return render_template(
                "add_patient.html"
            )


        result = db.execute(
            """
            INSERT INTO patients
            (
                patient_name,
                phone,
                gender
            )
            VALUES
            (
                %s,
                %s,
                %s
            )
            """,
            (
                patient_name,
                phone,
                gender
            )
        )


        if result != 1:

            flash(
                "Unable to create patient.",
                "error"
            )

            return render_template(
                "add_patient.html"
            )


        flash(
            "Patient added successfully.",
            "success"
        )


        return redirect(
            url_for("patients")
        )


    return render_template(
        "add_patient.html"
    )


# ============================================================
# EDIT PATIENT
# ============================================================

@app.route(
    "/patients/<int:patient_id>/edit",
    methods=["GET", "POST"]
)
@role_required("Receptionist")
def edit_patient(patient_id):

    patient = db.fetch_one(
        """
        SELECT
            patient_id,
            patient_name,
            phone,
            gender
        FROM patients
        WHERE patient_id = %s
        """,
        (patient_id,)
    )


    if not patient:

        flash(
            "Patient not found.",
            "error"
        )

        return redirect(
            url_for("patients")
        )


    if request.method == "POST":

        patient_name = (
            request.form.get("patient_name")
            or ""
        ).strip()

        phone = (
            request.form.get("phone")
            or ""
        ).strip()

        gender = (
            request.form.get("gender")
            or ""
        ).strip()


        if not patient_name:

            flash(
                "Patient name is required.",
                "error"
            )

            return render_template(
                "edit_patient.html",
                patient=patient
            )


        if not phone:

            flash(
                "Phone number is required.",
                "error"
            )

            return render_template(
                "edit_patient.html",
                patient=patient
            )


        if not gender:

            flash(
                "Gender is required.",
                "error"
            )

            return render_template(
                "edit_patient.html",
                patient=patient
            )


        # ----------------------------------------------------
        # Check duplicate phone belonging to another patient.
        # ----------------------------------------------------

        duplicate = db.fetch_one(
            """
            SELECT patient_id
            FROM patients
            WHERE phone = %s
              AND patient_id <> %s
            """,
            (
                phone,
                patient_id
            )
        )


        if duplicate:

            flash(
                "Another patient already uses this phone number.",
                "error"
            )

            return render_template(
                "edit_patient.html",
                patient=patient
            )


        result = db.execute(
            """
            UPDATE patients
            SET
                patient_name = %s,
                phone = %s,
                gender = %s
            WHERE patient_id = %s
            """,
            (
                patient_name,
                phone,
                gender,
                patient_id
            )
        )


        if result < 0:

            flash(
                "Unable to update patient.",
                "error"
            )

            return render_template(
                "edit_patient.html",
                patient=patient
            )


        flash(
            "Patient updated successfully.",
            "success"
        )


        return redirect(
            url_for("patients")
        )


    return render_template(
        "edit_patient.html",
        patient=patient
    )


# ============================================================
# DELETE PATIENT
# ============================================================

@app.route(
    "/patients/<int:patient_id>/delete",
    methods=["POST"]
)
@role_required("Receptionist")
def delete_patient(patient_id):

    patient = db.fetch_one(
        """
        SELECT patient_id
        FROM patients
        WHERE patient_id = %s
        """,
        (patient_id,)
    )


    if not patient:

        flash(
            "Patient not found.",
            "error"
        )

        return redirect(
            url_for("patients")
        )


    # --------------------------------------------------------
    # Protect appointment history.
    # --------------------------------------------------------

    appointment = db.fetch_one(
        """
        SELECT appointment_id
        FROM appointments
        WHERE patient_id = %s
        LIMIT 1
        """,
        (patient_id,)
    )


    if appointment:

        flash(
            "Patient cannot be deleted because appointment history exists.",
            "error"
        )

        return redirect(
            url_for("patients")
        )


    result = db.execute(
        """
        DELETE FROM patients
        WHERE patient_id = %s
        """,
        (patient_id,)
    )


    if result != 1:

        flash(
            "Unable to delete patient.",
            "error"
        )

        return redirect(
            url_for("patients")
        )


    flash(
        "Patient deleted successfully.",
        "success"
    )


    return redirect(
        url_for("patients")
    )


# ============================================================
# APPOINTMENT MANAGEMENT
# ============================================================

@app.route("/appointments")
@role_required(
    "Admin",
    "Receptionist"
)
def appointments():

    appointments_data = db.fetch_all(
        """
        SELECT
            a.appointment_id,
            a.patient_id,
            a.doctor_id,
            a.appointment_date,
            a.appointment_time,
            a.reason,
            a.status,
            a.consultation_notes,
            p.patient_name,
            p.phone,
            u.full_name AS doctor_name,
            d.specialization
        FROM appointments a
        JOIN patients p
            ON a.patient_id = p.patient_id
        JOIN doctors d
            ON a.doctor_id = d.doctor_id
        JOIN users u
            ON d.user_id = u.user_id
        ORDER BY
            a.appointment_date DESC,
            a.appointment_time DESC
        """
    )


    return render_template(
        "appointments.html",
        appointments=appointments_data
    )


# ============================================================
# BOOK APPOINTMENT
# ============================================================

@app.route(
    "/appointments/book",
    methods=["GET", "POST"]
)
@role_required("Receptionist")
def book_appointment():

    patients_data = db.fetch_all(
        """
        SELECT
            patient_id,
            patient_name,
            phone
        FROM patients
        ORDER BY patient_name
        """
    )


    doctors_data = db.fetch_all(
        """
        SELECT
            d.doctor_id,
            u.full_name,
            d.specialization,
            d.consultation_fee
        FROM doctors d
        JOIN users u
            ON d.user_id = u.user_id
        WHERE d.status = 'Active'
          AND u.status = 'Active'
        ORDER BY u.full_name
        """
    )


    if request.method == "POST":

        patient_id_raw = (
            request.form.get("patient_id")
            or ""
        ).strip()

        doctor_id_raw = (
            request.form.get("doctor_id")
            or ""
        ).strip()

        appointment_date_raw = (
            request.form.get("appointment_date")
            or ""
        ).strip()

        appointment_time_raw = (
            request.form.get("appointment_time")
            or ""
        ).strip()

        reason = (
            request.form.get("reason")
            or ""
        ).strip()


        # ----------------------------------------------------
        # Numeric IDs
        # ----------------------------------------------------

        try:

            patient_id = int(
                patient_id_raw
            )

            doctor_id = int(
                doctor_id_raw
            )

        except ValueError:

            flash(
                "Invalid patient or doctor selection.",
                "error"
            )

            return render_template(
                "book_appointment.html",
                patients=patients_data,
                doctors=doctors_data
            )


        # ----------------------------------------------------
        # Date / time
        # ----------------------------------------------------

        appointment_date = parse_date(
            appointment_date_raw
        )

        appointment_time = parse_time(
            appointment_time_raw
        )


        if appointment_date is None:

            flash(
                "Please enter a valid appointment date.",
                "error"
            )

            return render_template(
                "book_appointment.html",
                patients=patients_data,
                doctors=doctors_data
            )


        if appointment_time is None:

            flash(
                "Please enter a valid appointment time.",
                "error"
            )

            return render_template(
                "book_appointment.html",
                patients=patients_data,
                doctors=doctors_data
            )


        # ----------------------------------------------------
        # Date validation
        # ----------------------------------------------------

        today = date.today()

        if appointment_date < today:

            flash(
                "Appointment date cannot be in the past.",
                "error"
            )

            return render_template(
                "book_appointment.html",
                patients=patients_data,
                doctors=doctors_data
            )


        if appointment_date == today:

            current_time = datetime.now().time()

            if appointment_time <= current_time:

                flash(
                    "Today's appointment time must be in the future.",
                    "error"
                )

                return render_template(
                    "book_appointment.html",
                    patients=patients_data,
                    doctors=doctors_data
                )


        # ----------------------------------------------------
        # Reason length
        # ----------------------------------------------------

        if len(reason) > 255:

            flash(
                "Reason cannot exceed 255 characters.",
                "error"
            )

            return render_template(
                "book_appointment.html",
                patients=patients_data,
                doctors=doctors_data
            )


        # ----------------------------------------------------
        # Patient exists
        # ----------------------------------------------------

        patient = db.fetch_one(
            """
            SELECT patient_id
            FROM patients
            WHERE patient_id = %s
            """,
            (patient_id,)
        )


        if not patient:

            flash(
                "Selected patient does not exist.",
                "error"
            )

            return render_template(
                "book_appointment.html",
                patients=patients_data,
                doctors=doctors_data
            )


        # ----------------------------------------------------
        # Doctor must be active
        # ----------------------------------------------------

        doctor = db.fetch_one(
            """
            SELECT
                d.doctor_id,
                d.consultation_fee
            FROM doctors d
            JOIN users u
                ON d.user_id = u.user_id
            WHERE d.doctor_id = %s
              AND d.status = 'Active'
              AND u.status = 'Active'
            """,
            (doctor_id,)
        )


        if not doctor:

            flash(
                "Selected doctor is not active or does not exist.",
                "error"
            )

            return render_template(
                "book_appointment.html",
                patients=patients_data,
                doctors=doctors_data
            )


        # ----------------------------------------------------
        # Duplicate scheduled appointment
        # ----------------------------------------------------

        duplicate = db.fetch_one(
            """
            SELECT appointment_id
            FROM appointments
            WHERE doctor_id = %s
              AND appointment_date = %s
              AND appointment_time = %s
              AND status = 'Scheduled'
            """,
            (
                doctor_id,
                appointment_date,
                appointment_time
            )
        )


        if duplicate:

            flash(
                "The doctor already has a scheduled appointment at this date and time.",
                "error"
            )

            return render_template(
                "book_appointment.html",
                patients=patients_data,
                doctors=doctors_data
            )


        # ----------------------------------------------------
        # Insert appointment
        # ----------------------------------------------------

        result = db.execute(
            """
            INSERT INTO appointments
            (
                patient_id,
                doctor_id,
                appointment_date,
                appointment_time,
                reason,
                status
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                'Scheduled'
            )
            """,
            (
                patient_id,
                doctor_id,
                appointment_date,
                appointment_time,
                reason if reason else None
            )
        )


        if result != 1:

            flash(
                "Unable to book appointment.",
                "error"
            )

            return render_template(
                "book_appointment.html",
                patients=patients_data,
                doctors=doctors_data
            )


        flash(
            "Appointment booked successfully.",
            "success"
        )


        return redirect(
            url_for("appointments")
        )


    return render_template(
        "book_appointment.html",
        patients=patients_data,
        doctors=doctors_data
    )


# ============================================================
# CANCEL APPOINTMENT
# ============================================================

@app.route(
    "/appointments/<int:appointment_id>/cancel",
    methods=["POST"]
)
@role_required("Receptionist")
def cancel_appointment(appointment_id):

    appointment = db.fetch_one(
        """
        SELECT
            appointment_id,
            status
        FROM appointments
        WHERE appointment_id = %s
        """,
        (appointment_id,)
    )


    if not appointment:

        flash(
            "Appointment not found.",
            "error"
        )

        return redirect(
            url_for("appointments")
        )


    if appointment[1] != "Scheduled":

        flash(
            "Only scheduled appointments can be cancelled.",
            "error"
        )

        return redirect(
            url_for("appointments")
        )


    # A scheduled appointment should normally have
    # no payment, but protect against inconsistent data.

    payment = db.fetch_one(
        """
        SELECT payment_id
        FROM payments
        WHERE appointment_id = %s
        """,
        (appointment_id,)
    )


    if payment:

        flash(
            "This appointment already has a payment and cannot be cancelled.",
            "error"
        )

        return redirect(
            url_for("appointments")
        )


    # --------------------------------------------------------
    # Final requirement:
    # cancellation permanently deletes the appointment.
    # --------------------------------------------------------

    result = db.execute(
        """
        DELETE FROM appointments
        WHERE appointment_id = %s
          AND status = 'Scheduled'
        """,
        (appointment_id,)
    )


    if result != 1:

        flash(
            "Unable to cancel appointment.",
            "error"
        )

        return redirect(
            url_for("appointments")
        )


    flash(
        "Appointment cancelled successfully.",
        "success"
    )


    return redirect(
        url_for("appointments")
    )


# ============================================================
# DOCTOR - MY APPOINTMENTS
# ============================================================

@app.route("/my-appointments")
@role_required("Doctor")
def my_appointments():

    doctor_id = get_doctor_id_for_user(
        session["user_id"]
    )


    if not doctor_id:

        flash(
            "Active doctor profile not found.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )


    appointments_data = db.fetch_all(
        """
        SELECT
            a.appointment_id,
            a.patient_id,
            a.doctor_id,
            a.appointment_date,
            a.appointment_time,
            a.reason,
            a.status,
            a.consultation_notes,
            p.patient_name,
            p.phone
        FROM appointments a
        JOIN patients p
            ON a.patient_id = p.patient_id
        WHERE a.doctor_id = %s
        ORDER BY
            a.appointment_date,
            a.appointment_time
        """,
        (doctor_id,)
    )


    return render_template(
        "my_appointments.html",
        appointments=appointments_data
    )


# ============================================================
# COMPLETE APPOINTMENT
# ============================================================

@app.route(
    "/appointments/<int:appointment_id>/complete",
    methods=["POST"]
)
@role_required("Doctor")
def complete_appointment(appointment_id):

    doctor_id = get_doctor_id_for_user(
        session["user_id"]
    )


    if not doctor_id:

        flash(
            "Active doctor profile not found.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )


    appointment = db.fetch_one(
        """
        SELECT
            appointment_id,
            status
        FROM appointments
        WHERE appointment_id = %s
          AND doctor_id = %s
        """,
        (
            appointment_id,
            doctor_id
        )
    )


    if not appointment:

        flash(
            "Appointment not found or it does not belong to you.",
            "error"
        )

        return redirect(
            url_for("my_appointments")
        )


    if appointment[1] != "Scheduled":

        flash(
            "Only scheduled appointments can be completed.",
            "error"
        )

        return redirect(
            url_for("my_appointments")
        )


    result = db.execute(
        """
        UPDATE appointments
        SET status = 'Completed'
        WHERE appointment_id = %s
          AND doctor_id = %s
          AND status = 'Scheduled'
        """,
        (
            appointment_id,
            doctor_id
        )
    )


    if result != 1:

        flash(
            "Unable to complete appointment.",
            "error"
        )

        return redirect(
            url_for("my_appointments")
        )


    flash(
        "Appointment marked as completed.",
        "success"
    )


    return redirect(
        url_for("my_appointments")
    )


# ============================================================
# CONSULTATION NOTES
# ============================================================

@app.route(
    "/appointments/<int:appointment_id>/notes",
    methods=["GET", "POST"]
)
@role_required("Doctor")
def consultation_notes(appointment_id):

    doctor_id = get_doctor_id_for_user(
        session["user_id"]
    )


    if not doctor_id:

        flash(
            "Active doctor profile not found.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )


    appointment = db.fetch_one(
        """
        SELECT
            a.appointment_id,
            p.patient_name,
            p.phone,
            a.appointment_date,
            a.appointment_time,
            a.reason,
            a.status,
            a.consultation_notes
        FROM appointments a
        JOIN patients p
            ON a.patient_id = p.patient_id
        WHERE a.appointment_id = %s
          AND a.doctor_id = %s
        """,
        (
            appointment_id,
            doctor_id
        )
    )


    if not appointment:

        flash(
            "Appointment not found or it does not belong to you.",
            "error"
        )

        return redirect(
            url_for("my_appointments")
        )


    if request.method == "POST":

        if appointment[6] == "Cancelled":

            flash(
                "Consultation notes cannot be added to a cancelled appointment.",
                "error"
            )

            return redirect(
                url_for(
                    "consultation_notes",
                    appointment_id=appointment_id
                )
            )


        notes = (
            request.form.get("consultation_notes")
            or ""
        ).strip()


        if not notes:

            flash(
                "Consultation notes cannot be empty.",
                "error"
            )

            return render_template(
                "consultation_notes.html",
                appointment=appointment
            )


        if len(notes) > 5000:

            flash(
                "Consultation notes cannot exceed 5000 characters.",
                "error"
            )

            return render_template(
                "consultation_notes.html",
                appointment=appointment
            )


        result = db.execute(
            """
            UPDATE appointments
            SET consultation_notes = %s
            WHERE appointment_id = %s
              AND doctor_id = %s
            """,
            (
                notes,
                appointment_id,
                doctor_id
            )
        )


        if result < 0:

            flash(
                "Unable to save consultation notes.",
                "error"
            )

            return render_template(
                "consultation_notes.html",
                appointment=appointment
            )


        flash(
            "Consultation notes saved successfully.",
            "success"
        )


        return redirect(
            url_for("my_appointments")
        )


    return render_template(
        "consultation_notes.html",
        appointment=appointment
    )


# ============================================================
# PAYMENT MANAGEMENT
# ============================================================

@app.route("/payments")
@role_required(
    "Admin",
    "Receptionist"
)
def payments():

    payments_data = db.fetch_all(
        """
        SELECT
            p.payment_id,
            p.appointment_id,
            p.amount,
            p.payment_method,
            pt.patient_name,
            u.full_name AS doctor_name,
            a.appointment_date,
            a.appointment_time
        FROM payments p
        JOIN appointments a
            ON p.appointment_id = a.appointment_id
        JOIN patients pt
            ON a.patient_id = pt.patient_id
        JOIN doctors d
            ON a.doctor_id = d.doctor_id
        JOIN users u
            ON d.user_id = u.user_id
        ORDER BY
            p.payment_id DESC
        """
    )


    return render_template(
        "payments.html",
        payments=payments_data
    )


# ============================================================
# ADD PAYMENT
# ============================================================

@app.route(
    "/payments/add",
    methods=["GET", "POST"]
)
@role_required("Receptionist")
def add_payment():

    # --------------------------------------------------------
    # Only completed appointments without an existing
    # payment are shown.
    # --------------------------------------------------------

    appointments_data = db.fetch_all(
        """
        SELECT
            a.appointment_id,
            pt.patient_name,
            u.full_name AS doctor_name,
            a.appointment_date,
            a.appointment_time,
            d.consultation_fee
        FROM appointments a
        JOIN patients pt
            ON a.patient_id = pt.patient_id
        JOIN doctors d
            ON a.doctor_id = d.doctor_id
        JOIN users u
            ON d.user_id = u.user_id
        LEFT JOIN payments p
            ON a.appointment_id = p.appointment_id
        WHERE a.status = 'Completed'
          AND p.payment_id IS NULL
        ORDER BY
            a.appointment_date DESC,
            a.appointment_time DESC
        """
    )


    if request.method == "POST":

        appointment_id_raw = (
            request.form.get("appointment_id")
            or ""
        ).strip()

        payment_method = (
            request.form.get("payment_method")
            or ""
        ).strip()


        # ----------------------------------------------------
        # Appointment ID
        # ----------------------------------------------------

        try:

            appointment_id = int(
                appointment_id_raw
            )

        except ValueError:

            flash(
                "Invalid appointment selection.",
                "error"
            )

            return render_template(
                "add_payment.html",
                appointments=appointments_data
            )


        # ----------------------------------------------------
        # Payment method
        # ----------------------------------------------------

        allowed_methods = {
            "Cash",
            "UPI",
            "Card"
        }


        if payment_method not in allowed_methods:

            flash(
                "Invalid payment method.",
                "error"
            )

            return render_template(
                "add_payment.html",
                appointments=appointments_data
            )


        # ----------------------------------------------------
        # Re-fetch payment data from database.
        #
        # Never trust a fee submitted by the browser.
        # ----------------------------------------------------

        appointment = db.fetch_one(
            """
            SELECT
                a.appointment_id,
                a.status,
                d.consultation_fee
            FROM appointments a
            JOIN doctors d
                ON a.doctor_id = d.doctor_id
            WHERE a.appointment_id = %s
            """,
            (appointment_id,)
        )


        if not appointment:

            flash(
                "Appointment not found.",
                "error"
            )

            return render_template(
                "add_payment.html",
                appointments=appointments_data
            )


        if appointment[1] != "Completed":

            flash(
                "Payment can only be recorded for a completed appointment.",
                "error"
            )

            return render_template(
                "add_payment.html",
                appointments=appointments_data
            )


        # ----------------------------------------------------
        # Check existing payment.
        # ----------------------------------------------------

        existing_payment = db.fetch_one(
            """
            SELECT payment_id
            FROM payments
            WHERE appointment_id = %s
            """,
            (appointment_id,)
        )


        if existing_payment:

            flash(
                "A payment already exists for this appointment.",
                "error"
            )

            return render_template(
                "add_payment.html",
                appointments=appointments_data
            )


        # ----------------------------------------------------
        # Authoritative amount.
        # ----------------------------------------------------

        amount = appointment[2]


        if amount is None:

            flash(
                "Doctor consultation fee is not available.",
                "error"
            )

            return render_template(
                "add_payment.html",
                appointments=appointments_data
            )


        # ----------------------------------------------------
        # Insert payment.
        # ----------------------------------------------------

        result = db.execute(
            """
            INSERT INTO payments
            (
                appointment_id,
                amount,
                payment_method
            )
            VALUES
            (
                %s,
                %s,
                %s
            )
            """,
            (
                appointment_id,
                amount,
                payment_method
            )
        )


        if result != 1:

            flash(
                "Unable to record payment.",
                "error"
            )

            return render_template(
                "add_payment.html",
                appointments=appointments_data
            )


        flash(
            "Payment recorded successfully.",
            "success"
        )


        return redirect(
            url_for("payments")
        )


    return render_template(
        "add_payment.html",
        appointments=appointments_data
    )


# ============================================================
# REPORTS MAIN PAGE
# ============================================================

@app.route("/reports")
@role_required("Admin")
def reports():

    return render_template(
        "reports.html"
    )


# ============================================================
# REPORT 1:
# TODAY'S APPOINTMENTS
# ============================================================

@app.route("/reports/today-appointments")
@role_required("Admin")
def today_appointments_report():

    rows = db.fetch_all(
        """
        SELECT
            a.appointment_id,
            p.patient_name,
            p.phone,
            u.full_name AS doctor_name,
            d.specialization,
            a.appointment_date,
            a.appointment_time,
            a.reason,
            a.status,
            a.consultation_notes
        FROM appointments a
        JOIN patients p
            ON a.patient_id = p.patient_id
        JOIN doctors d
            ON a.doctor_id = d.doctor_id
        JOIN users u
            ON d.user_id = u.user_id
        WHERE a.appointment_date = CURDATE()
        ORDER BY a.appointment_time
        """
    )


    headers = [
        "Appointment ID",
        "Patient Name",
        "Phone",
        "Doctor Name",
        "Specialization",
        "Appointment Date",
        "Appointment Time",
        "Reason",
        "Status",
        "Consultation Notes"
    ]


    return send_csv(
        "today_appointments.csv",
        headers,
        rows
    )


# ============================================================
# REPORT 2:
# DOCTOR REPORT
# ============================================================

@app.route("/reports/doctor")
@role_required("Admin")
def doctor_report():

    rows = db.fetch_all(
        """
        SELECT
            d.doctor_id,
            u.username,
            u.full_name,
            d.specialization,
            d.consultation_fee,
            d.status,
            COUNT(DISTINCT a.appointment_id) AS total_appointments,
            COUNT(
                DISTINCT CASE
                    WHEN a.status = 'Completed'
                    THEN a.appointment_id
                END
            ) AS completed_appointments,
            COALESCE(
                SUM(p.amount),
                0
            ) AS total_revenue
        FROM doctors d
        JOIN users u
            ON d.user_id = u.user_id
        LEFT JOIN appointments a
            ON d.doctor_id = a.doctor_id
        LEFT JOIN payments p
            ON a.appointment_id = p.appointment_id
        GROUP BY
            d.doctor_id,
            u.username,
            u.full_name,
            d.specialization,
            d.consultation_fee,
            d.status
        ORDER BY
            u.full_name
        """
    )


    headers = [
        "Doctor ID",
        "Username",
        "Doctor Name",
        "Specialization",
        "Consultation Fee",
        "Doctor Status",
        "Total Appointments",
        "Completed Appointments",
        "Total Revenue"
    ]


    return send_csv(
        "doctor_report.csv",
        headers,
        rows
    )


# ============================================================
# REPORT 3:
# PATIENT HISTORY
# ============================================================

@app.route("/reports/patient-history")
@role_required("Admin")
def patient_history_report():

    rows = db.fetch_all(
        """
        SELECT
            p.patient_id,
            p.patient_name,
            p.phone,
            p.gender,
            a.appointment_id,
            a.appointment_date,
            a.appointment_time,
            u.full_name AS doctor_name,
            d.specialization,
            a.reason,
            a.status,
            a.consultation_notes
        FROM patients p
        LEFT JOIN appointments a
            ON p.patient_id = a.patient_id
        LEFT JOIN doctors d
            ON a.doctor_id = d.doctor_id
        LEFT JOIN users u
            ON d.user_id = u.user_id
        ORDER BY
            p.patient_name,
            a.appointment_date,
            a.appointment_time
        """
    )


    headers = [
        "Patient ID",
        "Patient Name",
        "Phone",
        "Gender",
        "Appointment ID",
        "Appointment Date",
        "Appointment Time",
        "Doctor Name",
        "Specialization",
        "Reason",
        "Status",
        "Consultation Notes"
    ]


    return send_csv(
        "patient_history.csv",
        headers,
        rows
    )


# ============================================================
# REPORT 4:
# REVENUE REPORT
# ============================================================

@app.route("/reports/revenue")
@role_required("Admin")
def revenue_report():

    rows = db.fetch_all(
        """
        SELECT
            p.payment_id,
            p.appointment_id,
            pt.patient_name,
            u.full_name AS doctor_name,
            d.specialization,
            a.appointment_date,
            a.appointment_time,
            p.amount,
            p.payment_method
        FROM payments p
        JOIN appointments a
            ON p.appointment_id = a.appointment_id
        JOIN patients pt
            ON a.patient_id = pt.patient_id
        JOIN doctors d
            ON a.doctor_id = d.doctor_id
        JOIN users u
            ON d.user_id = u.user_id
        ORDER BY
            a.appointment_date DESC,
            p.payment_id DESC
        """
    )


    headers = [
        "Payment ID",
        "Appointment ID",
        "Patient Name",
        "Doctor Name",
        "Specialization",
        "Appointment Date",
        "Appointment Time",
        "Amount",
        "Payment Method"
    ]


    return send_csv(
        "revenue_report.csv",
        headers,
        rows
    )


# ============================================================
# REPORT 5:
# MONTHLY CLINIC REPORT
# ============================================================

@app.route("/reports/monthly")
@role_required("Admin")
def monthly_report():

    rows = db.fetch_all(
        """
        SELECT
            DATE_FORMAT(
                a.appointment_date,
                '%Y-%m'
            ) AS report_month,

            COUNT(
                DISTINCT a.appointment_id
            ) AS total_appointments,

            COUNT(
                DISTINCT CASE
                    WHEN a.status = 'Completed'
                    THEN a.appointment_id
                END
            ) AS completed_appointments,

            COUNT(
                DISTINCT CASE
                    WHEN a.status = 'Scheduled'
                    THEN a.appointment_id
                END
            ) AS scheduled_appointments,

            COALESCE(
                SUM(p.amount),
                0
            ) AS total_revenue

        FROM appointments a

        LEFT JOIN payments p
            ON a.appointment_id = p.appointment_id

        GROUP BY
            DATE_FORMAT(
                a.appointment_date,
                '%Y-%m'
            )

        ORDER BY
            report_month DESC
        """
    )


    headers = [
        "Month",
        "Total Appointments",
        "Completed Appointments",
        "Scheduled Appointments",
        "Total Revenue"
    ]


    return send_csv(
        "monthly_clinic_report.csv",
        headers,
        rows
    )


# ============================================================
# APPLICATION START
# ============================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )