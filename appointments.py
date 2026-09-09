from datetime import datetime
from mysql.connector import Error


class AppointmentManager:
    """
    Handles appointment operations.

    Database tables used:
        patients
        doctors
        users
        appointments

    Appointment lifecycle:
        Scheduled -> Completed
        Scheduled -> Deleted when cancelled
    """

    def __init__(self, db):
        self.db = db

    def format_time(self, appointment_time):
        """
        Convert MySQL TIME value into HH:MM format.

        mysql.connector may return MySQL TIME values
        as datetime.timedelta objects.
        """

        if hasattr(appointment_time, "strftime"):
            return appointment_time.strftime("%H:%M")

        total_seconds = int(
            appointment_time.total_seconds()
        )

        hours = (total_seconds // 3600) % 24
        minutes = (total_seconds % 3600) // 60

        return f"{hours:02d}:{minutes:02d}"

    def book_appointment(self):
        """Book a new appointment."""

        print("\n" + "=" * 55)
        print("               BOOK APPOINTMENT")
        print("=" * 55)

        patient_input = input("Patient ID: ").strip()
        doctor_input = input("Doctor ID: ").strip()

        appointment_date = input(
            "Appointment date (YYYY-MM-DD): "
        ).strip()

        appointment_time = input(
            "Appointment time (HH:MM): "
        ).strip()

        reason = input("Reason for visit: ").strip()

        # -----------------------------
        # Validate patient ID
        # -----------------------------
        try:
            patient_id = int(patient_input)

            if patient_id <= 0:
                raise ValueError

        except ValueError:
            print("\nInvalid patient ID.")
            return

        # -----------------------------
        # Validate doctor ID
        # -----------------------------
        try:
            doctor_id = int(doctor_input)

            if doctor_id <= 0:
                raise ValueError

        except ValueError:
            print("\nInvalid doctor ID.")
            return

        # -----------------------------
        # Validate date
        # -----------------------------
        try:
            selected_date = datetime.strptime(
                appointment_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:
            print("\nInvalid date. Use YYYY-MM-DD.")
            return

        # -----------------------------
        # Validate time
        # -----------------------------
        try:
            selected_time = datetime.strptime(
                appointment_time,
                "%H:%M"
            ).time()

        except ValueError:
            print("\nInvalid time. Use HH:MM.")
            return

        # -----------------------------
        # Prevent past appointments
        # -----------------------------
        today = datetime.now().date()
        current_time = datetime.now().time()

        if selected_date < today:
            print("\nAppointment date cannot be in the past.")
            return

        if (
            selected_date == today
            and selected_time <= current_time
        ):
            print(
                "\nAppointment time must be in the future."
            )
            return

        # -----------------------------
        # Validate reason
        # -----------------------------
        if len(reason) > 255:
            print(
                "\nReason is too long. "
                "Maximum 255 characters."
            )
            return

        # -----------------------------
        # Check patient
        # -----------------------------
        patient = self.db.fetch_one(
            """
            SELECT
                patient_id,
                patient_name
            FROM patients
            WHERE patient_id = %s
            """,
            (patient_id,)
        )

        if not patient:
            print("\nPatient not found.")
            return

        # -----------------------------
        # Check doctor
        # -----------------------------
        doctor = self.db.fetch_one(
            """
            SELECT
                d.doctor_id,
                u.full_name,
                d.specialization,
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
            print(
                "\nDoctor not found or doctor is inactive."
            )
            return

        # -----------------------------
        # Check double booking
        # -----------------------------
        existing_appointment = self.db.fetch_one(
            """
            SELECT appointment_id
            FROM appointments
            WHERE doctor_id = %s
              AND appointment_date = %s
              AND appointment_time = %s
            """,
            (
                doctor_id,
                selected_date,
                selected_time
            )
        )

        if existing_appointment:
            print(
                "\nDoctor is already booked at "
                "this date and time."
            )
            return

        # -----------------------------
        # Insert appointment
        # -----------------------------
        query = """
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
            (%s, %s, %s, %s, %s, 'Scheduled')
        """

        try:
            rows = self.db.execute(
                query,
                (
                    patient_id,
                    doctor_id,
                    selected_date,
                    selected_time,
                    reason if reason else None
                )
            )

            if rows <= 0:
                print(
                    "\nAppointment could not be booked."
                )
                return

            # Find the generated appointment ID.
            appointment = self.db.fetch_one(
                """
                SELECT appointment_id
                FROM appointments
                WHERE patient_id = %s
                  AND doctor_id = %s
                  AND appointment_date = %s
                  AND appointment_time = %s
                ORDER BY appointment_id DESC
                LIMIT 1
                """,
                (
                    patient_id,
                    doctor_id,
                    selected_date,
                    selected_time
                )
            )

            print(
                "\nAppointment booked successfully!"
            )

            if appointment:
                print(
                    "Appointment ID:",
                    appointment[0]
                )

            print(
                "Patient :",
                patient[1]
            )

            print(
                "Doctor  :",
                doctor[1]
            )

            print(
                "Date    :",
                selected_date
            )

            print(
                "Time    :",
                selected_time.strftime("%H:%M")
            )

            print("Status  : Scheduled")

        except Error as error:
            print(
                "\nUnable to book appointment:",
                error
            )

    def view_appointments(self):
        """Display all appointments."""

        print("\n" + "=" * 120)
        print("                           ALL APPOINTMENTS")
        print("=" * 120)

        query = """
            SELECT
                a.appointment_id,
                p.patient_name,
                u.full_name AS doctor_name,
                d.specialization,
                a.appointment_date,
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
            ORDER BY
                a.appointment_date,
                a.appointment_time
        """

        appointments = self.db.fetch_all(query)

        if not appointments:
            print("No appointments found.")
            return

        print(
            f"{'ID':<5}"
            f"{'Patient':<20}"
            f"{'Doctor':<20}"
            f"{'Specialization':<18}"
            f"{'Date':<12}"
            f"{'Time':<8}"
            f"{'Reason':<25}"
            f"{'Status':<12}"
        )

        print("-" * 120)

        for appointment in appointments:

            (
                appointment_id,
                patient_name,
                doctor_name,
                specialization,
                appointment_date,
                appointment_time,
                reason,
                status
            ) = appointment

            display_reason = reason or "N/A"

            print(
                f"{appointment_id:<5}"
                f"{patient_name:<20}"
                f"{doctor_name:<20}"
                f"{specialization:<18}"
                f"{str(appointment_date):<12}"
                f"{self.format_time(appointment_time):<8}"
                f"{display_reason[:24]:<25}"
                f"{status:<12}"
            )

    def cancel_appointment(self):
        """
        Cancel an appointment by permanently deleting
        the scheduled appointment record.

        Only Scheduled appointments can be cancelled.
        Completed appointments cannot be cancelled.
        """

        self.view_appointments()

        print("\n" + "=" * 55)
        print("             CANCEL APPOINTMENT")
        print("=" * 55)

        appointment_input = input(
            "Enter appointment ID: "
        ).strip()

        try:
            appointment_id = int(appointment_input)

            if appointment_id <= 0:
                raise ValueError

        except ValueError:
            print("\nInvalid appointment ID.")
            return

        # Get appointment details.
        appointment = self.db.fetch_one(
            """
            SELECT
                a.appointment_id,
                p.patient_name,
                u.full_name,
                a.appointment_date,
                a.appointment_time,
                a.status
            FROM appointments a
            JOIN patients p
                ON a.patient_id = p.patient_id
            JOIN doctors d
                ON a.doctor_id = d.doctor_id
            JOIN users u
                ON d.user_id = u.user_id
            WHERE a.appointment_id = %s
            """,
            (appointment_id,)
        )

        if not appointment:
            print("\nAppointment not found.")
            return

        status = appointment[5]

        # Only scheduled appointments can be cancelled.
        if status != "Scheduled":
            print(
                "\nOnly scheduled appointments "
                "can be cancelled."
            )
            return

        print("\nPatient :", appointment[1])
        print("Doctor  :", appointment[2])
        print("Date    :", appointment[3])
        print(
            "Time    :",
            self.format_time(appointment[4])
        )
        print("Status  :", status)

        confirm = input(
            "\nDelete this appointment? (y/n): "
        ).strip().lower()

        if confirm != "y":
            print("\nCancellation aborted.")
            return

        # Check whether a payment exists.
        payment = self.db.fetch_one(
            """
            SELECT payment_id
            FROM payments
            WHERE appointment_id = %s
            """,
            (appointment_id,)
        )

        if payment:
            print(
                "\nAppointment cannot be deleted because "
                "a payment already exists."
            )
            return

        try:
            rows = self.db.execute(
                """
                DELETE FROM appointments
                WHERE appointment_id = %s
                  AND status = 'Scheduled'
                """,
                (appointment_id,)
            )

            if rows > 0:
                print(
                    "\nAppointment cancelled successfully."
                )
                print("Appointment record deleted.")

            else:
                print(
                    "\nAppointment could not be cancelled."
                )

        except Error as error:
            print(
                "\nUnable to cancel appointment:",
                error
            )

    def get_doctor_id(self, user_id):
        """Return the doctor ID belonging to a logged-in doctor."""

        doctor = self.db.fetch_one(
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

    def view_my_appointments(self, user_id):
        """Display appointments belonging only to the logged-in doctor."""

        doctor_id = self.get_doctor_id(user_id)

        if not doctor_id:
            print(
                "\nDoctor profile not found or inactive."
            )
            return

        print("\n" + "=" * 105)
        print("                    MY APPOINTMENTS")
        print("=" * 105)

        query = """
            SELECT
                a.appointment_id,
                p.patient_name,
                p.phone,
                a.appointment_date,
                a.appointment_time,
                a.reason,
                a.status
            FROM appointments a
            JOIN patients p
                ON a.patient_id = p.patient_id
            WHERE a.doctor_id = %s
            ORDER BY
                a.appointment_date,
                a.appointment_time
        """

        appointments = self.db.fetch_all(
            query,
            (doctor_id,)
        )

        if not appointments:
            print("No appointments found.")
            return

        print(
            f"{'ID':<5}"
            f"{'Patient':<20}"
            f"{'Phone':<15}"
            f"{'Date':<12}"
            f"{'Time':<8}"
            f"{'Reason':<25}"
            f"{'Status':<12}"
        )

        print("-" * 105)

        for appointment in appointments:

            (
                appointment_id,
                patient_name,
                phone,
                appointment_date,
                appointment_time,
                reason,
                status
            ) = appointment

            display_reason = reason or "N/A"

            print(
                f"{appointment_id:<5}"
                f"{patient_name:<20}"
                f"{phone:<15}"
                f"{str(appointment_date):<12}"
                f"{self.format_time(appointment_time):<8}"
                f"{display_reason[:24]:<25}"
                f"{status:<12}"
            )

    def complete_appointment(self, user_id):
        """
        Mark the logged-in doctor's scheduled appointment
        as Completed.
        """

        doctor_id = self.get_doctor_id(user_id)

        if not doctor_id:
            print(
                "\nDoctor profile not found or inactive."
            )
            return

        self.view_my_appointments(user_id)

        print("\n" + "=" * 55)
        print("            COMPLETE APPOINTMENT")
        print("=" * 55)

        appointment_input = input(
            "Appointment ID: "
        ).strip()

        try:
            appointment_id = int(appointment_input)

            if appointment_id <= 0:
                raise ValueError

        except ValueError:
            print("\nInvalid appointment ID.")
            return

        appointment = self.db.fetch_one(
            """
            SELECT
                appointment_id,
                patient_id,
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
            print(
                "\nAppointment not found or it does "
                "not belong to you."
            )
            return

        if appointment[2] == "Completed":
            print(
                "\nAppointment is already completed."
            )
            return

        if appointment[2] != "Scheduled":
            print(
                "\nOnly scheduled appointments "
                "can be completed."
            )
            return

        try:
            rows = self.db.execute(
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

            if rows > 0:
                print(
                    "\nAppointment completed successfully."
                )
            else:
                print(
                    "\nAppointment could not be completed."
                )

        except Error as error:
            print(
                "\nUnable to complete appointment:",
                error
            )

    def add_consultation_notes(self, user_id):
        """Add or update consultation notes."""

        doctor_id = self.get_doctor_id(user_id)

        if not doctor_id:
            print(
                "\nDoctor profile not found or inactive."
            )
            return

        self.view_my_appointments(user_id)

        print("\n" + "=" * 55)
        print("          CONSULTATION NOTES")
        print("=" * 55)

        appointment_input = input(
            "Appointment ID: "
        ).strip()

        try:
            appointment_id = int(appointment_input)

            if appointment_id <= 0:
                raise ValueError

        except ValueError:
            print("\nInvalid appointment ID.")
            return

        appointment = self.db.fetch_one(
            """
            SELECT
                appointment_id,
                status,
                consultation_notes
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
            print(
                "\nAppointment not found or it does "
                "not belong to you."
            )
            return

        if appointment[1] != "Completed":
            print(
                "\nConsultation notes can be added "
                "only after completing the appointment."
            )
            return

        print("\nCurrent notes:")

        if appointment[2]:
            print(appointment[2])
        else:
            print("No notes added.")

        notes = input(
            "\nEnter consultation notes: "
        ).strip()

        if not notes:
            print(
                "\nConsultation notes cannot be empty."
            )
            return

        try:
            rows = self.db.execute(
                """
                UPDATE appointments
                SET consultation_notes = %s
                WHERE appointment_id = %s
                  AND doctor_id = %s
                  AND status = 'Completed'
                """,
                (
                    notes,
                    appointment_id,
                    doctor_id
                )
            )

            if rows > 0:
                print(
                    "\nConsultation notes saved successfully."
                )
            else:
                print("\nNo changes were made.")

        except Error as error:
            print(
                "\nUnable to save consultation notes:",
                error
            )

    def appointment_menu(self, role, user_id=None):
        """
        Display appointment operations based on role.

        Receptionist:
            Book
            View
            Cancel

        Doctor:
            View own appointments
            Complete
            Consultation notes

        Admin:
            View appointments
        """

        while True:

            if role == "Receptionist":

                print("\n" + "=" * 55)
                print("          APPOINTMENT MANAGEMENT")
                print("=" * 55)

                print("1. Book Appointment")
                print("2. View Appointments")
                print("3. Cancel Appointment")
                print("4. Back")

                choice = input(
                    "\nEnter your choice: "
                ).strip()

                if choice == "1":
                    self.book_appointment()

                elif choice == "2":
                    self.view_appointments()

                elif choice == "3":
                    self.cancel_appointment()

                elif choice == "4":
                    break

                else:
                    print(
                        "\nInvalid choice. Please try again."
                    )

            elif role == "Doctor":

                print("\n" + "=" * 55)
                print("           DOCTOR APPOINTMENTS")
                print("=" * 55)

                print("1. View My Appointments")
                print("2. Complete Appointment")
                print("3. Add Consultation Notes")
                print("4. Back")

                choice = input(
                    "\nEnter your choice: "
                ).strip()

                if choice == "1":
                    self.view_my_appointments(
                        user_id
                    )

                elif choice == "2":
                    self.complete_appointment(
                        user_id
                    )

                elif choice == "3":
                    self.add_consultation_notes(
                        user_id
                    )

                elif choice == "4":
                    break

                else:
                    print(
                        "\nInvalid choice. Please try again."
                    )

            elif role == "Admin":

                print("\n" + "=" * 55)
                print("             APPOINTMENTS")
                print("=" * 55)

                print("1. View Appointments")
                print("2. Back")

                choice = input(
                    "\nEnter your choice: "
                ).strip()

                if choice == "1":
                    self.view_appointments()

                elif choice == "2":
                    break

                else:
                    print(
                        "\nInvalid choice. Please try again."
                    )

            else:
                print("\nInvalid role.")
                break