from database import DatabaseManager
from auth import AuthManager
from doctors import DoctorManager
from patients import PatientManager
from appointments import AppointmentManager
from payments import PaymentManager
from reports import ReportManager
def display_header():
    """Display the application header."""
    print("\n" + "=" * 60)
    print("              CLINIC APPOINTMENT SYSTEM")
    print("=" * 60)

def admin_menu(user,doctor_manager,patient_manager,appointment_manager,payment_manager,report_manager):
    """Display the Admin dashboard."""
    while True:
        print("\n" + "=" * 60)
        print("                    ADMIN MENU")
        print("=" * 60)
        print("Welcome,", user["full_name"])
        print("\n1. Manage Doctors")
        print("2. View Patients")
        print("3. View Appointments")
        print("4. View Payments")
        print("5. Reports")
        print("6. Logout")
        choice = input("\nEnter your choice: ").strip()
        if choice == "1":
            doctor_manager.doctor_menu()
        elif choice == "2":
            patient_manager.view_patients()
        elif choice == "3":
            appointment_manager.view_appointments()
        elif choice == "4":
            payment_manager.view_payments()
        elif choice == "5":
            report_manager.report_menu()
        elif choice == "6":
            return
        else:
            print("\nInvalid choice. Please try again.")
def receptionist_menu(user,patient_manager,appointment_manager,payment_manager):
    """Display the Receptionist dashboard."""
    while True:
        print("\n" + "=" * 60)
        print("                 RECEPTIONIST MENU")
        print("=" * 60)
        print("Welcome,", user["full_name"])
        print("\n1. Patient Management")
        print("2. Appointment Management")
        print("3. Payment Management")
        print("4. Logout")
        choice = input("\nEnter your choice: ").strip()
        if choice == "1":
            patient_manager.patient_menu()
        elif choice == "2":
            appointment_manager.appointment_menu("Receptionist")
        elif choice == "3":
            payment_manager.payment_menu("Receptionist")
        elif choice == "4":
            return
        else:
            print("\nInvalid choice. Please try again.")
def doctor_menu(user, appointment_manager):
    """Display the Doctor dashboard."""
    while True:
        print("\n" + "=" * 60)
        print("                    DOCTOR MENU")
        print("=" * 60)
        print("Welcome,", user["full_name"])
        print("\n1. My Appointments")
        print("2. Complete Appointment")
        print("3. Add Consultation Notes")
        print("4. Logout")

        choice = input("\nEnter your choice: ").strip()

        if choice == "1":
            appointment_manager.view_my_appointments(
                user["user_id"]
            )

        elif choice == "2":
            appointment_manager.complete_appointment(
                user["user_id"]
            )

        elif choice == "3":
            appointment_manager.add_consultation_notes(
                user["user_id"]
            )

        elif choice == "4":
            return

        else:
            print("\nInvalid choice. Please try again.")


def login_user(auth):
    """
    Handle login interaction.

    Returns:
        Logged-in user dictionary or None.
    """

    print("\n" + "=" * 60)
    print("                       LOGIN")
    print("=" * 60)

    username = input("Username: ").strip()
    password = input("Password: ").strip()

    if not username or not password:
        print("\nUsername and password are required.")
        return None

    user = auth.login(username, password)

    if user:
        print("\nLogin successful!")
        print("Welcome,", user["full_name"])
        print("Role:", user["role"])
        return user

    print("\nInvalid username or password.")
    return None


def create_managers(db):
    """
    Create all application manager objects.

    Returns:
        Tuple containing all manager objects.
    """

    auth = AuthManager(db)
    doctor_manager = DoctorManager(db)
    patient_manager = PatientManager(db)
    appointment_manager = AppointmentManager(db)
    payment_manager = PaymentManager(db)
    report_manager = ReportManager(db)

    return (
        auth,
        doctor_manager,
        patient_manager,
        appointment_manager,
        payment_manager,
        report_manager
    )


def run_application(db):
    """Run the complete clinic application."""
    (auth,doctor_manager,patient_manager,appointment_manager,payment_manager,report_manager) = create_managers(db)
    while True:

        display_header()

        print("\n1. Login")
        print("2. Exit")

        choice = input("\nEnter your choice: ").strip()

        if choice == "1":

            user = login_user(auth)

            if not user:
                continue

            role = user["role"]

            if role == "Admin":

                admin_menu(
                    user,
                    doctor_manager,
                    patient_manager,
                    appointment_manager,
                    payment_manager,
                    report_manager
                )

            elif role == "Receptionist":

                receptionist_menu(
                    user,
                    patient_manager,
                    appointment_manager,
                    payment_manager
                )

            elif role == "Doctor":

                doctor_menu(
                    user,
                    appointment_manager
                )

            else:
                print("\nInvalid user role.")

            auth.logout()
            print("\nLogged out successfully.")

        elif choice == "2":
            print("\nThank you for using Clinic Appointment System.")
            break

        else:
            print("\nInvalid choice. Please try again.")


def main():
    """Application entry point."""

    db = DatabaseManager()
    try:
        if not db.connect():
            print("\nUnable to connect to the database.")
            print("Please check your MySQL server and credentials.")
            return

        print("\nDatabase connected successfully.")

        run_application(db)

    except KeyboardInterrupt:
        print("\n\nApplication interrupted by user.")

    except EOFError:
        print("\n\nApplication terminated.")

    finally:
        db.close()
if __name__ == "__main__":
    main()

