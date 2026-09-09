
from decimal import Decimal, InvalidOperation
from mysql.connector import Error


class DoctorManager:
    """
    Handles all doctor-related operations.

    Related tables:
        users
        doctors

    Doctor lifecycle:
        Add -> Active -> Deactivate -> Inactive -> Activate
                                  \
                                   -> Delete
    """

    def __init__(self, db):
        self.db = db

    def add_doctor(self):
        """Create a new doctor user account and doctor profile."""

        print("\n" + "=" * 55)
        print("                    ADD DOCTOR")
        print("=" * 55)

        full_name = input("Doctor name: ").strip()
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        specialization = input("Specialization: ").strip()
        fee_input = input("Consultation fee: ").strip()

        if not full_name or not username or not password or not specialization:
            print("\nAll fields are required.")
            return

        try:
            fee = Decimal(fee_input)

            if fee <= 0:
                print("\nConsultation fee must be greater than 0.")
                return

            if fee.as_tuple().exponent < -2:
                print("\nConsultation fee can have at most 2 decimal places.")
                return

        except InvalidOperation:
            print("\nInvalid consultation fee.")
            return

        # Username must be unique.
        existing_user = self.db.fetch_one(
            """
            SELECT user_id
            FROM users
            WHERE username = %s
            """,
            (username,)
        )

        if existing_user:
            print("\nUsername already exists.")
            return

        connection = self.db.connection
        cursor = None

        try:
            cursor = connection.cursor()

            # Create login account.
            cursor.execute(
                """
                INSERT INTO users
                (username, password, full_name, role, status)
                VALUES (%s, %s, %s, 'Doctor', 'Active')
                """,
                (username, password, full_name)
            )

            user_id = cursor.lastrowid

            # Create doctor profile.
            cursor.execute(
                """
                INSERT INTO doctors
                (user_id, specialization, consultation_fee, status)
                VALUES (%s, %s, %s, 'Active')
                """,
                (user_id, specialization, fee)
            )

            doctor_id = cursor.lastrowid

            connection.commit()

            print("\nDoctor added successfully!")
            print("Doctor ID:", doctor_id)
            print("Username :", username)
            print("Status   : Active")

        except Error as error:
            connection.rollback()
            print("\nUnable to add doctor:", error)

        finally:
            if cursor:
                cursor.close()

    def view_doctors(self):
        """Display all doctors."""

        print("\n" + "=" * 90)
        print("                         DOCTORS")
        print("=" * 90)

        query = """
            SELECT
                d.doctor_id,
                u.full_name,
                u.username,
                d.specialization,
                d.consultation_fee,
                d.status
            FROM doctors d
            JOIN users u
                ON d.user_id = u.user_id
            ORDER BY d.doctor_id
        """

        doctors = self.db.fetch_all(query)

        if not doctors:
            print("No doctors found.")
            return

        print(
            f"{'ID':<5}"
            f"{'Name':<22}"
            f"{'Username':<15}"
            f"{'Specialization':<22}"
            f"{'Fee':<10}"
            f"{'Status':<10}"
        )

        print("-" * 90)

        for doctor in doctors:
            doctor_id, name, username, specialization, fee, status = doctor

            print(
                f"{doctor_id:<5}"
                f"{name:<22}"
                f"{username:<15}"
                f"{specialization:<22}"
                f"₹{Decimal(str(fee)):<9.2f}"
                f"{status:<10}"
            )

        print("-" * 90)

    def update_doctor(self):
        """Update doctor specialization and consultation fee."""

        self.view_doctors()

        print("\n" + "=" * 55)
        print("                  UPDATE DOCTOR")
        print("=" * 55)

        doctor_input = input("Enter doctor ID: ").strip()

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
                doctor_id,
                specialization,
                consultation_fee,
                status
            FROM doctors
            WHERE doctor_id = %s
            """,
            (doctor_id,)
        )

        if not doctor:
            print("\nDoctor not found.")
            return

        if doctor[3] == "Inactive":
            print("\nInactive doctor cannot be updated.")
            return

        print("\nPress Enter to keep the current value.")

        specialization = input(
            f"Specialization [{doctor[1]}]: "
        ).strip()

        fee_input = input(
            f"Consultation fee [{doctor[2]}]: "
        ).strip()

        if not specialization:
            specialization = doctor[1]

        if fee_input:

            try:
                fee = Decimal(fee_input)

                if fee <= 0:
                    print("\nConsultation fee must be greater than 0.")
                    return

                if fee.as_tuple().exponent < -2:
                    print(
                        "\nConsultation fee can have at most "
                        "2 decimal places."
                    )
                    return

            except InvalidOperation:
                print("\nInvalid consultation fee.")
                return

        else:
            fee = Decimal(str(doctor[2]))

        query = """
            UPDATE doctors
            SET specialization = %s,
                consultation_fee = %s
            WHERE doctor_id = %s
        """

        try:
            rows = self.db.execute(
                query,
                (specialization, fee, doctor_id)
            )

            if rows > 0:
                print("\nDoctor updated successfully.")
            else:
                print("\nNo changes were made.")

        except Error as error:
            print("\nUnable to update doctor:", error)

    def deactivate_doctor(self):
        """
        Deactivate the doctor and login account.

        Existing appointments remain untouched.
        """

        self.view_doctors()

        print("\n" + "=" * 55)
        print("                DEACTIVATE DOCTOR")
        print("=" * 55)

        doctor_input = input("Enter doctor ID: ").strip()

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
                d.user_id,
                u.full_name,
                d.status
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

        if doctor[3] == "Inactive":
            print("\nDoctor is already inactive.")
            return

        print("\nDoctor:", doctor[2])

        confirm = input(
            "Deactivate this doctor? (y/n): "
        ).strip().lower()

        if confirm != "y":
            print("\nOperation cancelled.")
            return

        connection = self.db.connection
        cursor = None

        try:
            cursor = connection.cursor()

            # Deactivate doctor profile.
            cursor.execute(
                """
                UPDATE doctors
                SET status = 'Inactive'
                WHERE doctor_id = %s
                """,
                (doctor_id,)
            )

            # Deactivate login account.
            cursor.execute(
                """
                UPDATE users
                SET status = 'Inactive'
                WHERE user_id = %s
                """,
                (doctor[1],)
            )

            connection.commit()

            print("\nDoctor deactivated successfully.")

        except Error as error:
            connection.rollback()
            print("\nUnable to deactivate doctor:", error)

        finally:
            if cursor:
                cursor.close()

    def activate_doctor(self):
        """
        Activate an inactive doctor and login account.
        """

        self.view_doctors()

        print("\n" + "=" * 55)
        print("                  ACTIVATE DOCTOR")
        print("=" * 55)

        doctor_input = input("Enter doctor ID: ").strip()

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
                d.user_id,
                u.full_name,
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
            print("\nDoctor not found.")
            return

        doctor_status = doctor[3]
        user_status = doctor[4]

        if doctor_status == "Active" and user_status == "Active":
            print("\nDoctor is already active.")
            return

        connection = self.db.connection
        cursor = None

        try:
            cursor = connection.cursor()

            # Activate doctor profile.
            cursor.execute(
                """
                UPDATE doctors
                SET status = 'Active'
                WHERE doctor_id = %s
                """,
                (doctor_id,)
            )

            # Activate login account.
            cursor.execute(
                """
                UPDATE users
                SET status = 'Active'
                WHERE user_id = %s
                """,
                (doctor[1],)
            )

            connection.commit()

            print("\nDoctor activated successfully.")
            print("Doctor:", doctor[2])

        except Error as error:
            connection.rollback()
            print("\nUnable to activate doctor:", error)

        finally:
            if cursor:
                cursor.close()

    def delete_doctor(self):
        """
        Permanently delete a doctor only when no appointment
        references the doctor.

        This preserves appointment history.
        """

        self.view_doctors()

        print("\n" + "=" * 55)
        print("                  DELETE DOCTOR")
        print("=" * 55)

        doctor_input = input("Enter doctor ID: ").strip()

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
                d.user_id,
                u.full_name,
                d.status
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

        # IMPORTANT:
        # appointments.doctor_id is a foreign key.
        # If appointments exist, deleting the doctor would
        # break historical appointment records.
        appointment_count = self.db.fetch_one(
            """
            SELECT COUNT(*)
            FROM appointments
            WHERE doctor_id = %s
            """,
            (doctor_id,)
        )

        if appointment_count and appointment_count[0] > 0:
            print(
                "\nDoctor cannot be deleted because "
                f"{appointment_count[0]} appointment(s) exist."
            )
            print(
                "Use 'Deactivate Doctor' instead to preserve history."
            )
            return

        print("\nDoctor:", doctor[2])
        print("Status:", doctor[3])

        confirm = input(
            "\nPERMANENTLY delete this doctor? (y/n): "
        ).strip().lower()

        if confirm != "y":
            print("\nDelete operation cancelled.")
            return

        connection = self.db.connection
        cursor = None

        try:
            cursor = connection.cursor()

            # Delete doctor profile first because it references users.
            cursor.execute(
                """
                DELETE FROM doctors
                WHERE doctor_id = %s
                """,
                (doctor_id,)
            )

            # Delete associated login account.
            cursor.execute(
                """
                DELETE FROM users
                WHERE user_id = %s
                """,
                (doctor[1],)
            )

            connection.commit()

            print("\nDoctor deleted successfully.")

        except Error as error:
            connection.rollback()
            print("\nUnable to delete doctor:", error)

        finally:
            if cursor:
                cursor.close()

    def doctor_menu(self):
        """Display the Admin doctor-management menu."""

        while True:

            print("\n" + "=" * 55)
            print("                DOCTOR MANAGEMENT")
            print("=" * 55)

            print("1. Add Doctor")
            print("2. View Doctors")
            print("3. Update Doctor")
            print("4. Deactivate Doctor")
            print("5. Activate Doctor")
            print("6. Delete Doctor")
            print("7. Back")

            choice = input("\nEnter your choice: ").strip()

            if choice == "1":
                self.add_doctor()

            elif choice == "2":
                self.view_doctors()

            elif choice == "3":
                self.update_doctor()

            elif choice == "4":
                self.deactivate_doctor()

            elif choice == "5":
                self.activate_doctor()

            elif choice == "6":
                self.delete_doctor()

            elif choice == "7":
                break

            else:
                print("\nInvalid choice. Please try again.")

