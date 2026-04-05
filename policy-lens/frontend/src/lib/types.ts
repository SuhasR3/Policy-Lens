export interface DrugSearchResult {
  id: number;
  policy_id: number;
  payer: string;
  policy_title: string;
  effective_date: string | null;
  drug_name: string;
  generic_name: string | null;
  brand_names: string[] | null;
  hcpcs_code: string | null;
  access_status_group: string | null;
  drug_category: string | null;
  prior_auth_required: number | null;
  step_therapy_required: number | null;
  site_of_care_required: number | null;
  dosing_limit_summary: string | null;
  covered_diagnoses: string[] | null;
  coverage_level: string | null;
  notes: string | null;
}

export interface TrendingDrug {
  drug_name: string;
  payer_count: number;
}

export interface PayerComparison {
  id: number;
  policy_id: number;
  payer: string;
  policy_title: string;
  effective_date: string | null;
  drug_name: string;
  generic_name: string | null;
  brand_names: string[] | null;
  hcpcs_code: string | null;
  hcpcs_codes: string[] | null;
  access_status_group: string | null;
  coverage_level: string | null;
  drug_category: string | null;
  prior_auth_required: number | null;
  prior_auth_criteria: string | null;
  step_therapy_required: number | null;
  step_therapy_details: string | null;
  site_of_care_required: number | null;
  site_of_care_details: string | null;
  dosing_limit_summary: string | null;
  covered_diagnoses: string[] | null;
  notes: string | null;
}

export interface SummaryMetric {
  label: string;
  value: string;
  detail: string;
  primary?: boolean;
}

export interface CompareSummary {
  payer_coverage: SummaryMetric;
  total_entries: SummaryMetric;
  clinical_variance: SummaryMetric;
  market_access_score: SummaryMetric;
}
