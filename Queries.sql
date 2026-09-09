CREATE database clinic_management;
USE clinic_management;
-- Table 1  users
CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'Active'
);
-- Table 2 doctors
CREATE TABLE doctors (
    doctor_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL UNIQUE,
    specialization VARCHAR(100) NOT NULL,
    consultation_fee DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'Active',
    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
);
-- Table 3 patients
CREATE TABLE patients (
    patient_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL UNIQUE,
    gender VARCHAR(10) NOT NULL
);
-- Table 4 appointments

CREATE TABLE appointments (
    appointment_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    reason VARCHAR(255),
    status VARCHAR(20) DEFAULT 'Scheduled',
    consultation_notes TEXT,
    FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id),
    FOREIGN KEY (doctor_id)
        REFERENCES doctors(doctor_id),
    UNIQUE (doctor_id, appointment_date, appointment_time)
);

-- Table 5 payments
CREATE TABLE payments (
    payment_id INT PRIMARY KEY AUTO_INCREMENT,
    appointment_id INT NOT NULL UNIQUE,
    amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(20) NOT NULL,
    FOREIGN KEY (appointment_id)
        REFERENCES appointments(appointment_id)
);

-- USE clinic_management;


SELECT * FROM users;

USE clinic_management;

SELECT
    user_id,
    username,
    password,
    full_name,
    role,
    status
FROM users
WHERE username = 'reception';
SELECT * FROM DOCTORS;

  
SELECT * FROM appointments;

USE clinic_management;

SELECT COUNT(*) AS users_count FROM users;
SELECT COUNT(*) AS doctors_count FROM doctors;
SELECT COUNT(*) AS patients_count FROM patients;
SELECT COUNT(*) AS appointments_count FROM appointments;
SELECT COUNT(*) AS payments_count FROM payments;

select * from doctors;
select * from users;
select * from patients;
select * from appointments;
SELECT * from payments;

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
		ORDER BY d.consultation_fee;