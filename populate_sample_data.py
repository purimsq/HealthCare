import sqlite3
from datetime import datetime, timedelta
import random
import hashlib
import database
import os

def hash_password(password):
    """Hash a password for storing."""
    return hashlib.sha256(password.encode()).hexdigest()

def populate_sample_data():
    """Populate the database with sample data while preserving existing users."""
    print("Populating database with sample data...")
    
    # Preserve existing users
    existing_users = database.fetch_all("SELECT username FROM Users")
    existing_usernames = [user[0] for user in existing_users]
    print(f"Preserving {len(existing_usernames)} existing users: {', '.join(existing_usernames)}")
    
    # Sample data for users (will only add if they don't exist)
    sample_users = [
        {
            "username": "dr_smith",
            "password": hash_password("Doctor@123"),
            "email": "smith@hospital.com",
            "full_name": "Dr. John Smith",
            "role": "doctor",
            "created_at": datetime.now() - timedelta(days=30),
            "status": "active"
        },
        {
            "username": "dr_patel",
            "password": hash_password("Doctor@123"),
            "email": "patel@hospital.com",
            "full_name": "Dr. Anita Patel",
            "role": "doctor",
            "created_at": datetime.now() - timedelta(days=25),
            "status": "active"
        },
        {
            "username": "nurse_jones",
            "password": hash_password("Nurse@123"),
            "email": "jones@hospital.com",
            "full_name": "Sarah Jones",
            "role": "nurse",
            "created_at": datetime.now() - timedelta(days=20),
            "status": "active"
        },
        {
            "username": "receptionist",
            "password": hash_password("Front@123"),
            "email": "reception@hospital.com",
            "full_name": "Mary Johnson",
            "role": "receptionist",
            "created_at": datetime.now() - timedelta(days=28),
            "status": "active"
        },
        {
            "username": "pharmacist",
            "password": hash_password("Pharm@123"),
            "email": "pharmacy@hospital.com",
            "full_name": "Robert Chen",
            "role": "pharmacist",
            "created_at": datetime.now() - timedelta(days=22),
            "status": "active"
        }
    ]
    
    # Add sample users if they don't exist already
    for user in sample_users:
        if user["username"] not in existing_usernames:
            user_id = database.insert_record("Users", user)
            print(f"Added user: {user['username']} (ID: {user_id})")
    
    # Get all users for reference in other tables
    all_users = database.fetch_all("SELECT user_id, username, role FROM Users")
    doctors = [(user_id, username) for user_id, username, role in all_users if role == 'doctor']
    
    # Sample patients
    first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth", 
                  "David", "Susan", "Richard", "Jessica", "Joseph", "Sarah", "Thomas", "Karen", "Charles", "Nancy",
                  "Christopher", "Lisa", "Daniel", "Margaret", "Matthew", "Betty"]
    
    last_names = ["Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor",
                 "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson", "Garcia", "Martinez", "Robinson"]
    
    genders = ["Male", "Female"]
    blood_groups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
    
    # Check how many patients already exist
    existing_patients_count = database.fetch_one("SELECT COUNT(*) FROM Patients")[0]
    print(f"Found {existing_patients_count} existing patients")
    
    # Only add more patients if we have less than 20
    if existing_patients_count < 20:
        num_patients_to_add = 20 - existing_patients_count
        print(f"Adding {num_patients_to_add} new sample patients")
        
        for i in range(num_patients_to_add):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            dob = datetime.now() - timedelta(days=random.randint(365*18, 365*85))  # 18 to 85 years old
            
            patient = {
                "first_name": first_name,
                "last_name": last_name,
                "date_of_birth": dob.strftime('%Y-%m-%d'),
                "gender": random.choice(genders),
                "blood_group": random.choice(blood_groups),
                "address": f"{random.randint(1, 999)} Main St, City, Country",
                "contact_number": f"07{random.randint(10000000, 99999999)}",
                "email": f"{first_name.lower()}.{last_name.lower()}@email.com",
                "emergency_contact": f"{random.choice(first_names)} {random.choice(last_names)}",
                "emergency_contact_number": f"07{random.randint(10000000, 99999999)}",
                "registration_date": (datetime.now() - timedelta(days=random.randint(1, 365))).strftime('%Y-%m-%d'),
                "notes": "Sample patient record",
                "status": "active"
            }
            
            patient_id = database.insert_record("Patients", patient)
            print(f"Added patient: {first_name} {last_name} (ID: {patient_id})")
    
    # Get all patients for appointments and billing
    patients = database.fetch_all("SELECT patient_id, first_name, last_name FROM Patients")
    
    # Check if we have enough appointments
    existing_appointments_count = database.fetch_one("SELECT COUNT(*) FROM Appointments")[0]
    print(f"Found {existing_appointments_count} existing appointments")
    
    # Add sample appointments if we have less than 30
    if existing_appointments_count < 30 and doctors and patients:
        num_appointments_to_add = 30 - existing_appointments_count
        print(f"Adding {num_appointments_to_add} new sample appointments")
        
        for i in range(num_appointments_to_add):
            patient_id, _, _ = random.choice(patients)
            doctor_id, _ = random.choice(doctors)
            
            # Appointment date between past week and next two weeks
            days_offset = random.randint(-7, 14)
            appointment_date = (datetime.now() + timedelta(days=days_offset)).strftime('%Y-%m-%d')
            
            # Random hour between 8 AM and 5 PM
            hour = random.randint(8, 17)
            minute = random.choice([0, 15, 30, 45])
            appointment_time = f"{hour:02d}:{minute:02d}"
            
            statuses = ["scheduled", "completed", "cancelled", "no-show"]
            weights = [0.6, 0.3, 0.05, 0.05]  # Probability weights
            status = random.choices(statuses, weights=weights, k=1)[0]
            
            reasons = [
                "Annual check-up", 
                "Follow-up appointment", 
                "Consultation", 
                "Vaccination", 
                "Lab results review",
                "Prescription renewal",
                "Specialist referral",
                "Preventive care",
                "Minor illness",
                "Health concern"
            ]
            
            appointment = {
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "appointment_date": appointment_date,
                "appointment_time": appointment_time,
                "status": status,
                "reason": random.choice(reasons),
                "notes": "Sample appointment record",
                "created_at": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d %H:%M:%S')
            }
            
            appointment_id = database.insert_record("Appointments", appointment)
            print(f"Added appointment ID: {appointment_id} for patient {patient_id} with Dr. {doctors[doctors.index((doctor_id, doctors[doctors.index((doctor_id, _))][1]))][1]}")
    
    # Add sample inventory items
    existing_inventory_count = database.fetch_one("SELECT COUNT(*) FROM Inventory")[0]
    print(f"Found {existing_inventory_count} existing inventory items")
    
    if existing_inventory_count < 15:
        num_items_to_add = 15 - existing_inventory_count
        print(f"Adding {num_items_to_add} new sample inventory items")
        
        sample_inventory = [
            {"item_name": "Surgical Gloves", "category": "Medical Supplies", "quantity": random.randint(100, 1000), "unit": "pairs", "unit_price": 2.50, "supplier": "MediSupply Ltd", "reorder_level": 100, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"item_name": "Surgical Masks", "category": "Medical Supplies", "quantity": random.randint(200, 2000), "unit": "pieces", "unit_price": 1.20, "supplier": "MediSupply Ltd", "reorder_level": 200, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"item_name": "Syringes 5ml", "category": "Medical Supplies", "quantity": random.randint(300, 3000), "unit": "pieces", "unit_price": 0.75, "supplier": "MediSupply Ltd", "reorder_level": 300, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"item_name": "Bandages", "category": "Medical Supplies", "quantity": random.randint(200, 800), "unit": "rolls", "unit_price": 3.25, "supplier": "MediSupply Ltd", "reorder_level": 150, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"item_name": "Thermometers", "category": "Equipment", "quantity": random.randint(50, 200), "unit": "pieces", "unit_price": 12.99, "supplier": "MedTech Inc", "reorder_level": 30, "expiry_date": None},
            {"item_name": "Stethoscopes", "category": "Equipment", "quantity": random.randint(10, 50), "unit": "pieces", "unit_price": 89.99, "supplier": "MedTech Inc", "reorder_level": 5, "expiry_date": None},
            {"item_name": "Blood Pressure Monitors", "category": "Equipment", "quantity": random.randint(10, 30), "unit": "pieces", "unit_price": 75.50, "supplier": "MedTech Inc", "reorder_level": 5, "expiry_date": None},
            {"item_name": "Disposable Gowns", "category": "Medical Supplies", "quantity": random.randint(100, 500), "unit": "pieces", "unit_price": 5.99, "supplier": "MediSupply Ltd", "reorder_level": 50, "expiry_date": (datetime.now() + timedelta(days=365*2)).strftime('%Y-%m-%d')},
            {"item_name": "Antiseptic Solution", "category": "Medical Supplies", "quantity": random.randint(50, 200), "unit": "bottles", "unit_price": 8.75, "supplier": "PharmaCare", "reorder_level": 30, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"item_name": "Gauze Pads", "category": "Medical Supplies", "quantity": random.randint(300, 1000), "unit": "boxes", "unit_price": 15.25, "supplier": "MediSupply Ltd", "reorder_level": 100, "expiry_date": (datetime.now() + timedelta(days=365*2)).strftime('%Y-%m-%d')},
            {"item_name": "Cotton Balls", "category": "Medical Supplies", "quantity": random.randint(100, 500), "unit": "bags", "unit_price": 4.50, "supplier": "MediSupply Ltd", "reorder_level": 50, "expiry_date": (datetime.now() + timedelta(days=365*3)).strftime('%Y-%m-%d')},
            {"item_name": "Tongue Depressors", "category": "Medical Supplies", "quantity": random.randint(200, 1000), "unit": "boxes", "unit_price": 6.25, "supplier": "MediSupply Ltd", "reorder_level": 100, "expiry_date": (datetime.now() + timedelta(days=365*5)).strftime('%Y-%m-%d')},
            {"item_name": "IV Sets", "category": "Medical Supplies", "quantity": random.randint(50, 200), "unit": "sets", "unit_price": 12.75, "supplier": "MediSupply Ltd", "reorder_level": 30, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"item_name": "Examination Gloves", "category": "Medical Supplies", "quantity": random.randint(200, 1000), "unit": "boxes", "unit_price": 18.99, "supplier": "MediSupply Ltd", "reorder_level": 50, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"item_name": "Hand Sanitizer", "category": "Medical Supplies", "quantity": random.randint(100, 300), "unit": "bottles", "unit_price": 7.50, "supplier": "PharmaCare", "reorder_level": 50, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')}
        ]
        
        for i in range(min(num_items_to_add, len(sample_inventory))):
            item = sample_inventory[i]
            item["last_updated"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            item["status"] = "available" if item["quantity"] > item["reorder_level"] else "low stock"
            
            item_id = database.insert_record("Inventory", item)
            print(f"Added inventory item: {item['item_name']} (ID: {item_id})")
    
    # Add sample pharmacy items
    existing_pharmacy_count = database.fetch_one("SELECT COUNT(*) FROM Pharmacy")[0]
    print(f"Found {existing_pharmacy_count} existing pharmacy items")
    
    if existing_pharmacy_count < 15:
        num_meds_to_add = 15 - existing_pharmacy_count
        print(f"Adding {num_meds_to_add} new sample medications")
        
        sample_medications = [
            {"name": "Paracetamol 500mg", "generic_name": "Acetaminophen", "category": "Pain Relief", "dosage": "500mg", "stock_quantity": random.randint(200, 1000), "unit_price": 5.25, "supplier": "PharmaCare", "reorder_level": 100, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"name": "Amoxicillin 250mg", "generic_name": "Amoxicillin", "category": "Antibiotic", "dosage": "250mg", "stock_quantity": random.randint(100, 500), "unit_price": 12.50, "supplier": "PharmaCare", "reorder_level": 50, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"name": "Ibuprofen 400mg", "generic_name": "Ibuprofen", "category": "Anti-inflammatory", "dosage": "400mg", "stock_quantity": random.randint(200, 800), "unit_price": 7.99, "supplier": "PharmaCare", "reorder_level": 100, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"name": "Omeprazole 20mg", "generic_name": "Omeprazole", "category": "Antacid", "dosage": "20mg", "stock_quantity": random.randint(100, 500), "unit_price": 15.75, "supplier": "PharmaCare", "reorder_level": 50, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"name": "Atorvastatin 10mg", "generic_name": "Atorvastatin", "category": "Statin", "dosage": "10mg", "stock_quantity": random.randint(100, 400), "unit_price": 18.25, "supplier": "PharmaCare", "reorder_level": 50, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"name": "Metformin 500mg", "generic_name": "Metformin", "category": "Antidiabetic", "dosage": "500mg", "stock_quantity": random.randint(150, 600), "unit_price": 14.50, "supplier": "PharmaCare", "reorder_level": 75, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"name": "Amlodipine 5mg", "generic_name": "Amlodipine", "category": "Antihypertensive", "dosage": "5mg", "stock_quantity": random.randint(100, 400), "unit_price": 16.99, "supplier": "PharmaCare", "reorder_level": 50, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"name": "Salbutamol Inhaler", "generic_name": "Salbutamol", "category": "Bronchodilator", "dosage": "100mcg", "stock_quantity": random.randint(50, 200), "unit_price": 25.75, "supplier": "PharmaCare", "reorder_level": 25, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"name": "Cetirizine 10mg", "generic_name": "Cetirizine", "category": "Antihistamine", "dosage": "10mg", "stock_quantity": random.randint(100, 500), "unit_price": 8.50, "supplier": "PharmaCare", "reorder_level": 50, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"name": "Losartan 50mg", "generic_name": "Losartan", "category": "Antihypertensive", "dosage": "50mg", "stock_quantity": random.randint(100, 400), "unit_price": 17.25, "supplier": "PharmaCare", "reorder_level": 50, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"name": "Sertraline 50mg", "generic_name": "Sertraline", "category": "Antidepressant", "dosage": "50mg", "stock_quantity": random.randint(100, 300), "unit_price": 22.99, "supplier": "PharmaCare", "reorder_level": 50, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"name": "Levothyroxine 25mcg", "generic_name": "Levothyroxine", "category": "Thyroid Hormone", "dosage": "25mcg", "stock_quantity": random.randint(100, 400), "unit_price": 19.50, "supplier": "PharmaCare", "reorder_level": 50, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"name": "Warfarin 5mg", "generic_name": "Warfarin", "category": "Anticoagulant", "dosage": "5mg", "stock_quantity": random.randint(50, 200), "unit_price": 15.99, "supplier": "PharmaCare", "reorder_level": 25, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"name": "Prednisolone 5mg", "generic_name": "Prednisolone", "category": "Corticosteroid", "dosage": "5mg", "stock_quantity": random.randint(100, 300), "unit_price": 13.75, "supplier": "PharmaCare", "reorder_level": 50, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')},
            {"name": "Furosemide 40mg", "generic_name": "Furosemide", "category": "Diuretic", "dosage": "40mg", "stock_quantity": random.randint(100, 300), "unit_price": 11.50, "supplier": "PharmaCare", "reorder_level": 50, "expiry_date": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')}
        ]
        
        for i in range(min(num_meds_to_add, len(sample_medications))):
            med = sample_medications[i]
            med["status"] = "available" if med["stock_quantity"] > med["reorder_level"] else "low stock"
            
            med_id = database.insert_record("Pharmacy", med)
            print(f"Added medication: {med['name']} (ID: {med_id})")
    
    # Add sample billing records
    existing_billing_count = database.fetch_one("SELECT COUNT(*) FROM Billing")[0]
    print(f"Found {existing_billing_count} existing billing records")
    
    if existing_billing_count < 25 and patients:
        num_bills_to_add = 25 - existing_billing_count
        print(f"Adding {num_bills_to_add} new sample billing records")
        
        services = [
            {"description": "General Consultation", "amount": random.uniform(1500, 3000)},
            {"description": "Specialist Consultation", "amount": random.uniform(3000, 6000)},
            {"description": "Laboratory Tests", "amount": random.uniform(2000, 8000)},
            {"description": "X-Ray", "amount": random.uniform(3500, 5000)},
            {"description": "Ultrasound", "amount": random.uniform(4000, 7000)},
            {"description": "CT Scan", "amount": random.uniform(15000, 25000)},
            {"description": "MRI", "amount": random.uniform(20000, 35000)},
            {"description": "Minor Surgery", "amount": random.uniform(10000, 20000)},
            {"description": "Medication", "amount": random.uniform(1000, 5000)},
            {"description": "Physical Therapy", "amount": random.uniform(2500, 4500)},
            {"description": "Emergency Care", "amount": random.uniform(5000, 15000)},
            {"description": "Dental Procedure", "amount": random.uniform(3000, 8000)},
            {"description": "Vaccination", "amount": random.uniform(1000, 3000)},
            {"description": "Follow-up Visit", "amount": random.uniform(1000, 2000)}
        ]
        
        insurance_providers = [
            "National Health Insurance",
            "MediCover",
            "AAR Insurance",
            "Jubilee Health Insurance",
            "CIC Insurance",
            "APA Insurance",
            "Britam Health Insurance",
            "Madison Insurance",
            "GA Insurance",
            None  # For self-pay patients
        ]
        
        for i in range(num_bills_to_add):
            patient_id, _, _ = random.choice(patients)
            service = random.choice(services)
            
            # Bill date within past 90 days
            bill_date = datetime.now() - timedelta(days=random.randint(0, 90))
            
            # Due date between bill date and 30 days later
            due_date = bill_date + timedelta(days=random.randint(7, 30))
            
            insurance_provider = random.choice(insurance_providers)
            insurance_policy_number = None
            if insurance_provider:
                insurance_policy_number = f"INS-{random.randint(100000, 999999)}"
            
            statuses = ["paid", "unpaid", "partially paid", "overdue"]
            weights = [0.6, 0.2, 0.1, 0.1]  # Probability weights
            status = random.choices(statuses, weights=weights, k=1)[0]
            
            bill = {
                "patient_id": patient_id,
                "service_description": service["description"],
                "amount": service["amount"],
                "insurance_provider": insurance_provider,
                "insurance_policy_number": insurance_policy_number,
                "bill_date": bill_date.strftime('%Y-%m-%d %H:%M:%S'),
                "due_date": due_date.strftime('%Y-%m-%d'),
                "status": status
            }
            
            bill_id = database.insert_record("Billing", bill)
            print(f"Added bill: {bill_id} for patient {patient_id} - {service['description']} (KSH {service['amount']:.2f})")
    
    # Add sample medical history records
    existing_medical_records_count = database.fetch_one("SELECT COUNT(*) FROM MedicalHistory")[0]
    print(f"Found {existing_medical_records_count} existing medical records")
    
    if existing_medical_records_count < 30 and patients and doctors:
        num_records_to_add = 30 - existing_medical_records_count
        print(f"Adding {num_records_to_add} new sample medical records")
        
        diagnoses = [
            "Hypertension",
            "Type 2 Diabetes",
            "Acute Upper Respiratory Infection",
            "Gastroenteritis",
            "Migraines",
            "Lower Back Pain",
            "Anxiety Disorder",
            "Urinary Tract Infection",
            "Asthma",
            "Allergic Rhinitis",
            "Osteoarthritis",
            "Iron Deficiency Anemia",
            "Gastro-esophageal Reflux Disease",
            "Pneumonia",
            "Hypercholesterolemia"
        ]
        
        treatments = [
            "Prescribed medication and lifestyle modifications",
            "Medication, dietary changes, and follow-up in 2 weeks",
            "Rest, increased fluid intake, and antipyretics",
            "Oral rehydration and probiotics",
            "Pain management and trigger avoidance",
            "Physical therapy and anti-inflammatory medication",
            "Cognitive behavioral therapy and medication",
            "Antibiotics for 7 days and increased water intake",
            "Inhaler prescription and allergen avoidance",
            "Antihistamines and nasal spray",
            "Pain management and joint protection exercises",
            "Iron supplements and dietary counseling",
            "Antacids and dietary modifications",
            "Antibiotics and respiratory therapy",
            "Statin therapy and lifestyle modifications"
        ]
        
        for i in range(num_records_to_add):
            patient_id, _, _ = random.choice(patients)
            doctor_id, _ = random.choice(doctors)
            
            diagnosis_index = random.randint(0, len(diagnoses) - 1)
            diagnosis = diagnoses[diagnosis_index]
            treatment = treatments[diagnosis_index]
            
            # Record date within past 180 days
            record_date = datetime.now() - timedelta(days=random.randint(0, 180))
            
            record = {
                "patient_id": patient_id,
                "diagnosis": diagnosis,
                "treatment": treatment,
                "doctor_id": doctor_id,
                "date": record_date.strftime('%Y-%m-%d %H:%M:%S'),
                "notes": "Sample medical record"
            }
            
            record_id = database.insert_record("MedicalHistory", record)
            print(f"Added medical record: {record_id} for patient {patient_id} - {diagnosis}")
    
    # Add sample prescriptions
    existing_prescriptions_count = database.fetch_one("SELECT COUNT(*) FROM Prescriptions")[0]
    print(f"Found {existing_prescriptions_count} existing prescriptions")
    
    if existing_prescriptions_count < 25 and patients and doctors:
        # Get medications
        medications = database.fetch_all("SELECT medication_id, name FROM Pharmacy")
        
        if medications:
            num_prescriptions_to_add = 25 - existing_prescriptions_count
            print(f"Adding {num_prescriptions_to_add} new sample prescriptions")
            
            frequencies = ["Once daily", "Twice daily", "Three times daily", "Four times daily", "As needed", "Every morning", "Every night", "With meals"]
            durations = ["7 days", "14 days", "30 days", "3 months", "6 months", "Indefinite", "Until next appointment"]
            statuses = ["pending", "filled", "cancelled", "expired"]
            weights = [0.3, 0.5, 0.1, 0.1]  # Probability weights
            
            for i in range(num_prescriptions_to_add):
                patient_id, _, _ = random.choice(patients)
                doctor_id, _ = random.choice(doctors)
                medication_id, medication_name = random.choice(medications)
                
                dosage = f"{random.choice(['1', '2'])} tablet(s)"
                frequency = random.choice(frequencies)
                duration = random.choice(durations)
                status = random.choices(statuses, weights=weights, k=1)[0]
                
                created_at = datetime.now() - timedelta(days=random.randint(0, 90))
                
                prescription = {
                    "patient_id": patient_id,
                    "doctor_id": doctor_id,
                    "medication_id": medication_id,
                    "dosage": dosage,
                    "frequency": frequency,
                    "duration": duration,
                    "notes": f"Take as directed for {random.choice(['pain', 'inflammation', 'infection', 'blood pressure', 'cholesterol', 'diabetes', 'anxiety', 'depression', 'allergies', 'cough'])}.",
                    "status": status,
                    "created_at": created_at.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                prescription_id = database.insert_record("Prescriptions", prescription)
                print(f"Added prescription: {prescription_id} for patient {patient_id} - {medication_name}")
    
    # Add sample staff records (for users with appropriate roles)
    staff_roles = ['doctor', 'nurse', 'receptionist', 'pharmacist']
    users_for_staff = [(user_id, username, role) for user_id, username, role in all_users if role in staff_roles]
    
    existing_staff_count = database.fetch_one("SELECT COUNT(*) FROM Staff")[0]
    print(f"Found {existing_staff_count} existing staff records")
    
    # Check which users don't have staff records yet
    existing_staff_user_ids = database.fetch_all("SELECT user_id FROM Staff")
    existing_staff_user_ids = [user_id[0] for user_id in existing_staff_user_ids]
    
    users_needing_staff_records = [user for user in users_for_staff if user[0] not in existing_staff_user_ids]
    
    if users_needing_staff_records:
        print(f"Adding {len(users_needing_staff_records)} new staff records for existing users")
        
        departments = {
            'doctor': ['General Medicine', 'Cardiology', 'Pediatrics', 'Orthopedics', 'Gynecology', 'Dermatology', 'Neurology'],
            'nurse': ['Emergency', 'ICU', 'Pediatric', 'Surgical', 'Obstetric', 'Oncology'],
            'receptionist': ['Front Desk', 'Admissions', 'Outpatient', 'Specialty Clinics'],
            'pharmacist': ['Main Pharmacy', 'Outpatient Pharmacy', 'Clinical Pharmacy']
        }
        
        positions = {
            'doctor': ['Consultant', 'Specialist', 'Resident', 'Attending Physician'],
            'nurse': ['Head Nurse', 'Registered Nurse', 'Nursing Assistant', 'Charge Nurse'],
            'receptionist': ['Senior Receptionist', 'Receptionist', 'Front Office Coordinator'],
            'pharmacist': ['Chief Pharmacist', 'Clinical Pharmacist', 'Staff Pharmacist']
        }
        
        for user_id, username, role in users_needing_staff_records:
            department = random.choice(departments.get(role, ['General']))
            position = random.choice(positions.get(role, ['Staff']))
            
            # Hire date between 1-5 years ago
            hire_date = datetime.now() - timedelta(days=random.randint(365, 365*5))
            
            # Salary based on role
            base_salaries = {
                'doctor': random.uniform(150000, 300000),
                'nurse': random.uniform(70000, 120000),
                'receptionist': random.uniform(40000, 60000),
                'pharmacist': random.uniform(100000, 180000)
            }
            
            salary = base_salaries.get(role, random.uniform(40000, 100000))
            
            staff = {
                "user_id": user_id,
                "department": department,
                "position": position,
                "hire_date": hire_date.strftime('%Y-%m-%d'),
                "salary": salary,
                "contact_number": f"07{random.randint(10000000, 99999999)}",
                "emergency_contact": f"{random.choice(first_names)} {random.choice(last_names)}",
                "status": "active"
            }
            
            staff_id = database.insert_record("Staff", staff)
            print(f"Added staff record: {staff_id} for {username} ({role}) in {department}")
    
    print("Database population complete!")

if __name__ == "__main__":
    # Initialize the database if it doesn't exist
    database.init_db()
    
    # Populate with sample data
    populate_sample_data()