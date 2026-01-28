"""
Healthcare Dataset Generator
============================

A fictional healthcare dataset with two versions demonstrating good vs bad data modeling:

**Clean Version (Star Schema) - 9 Tables:**

Dimensions:
    - dim_patient: Patient master data (demographics, insurance)
    - dim_provider: Provider/physician data (NPI, specialty, facility)
    - dim_date: Date dimension with fiscal calendar and flu season
    - dim_diagnosis: ICD-10 diagnosis codes with descriptions
    - dim_procedure: CPT procedure codes with descriptions
    - dim_payer: Insurance payer and plan information

Facts:
    - fact_encounters: Patient encounters (admissions, visits)
    - fact_claims: Insurance claims with amounts
    - fact_prescriptions: Medication prescriptions

**Dirty Version (Super Table) - 1 Table with 100+ columns:**

Anti-patterns included:
    - 10+ patient ID columns (with CONFLICTING values!)
    - 10+ date columns (different formats: date, MM/DD/YYYY, YYYYMMDD, ISO)
    - 8+ diagnosis columns (dx1, primary_dx may differ!)
    - 8+ provider columns (npi and NPI are DIFFERENT!)
    - 15+ amount columns (all slightly different values!)
    - Mixed boolean formats (0/1/Y/N/True/False/YES/NO)
    - Cryptic undocumented codes (enc_type, flg1, cd1, status_cd)

Usage
-----

.. code-block:: python

    from dataset_generators.healthcare import (
        generate_healthcare_star_schema,
        generate_healthcare_super_table,
        set_random_seed,
        scale_count,
    )

    # Set seed for reproducibility
    set_random_seed(42)

    # Generate star schema (clean version)
    star_data = generate_healthcare_star_schema(
        scale=1.0,  # 1.0 = full size, 0.1 = 10%
        seed=42,
        output_dir='./data/healthcare_star'
    )

    # Generate super table (dirty version)
    super_df = generate_healthcare_super_table(
        n_rows=50000,
        seed=42,
        output_dir='./data/healthcare_super'
    )

Demo Questions
--------------

Questions that **FAIL** on Super Table:

1. "How many unique patients do we have?"
   - Problem: 10+ patient ID columns with DIFFERENT values

2. "Show admissions from January 2024"
   - Problem: 10+ date columns with different formats

3. "What is our total revenue?"
   - Problem: 15+ amount columns, all different values

4. "Which provider has the most encounters?"
   - Problem: provider_id vs PROVIDER_ID have DIFFERENT values

5. "Show only emergency encounters"
   - Problem: is_emergency has 0/1/Y/N/True/False mixed

Same Questions **SUCCEED** on Star Schema:

- Single patient_key in fact_encounters
- Consistent date_key (YYYYMMDD integer)
- Clear billed_amount, paid_amount columns
- Single provider_key linking to dim_provider
- Consistent encounter_type string values
"""

from .utils import set_random_seed, scale_count
from .clean_generator import generate_healthcare_star_schema
from .dirty_generator import generate_healthcare_super_table, HEALTHCARE_FAILURE_SCENARIOS

__all__ = [
    'set_random_seed',
    'scale_count',
    'generate_healthcare_star_schema',
    'generate_healthcare_super_table',
    'HEALTHCARE_FAILURE_SCENARIOS',
]
