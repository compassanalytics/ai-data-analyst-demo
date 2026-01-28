"""
Healthcare Star Schema Generator - GOOD Data Engineering Example
================================================================

This generates a well-designed star schema for healthcare data.
Demonstrates proper dimensional modeling that works well with AI/BI tools like Genie.

Tables:
- dim_patient: Patient dimension
- dim_provider: Provider dimension
- dim_date: Date dimension with fiscal calendar
- dim_diagnosis: Diagnosis dimension (ICD-10)
- dim_procedure: Procedure dimension (CPT)
- dim_payer: Payer/insurance dimension
- fact_encounters: Patient encounters
- fact_claims: Insurance claims
- fact_prescriptions: Medication prescriptions

Key Features (Why Genie will succeed):
- Clear, business-friendly column names
- Proper foreign key relationships
- Consistent naming conventions
- Logical data types
- Built for common analytical queries
"""

from typing import Dict, Optional
from datetime import datetime
import random

import pandas as pd

from .utils import (
    set_random_seed,
    scale_count,
    generate_mrn,
    generate_npi,
    generate_insurance_member_id,
    generate_patient_demographics,
    generate_encounter_dates,
    generate_claim_amounts,
    get_age_appropriate_diagnosis,
    calculate_length_of_stay,
    generate_encounter_id_prefix,
    generate_flu_season_flag,
    weighted_choice,
    fake,
)
from .codes import (
    ICD10_CODES_CLEAN,
    CPT_CODES,
    SPECIALTIES,
    PAYER_TYPES,
    ENCOUNTER_TYPES,
    FACILITY_NAMES,
    MEDICATIONS,
    PROVIDER_CREDENTIALS,
    CLAIM_STATUS,
)


def generate_dim_patient(n: int = 5000, seed: Optional[int] = None) -> pd.DataFrame:
    """
    Generate patient dimension table.

    Args:
        n: Number of patients to generate
        seed: Random seed for reproducibility

    Returns:
        DataFrame with patient dimension data
    """
    if seed is not None:
        set_random_seed(seed)

    records = []
    for i in range(1, n + 1):
        demographics = generate_patient_demographics()

        # Select primary payer based on age
        age = demographics['age']
        if age >= 65:
            # Elderly more likely to have Medicare
            payer_weights = [0.60, 0.05, 0.10, 0.10, 0.05, 0.03, 0.03, 0.02, 0.02]
        elif age < 18:
            # Children more likely on Medicaid or parent's insurance
            payer_weights = [0.05, 0.30, 0.20, 0.20, 0.10, 0.08, 0.02, 0.03, 0.02]
        else:
            # Working age - commercial insurance dominant
            payer_weights = [0.15, 0.10, 0.18, 0.18, 0.12, 0.10, 0.05, 0.08, 0.04]

        payer_names = [p[0] for p in PAYER_TYPES]
        primary_payer = random.choices(payer_names, weights=payer_weights)[0]

        records.append({
            'patient_key': i,
            'mrn': generate_mrn(),
            'first_name': demographics['first_name'],
            'last_name': demographics['last_name'],
            'date_of_birth': demographics['dob'],
            'gender': demographics['gender'],
            'address': demographics['address'],
            'city': demographics['city'],
            'state': demographics['state'],
            'zip_code': demographics['zip_code'],
            'phone': demographics['phone'],
            'primary_payer': primary_payer,
            'insurance_member_id': generate_insurance_member_id(primary_payer),
            'is_active': random.random() < 0.92,
        })

    return pd.DataFrame(records)


def generate_dim_provider(n: int = 500, seed: Optional[int] = None) -> pd.DataFrame:
    """
    Generate provider dimension table.

    Args:
        n: Number of providers to generate
        seed: Random seed for reproducibility

    Returns:
        DataFrame with provider dimension data
    """
    if seed is not None:
        set_random_seed(seed)

    records = []
    for i in range(1, n + 1):
        specialty = weighted_choice(SPECIALTIES)
        gender = random.choice(['Male', 'Female'])

        if gender == 'Male':
            first_name = fake.first_name_male()
        else:
            first_name = fake.first_name_female()

        records.append({
            'provider_key': i,
            'npi': generate_npi(),
            'first_name': first_name,
            'last_name': fake.last_name(),
            'specialty': specialty,
            'facility': random.choice(FACILITY_NAMES),
            'credentials': random.choice(PROVIDER_CREDENTIALS),
            'is_active': random.random() < 0.90,
        })

    return pd.DataFrame(records)


def generate_dim_date(
    start: str = "2022-01-01",
    end: str = "2025-12-31",
    seed: Optional[int] = None
) -> pd.DataFrame:
    """
    Generate date dimension table with fiscal calendar support.

    Args:
        start: Start date in YYYY-MM-DD format
        end: End date in YYYY-MM-DD format
        seed: Random seed for reproducibility

    Returns:
        DataFrame with date dimension data
    """
    dates = pd.date_range(start=start, end=end, freq='D')

    records = []
    for d in dates:
        # Fiscal year starts July 1 (common for healthcare)
        if d.month >= 7:
            fiscal_year = d.year + 1
        else:
            fiscal_year = d.year

        # Fiscal quarter
        fiscal_month = (d.month - 7) % 12 + 1
        fiscal_quarter = (fiscal_month - 1) // 3 + 1

        records.append({
            'date_key': int(d.strftime('%Y%m%d')),
            'full_date': d.date(),
            'year': d.year,
            'month': d.month,
            'month_name': d.strftime('%B'),
            'quarter': (d.month - 1) // 3 + 1,
            'fiscal_year': fiscal_year,
            'fiscal_quarter': fiscal_quarter,
            'is_weekend': d.dayofweek >= 5,
            'is_flu_season': generate_flu_season_flag(d),
        })

    return pd.DataFrame(records)


def generate_dim_diagnosis(seed: Optional[int] = None) -> pd.DataFrame:
    """
    Generate diagnosis dimension table from ICD-10 codes.

    Args:
        seed: Random seed for reproducibility

    Returns:
        DataFrame with diagnosis dimension data
    """
    records = []
    for i, (code, description, category) in enumerate(ICD10_CODES_CLEAN, start=1):
        # Derive chapter from first character
        chapter_map = {
            'A': 'Infectious Diseases', 'B': 'Infectious Diseases',
            'C': 'Neoplasms', 'D': 'Blood Diseases',
            'E': 'Endocrine/Metabolic', 'F': 'Mental Disorders',
            'G': 'Nervous System', 'H': 'Eye/Ear',
            'I': 'Circulatory System', 'J': 'Respiratory System',
            'K': 'Digestive System', 'L': 'Skin',
            'M': 'Musculoskeletal', 'N': 'Genitourinary',
            'O': 'Pregnancy', 'P': 'Perinatal',
            'Q': 'Congenital', 'R': 'Symptoms/Signs',
            'S': 'Injury', 'T': 'Injury',
            'V': 'External Causes', 'W': 'External Causes',
            'X': 'External Causes', 'Y': 'External Causes',
            'Z': 'Health Status',
        }
        chapter = chapter_map.get(code[0], 'Other')

        records.append({
            'diagnosis_key': i,
            'icd10_code': code,
            'description': description,
            'category': category,
            'chapter': chapter,
        })

    return pd.DataFrame(records)


def generate_dim_procedure(seed: Optional[int] = None) -> pd.DataFrame:
    """
    Generate procedure dimension table from CPT codes.

    Args:
        seed: Random seed for reproducibility

    Returns:
        DataFrame with procedure dimension data
    """
    records = []
    for i, (code, description, category) in enumerate(CPT_CODES, start=1):
        records.append({
            'procedure_key': i,
            'cpt_code': code,
            'description': description,
            'category': category,
        })

    return pd.DataFrame(records)


def generate_dim_payer(seed: Optional[int] = None) -> pd.DataFrame:
    """
    Generate payer dimension table.

    Args:
        seed: Random seed for reproducibility

    Returns:
        DataFrame with payer dimension data
    """
    records = []
    payer_key = 1

    for payer_name, weight, plan_types in PAYER_TYPES:
        for plan_type in plan_types:
            # Determine payer type category
            if payer_name in ['Medicare', 'Medicaid']:
                payer_type = 'Government'
            elif payer_name == 'Self-Pay':
                payer_type = 'Self-Pay'
            elif payer_name == 'Workers Compensation':
                payer_type = 'Workers Comp'
            else:
                payer_type = 'Commercial'

            records.append({
                'payer_key': payer_key,
                'payer_name': payer_name,
                'plan_type': plan_type,
                'payer_type': payer_type,
            })
            payer_key += 1

    return pd.DataFrame(records)


def generate_fact_encounters(
    dim_patient: pd.DataFrame,
    dim_provider: pd.DataFrame,
    dim_date: pd.DataFrame,
    dim_diagnosis: pd.DataFrame,
    n: int = 50000,
    seed: Optional[int] = None
) -> pd.DataFrame:
    """
    Generate fact encounters table.

    Args:
        dim_patient: Patient dimension DataFrame
        dim_provider: Provider dimension DataFrame
        dim_date: Date dimension DataFrame
        dim_diagnosis: Diagnosis dimension DataFrame
        n: Number of encounters to generate
        seed: Random seed for reproducibility

    Returns:
        DataFrame with encounter fact data
    """
    if seed is not None:
        set_random_seed(seed)

    patient_keys = dim_patient['patient_key'].tolist()
    provider_keys = dim_provider['provider_key'].tolist()
    date_keys = dim_date['date_key'].tolist()
    diagnosis_keys = dim_diagnosis['diagnosis_key'].tolist()

    # Create lookup for patient demographics
    patient_lookup = dim_patient.set_index('patient_key')[['date_of_birth', 'gender']].to_dict('index')

    # Create diagnosis code lookup
    diagnosis_lookup = dim_diagnosis.set_index('diagnosis_key')[['icd10_code', 'description', 'category']].to_dict('index')
    diagnosis_codes = [(k, v['icd10_code'], v['description'], v['category']) for k, v in diagnosis_lookup.items()]

    records = []
    for i in range(1, n + 1):
        # Select patient and get their demographics
        patient_key = random.choice(patient_keys)
        patient_info = patient_lookup[patient_key]

        # Calculate age
        dob = patient_info['date_of_birth']
        today = datetime.now().date()
        age = (today - dob).days // 365

        gender = patient_info['gender']

        # Get age-appropriate diagnosis
        dx_codes_for_selection = [(code, desc, cat) for _, code, desc, cat in diagnosis_codes]
        selected_dx = get_age_appropriate_diagnosis(gender, age, dx_codes_for_selection)

        # Find the diagnosis key
        primary_diagnosis_key = None
        for dk, code, desc, cat in diagnosis_codes:
            if code == selected_dx[0]:
                primary_diagnosis_key = dk
                break

        if primary_diagnosis_key is None:
            primary_diagnosis_key = random.choice(diagnosis_keys)

        # Select encounter type
        encounter_type = weighted_choice(ENCOUNTER_TYPES)

        # Generate dates
        admit_dt, discharge_dt = generate_encounter_dates(encounter_type)

        # Find date keys
        admit_date_key = int(admit_dt.strftime('%Y%m%d'))
        discharge_date_key = int(discharge_dt.strftime('%Y%m%d'))

        # Ensure date keys exist (clamp to available range)
        if admit_date_key < min(date_keys):
            admit_date_key = min(date_keys)
        if admit_date_key > max(date_keys):
            admit_date_key = max(date_keys)
        if discharge_date_key < min(date_keys):
            discharge_date_key = min(date_keys)
        if discharge_date_key > max(date_keys):
            discharge_date_key = max(date_keys)

        los = calculate_length_of_stay(admit_dt, discharge_dt)

        # Generate encounter ID
        prefix = generate_encounter_id_prefix(encounter_type)

        records.append({
            'encounter_key': i,
            'encounter_id': f"{prefix}-{i:08d}",
            'patient_key': patient_key,
            'provider_key': random.choice(provider_keys),
            'admit_date_key': admit_date_key,
            'discharge_date_key': discharge_date_key,
            'primary_diagnosis_key': primary_diagnosis_key,
            'encounter_type': encounter_type,
            'length_of_stay': los,
        })

    return pd.DataFrame(records)


def generate_fact_claims(
    fact_encounters: pd.DataFrame,
    dim_payer: pd.DataFrame,
    n: int = 60000,
    seed: Optional[int] = None
) -> pd.DataFrame:
    """
    Generate fact claims table with 1-3 claims per encounter.

    Args:
        fact_encounters: Encounters fact DataFrame
        dim_payer: Payer dimension DataFrame
        n: Target number of claims to generate
        seed: Random seed for reproducibility

    Returns:
        DataFrame with claims fact data
    """
    if seed is not None:
        set_random_seed(seed)

    encounter_keys = fact_encounters['encounter_key'].tolist()
    payer_keys = dim_payer['payer_key'].tolist()

    # Create encounter lookup
    encounter_lookup = fact_encounters.set_index('encounter_key')['encounter_type'].to_dict()

    records = []
    claim_key = 1

    # Distribute claims across encounters
    # 70% have 1 claim, 20% have 2, 10% have 3
    for enc_key in encounter_keys:
        num_claims = random.choices([1, 2, 3], weights=[0.70, 0.20, 0.10])[0]

        encounter_type = encounter_lookup.get(enc_key, 'Outpatient')

        for _ in range(num_claims):
            if claim_key > n:
                break

            amounts = generate_claim_amounts(encounter_type)
            status = weighted_choice(CLAIM_STATUS)

            records.append({
                'claim_key': claim_key,
                'claim_id': f"CLM-{claim_key:010d}",
                'encounter_key': enc_key,
                'payer_key': random.choice(payer_keys),
                'billed_amount': amounts['billed_amount'],
                'allowed_amount': amounts['allowed_amount'],
                'paid_amount': amounts['paid_amount'],
                'patient_responsibility': amounts['patient_responsibility'],
                'claim_status': status,
            })
            claim_key += 1

        if claim_key > n:
            break

    return pd.DataFrame(records)


def generate_fact_prescriptions(
    fact_encounters: pd.DataFrame,
    dim_patient: pd.DataFrame,
    dim_provider: pd.DataFrame,
    n: int = 40000,
    seed: Optional[int] = None
) -> pd.DataFrame:
    """
    Generate fact prescriptions table.

    Args:
        fact_encounters: Encounters fact DataFrame
        dim_patient: Patient dimension DataFrame
        dim_provider: Provider dimension DataFrame
        n: Number of prescriptions to generate
        seed: Random seed for reproducibility

    Returns:
        DataFrame with prescriptions fact data
    """
    if seed is not None:
        set_random_seed(seed)

    encounter_keys = fact_encounters['encounter_key'].tolist()
    patient_keys = dim_patient['patient_key'].tolist()
    provider_keys = dim_provider['provider_key'].tolist()

    # Flatten medications list
    all_medications = []
    for category, meds in MEDICATIONS.items():
        for name, dosage, form in meds:
            all_medications.append((name, dosage, form, category))

    records = []
    for i in range(1, n + 1):
        medication = random.choice(all_medications)

        # Generate realistic quantity and days supply
        if medication[2] in ['Tablet', 'Capsule', 'Tablet ER', 'Tablet XL', 'Tablet ODT']:
            quantity = random.choice([30, 60, 90, 14, 7, 10, 20, 28])
            days_supply = quantity  # Typically 1 per day
        elif medication[2] == 'Inhaler':
            quantity = random.choice([1, 2, 3])
            days_supply = quantity * 30
        elif medication[2] == 'Injectable':
            quantity = random.choice([1, 3, 5, 10])
            days_supply = quantity * 7
        elif medication[2] == 'Diskus':
            quantity = 1
            days_supply = 30
        else:
            quantity = random.choice([30, 60, 90])
            days_supply = quantity

        refills = random.choices([0, 1, 2, 3, 5, 11], weights=[0.20, 0.15, 0.20, 0.20, 0.15, 0.10])[0]

        records.append({
            'prescription_key': i,
            'prescription_id': f"RX-{i:010d}",
            'encounter_key': random.choice(encounter_keys),
            'patient_key': random.choice(patient_keys),
            'provider_key': random.choice(provider_keys),
            'medication_name': medication[0],
            'dosage': medication[1],
            'form': medication[2],
            'medication_category': medication[3],
            'quantity': quantity,
            'days_supply': days_supply,
            'refills': refills,
        })

    return pd.DataFrame(records)


def generate_healthcare_star_schema(
    scale: float = 1.0,
    seed: int = 42,
    output_dir: Optional[str] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Generate complete healthcare star schema dataset.

    Args:
        scale: Scale factor for record counts (1.0 = full, 0.1 = 10%)
        seed: Random seed for reproducibility
        output_dir: Optional directory to save parquet files

    Returns:
        Dictionary of DataFrames keyed by table name
    """
    import os

    set_random_seed(seed)

    print("Generating Healthcare Star Schema...")

    # Scale record counts
    n_patients = scale_count(5000, scale)
    n_providers = scale_count(500, scale)
    n_encounters = scale_count(50000, scale)
    n_claims = scale_count(60000, scale)
    n_prescriptions = scale_count(40000, scale)

    # Generate dimensions
    print(f"  - dim_patient ({n_patients:,} rows)")
    dim_patient = generate_dim_patient(n=n_patients, seed=seed)

    print(f"  - dim_provider ({n_providers:,} rows)")
    dim_provider = generate_dim_provider(n=n_providers, seed=seed)

    print("  - dim_date")
    dim_date = generate_dim_date(start="2022-01-01", end="2025-12-31", seed=seed)

    print("  - dim_diagnosis")
    dim_diagnosis = generate_dim_diagnosis(seed=seed)

    print("  - dim_procedure")
    dim_procedure = generate_dim_procedure(seed=seed)

    print("  - dim_payer")
    dim_payer = generate_dim_payer(seed=seed)

    # Generate facts
    print(f"  - fact_encounters ({n_encounters:,} rows)")
    fact_encounters = generate_fact_encounters(
        dim_patient, dim_provider, dim_date, dim_diagnosis,
        n=n_encounters, seed=seed
    )

    print(f"  - fact_claims (~{n_claims:,} rows)")
    fact_claims = generate_fact_claims(
        fact_encounters, dim_payer, n=n_claims, seed=seed
    )

    print(f"  - fact_prescriptions ({n_prescriptions:,} rows)")
    fact_prescriptions = generate_fact_prescriptions(
        fact_encounters, dim_patient, dim_provider,
        n=n_prescriptions, seed=seed
    )

    datasets = {
        'dim_patient': dim_patient,
        'dim_provider': dim_provider,
        'dim_date': dim_date,
        'dim_diagnosis': dim_diagnosis,
        'dim_procedure': dim_procedure,
        'dim_payer': dim_payer,
        'fact_encounters': fact_encounters,
        'fact_claims': fact_claims,
        'fact_prescriptions': fact_prescriptions,
    }

    # Save to parquet if output directory specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        for table_name, df in datasets.items():
            path = os.path.join(output_dir, f'{table_name}.parquet')
            df.to_parquet(path, index=False)
            print(f"    Saved {path}")

    return datasets
