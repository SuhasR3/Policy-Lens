# ANTON Rx CHALLENGE
## Medical Benefit Drug Policy Tracker

**Innovation Hacks 2.0 • April 3–5, 2026 • Arizona State University**

> *Confidential — For Hackathon Use Only | Anton Rx LLC*

---

## Problem Statement

Health plans govern coverage of medical benefit drugs through individual medical policies that vary by payer and change frequently. There is no centralized, standardized source for tracking which drugs are covered under which policies, what clinical criteria apply, or how those policies differ across plans. Build an AI-powered system that can ingest, parse, and normalize medical policy documents from multiple health plans to create a searchable, comparable view of medical benefit drug coverage, enabling users to quickly answer questions like:

- *"Which plans cover Drug X?"*
- *"What prior auth criteria does Plan Y require for Drug Z?"*
- *"What changed across payer policies this quarter?"*

---

## The Simple Version

You know how when you get a prescription, you go to the pharmacy, hand over your insurance card, and the pharmacist can instantly tell you if your drug is covered and what it'll cost? That's the **pharmacy benefit** — it's standardized, electronic, and pretty well organized.

Now imagine a completely different world. Your doctor says you need a medication that has to be injected or infused in a clinic — something like a cancer drug, an immunotherapy, or a biologic for rheumatoid arthritis. These drugs don't go through the pharmacy at all. They're covered under your **medical benefit** — the same part of your insurance that covers surgeries and doctor visits.

Here's the problem: there's no clean formulary list for these drugs. Instead, every health plan writes its own **medical policy** — a lengthy document that spells out whether the drug is covered, what diagnosis you need, what other drugs you must have tried first, whether prior authorization is required, and where you're allowed to receive the infusion.

These policies are different at every health plan. They're published in different formats. They change constantly. And there's no single place to look them all up and compare them.

**That's the problem we want you to solve.**

---

## A Note on Terminology

One thing that makes this space confusing — even for people who work in it — is that the same concept goes by many different names depending on who you're talking to. The following terms all refer to the same general category: *drugs that are administered in a clinical setting and covered under a patient's medical insurance benefit rather than their pharmacy benefit:*

- Medical benefit drugs
- Medical pharmacy drugs
- Medical drug
- Specialty drugs on the medical benefit
- Provider-administered drugs
- Physician-administered drugs
- Medical injectables / Medical injectable drugs
- Buy-and-bill drugs *(referring to how the provider purchases the drug and bills the insurer)*

Similarly, the policies governing these drugs go by different names at different health plans: *medical policies, medical benefit drug policies, drug and biologic coverage policies, medical pharmacy policies, coverage determination guidelines, clinical policy bulletins,* and others.

These are all variations of the same thing: a document that defines whether and how a health plan covers a specific drug under the medical benefit.

> Don't let the vocabulary trip you up. If it's a drug given by a doctor or nurse in a clinical setting and the insurance company has a policy document saying when they'll pay for it, that's what we're talking about.

---

## Why This Matters

Anton Rx is an independent formulary and rebate management firm that advises health plans and other stakeholders on how to manage drug costs across both the pharmacy and medical benefit. To do that effectively, the team needs to know — across dozens of payers — which medical benefit drugs are covered, under what criteria, and how those criteria differ from plan to plan.

Today, this is a largely **manual, research-intensive process**: analysts read policy PDFs one at a time, extract the relevant details, and try to keep up with quarterly changes. It's slow, expensive, and error prone.

---

## The Challenge

Build an AI-powered system that can ingest, parse, and normalize medical policy documents from multiple health plans to create a searchable, comparable view of medical benefit drug coverage across payers.

Your solution should help a user answer questions like:

- "Which health plans cover Drug X under their medical benefit?"
- "What prior authorization criteria does Plan Y require for Drug Z?"
- "How do coverage criteria for Drug X differ between Plan A, Plan B, and Plan C?"
- "What medical policy changes were made across payers this quarter?"

---

## Where to Find Real Data

**Starter data:** A zip file of sample policies is included to get you going immediately — no scraping required. If you want additional policies beyond what's provided, you can download more from the sources below.

Major health plans publish their medical policies online. Each payer organizes and formats their policies differently, which is part of the challenge:

| Payer | Format | Links |
|---|---|---|
| **UnitedHealthcare** | Individual PDFs per drug, with monthly update bulletins | [Commercial Medical Drug Policies](https://www.uhcprovider.com) — Example: Botulinum Toxins A and B |
| **Cigna** | PDFs organized by policy number and A-Z index | [Cigna Drug Policy A-Z Index](https://www.cigna.com) — Example: Rituximab for Non-Oncology Indications |
| **EmblemHealth** | Individual policies per drug category via third-party portal | [GatewayPA — EmblemHealth Policies](https://www.gatewaypa.com) — Example: Denosumab |
| **UPMC Health Plan** | Single comprehensive documents for all medical pharmacy coverage | [UPMC Prior Authorization Policies](https://www.upmchealthplan.com) / [UPMC Part B Step Therapy](https://www.upmchealthplan.com) |
| **Priority Health** | Single drug list document | [2026 Commercial Medical Drug List (PDF)](https://www.priorityhealth.com) |
| **BCBS North Carolina** | Search-style interface by individual drug | [BCBS NC Drug Search](https://www.bcbsnc.com) — Example: Preferred Injectable Oncology Program |
| **Florida Blue** | Third-party platform (MCG), searchable by drug category or specific drug | [Florida Blue MCG Portal](https://www.floridablue.com) — Example: Bevacizumab |

Notice how varied the formats are — some plans publish one PDF per drug, others put everything in a single document, and others use interactive web portals. This inconsistency is exactly why this problem is so hard to solve manually.

> You don't need to ingest all of these — even a prototype that demonstrates the concept across **3–5 policies from 2–3 payers** would be impressive.

---

## What We're Looking For

You have creative freedom in how you approach this, but strong submissions will demonstrate some combination of the following:

- **Ingestion and parsing** of unstructured or semi-structured policy documents (PDFs, HTML pages, etc.)
- **Extraction of structured data:** drug names, covered indications, clinical criteria, prior authorization requirements, step therapy requirements, effective dates, site-of-care restrictions
- **Normalization across payers** so that apples-to-apples comparison is possible
- **A usable interface:** search, filtering, side-by-side comparison views, or natural language querying
- **Change detection or alerting** when a policy is updated

**Output format:** There are no required output formats. Teams are free to deliver a web app, dashboard, API, CLI tool, or any other interface that demonstrates their solution. We care about the approach and the thinking, not a specific deliverable format.

---

## Judging Criteria

| Criterion | Weight | Description |
|---|---|---|
| **Problem Understanding** | 20% | Does the team clearly understand the real-world pain point? |
| **Technical Implementation** | 25% | How effectively does the solution use AI/ML, NLP, or other technical approaches? |
| **Usability & Design** | 20% | Is the output clear, navigable, and useful to a non-technical stakeholder? |
| **Completeness** | 20% | How end-to-end is the prototype? (ingestion → extraction → comparison → interface) |
| **Creativity & Wow Factor** | 15% | Did the team do something unexpected or particularly clever? |

**Prize:** Announced at opening ceremony.

---

## Glossary

| Term | Definition |
|---|---|
| **Biologic** | A complex drug derived from living organisms, often administered by injection or infusion. Examples include treatments for cancer, autoimmune diseases, and rare conditions. Biologics are among the most expensive drugs on the market. |
| **Buy-and-Bill** | A model where a healthcare provider purchases a drug, administers it to the patient, and then bills the patient's insurance for reimbursement. This is the standard model for most medical benefit drugs. |
| **Coverage Criteria** | The specific clinical conditions a patient must meet for a health plan to approve coverage of a drug. These may include diagnosis requirements, lab results, prior drug failures, or prescriber specialty requirements. |
| **Formulary** | A list of drugs covered by an insurance plan, typically organized into tiers that affect patient cost-sharing. Pharmacy benefit drugs have well-structured formularies; medical benefit drugs generally do not — which is the core of this challenge. |
| **HCPCS Code** | Healthcare Common Procedure Coding System. A standardized code set used to bill for drugs, procedures, and services. Medical benefit drugs are identified by J-codes (e.g., J9035 for bevacizumab). These codes appear in medical policies and are useful for identifying specific drugs across payers. |
| **Medical Benefit** | The part of a health insurance plan that covers services provided by doctors and facilities — surgeries, office visits, and infusions. Drugs administered in a clinical setting are typically covered here, not under the pharmacy benefit. |
| **Medical Policy** | A document published by a health plan that defines whether a specific drug or service is considered medically necessary and under what conditions it will be covered. Also called: medical benefit drug policy, drug and biologic coverage policy, medical pharmacy policy, coverage determination guideline, clinical policy bulletin. The name varies by payer, but the function is the same. |
| **Payer** | An organization that pays for healthcare services — typically a health insurance company or health plan (e.g., UnitedHealthcare, Cigna, Aetna, a Blue Cross Blue Shield plan). |
| **PBM** | Pharmacy Benefit Manager. A company that manages the pharmacy benefit on behalf of a health plan, including formulary design, rebate negotiation, and claims processing. PBMs typically do not manage the medical benefit side — which is one reason medical benefit drug tracking is less standardized. |
| **Pharmacy Benefit** | The part of a health insurance plan that covers prescription drugs picked up at a retail or mail-order pharmacy. This is the familiar, well-organized side of drug coverage with clear formulary tiers and electronic eligibility checks. |
| **Prior Authorization (PA)** | A requirement that a provider obtain approval from the health plan before administering a drug, confirming that the patient meets coverage criteria. PA criteria vary by payer and by drug. |
| **Site of Care** | Where a drug is physically administered: hospital outpatient department, physician office, ambulatory infusion center, or home infusion. Some health plans restrict which sites they will reimburse, often preferring lower-cost settings. |
| **Step Therapy** | A policy requiring patients to try (and fail) one or more lower-cost or preferred drugs before a more expensive drug will be covered. For example, a plan might require trying a biosimilar before approving the reference biologic. |

---

## About Anton Rx

Anton Rx is a pharmacy intelligence firm that helps health plans and other managed care organizations lower pharmaceutical drug costs through a proprietary matrix of formulary designs, custom contracts, and advanced analytics. Anton Rx focuses on delivering transparent, actionable insights that drive better decisions and better outcomes.

Our sister company, **Anton Intelligence**, is the technology and AI arm of the organization, building software that powers smarter decisions in healthcare. Our engineering team works at the intersection of AI, data analytics, and healthcare operations — and **we're hiring**. If you're passionate about using technology to solve real problems in a complex, regulated industry, come talk to us at the event.
