# Clinic Management System

A role-based Clinic Appointment Management System developed using Python, Flask, MySQL, HTML, CSS and JavaScript.

The system manages doctors, patients, appointments, payments and clinic reports with separate access permissions for Admin, Receptionist and Doctor.

---

## Features

### Admin

- Admin login
- Dashboard with clinic statistics
- Doctor management
  - Add doctor
  - View doctors
  - Edit doctor
  - Activate doctor
  - Deactivate doctor
  - Delete doctor
- View patients
- View appointments
- View payments
- Generate clinic reports
  - Today's appointments
  - Doctor report
  - Patient history
  - Revenue report
  - Monthly clinic report

### Receptionist

- Receptionist login
- Dashboard
- Patient management
  - Add patient
  - View patients
  - Edit patient
  - Delete patient
- View active doctors
- Appointment management
  - Book appointment
  - View appointments
  - Cancel appointment
- Payment management
  - Record payment
  - View payments

### Doctor

- Doctor login
- Doctor dashboard
- View assigned appointments
- Complete appointments
- Add and update consultation notes
- View patient information related to assigned appointments

---

## Technology Stack

| Layer | Technology |
|---|---|
| Programming Language | Python |
| Web Framework | Flask |
| Frontend | HTML, CSS, JavaScript |
| Template Engine | Jinja2 |
| Database | MySQL |
| Python MySQL Driver | mysql-connector-python |
| Production Server | Gunicorn |
| Version Control | Git |
| Source Code Hosting | GitHub |
| Cloud Hosting | Railway |

---

## System Architecture

```text
                    User Browser
                         |
                         v
                HTML / CSS / JavaScript
                         |
                         v
                   Jinja2 Templates
                         |
                         v
                   Flask Application
                         |
                         v
                  DatabaseManager
                         |
                         v
                       MySQL

ClinicManagement/
│
├── database.py
├── auth.py
├── doctors.py
├── patients.py
├── appointments.py
├── payments.py
├── reports.py
├── main.py
├── Queries.sql
├── requirements.txt
├── .gitignore
├── README.md
│
└── web/
    ├── __init__.py
    ├── app.py
    │
    └── templates/
        ├── login.html
        ├── dashboard.html
        ├── doctors.html
        ├── add_doctor.html
        ├── edit_doctor.html
        ├── patients.html
        ├── add_patient.html
        ├── edit_patient.html
        ├── appointments.html
        ├── book_appointment.html
        ├── my_appointments.html
        ├── consultation_notes.html
        ├── payments.html
        ├── add_payment.html
        └── reports.html