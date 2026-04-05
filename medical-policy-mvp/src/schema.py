"""Pydantic models powering cross-payer coverage comparison.

Three levels:
  PolicyDocument   — one per ingested file (metadata + lists)
  DrugEntry        — one per drug product mentioned in the policy
  CoverageEntry    — one per (drug × indication); drives the comparison view
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Step therapy — two distinct types
# ---------------------------------------------------------------------------


class ClinicalStepTherapy(BaseModel):
    """Patient must try a DIFFERENT drug/class first (efficacy-driven)."""

    required_prior_drugs: list[str] = []
    condition: str = ""  # "failure, contraindication, or intolerance to one"


class BiosimilarStepTherapy(BaseModel):
    """Patient must try a CHEAPER VERSION of the same drug first (cost-driven)."""

    preferred_products: list[str] = []   # ["Mvasi", "Zirabev"]
    restricted_products: list[str] = []  # ["Avastin", "Alymsys"]
    condition: str = ""  # "inadequate response, contraindication, or intolerance"


# ---------------------------------------------------------------------------
# Level 2: Drug identity
# ---------------------------------------------------------------------------


class DrugEntry(BaseModel):
    generic_name: str                          # "bevacizumab"
    brand_name: Optional[str] = None           # "Avastin"
    hcpcs_codes: list[str] = []                # ["J9035"]
    is_biosimilar: bool = False
    reference_product: Optional[str] = None    # "Avastin" if biosimilar
    access_status: Optional[
        Literal["preferred", "non_preferred", "restricted", "not_covered", "excluded"]
    ] = None
    category_position: Optional[str] = None    # "preferred 1 of 2"
    therapeutic_class: Optional[str] = None    # "VEGF inhibitor"


# ---------------------------------------------------------------------------
# Level 3: Coverage entry — one row per (drug × indication)
# ---------------------------------------------------------------------------


class CoverageEntry(BaseModel):
    drug_generic_name: str
    drug_brand_names: list[str] = []
    hcpcs_codes: list[str] = []
    indication: str                            # "Cervical Cancer"
    applies_to_products: list[str] = []        # ["Botox only"] or ["all"]
    is_covered: bool = True
    coverage_level: Optional[str] = None       # "covered with PA"
    pa_required: bool = False
    pa_criteria: list[str] = []                # preserve AND/OR logic; prefix "ALL:" or "ONE:"
    clinical_step_therapy: Optional[ClinicalStepTherapy] = None
    biosimilar_step_therapy: Optional[BiosimilarStepTherapy] = None
    dosing_limits: Optional[str] = None
    site_of_care_restriction: Optional[str] = None
    approval_duration_initial: Optional[str] = None
    approval_duration_renewal: Optional[str] = None
    required_regimens: list[str] = []          # ["paclitaxel + cisplatin", ...]
    icd10_codes: list[str] = []


# ---------------------------------------------------------------------------
# Excluded indications
# ---------------------------------------------------------------------------


class ExcludedIndication(BaseModel):
    indication: str                        # "Chronic daily headache"
    applies_to_products: list[str] = []   # ["all"] or ["Daxxify", "Dysport"]
    reason: Optional[str] = None          # "unproven and not medically necessary"


# ---------------------------------------------------------------------------
# Level 1: Policy document (one per file)
# ---------------------------------------------------------------------------


class PolicyDocument(BaseModel):
    payer: str                             # "Florida Blue"
    policy_id: Optional[str] = None       # "09-J0000-66"
    policy_title: str
    document_type: Literal["single_drug_policy", "drug_list", "preferred_product_program"]
    effective_date: Optional[str] = None
    revision_date: Optional[str] = None
    original_effective_date: Optional[str] = None
    general_requirements: list[str] = []  # apply to ALL drugs/indications in the policy
    policy_changes: list[str] = []        # what changed in the latest revision
    drugs: list[DrugEntry] = []
    coverage_entries: list[CoverageEntry] = []
    excluded_indications: list[ExcludedIndication] = []
    raw_text: Optional[str] = None        # filled after extraction for RAG


# ---------------------------------------------------------------------------
# Drug list models (Priority Health-style mega documents)
# ---------------------------------------------------------------------------


class DrugListEntry(BaseModel):
    payer: str
    hcpcs_code: str
    drug_name: Optional[str] = None
    description: str
    coverage_level: str                    # "PA", "Not Covered", "SOS", "CC", "CA"
    pa_required: bool = False              # derived from coverage_level
    site_of_service: bool = False          # true if SOS in notes
    notes: Optional[str] = None
    covered_alternatives: list[str] = []
    therapeutic_class: Optional[str] = None  # from TOC section header


class DrugListDocument(BaseModel):
    payer: str
    policy_title: str
    effective_date: Optional[str] = None
    entries: list[DrugListEntry] = []
