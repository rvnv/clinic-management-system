from mysql.connector import Error
class PatientManager:
    """
    Handles patient-related operations.

    Database table:
        patients
        ├── patient_id
        ├── patient_name
        ├── phone
        └── gender
    """
    def __init__(self, db):
        self.db = db
    def register_patient(self):
        """Register a new patient."""
        print("\n" + "=" * 50)
        print("             REGISTER PATIENT")
        print("=" * 50)
        patient_name = input("Patient name: ").strip()
        phone = input("Phone number: ").strip()
        gender = input("Gender (Male/Female/Other): ").strip()
        # Basic input validation
        if not patient_name or not phone or not gender:
            print("\nAll fields are required.")
            return
        # Keep the phone format simple for this project.
        if not phone.isdigit():
            print("\nPhone number must contain digits only.")
            return
        if len(phone) < 10 or len(phone) > 15:
            print("\nPhone number must contain 10 to 15 digits.")
            return
        allowed_genders = ("male", "female", "other")
        if gender.lower() not in allowed_genders:
            print("\nInvalid gender. Use Male, Female, or Other.")
            return
        # Check duplicate phone before INSERT.
        existing_patient = self.db.fetch_one(
            """
            SELECT patient_id, patient_name
            FROM patients
            WHERE phone = %s
            """,
            (phone,)
        )
        if existing_patient:
            print(
                f"\nPhone number already belongs to "
                f"{existing_patient[1]} (Patient ID: {existing_patient[0]})."
            )
            return
        query = """
            INSERT INTO patients
            (patient_name, phone, gender)
            VALUES (%s, %s, %s)
        """
        try:
            rows = self.db.execute(
                query,
                (patient_name, phone, gender.title())
            )
            if rows > 0:
                # Fetch the newly generated ID for a useful confirmation.
                patient = self.db.fetch_one(
                    """
                    SELECT patient_id
                    FROM patients
                    WHERE phone = %s
                    """,
                    (phone,)
                )

                print("\nPatient registered successfully!")

                if patient:
                    print("Patient ID:", patient[0])

            else:
                print("\nPatient registration failed.")

        except Error as error:
            print("\nUnable to register patient:", error)

    def view_patients(self):
        """Display all patients."""

        print("\n" + "=" * 75)
        print("                         PATIENTS")
        print("=" * 75)

        query = """
            SELECT
                patient_id,
                patient_name,
                phone,
                gender
            FROM patients
            ORDER BY patient_id
        """

        patients = self.db.fetch_all(query)

        if not patients:
            print("No patients found.")
            return

        print(
            f"{'ID':<5}"
            f"{'Patient Name':<25}"
            f"{'Phone':<16}"
            f"{'Gender':<10}"
        )

        print("-" * 75)

        for patient in patients:
            patient_id, name, phone, gender = patient

            print(
                f"{patient_id:<5}"
                f"{name:<25}"
                f"{phone:<16}"
                f"{gender:<10}"
            )

        print("-" * 75)
        print("Total Patients:", len(patients))

    def search_patient(self):
        """Search for a patient by ID or phone number."""

        print("\n" + "=" * 50)
        print("             SEARCH PATIENT")
        print("=" * 50)

        print("1. Search by Patient ID")
        print("2. Search by Phone")
        print("3. Back")

        choice = input("\nEnter your choice: ").strip()

        if choice == "1":
            patient_input = input("Enter patient ID: ").strip()

            try:
                patient_id = int(patient_input)
            except ValueError:
                print("\nPatient ID must be a number.")
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

        elif choice == "2":
            phone = input("Enter phone number: ").strip()

            if not phone.isdigit():
                print("\nPhone number must contain digits only.")
                return

            patient = self.db.fetch_one(
                """
                SELECT
                    patient_id,
                    patient_name,
                    phone,
                    gender
                FROM patients
                WHERE phone = %s
                """,
                (phone,)
            )

        elif choice == "3":
            return

        else:
            print("\nInvalid choice.")
            return

        if not patient:
            print("\nPatient not found.")
            return

        print("\n" + "-" * 45)
        print("Patient ID    :", patient[0])
        print("Patient Name  :", patient[1])
        print("Phone         :", patient[2])
        print("Gender        :", patient[3])
        print("-" * 45)

    def update_patient(self):
        """Update patient name, phone, or gender."""

        self.view_patients()

        print("\n" + "=" * 50)
        print("              UPDATE PATIENT")
        print("=" * 50)

        patient_input = input("Enter patient ID: ").strip()

        try:
            patient_id = int(patient_input)
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

        print("\nPress Enter to keep the current value.")

        new_name = input(
            f"Patient name [{patient[1]}]: "
        ).strip()

        new_phone = input(
            f"Phone [{patient[2]}]: "
        ).strip()

        new_gender = input(
            f"Gender [{patient[3]}]: "
        ).strip()

        # Keep existing values when the user presses Enter.
        if not new_name:
            new_name = patient[1]

        if not new_phone:
            new_phone = patient[2]

        if not new_gender:
            new_gender = patient[3]

        # Validate name
        if not new_name:
            print("\nPatient name cannot be empty.")
            return

        # Validate phone
        if not new_phone.isdigit():
            print("\nPhone number must contain digits only.")
            return

        if len(new_phone) < 10 or len(new_phone) > 15:
            print("\nPhone number must contain 10 to 15 digits.")
            return

        # Validate gender
        allowed_genders = ("male", "female", "other")

        if new_gender.lower() not in allowed_genders:
            print("\nInvalid gender. Use Male, Female, or Other.")
            return

        new_gender = new_gender.title()

        # If the phone is changing, make sure another patient
        # does not already use it.
        if new_phone != patient[2]:

            existing_patient = self.db.fetch_one(
                """
                SELECT patient_id, patient_name
                FROM patients
                WHERE phone = %s
                """,
                (new_phone,)
            )

            if existing_patient and existing_patient[0] != patient_id:
                print(
                    f"\nPhone number already belongs to "
                    f"{existing_patient[1]} "
                    f"(Patient ID: {existing_patient[0]})."
                )
                return

        query = """
            UPDATE patients
            SET patient_name = %s,
                phone = %s,
                gender = %s
            WHERE patient_id = %s
        """

        try:
            rows = self.db.execute(
                query,
                (new_name, new_phone, new_gender, patient_id)
            )

            if rows > 0:
                print("\nPatient updated successfully.")
            else:
                print("\nNo changes were made.")

        except Error as error:
            print("\nUnable to update patient:", error)

    def patient_menu(self):
        """Display patient management menu for Admin/Receptionist."""

        while True:
            print("\n" + "=" * 50)
            print("            PATIENT MANAGEMENT")
            print("=" * 50)

            print("1. Register Patient")
            print("2. View Patients")
            print("3. Search Patient")
            print("4. Update Patient")
            print("5. Back")

            choice = input("\nEnter your choice: ").strip()

            if choice == "1":
                self.register_patient()

            elif choice == "2":
                self.view_patients()

            elif choice == "3":
                self.search_patient()

            elif choice == "4":
                self.update_patient()

            elif choice == "5":
                break

            else:
                print("\nInvalid choice. Please try again.")

