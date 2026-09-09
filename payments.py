from decimal import Decimal
from mysql.connector import Error


class PaymentManager:
    """
    Handles payment operations.

    Database tables:
        payments
        appointments
        patients
        doctors
        users

    Payment rules:
        1. Only a COMPLETED appointment can receive payment.
        2. One appointment can have only one payment.
        3. Payment amount comes automatically from the doctor's
           consultation fee.
    """

    VALID_METHODS = {
        "cash": "Cash",
        "upi": "UPI",
        "card": "Card"
    }

    def __init__(self, db):
        self.db = db

    def record_payment(self):
        """Record payment for a completed appointment."""

        print("\n" + "=" * 55)
        print("                RECORD PAYMENT")
        print("=" * 55)

        appointment_input = input("Appointment ID: ").strip()

        # -------------------------------------------------
        # Validate appointment ID
        # -------------------------------------------------
        try:
            appointment_id = int(appointment_input)

            if appointment_id <= 0:
                raise ValueError

        except ValueError:
            print("\nInvalid appointment ID.")
            return

        # -------------------------------------------------
        # Get appointment details
        # -------------------------------------------------
        appointment = self.db.fetch_one(
            """
            SELECT
                a.appointment_id,
                a.status,
                p.patient_name,
                u.full_name AS doctor_name,
                d.consultation_fee
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

        status = appointment[1]
        patient_name = appointment[2]
        doctor_name = appointment[3]

        try:
            consultation_fee = Decimal(
                str(appointment[4])
            )
        except Exception:
            print("\nInvalid consultation fee.")
            return

        # -------------------------------------------------
        # Payment allowed only for completed appointment
        # -------------------------------------------------
        if status != "Completed":
            print(
                "\nPayment can be recorded only after "
                "the appointment is completed."
            )
            return

        # -------------------------------------------------
        # Check whether payment already exists
        # -------------------------------------------------
        existing_payment = self.db.fetch_one(
            """
            SELECT
                payment_id,
                amount,
                payment_method
            FROM payments
            WHERE appointment_id = %s
            """,
            (appointment_id,)
        )

        if existing_payment:
            print(
                "\nPayment already exists for this appointment."
            )
            print("Payment ID :", existing_payment[0])
            print(
                "Amount     :",
                f"₹{Decimal(str(existing_payment[1])):.2f}"
            )
            print("Method     :", existing_payment[2])
            return

        # -------------------------------------------------
        # Display appointment details
        # -------------------------------------------------
        print("\nAppointment Details")
        print("-" * 45)
        print("Patient          :", patient_name)
        print("Doctor           :", doctor_name)
        print(
            "Consultation Fee :",
            f"₹{consultation_fee:.2f}"
        )

        # Amount is automatically taken from consultation fee.
        amount = consultation_fee

        print(
            "\nAmount to Pay    :",
            f"₹{amount:.2f}"
        )

        # -------------------------------------------------
        # Payment method
        # -------------------------------------------------
        payment_method_input = input(
            "\nPayment method (Cash/UPI/Card): "
        ).strip().lower()

        if payment_method_input not in self.VALID_METHODS:
            print("\nInvalid payment method.")
            print("Allowed methods: Cash, UPI, Card")
            return

        # Convert normalized value back to proper display/database value.
        payment_method = self.VALID_METHODS[
            payment_method_input
        ]

        # -------------------------------------------------
        # Confirmation
        # -------------------------------------------------
        confirm = input(
            "\nConfirm payment? (y/n): "
        ).strip().lower()

        if confirm != "y":
            print("\nPayment cancelled.")
            return

        # -------------------------------------------------
        # Insert payment
        # -------------------------------------------------
        query = """
            INSERT INTO payments
            (
                appointment_id,
                amount,
                payment_method
            )
            VALUES (%s, %s, %s)
        """

        try:
            rows = self.db.execute(
                query,
                (
                    appointment_id,
                    amount,
                    payment_method
                )
            )

            if rows > 0:

                payment = self.db.fetch_one(
                    """
                    SELECT payment_id
                    FROM payments
                    WHERE appointment_id = %s
                    """,
                    (appointment_id,)
                )

                print("\nPayment recorded successfully!")

                if payment:
                    print("Payment ID:", payment[0])

                print("Amount :", f"₹{amount:.2f}")
                print("Method :", payment_method)

            else:
                print(
                    "\nPayment could not be recorded."
                )

        except Error as error:
            print(
                "\nUnable to record payment:",
                error
            )

    def view_payments(self):
        """Display all payment records."""

        print("\n" + "=" * 105)
        print("                           PAYMENT RECORDS")
        print("=" * 105)

        query = """
            SELECT
                p.payment_id,
                p.appointment_id,
                pt.patient_name,
                u.full_name AS doctor_name,
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
            ORDER BY p.payment_id
        """

        payments = self.db.fetch_all(query)

        if not payments:
            print("No payment records found.")
            return

        print(
            f"{'ID':<6}"
            f"{'Appt ID':<10}"
            f"{'Patient':<22}"
            f"{'Doctor':<22}"
            f"{'Amount':<14}"
            f"{'Method':<12}"
        )

        print("-" * 105)

        total_amount = Decimal("0.00")

        for payment in payments:

            (
                payment_id,
                appointment_id,
                patient_name,
                doctor_name,
                amount,
                payment_method
            ) = payment

            amount = Decimal(str(amount))
            total_amount += amount

            print(
                f"{payment_id:<6}"
                f"{appointment_id:<10}"
                f"{patient_name:<22}"
                f"{doctor_name:<22}"
                f"₹{amount:<13.2f}"
                f"{payment_method:<12}"
            )

        print("-" * 105)
        print("Total Payments :", len(payments))
        print(
            "Total Revenue  :",
            f"₹{total_amount:.2f}"
        )

    def payment_menu(self, role):
        """Display payment operations according to role."""

        while True:

            print("\n" + "=" * 55)
            print("                PAYMENT MANAGEMENT")
            print("=" * 55)

            if role == "Receptionist":

                print("1. Record Payment")
                print("2. View Payments")
                print("3. Back")

                choice = input(
                    "\nEnter your choice: "
                ).strip()

                if choice == "1":
                    self.record_payment()

                elif choice == "2":
                    self.view_payments()

                elif choice == "3":
                    break

                else:
                    print(
                        "\nInvalid choice. Please try again."
                    )

            elif role == "Admin":

                print("1. View Payments")
                print("2. Back")

                choice = input(
                    "\nEnter your choice: "
                ).strip()

                if choice == "1":
                    self.view_payments()

                elif choice == "2":
                    break

                else:
                    print(
                        "\nInvalid choice. Please try again."
                    )

            else:
                print("\nPayment access denied.")
                break