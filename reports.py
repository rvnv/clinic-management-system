import csv
from decimal import Decimal
from datetime import datetime


class ReportManager:

    def __init__(self, db):
        self.db = db

    def format_time(self, appointment_time):
        """
        Convert MySQL TIME value into HH:MM.

        mysql.connector may return TIME as
        datetime.timedelta.
        """

        if hasattr(appointment_time, "strftime"):
            return appointment_time.strftime("%H:%M")

        total_seconds = int(
            appointment_time.total_seconds()
        )

        hours = (total_seconds // 3600) % 24
        minutes = (total_seconds % 3600) // 60

        return f"{hours:02d}:{minutes:02d}"

    # ============================================================
    # 1. TODAY'S APPOINTMENTS
    # ============================================================

    def todays_appointments(self):
        """Display today's appointments and create CSV."""

        today = datetime.now().date()

        print("\n" + "=" * 110)
        print("                  TODAY'S APPOINTMENTS")
        print("=" * 110)

        print("Date:", today)

        query = """
            SELECT
                a.appointment_id,
                p.patient_name,
                u.full_name AS doctor_name,
                d.specialization,
                a.appointment_time,
                a.reason,
                a.status
            FROM appointments a
            JOIN patients p
                ON a.patient_id = p.patient_id
            JOIN doctors d
                ON a.doctor_id = d.doctor_id
            JOIN users u
                ON d.user_id = u.user_id
            WHERE a.appointment_date = %s
            ORDER BY a.appointment_time
        """

        appointments = self.db.fetch_all(
            query,
            (today,)
        )

        print(
            f"\n{'ID':<5}"
            f"{'Patient':<22}"
            f"{'Doctor':<22}"
            f"{'Specialization':<20}"
            f"{'Time':<8}"
            f"{'Reason':<20}"
            f"{'Status':<12}"
        )

        print("-" * 110)

        if not appointments:
            print("No appointments found for today.")

        else:
            for appointment in appointments:

                (
                    appointment_id,
                    patient_name,
                    doctor_name,
                    specialization,
                    appointment_time,
                    reason,
                    status
                ) = appointment

                display_reason = reason or "N/A"

                print(
                    f"{appointment_id:<5}"
                    f"{patient_name:<22}"
                    f"{doctor_name:<22}"
                    f"{specialization:<20}"
                    f"{self.format_time(appointment_time):<8}"
                    f"{display_reason[:19]:<20}"
                    f"{status:<12}"
                )

        print("-" * 110)

        print(
            "Total Appointments:",
            len(appointments)
        )

        # -------------------------
        # Create CSV
        # -------------------------

        try:

            with open(
                "today_appointments.csv",
                "w",
                newline="",
                encoding="utf-8-sig"
            ) as file:

                writer = csv.writer(file)

                writer.writerow([
                    "Appointment ID",
                    "Patient",
                    "Doctor",
                    "Specialization",
                    "Date",
                    "Time",
                    "Reason",
                    "Status"
                ])

                for appointment in appointments:

                    (
                        appointment_id,
                        patient_name,
                        doctor_name,
                        specialization,
                        appointment_time,
                        reason,
                        status
                    ) = appointment

                    writer.writerow([
                        appointment_id,
                        patient_name,
                        doctor_name,
                        specialization,
                        today,
                        self.format_time(
                            appointment_time
                        ),
                        reason or "",
                        status
                    ])

            print(
                "\nCSV created: today_appointments.csv"
            )

        except OSError as error:

            print(
                "\nUnable to create CSV:",
                error
            )

    # ============================================================
    # 2. DOCTOR-WISE REPORT
    # ============================================================

    def doctor_report(self):
        """Display doctor statistics and create CSV."""

        print("\n" + "=" * 70)
        print("                  DOCTOR-WISE REPORT")
        print("=" * 70)

        doctor_input = input(
            "Enter doctor ID: "
        ).strip()

        try:

            doctor_id = int(doctor_input)

            if doctor_id <= 0:
                raise ValueError

        except ValueError:

            print("\nInvalid doctor ID.")
            return

        doctor = self.db.fetch_one(
            """
            SELECT
                d.doctor_id,
                u.full_name,
                d.specialization
            FROM doctors d
            JOIN users u
                ON d.user_id = u.user_id
            WHERE d.doctor_id = %s
            """,
            (doctor_id,)
        )

        if not doctor:

            print("\nDoctor not found.")
            return

        statistics = self.db.fetch_one(
            """
            SELECT
                COUNT(*),

                SUM(
                    CASE
                        WHEN status = 'Completed'
                        THEN 1
                        ELSE 0
                    END
                ),

                SUM(
                    CASE
                        WHEN status = 'Scheduled'
                        THEN 1
                        ELSE 0
                    END
                )

            FROM appointments

            WHERE doctor_id = %s
            """,
            (doctor_id,)
        )

        total = statistics[0] or 0
        completed = statistics[1] or 0
        scheduled = statistics[2] or 0

        print("\nDoctor         :", doctor[1])
        print("Specialization :", doctor[2])

        print("\nAppointment Statistics")
        print("-" * 45)

        print(
            "Total Appointments :",
            total
        )

        print(
            "Completed          :",
            completed
        )

        print(
            "Scheduled          :",
            scheduled
        )

        # -------------------------
        # Create CSV
        # -------------------------

        try:

            with open(
                "doctor_report.csv",
                "w",
                newline="",
                encoding="utf-8-sig"
            ) as file:

                writer = csv.writer(file)

                writer.writerow([
                    "Doctor ID",
                    "Doctor Name",
                    "Specialization",
                    "Total Appointments",
                    "Completed",
                    "Scheduled"
                ])

                writer.writerow([
                    doctor[0],
                    doctor[1],
                    doctor[2],
                    total,
                    completed,
                    scheduled
                ])

            print(
                "\nCSV created: doctor_report.csv"
            )

        except OSError as error:

            print(
                "\nUnable to create CSV:",
                error
            )

    # ============================================================
    # 3. PATIENT HISTORY
    # ============================================================

    def patient_history(self):
        """Display patient history and create CSV."""

        print("\n" + "=" * 90)
        print("                   PATIENT HISTORY")
        print("=" * 90)

        patient_input = input(
            "Enter patient ID: "
        ).strip()

        try:

            patient_id = int(patient_input)

            if patient_id <= 0:
                raise ValueError

        except ValueError:

            print("\nInvalid patient ID.")
            return

        patient = self.db.fetch_one(
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

            print("\nPatient not found.")
            return

        history = self.db.fetch_all(
            """
            SELECT
                a.appointment_date,
                a.appointment_time,
                u.full_name AS doctor_name,
                d.specialization,
                a.reason,
                a.status
            FROM appointments a
            JOIN doctors d
                ON a.doctor_id = d.doctor_id
            JOIN users u
                ON d.user_id = u.user_id
            WHERE a.patient_id = %s
            ORDER BY
                a.appointment_date DESC,
                a.appointment_time DESC
            """,
            (patient_id,)
        )

        print("\nPatient Name :", patient[1])
        print("Phone        :", patient[2])
        print("Gender       :", patient[3])

        print("\n" + "-" * 110)

        if not history:

            print(
                "No appointment history found."
            )

        else:

            print(
                f"{'Date':<12}"
                f"{'Time':<8}"
                f"{'Doctor':<22}"
                f"{'Specialization':<20}"
                f"{'Reason':<25}"
                f"{'Status':<12}"
            )

            print("-" * 110)

            for record in history:

                (
                    appointment_date,
                    appointment_time,
                    doctor_name,
                    specialization,
                    reason,
                    status
                ) = record

                display_reason = reason or "N/A"

                print(
                    f"{str(appointment_date):<12}"
                    f"{self.format_time(appointment_time):<8}"
                    f"{doctor_name:<22}"
                    f"{specialization:<20}"
                    f"{display_reason[:24]:<25}"
                    f"{status:<12}"
                )

        # -------------------------
        # Create CSV
        # -------------------------

        try:

            with open(
                "patient_history.csv",
                "w",
                newline="",
                encoding="utf-8-sig"
            ) as file:

                writer = csv.writer(file)

                writer.writerow([
                    "Patient ID",
                    "Patient Name",
                    "Phone",
                    "Gender",
                    "Date",
                    "Time",
                    "Doctor",
                    "Specialization",
                    "Reason",
                    "Status"
                ])

                for record in history:

                    (
                        appointment_date,
                        appointment_time,
                        doctor_name,
                        specialization,
                        reason,
                        status
                    ) = record

                    writer.writerow([
                        patient[0],
                        patient[1],
                        patient[2],
                        patient[3],
                        appointment_date,
                        self.format_time(
                            appointment_time
                        ),
                        doctor_name,
                        specialization,
                        reason or "",
                        status
                    ])

            print(
                "\nCSV created: patient_history.csv"
            )

        except OSError as error:

            print(
                "\nUnable to create CSV:",
                error
            )

    # ============================================================
    # 4. REVENUE REPORT
    # ============================================================

    def revenue_report(self):
        """Display revenue report and create CSV."""

        print("\n" + "=" * 75)
        print("                    REVENUE REPORT")
        print("=" * 75)

        summary = self.db.fetch_one(
            """
            SELECT
                COUNT(*),
                COALESCE(SUM(amount), 0)
            FROM payments
            """
        )

        total_payments = summary[0]

        total_revenue = Decimal(
            str(summary[1])
        )

        print(
            "\nTotal Payments :",
            total_payments
        )

        print(
            "Total Revenue  :",
            f"₹{total_revenue:.2f}"
        )

        print("\nPayment Method Summary")
        print("-" * 60)

        method_summary = self.db.fetch_all(
            """
            SELECT
                payment_method,
                COUNT(*),
                SUM(amount)
            FROM payments
            GROUP BY payment_method
            ORDER BY payment_method
            """
        )

        if not method_summary:

            print("No payment records found.")

        else:

            print(
                f"{'Method':<20}"
                f"{'Payments':<15}"
                f"{'Amount':<15}"
            )

            print("-" * 60)

            for record in method_summary:

                method, count, amount = record

                amount = Decimal(
                    str(amount)
                )

                print(
                    f"{method:<20}"
                    f"{count:<15}"
                    f"₹{amount:.2f}"
                )

        # -------------------------
        # Create CSV
        # -------------------------

        try:

            with open(
                "revenue_report.csv",
                "w",
                newline="",
                encoding="utf-8-sig"
            ) as file:

                writer = csv.writer(file)

                writer.writerow([
                    "Payment Method",
                    "Payment Count",
                    "Amount"
                ])

                for record in method_summary:

                    method, count, amount = record

                    writer.writerow([
                        method,
                        count,
                        Decimal(str(amount))
                    ])

                # No blank writerow here.
                # This prevents an empty row in the CSV.

                writer.writerow([
                    "TOTAL",
                    total_payments,
                    total_revenue
                ])

            print(
                "\nCSV created: revenue_report.csv"
            )

        except OSError as error:

            print(
                "\nUnable to create CSV:",
                error
            )

    # ============================================================
    # 5. MONTHLY CLINIC REPORT
    # ============================================================

    def monthly_report(self):
        """Display monthly clinic statistics and create CSV."""

        print("\n" + "=" * 75)
        print("                  MONTHLY CLINIC REPORT")
        print("=" * 75)

        month_input = input(
            "Enter month (YYYY-MM): "
        ).strip()

        try:

            selected_month = datetime.strptime(
                month_input,
                "%Y-%m"
            )

        except ValueError:

            print(
                "\nInvalid month. Use YYYY-MM."
            )
            return

        year = selected_month.year
        month = selected_month.month

        appointment_stats = self.db.fetch_one(
            """
            SELECT
                COUNT(*),

                SUM(
                    CASE
                        WHEN status = 'Completed'
                        THEN 1
                        ELSE 0
                    END
                ),

                SUM(
                    CASE
                        WHEN status = 'Scheduled'
                        THEN 1
                        ELSE 0
                    END
                )

            FROM appointments

            WHERE YEAR(appointment_date) = %s
              AND MONTH(appointment_date) = %s
            """,
            (year, month)
        )

        total_appointments = (
            appointment_stats[0] or 0
        )

        completed = (
            appointment_stats[1] or 0
        )

        scheduled = (
            appointment_stats[2] or 0
        )

        patient_count = self.db.fetch_one(
            """
            SELECT
                COUNT(DISTINCT patient_id)
            FROM appointments
            WHERE YEAR(appointment_date) = %s
              AND MONTH(appointment_date) = %s
            """,
            (year, month)
        )

        total_patients = (
            patient_count[0] or 0
        )

        revenue = self.db.fetch_one(
            """
            SELECT
                COALESCE(SUM(p.amount), 0)
            FROM payments p
            JOIN appointments a
                ON p.appointment_id =
                   a.appointment_id
            WHERE YEAR(a.appointment_date) = %s
              AND MONTH(a.appointment_date) = %s
            """,
            (year, month)
        )

        total_revenue = Decimal(
            str(revenue[0])
        )

        month_name = selected_month.strftime(
            "%B %Y"
        )

        print("\nMonth:", month_name)

        print("\nClinic Statistics")
        print("-" * 55)

        print(
            "Patients with Appointments :",
            total_patients
        )

        print(
            "Total Appointments         :",
            total_appointments
        )

        print(
            "Completed                  :",
            completed
        )

        print(
            "Scheduled                  :",
            scheduled
        )

        print(
            "Total Revenue              :",
            f"₹{total_revenue:.2f}"
        )

        # -------------------------
        # Create CSV
        # -------------------------

        try:

            with open(
                "monthly_clinic_report.csv",
                "w",
                newline="",
                encoding="utf-8-sig"
            ) as file:

                writer = csv.writer(file)

                writer.writerow([
                    "Month",
                    "Patients with Appointments",
                    "Total Appointments",
                    "Completed",
                    "Scheduled",
                    "Total Revenue"
                ])

                writer.writerow([
                    month_name,
                    total_patients,
                    total_appointments,
                    completed,
                    scheduled,
                    total_revenue
                ])

            print(
                "\nCSV created: monthly_clinic_report.csv"
            )

        except OSError as error:

            print(
                "\nUnable to create CSV:",
                error
            )

    # ============================================================
    # REPORT MENU
    # ============================================================

    def report_menu(self):
        """Display Admin report menu."""

        while True:

            print("\n" + "=" * 60)
            print("                    REPORTS")
            print("=" * 60)

            print("1. Today's Appointments")
            print("2. Doctor-wise Report")
            print("3. Patient History")
            print("4. Revenue Report")
            print("5. Monthly Clinic Report")
            print("6. Back")

            choice = input(
                "\nEnter your choice: "
            ).strip()

            if choice == "1":

                self.todays_appointments()

            elif choice == "2":

                self.doctor_report()

            elif choice == "3":

                self.patient_history()

            elif choice == "4":

                self.revenue_report()

            elif choice == "5":

                self.monthly_report()

            elif choice == "6":

                break

            else:

                print(
                    "\nInvalid choice. Please try again."
                )