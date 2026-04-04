"""Pydantic models for medical benefit drug policies and payer drug lists."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class DrugEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    generic_name: Optional[str] = None
    brand_names: list[str] = Field(default_factory=list)
    hcpcs_codes: list[str] = Field(default_factory=list)
    is_biosimilar: Optional[bool] = None
    reference_product: Optional[str] = None


class CoveredIndication(BaseModel):
    model_config = ConfigDict(extra="ignore")

    indication_name: Optional[str] = None
    clinical_criteria: list[str] = Field(default_factory=list)
    required_combination_regimens: list[str] = Field(default_factory=list)
    icd10_codes: list[str] = Field(default_factory=list)
    applies_to_products: list[str] = Field(default_factory=list)


class StepTherapy(BaseModel):
    model_config = ConfigDict(extra="ignore")

    required_prior_drugs: list[str] = Field(default_factory=list)
    condition_description: Optional[str] = None
    applies_to_products: list[str] = Field(default_factory=list)


class DosingLimit(BaseModel):
    model_config = ConfigDict(extra="ignore")

    description: Optional[str] = None
    max_dose: Optional[str] = None
    frequency: Optional[str] = None
    max_units_per_period: Optional[str] = None


class PolicyDocument(BaseModel):
    """Rich single-drug (or multi-drug) medical policy. Most fields optional for partial extraction."""

    model_config = ConfigDict(extra="ignore")

    payer: Optional[str] = None
    policy_id: Optional[str] = None
    policy_title: Optional[str] = None
    effective_date: Optional[str] = None
    revision_date: Optional[str] = None
    document_type: Optional[Literal["single_drug_policy", "drug_list"]] = "single_drug_policy"
    drugs: list[DrugEntry] = Field(default_factory=list)
    covered_indications: list[CoveredIndication] = Field(default_factory=list)
    prior_auth_required: Optional[bool] = None
    step_therapy: list[StepTherapy] = Field(default_factory=list)
    excluded_indications: list[str] = Field(default_factory=list)
    approval_duration_initial: Optional[str] = None
    approval_duration_renewal: Optional[str] = None
    dosing_limits: list[DosingLimit] = Field(default_factory=list)
    site_of_care_restrictions: Optional[str] = None
    general_requirements: list[str] = Field(default_factory=list)
    preferred_products: list[str] = Field(default_factory=list)
    policy_changes: list[str] = Field(default_factory=list)
    raw_text: Optional[str] = None


class DrugListEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    payer: Optional[str] = None
    hcpcs_code: Optional[str] = None
    drug_name: Optional[str] = None
    description: Optional[str] = None
    coverage_level: Optional[str] = None
    notes: Optional[str] = None
    covered_alternatives: list[str] = Field(default_factory=list)


class DrugListChunkExtraction(BaseModel):
    """One chunk of a large consolidated drug list (e.g. Priority Health MDL)."""

    model_config = ConfigDict(extra="ignore")

    section_title: Optional[str] = None
    entries: list[DrugListEntry] = Field(default_factory=list)


class DrugListDocument(BaseModel):
    """Merged result after processing all chunks of a drug list PDF."""

    model_config = ConfigDict(extra="ignore")

    payer: Optional[str] = None
    document_type: Literal["drug_list"] = "drug_list"
    source_filename: Optional[str] = None
    entries: list[DrugListEntry] = Field(default_factory=list)
