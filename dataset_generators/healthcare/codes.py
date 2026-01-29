"""
Healthcare Dataset - Reference Codes and Constants
===================================================

This module contains reference data constants for generating realistic healthcare data.
Includes both real ICD-10/CPT codes for the clean star schema and synthetic codes
for the dirty super table.
"""


# =============================================================================
# ICD-10 CODES - CLEAN VERSION (Real codes for star schema)
# =============================================================================

ICD10_CODES_CLEAN: list[tuple[str, str, str]] = [
    # Diabetes (E11.x - Type 2 Diabetes Mellitus)
    ("E11.9", "Type 2 diabetes mellitus without complications", "Diabetes"),
    ("E11.65", "Type 2 diabetes mellitus with hyperglycemia", "Diabetes"),
    ("E11.21", "Type 2 diabetes mellitus with diabetic nephropathy", "Diabetes"),
    ("E11.22", "Type 2 diabetes mellitus with diabetic CKD", "Diabetes"),
    ("E11.40", "Type 2 diabetes mellitus with diabetic neuropathy", "Diabetes"),
    ("E11.51", "Type 2 diabetes mellitus with diabetic peripheral angiopathy", "Diabetes"),
    # Hypertension (I10.x - Essential Hypertension)
    ("I10", "Essential (primary) hypertension", "Cardiovascular"),
    ("I11.0", "Hypertensive heart disease with heart failure", "Cardiovascular"),
    ("I11.9", "Hypertensive heart disease without heart failure", "Cardiovascular"),
    ("I12.9", "Hypertensive chronic kidney disease", "Cardiovascular"),
    ("I13.0", "Hypertensive heart and CKD with heart failure", "Cardiovascular"),
    # Heart disease (I25.x - Chronic Ischemic Heart Disease)
    ("I25.10", "Atherosclerotic heart disease of native coronary artery", "Cardiovascular"),
    ("I25.5", "Ischemic cardiomyopathy", "Cardiovascular"),
    ("I25.9", "Chronic ischemic heart disease, unspecified", "Cardiovascular"),
    ("I50.9", "Heart failure, unspecified", "Cardiovascular"),
    ("I48.91", "Unspecified atrial fibrillation", "Cardiovascular"),
    # Respiratory (J06.x, J18.x)
    ("J06.9", "Acute upper respiratory infection, unspecified", "Respiratory"),
    ("J18.9", "Pneumonia, unspecified organism", "Respiratory"),
    ("J44.1", "COPD with acute exacerbation", "Respiratory"),
    ("J44.9", "COPD, unspecified", "Respiratory"),
    ("J45.20", "Mild intermittent asthma, uncomplicated", "Respiratory"),
    ("J45.40", "Moderate persistent asthma, uncomplicated", "Respiratory"),
    # Mental health (F32.x - Depression, F41.x - Anxiety)
    ("F32.0", "Major depressive disorder, single episode, mild", "Mental Health"),
    ("F32.1", "Major depressive disorder, single episode, moderate", "Mental Health"),
    ("F32.9", "Major depressive disorder, single episode, unspecified", "Mental Health"),
    ("F41.0", "Panic disorder", "Mental Health"),
    ("F41.1", "Generalized anxiety disorder", "Mental Health"),
    ("F41.9", "Anxiety disorder, unspecified", "Mental Health"),
    # Musculoskeletal (M54.x - Back Pain)
    ("M54.5", "Low back pain", "Musculoskeletal"),
    ("M54.2", "Cervicalgia", "Musculoskeletal"),
    ("M54.9", "Dorsalgia, unspecified", "Musculoskeletal"),
    ("M79.3", "Panniculitis, unspecified", "Musculoskeletal"),
    ("M25.50", "Pain in unspecified joint", "Musculoskeletal"),
    ("M17.11", "Primary osteoarthritis, right knee", "Musculoskeletal"),
    ("M17.12", "Primary osteoarthritis, left knee", "Musculoskeletal"),
    # Symptoms (R10.x - Abdominal Pain, other R codes)
    ("R10.9", "Unspecified abdominal pain", "Symptoms"),
    ("R10.11", "Right upper quadrant pain", "Symptoms"),
    ("R10.31", "Right lower quadrant pain", "Symptoms"),
    ("R51", "Headache", "Symptoms"),
    ("R05", "Cough", "Symptoms"),
    ("R50.9", "Fever, unspecified", "Symptoms"),
    ("R53.83", "Other fatigue", "Symptoms"),
    # Additional common diagnoses
    ("K21.0", "Gastroesophageal reflux disease with esophagitis", "Gastrointestinal"),
    ("N39.0", "Urinary tract infection, site not specified", "Genitourinary"),
    ("L03.90", "Cellulitis, unspecified", "Skin"),
    ("G43.909", "Migraine, unspecified, not intractable", "Neurological"),
]

# =============================================================================
# ICD CODES - DIRTY VERSION (Synthetic/fictional codes for super table)
# =============================================================================

ICD_CODES_DIRTY: list[tuple[str, str]] = [
    # Synthetic codes - NOT real ICD codes
    ("DX-001", "Synthetic Diagnosis Type A"),
    ("DX-002", "Synthetic Diagnosis Type B"),
    ("DX-003", "Synthetic Condition Alpha"),
    ("DX-004", "Synthetic Condition Beta"),
    ("DX-005", "Fictional Illness Category 1"),
    ("DX-006", "Fictional Illness Category 2"),
    ("DX-007", "Demo Diagnosis Primary"),
    ("DX-008", "Demo Diagnosis Secondary"),
    ("DX-009", "Test Condition Acute"),
    ("DX-010", "Test Condition Chronic"),
    # ICD-9 style synthetic codes (clearly marked)
    ("250.00-SYN", "Synthetic Diabetes Code"),
    ("401.9-SYN", "Synthetic Hypertension Code"),
    ("414.01-SYN", "Synthetic Heart Disease Code"),
    ("496-SYN", "Synthetic Respiratory Code"),
    ("311-SYN", "Synthetic Depression Code"),
    # More synthetic codes
    ("SYN-DIAB-01", "Fictional Diabetes Variant"),
    ("SYN-HTN-01", "Fictional Hypertension Variant"),
    ("SYN-CHF-01", "Fictional Heart Failure Variant"),
    ("SYN-COPD-01", "Fictional COPD Variant"),
    ("SYN-ANXI-01", "Fictional Anxiety Variant"),
    # Generic codes for chaos
    ("GEN-001", "Generic Diagnosis A"),
    ("GEN-002", "Generic Diagnosis B"),
    ("GEN-003", "Generic Diagnosis C"),
    ("UNK-001", "Unknown Condition Type"),
    ("MISC-001", "Miscellaneous Finding"),
]

# =============================================================================
# CPT CODES (Procedure Codes)
# =============================================================================

CPT_CODES: list[tuple[str, str, str]] = [
    # Evaluation & Management (E&M)
    ("99213", "Office visit, established patient, low complexity", "E&M"),
    ("99214", "Office visit, established patient, moderate complexity", "E&M"),
    ("99215", "Office visit, established patient, high complexity", "E&M"),
    ("99203", "Office visit, new patient, low complexity", "E&M"),
    ("99204", "Office visit, new patient, moderate complexity", "E&M"),
    ("99205", "Office visit, new patient, high complexity", "E&M"),
    # Hospital Care
    ("99221", "Initial hospital care, straightforward", "Hospital"),
    ("99222", "Initial hospital care, moderate complexity", "Hospital"),
    ("99223", "Initial hospital care, high complexity", "Hospital"),
    ("99231", "Subsequent hospital care, straightforward", "Hospital"),
    ("99232", "Subsequent hospital care, moderate complexity", "Hospital"),
    ("99233", "Subsequent hospital care, high complexity", "Hospital"),
    ("99238", "Hospital discharge day management, 30 min or less", "Hospital"),
    ("99239", "Hospital discharge day management, more than 30 min", "Hospital"),
    # Emergency Department
    ("99281", "ED visit, self-limited problem", "Emergency"),
    ("99282", "ED visit, low severity", "Emergency"),
    ("99283", "ED visit, moderate severity", "Emergency"),
    ("99284", "ED visit, high severity", "Emergency"),
    ("99285", "ED visit, high severity with threat to life", "Emergency"),
    # Laboratory
    ("80053", "Comprehensive metabolic panel", "Laboratory"),
    ("85025", "Complete blood count with differential", "Laboratory"),
    ("82947", "Glucose, quantitative", "Laboratory"),
    ("83036", "Hemoglobin A1c", "Laboratory"),
    ("80061", "Lipid panel", "Laboratory"),
    ("84443", "Thyroid stimulating hormone (TSH)", "Laboratory"),
    ("81001", "Urinalysis with microscopy", "Laboratory"),
    # Imaging
    ("71046", "Chest X-ray, 2 views", "Imaging"),
    ("74176", "CT abdomen and pelvis without contrast", "Imaging"),
    ("74177", "CT abdomen and pelvis with contrast", "Imaging"),
    ("70553", "MRI brain with and without contrast", "Imaging"),
    ("93306", "Echocardiography, complete", "Imaging"),
    ("73030", "Shoulder X-ray, complete", "Imaging"),
    # Procedures
    ("93000", "Electrocardiogram, routine", "Cardiology"),
    ("94010", "Spirometry", "Pulmonology"),
    ("36415", "Venipuncture", "Phlebotomy"),
]

# =============================================================================
# SPECIALTIES (Provider Specialties with weights)
# =============================================================================

SPECIALTIES: list[tuple[str, float]] = [
    ("Primary Care", 0.25),
    ("Internal Medicine", 0.15),
    ("Emergency Medicine", 0.10),
    ("Cardiology", 0.08),
    ("Orthopedics", 0.06),
    ("Gastroenterology", 0.05),
    ("Pulmonology", 0.05),
    ("Neurology", 0.04),
    ("Psychiatry", 0.04),
    ("Endocrinology", 0.03),
    ("Nephrology", 0.03),
    ("Dermatology", 0.03),
    ("Rheumatology", 0.02),
    ("Oncology", 0.02),
    ("Urology", 0.02),
    ("General Surgery", 0.03),
]

# =============================================================================
# PAYER TYPES (Insurance Payers with weights and plan types)
# =============================================================================

PAYER_TYPES: list[tuple[str, float, list[str]]] = [
    ("Medicare", 0.30, ["Medicare Advantage", "Medicare FFS", "Medicare Supplement"]),
    ("Medicaid", 0.15, ["Medicaid Managed Care", "Medicaid FFS"]),
    ("Blue Cross Blue Shield", 0.15, ["BCBS PPO", "BCBS HMO", "BCBS EPO"]),
    ("United Healthcare", 0.12, ["UHC PPO", "UHC HMO", "UHC POS"]),
    ("Aetna", 0.08, ["Aetna PPO", "Aetna HMO", "Aetna POS"]),
    ("Cigna", 0.07, ["Cigna PPO", "Cigna HMO", "Cigna Open Access"]),
    ("Humana", 0.05, ["Humana PPO", "Humana HMO", "Humana Gold Plus"]),
    ("Self-Pay", 0.05, ["Self-Pay", "Uninsured", "Charity Care"]),
    ("Workers Compensation", 0.03, ["Workers Comp", "Occupational Health"]),
]

# =============================================================================
# ENCOUNTER TYPES (Encounter types with weights)
# =============================================================================

ENCOUNTER_TYPES: list[tuple[str, float]] = [
    ("Outpatient", 0.60),
    ("Inpatient", 0.15),
    ("Emergency", 0.12),
    ("Observation", 0.05),
    ("Telehealth", 0.08),
]

# =============================================================================
# FACILITY NAMES (Fictional hospital names)
# =============================================================================

FACILITY_NAMES: list[str] = [
    "Mercy General Hospital",
    "St. Mary's Medical Center",
    "Community Health Regional",
    "University Medical Center",
    "Memorial Hospital System",
    "Valley Healthcare Center",
    "Riverside General Hospital",
    "Summit Medical Center",
    "Lakeside Community Hospital",
    "Northside Regional Medical",
    "Eastside Health System",
    "Westside Medical Center",
    "Central Valley Hospital",
    "Mountain View Medical",
    "Oceanside Healthcare",
    "Prairie Regional Hospital",
    "Heartland Medical Center",
    "Sunrise Community Health",
]

# =============================================================================
# MEDICATIONS (Medications by category)
# =============================================================================

MEDICATIONS: dict[str, list[tuple[str, str, str]]] = {
    "Diabetes": [
        ("Metformin", "500mg", "Tablet"),
        ("Metformin", "1000mg", "Tablet"),
        ("Glipizide", "5mg", "Tablet"),
        ("Glipizide", "10mg", "Tablet"),
        ("Insulin Glargine", "100 units/mL", "Injectable"),
        ("Insulin Lispro", "100 units/mL", "Injectable"),
        ("Sitagliptin", "100mg", "Tablet"),
        ("Empagliflozin", "10mg", "Tablet"),
        ("Empagliflozin", "25mg", "Tablet"),
    ],
    "Cardiovascular": [
        ("Lisinopril", "10mg", "Tablet"),
        ("Lisinopril", "20mg", "Tablet"),
        ("Amlodipine", "5mg", "Tablet"),
        ("Amlodipine", "10mg", "Tablet"),
        ("Atorvastatin", "20mg", "Tablet"),
        ("Atorvastatin", "40mg", "Tablet"),
        ("Metoprolol Succinate", "25mg", "Tablet ER"),
        ("Metoprolol Succinate", "50mg", "Tablet ER"),
        ("Losartan", "50mg", "Tablet"),
        ("Losartan", "100mg", "Tablet"),
        ("Carvedilol", "6.25mg", "Tablet"),
        ("Carvedilol", "12.5mg", "Tablet"),
        ("Furosemide", "20mg", "Tablet"),
        ("Furosemide", "40mg", "Tablet"),
        ("Aspirin", "81mg", "Tablet"),
        ("Clopidogrel", "75mg", "Tablet"),
    ],
    "Pain": [
        ("Acetaminophen", "500mg", "Tablet"),
        ("Ibuprofen", "400mg", "Tablet"),
        ("Ibuprofen", "800mg", "Tablet"),
        ("Naproxen", "500mg", "Tablet"),
        ("Meloxicam", "7.5mg", "Tablet"),
        ("Meloxicam", "15mg", "Tablet"),
        ("Gabapentin", "300mg", "Capsule"),
        ("Gabapentin", "600mg", "Tablet"),
        ("Tramadol", "50mg", "Tablet"),
        ("Cyclobenzaprine", "10mg", "Tablet"),
    ],
    "Antibiotics": [
        ("Amoxicillin", "500mg", "Capsule"),
        ("Amoxicillin-Clavulanate", "875mg", "Tablet"),
        ("Azithromycin", "250mg", "Tablet"),
        ("Ciprofloxacin", "500mg", "Tablet"),
        ("Levofloxacin", "500mg", "Tablet"),
        ("Doxycycline", "100mg", "Capsule"),
        ("Cephalexin", "500mg", "Capsule"),
        ("Sulfamethoxazole-Trimethoprim", "800-160mg", "Tablet"),
    ],
    "Mental Health": [
        ("Sertraline", "50mg", "Tablet"),
        ("Sertraline", "100mg", "Tablet"),
        ("Escitalopram", "10mg", "Tablet"),
        ("Escitalopram", "20mg", "Tablet"),
        ("Fluoxetine", "20mg", "Capsule"),
        ("Bupropion", "150mg", "Tablet XL"),
        ("Bupropion", "300mg", "Tablet XL"),
        ("Trazodone", "50mg", "Tablet"),
        ("Trazodone", "100mg", "Tablet"),
        ("Alprazolam", "0.5mg", "Tablet"),
        ("Lorazepam", "1mg", "Tablet"),
        ("Buspirone", "10mg", "Tablet"),
    ],
    "Respiratory": [
        ("Albuterol", "90mcg", "Inhaler"),
        ("Fluticasone", "110mcg", "Inhaler"),
        ("Fluticasone-Salmeterol", "250-50mcg", "Diskus"),
        ("Montelukast", "10mg", "Tablet"),
        ("Tiotropium", "18mcg", "Inhaler"),
        ("Prednisone", "10mg", "Tablet"),
        ("Prednisone", "20mg", "Tablet"),
    ],
    "Gastrointestinal": [
        ("Omeprazole", "20mg", "Capsule"),
        ("Omeprazole", "40mg", "Capsule"),
        ("Pantoprazole", "40mg", "Tablet"),
        ("Famotidine", "20mg", "Tablet"),
        ("Ondansetron", "4mg", "Tablet ODT"),
        ("Docusate Sodium", "100mg", "Capsule"),
        ("Polyethylene Glycol", "17g", "Powder"),
    ],
}

# =============================================================================
# PROVIDER CREDENTIALS
# =============================================================================

PROVIDER_CREDENTIALS: list[str] = [
    "MD",
    "DO",
    "NP",
    "PA",
    "PA-C",
    "APRN",
    "DNP",
]

# =============================================================================
# CLAIM STATUS CODES
# =============================================================================

CLAIM_STATUS: list[tuple[str, float]] = [
    ("Paid", 0.70),
    ("Pending", 0.12),
    ("Denied", 0.08),
    ("Partially Paid", 0.05),
    ("Under Review", 0.03),
    ("Appealed", 0.02),
]
