"""
Healthcare Super Table Generator - BAD Data Engineering Example
================================================================

This generates a denormalized "super table" that represents common anti-patterns
found in healthcare data systems. Demonstrates what NOT to do when designing
data for AI/BI tools.

CRITICAL: This module uses SYNTHETIC/FICTIONAL codes (ICD_CODES_DIRTY), NOT real
medical codes. This ensures the data cannot be mistaken for actual patient records.

Anti-patterns included:
1. All data flattened into one massive table (100+ columns)
2. Inconsistent naming conventions
3. Cryptic abbreviations
4. Duplicate/redundant columns with DIFFERENT values
5. Mixed data formats (dates, booleans, etc.)
6. Ambiguous column names
7. No clear relationships
8. Multiple date formats
9. Status codes without lookup
10. Conflicting values in similar columns

Why Genie will struggle:
- Too many columns to fit in context
- Ambiguous column names require guessing
- No clear business meaning without documentation
- Redundant columns cause confusion
- Inconsistent naming makes pattern matching fail
"""

import os
import random
from datetime import datetime, timedelta

import pandas as pd

from .codes import (
    FACILITY_NAMES,
    ICD_CODES_DIRTY,
    PAYER_TYPES,
    SPECIALTIES,
)
from .utils import (
    fake,
    set_random_seed,
)

# Failure scenarios for demonstration
HEALTHCARE_FAILURE_SCENARIOS = """
================================================================================
QUESTIONS THAT WILL CONFUSE GENIE (Healthcare Super Table Anti-Patterns)
================================================================================

1. PATIENT ID CHAOS
   Question: "How many unique patients do we have?"
   Problem: patient_id, patientID, PAT_ID, pat_id, mrn, MRN, member_id, MEMBER_ID,
            ssn, internal_patient_id all exist. Some have DIFFERENT values for
            the same row! Which is the true patient identifier?

2. DATE FORMAT NIGHTMARE
   Question: "Show admissions from January 2024"
   Problem: service_date (date), ServiceDate ('01/15/2024'), svc_dt ('20240115'),
            dos ('15-Jan-2024'), DATE_OF_SERVICE (ISO), admit_date, admission_dt,
            ADMIT_DT - all different formats. SQL varies by format!

3. DIAGNOSIS CODE CONFUSION
   Question: "What are our top diagnosis categories?"
   Problem: dx1, dx2, primary_dx, ICD_CODE, diagnosis, dx_code, DX_CD,
            diag_category all exist. dx1 vs primary_dx may conflict!
            Which is the PRIMARY diagnosis?

4. PROVIDER ID CONFLICTS
   Question: "Which provider has the most encounters?"
   Problem: provider_id and PROVIDER_ID have DIFFERENT values!
            npi and NPI have DIFFERENT values! attending_npi is yet another.
            Genie picks one, gets wrong answer.

5. AMOUNT AMBIGUITY
   Question: "What is our total revenue?"
   Problem: charge_amt, CHARGES, billed, billed_amt, total_charges, gross_charges,
            allowed_amt, ALLOWED, paid_amt, PAID, payment, reimb_amt - which one
            represents actual revenue? All have different values!

6. BOOLEAN CHAOS
   Question: "Show only admitted patients"
   Problem: is_admitted has mixed values: 0, 1, 'Y', 'N', True, False, 'YES', 'NO'
            admitted_flg, has_admission, admission_indicator - which to use?
            No consistent boolean format!

7. CRYPTIC CODES
   Question: "Show encounters by type"
   Problem: enc_type has values like 'OP', 'IP', 'ED', 'OBS', 'TH'.
            encounter_type has 'Outpatient', 'Inpatient', etc.
            type_cd has 1, 2, 3, 4, 5. status_cd has A, B, C.
            No documentation on what codes mean!

8. PAYER IDENTIFICATION
   Question: "What percentage of claims are Medicare?"
   Problem: ins_type, insurance_cd, payer_cd, PAYER, payer_name, INS_NAME
            all have different formats: codes vs names vs abbreviations.
            'MCD' vs 'Medicare' vs 'MDCR' vs 'MCR' - all the same payer!

9. DUPLICATE CALCULATIONS
   Question: "What is our average length of stay?"
   Problem: los, LOS, length_of_stay, stay_days, days_in_hospital, duration
            all exist. Some calculated differently! Which is correct?

10. CONFLICTING VALUES
    Question: "Show details for encounter 12345"
    Problem: The same encounter has enc_id='ENC-12345', encounter_id='12345',
             ENCOUNTER_ID='E12345'. patient_name and PAT_NAME are DIFFERENT!
             Data integrity is broken.

================================================================================
WHY STAR SCHEMA FIXES THESE PROBLEMS:
================================================================================

1. Single patient_key in dim_patient (one ID to rule them all)
2. Consistent date_key format (YYYYMMDD integer, always)
3. One diagnosis_key linking to dim_diagnosis with description
4. One provider_key linking to dim_provider with name and NPI
5. Clear amount columns: billed_amount, allowed_amount, paid_amount
6. Boolean fields are always proper booleans
7. Dimension tables contain code-to-description mappings
8. One payer_key linking to dim_payer with name and type
9. One length_of_stay column, calculated consistently
10. Referential integrity enforced through foreign keys

================================================================================
"""


def generate_healthcare_super_table(
    n_rows: int = 50000,
    seed: int = 42,
    output_dir: str | None = None,
) -> pd.DataFrame:
    """
    Generate a horribly denormalized healthcare super table with 100+ columns.

    CRITICAL: All chaos columns are forced to str type to avoid pandas errors.
    Uses SYNTHETIC codes (ICD_CODES_DIRTY) to avoid real medical data.

    Args:
        n_rows: Number of rows to generate
        seed: Random seed for reproducibility
        output_dir: Optional directory to save parquet file

    Returns:
        DataFrame with 100+ columns of anti-pattern chaos
    """
    set_random_seed(seed)

    print(f"Generating Healthcare Super Table ({n_rows:,} rows)...")

    # Generate dates within last 3 years
    dates = pd.date_range(start="2022-01-01", end="2025-12-31", freq="D").tolist()

    records = []

    for i in range(1, n_rows + 1):
        service_date = random.choice(dates)

        # Generate base values (may be reused with conflicts)
        base_patient_id = random.randint(10000, 99999)
        alt_patient_id = random.randint(10000, 99999)  # DIFFERENT for conflict!

        base_provider_id = random.randint(1000, 9999)
        alt_provider_id = random.randint(1000, 9999)  # DIFFERENT for conflict!

        base_npi = f"1{random.randint(100000000, 999999999)}"
        alt_npi = f"2{random.randint(100000000, 999999999)}"  # DIFFERENT!

        # Select encounter type
        enc_type = random.choice(["OP", "IP", "ED", "OBS", "TH"])
        enc_type_full = {
            "OP": "Outpatient",
            "IP": "Inpatient",
            "ED": "Emergency",
            "OBS": "Observation",
            "TH": "Telehealth",
        }[enc_type]

        # Length of stay (calculated DIFFERENTLY in different columns!)
        base_los = random.randint(0, 14)
        alt_los = base_los + random.randint(-2, 3)  # DIFFERENT calculation!

        # Amounts (different formulas = different values!)
        base_charge = round(random.uniform(100, 50000), 2)
        allowed_pct = random.uniform(0.4, 0.7)
        paid_pct = random.uniform(0.7, 0.95)

        billed = base_charge
        billed_alt = round(base_charge * random.uniform(0.95, 1.05), 2)  # DIFFERENT!
        allowed = round(base_charge * allowed_pct, 2)
        allowed_alt = round(base_charge * random.uniform(0.35, 0.75), 2)  # DIFFERENT!
        paid = round(allowed * paid_pct, 2)
        paid_alt = round(allowed * random.uniform(0.65, 0.98), 2)  # DIFFERENT!

        # Diagnosis - use SYNTHETIC codes only
        dx_code = random.choice(ICD_CODES_DIRTY)
        dx_code_2 = random.choice(ICD_CODES_DIRTY)

        # Payer info
        payer = random.choice(PAYER_TYPES)
        payer_name = payer[0]
        payer_codes = {
            "Medicare": ["MCD", "MCR", "MDCR", "01"],
            "Medicaid": ["MCA", "MCAD", "02"],
            "Blue Cross Blue Shield": ["BCBS", "BC", "BX", "03"],
            "United Healthcare": ["UHC", "UNT", "UNHC", "04"],
            "Aetna": ["AET", "AETN", "05"],
            "Cigna": ["CIG", "CGN", "06"],
            "Humana": ["HUM", "HMN", "07"],
            "Self-Pay": ["SELF", "SP", "PAY", "99"],
            "Workers Compensation": ["WC", "WKRS", "WCOMP", "08"],
        }
        payer_abbrevs = payer_codes.get(payer_name, ["UNK", "OTH", "00"])

        # Patient demographics
        first_name = fake.first_name()
        last_name = fake.last_name()
        alt_last_name = fake.last_name()  # DIFFERENT for conflict!

        # Facility
        facility = random.choice(FACILITY_NAMES)

        # Boolean chaos values
        bool_values = ["0", "1", "Y", "N", "True", "False", "YES", "NO", "T", "F", ""]

        record = {
            # =====================================================================
            # PATIENT IDs (10+ columns, CONFLICTING values!)
            # =====================================================================
            "patient_id": str(base_patient_id),
            "patientID": str(alt_patient_id),  # DIFFERENT!
            "PAT_ID": str(base_patient_id),
            "pat_id": str(random.randint(10000, 99999)),  # DIFFERENT!
            "mrn": f"MRN-{base_patient_id}",
            "MRN": f"MRN-{alt_patient_id}",  # DIFFERENT!
            "member_id": f"MEM{random.randint(100000000, 999999999)}",
            "MEMBER_ID": f"MBR{random.randint(100000000, 999999999)}",  # DIFFERENT!
            "ssn": f"000-{random.randint(10, 99)}-{random.randint(1000, 9999)}",
            "internal_patient_id": f"INT-{random.randint(1000000, 9999999)}",
            # =====================================================================
            # DATE columns (10+ columns, DIFFERENT formats!)
            # =====================================================================
            "service_date": str(service_date.date()),
            "ServiceDate": service_date.strftime("%m/%d/%Y"),
            "svc_dt": service_date.strftime("%Y%m%d"),
            "dos": service_date.strftime("%d-%b-%Y"),
            "DATE_OF_SERVICE": service_date.isoformat(),
            "admit_date": str(service_date.date()),
            "admission_dt": service_date.strftime("%Y-%m-%d %H:%M:%S"),
            "ADMIT_DT": service_date.strftime("%m-%d-%Y"),
            "discharge_date": str((service_date + timedelta(days=base_los)).date()),
            "disch_dt": (service_date + timedelta(days=alt_los)).strftime("%Y%m%d"),  # DIFFERENT!
            # =====================================================================
            # DIAGNOSIS columns (8+ columns, CONFLICTING!)
            # =====================================================================
            "dx1": dx_code[0],
            "dx2": dx_code_2[0],
            "primary_dx": random.choice(ICD_CODES_DIRTY)[0],  # May differ from dx1!
            "ICD_CODE": dx_code[0],
            "diagnosis": dx_code[1],
            "dx_code": random.choice(["DX-001", "DX-002", "SYN-DIAB-01", "GEN-003"]),  # Random!
            "DX_CD": random.choice(ICD_CODES_DIRTY)[0],  # Different!
            "diag_category": random.choice(["Category A", "Category B", "Category C"]),
            # =====================================================================
            # PROVIDER columns (8+ columns, CONFLICTING!)
            # =====================================================================
            "provider_id": str(base_provider_id),
            "PROVIDER_ID": str(alt_provider_id),  # DIFFERENT!
            "npi": base_npi,
            "NPI": alt_npi,  # DIFFERENT!
            "attending_npi": f"1{random.randint(100000000, 999999999)}",  # Another different one!
            "provider_name": f"Dr. {last_name}",
            "PROVIDER_NM": f"DR {alt_last_name}",  # DIFFERENT!
            "specialty": random.choice([s[0] for s in SPECIALTIES]),
            # =====================================================================
            # AMOUNT columns (15+ columns, CONFLICTING values!)
            # =====================================================================
            "charge_amt": str(billed),
            "CHARGES": str(billed_alt),  # DIFFERENT!
            "billed": str(billed),
            "billed_amt": str(billed_alt),  # DIFFERENT!
            "total_charges": str(round(billed * random.uniform(0.9, 1.1), 2)),  # DIFFERENT!
            "gross_charges": str(round(billed * random.uniform(0.85, 1.15), 2)),  # DIFFERENT!
            "allowed_amt": str(allowed),
            "ALLOWED": str(allowed_alt),  # DIFFERENT!
            "paid_amt": str(paid),
            "PAID": str(paid_alt),  # DIFFERENT!
            "payment": str(round(paid * random.uniform(0.95, 1.05), 2)),  # DIFFERENT!
            "reimb_amt": str(round(paid * random.uniform(0.90, 1.10), 2)),  # DIFFERENT!
            "copay": str(round(random.uniform(10, 100), 2)),
            "COPAY": str(round(random.uniform(15, 150), 2)),  # DIFFERENT!
            "coinsurance": str(round(random.uniform(0, 500), 2)),
            "deductible": str(round(random.uniform(0, 1000), 2)),
            # =====================================================================
            # BOOLEAN chaos (5+ columns, mixed formats!)
            # =====================================================================
            "is_admitted": str(random.choice(bool_values)),
            "admitted_flg": str(random.choice(["Y", "N", "1", "0"])),
            "emergency_flag": str(random.choice(bool_values)),
            "is_emergency": str(random.choice([0, 1, "Y", "N", True, False])),
            "has_surgery": str(random.choice(bool_values)),
            # =====================================================================
            # CRYPTIC codes (10+ columns, no documentation!)
            # =====================================================================
            "ins_type": random.choice(payer_abbrevs),
            "insurance_cd": random.choice(payer_abbrevs),
            "payer_cd": random.choice(payer_abbrevs),
            "PAYER": payer_name,
            "payer_name": random.choice([payer_name, payer_abbrevs[0]]),  # Inconsistent!
            "INS_NAME": random.choice([payer_name.upper(), payer_abbrevs[0]]),
            "coverage_level": random.choice(["1", "2", "3", "F", "E", "C"]),
            "enc_type": enc_type,
            "encounter_type": enc_type_full,
            "type_cd": str(random.randint(1, 5)),
            "flg1": str(random.choice([0, 1])),
            "flg2": random.choice(["Y", "N"]),
            "cd1": random.choice(["A", "B", "C", "D"]),
            "cd2": random.choice(["X", "Y", "Z"]),
            "val": str(round(random.uniform(0, 1000), 2)),
            "amt": str(round(random.uniform(0, 500), 2)),
            "cnt": str(random.randint(1, 100)),
            "status_cd": random.choice(["A", "B", "C", "P", "D", "X"]),
            # =====================================================================
            # ENCOUNTER IDs (conflicting!)
            # =====================================================================
            "enc_id": f"ENC-{i:08d}",
            "encounter_id": str(i),
            "ENCOUNTER_ID": f"E{i}",  # Different format!
            "visit_id": f"V-{random.randint(1000000, 9999999)}",  # Different!
            # =====================================================================
            # LENGTH OF STAY (multiple calculations!)
            # =====================================================================
            "los": str(base_los),
            "LOS": str(alt_los),  # DIFFERENT!
            "length_of_stay": str(base_los),
            "stay_days": str(random.randint(0, 20)),  # DIFFERENT!
            "days_in_hospital": str(alt_los + random.randint(-1, 2)),  # DIFFERENT!
            "duration": str(random.randint(0, 21)),  # DIFFERENT!
            # =====================================================================
            # PATIENT DEMOGRAPHICS (conflicting!)
            # =====================================================================
            "patient_name": f"{first_name} {last_name}",
            "PAT_NAME": f"{first_name} {alt_last_name}",  # DIFFERENT!
            "first_name": first_name,
            "last_name": last_name,
            "LAST_NM": alt_last_name,  # DIFFERENT!
            "dob": str((datetime.now() - timedelta(days=random.randint(6570, 36500))).date()),
            "DOB": (datetime.now() - timedelta(days=random.randint(6570, 36500))).strftime(
                "%m/%d/%Y"
            ),  # Different date!
            "gender": random.choice(["M", "F", "Male", "Female", "U", "Unknown", "1", "2"]),
            "sex": random.choice(["M", "F", "MALE", "FEMALE", "O"]),  # Different value!
            # =====================================================================
            # FACILITY (inconsistent)
            # =====================================================================
            "facility": facility,
            "FACILITY": facility.upper(),
            "fac_cd": f"FAC-{random.randint(100, 999)}",
            "location": random.choice(FACILITY_NAMES),  # May differ!
            "LOC_CD": random.choice(["L01", "L02", "L03", "L04", "L05"]),
            # =====================================================================
            # TIMESTAMPS (various formats)
            # =====================================================================
            "created_at": (service_date + timedelta(hours=random.randint(0, 23))).isoformat(),
            "modified_dt": service_date.strftime("%Y-%m-%d %H:%M:%S"),
            "last_update": service_date.strftime("%m/%d/%y"),
            "etl_timestamp": datetime.now().isoformat(),
            # =====================================================================
            # MORE RANDOM FIELDS (to hit 100+ columns)
            # =====================================================================
            "ref_num": f"REF{random.randint(100000, 999999)}",
            "auth_num": f"AUTH{random.randint(10000, 99999)}",
            "claim_id": f"CLM-{random.randint(1000000000, 9999999999)}",
            "CLAIM_ID": f"C{random.randint(1000000, 9999999)}",  # DIFFERENT!
            "invoice_num": f"INV-{random.randint(100000, 999999)}",
            "account_num": f"ACCT-{random.randint(10000, 99999)}",
            "bill_type": random.choice(["111", "121", "131", "141", "112"]),
            "rev_code": random.choice(["0100", "0120", "0250", "0300", "0450"]),
            "drg": random.choice(["470", "871", "291", "392", "065"]),
            "DRG_CD": random.choice(["470", "871", "291", "392", "065"]),  # May differ!
            "proc_cd": random.choice(["99213", "99214", "99215", "99221", "99281"]),
            "modifier": random.choice(["", "25", "59", "GT", "GY"]),
            "pos": random.choice(["11", "21", "22", "23", "81"]),
            "tos": random.choice(["1", "2", "3", "4", "5"]),
            "units": str(random.randint(1, 10)),
            "UNITS": str(random.randint(1, 12)),  # DIFFERENT!
        }

        records.append(record)

    # Create DataFrame with all columns as strings to avoid mixed type issues
    df = pd.DataFrame(records)

    # Verify column count
    print("\nSuper Table Generated:")
    print(f"  Rows: {len(df):,}")
    print(f"  Columns: {len(df.columns)}")

    print("\nColumn examples demonstrating chaos:")
    print("  Patient IDs: patient_id, patientID, PAT_ID, pat_id, mrn, MRN, member_id, MEMBER_ID")
    print("  Dates: service_date, ServiceDate, svc_dt, dos, DATE_OF_SERVICE, admit_date")
    print("  Amounts: charge_amt, CHARGES, billed, billed_amt, paid_amt, PAID")
    print("  Booleans: is_admitted (0/1/Y/N/True/False), admitted_flg, emergency_flag")
    print("  LOS: los, LOS, length_of_stay, stay_days, days_in_hospital, duration")

    # Save to parquet if output directory specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "healthcare_super_table.parquet")
        df.to_parquet(path, index=False)
        print(f"\n    Saved {path}")

    return df


if __name__ == "__main__":
    df = generate_healthcare_super_table(n_rows=50000, output_dir="./data/healthcare_super")

    print("\n" + "=" * 80)
    print("ANTI-PATTERNS IN THIS TABLE:")
    print("=" * 80)
    print(HEALTHCARE_FAILURE_SCENARIOS)
