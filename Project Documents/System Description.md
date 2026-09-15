PRACTICAL ASSIGNMENT | AGENTIC AI ENGINEER

# PRACTICAL ASSIGNMENT

Armenian Bank Product  
Tariff Monitoring Agent  
Agentic AI Engineer (Google Cloud AI)

Timeframe                                                    Up to 12 calendar days

Core stack                                                   Python, Google Agent Development Kit (ADK), Gemini

Goal                                                         Demonstrate practical agent engineering, not only  
                                                             final extraction accuracy

## 1. Objective

Build an AI agent that monitors publicly available banking product information from Armenian banks public website (in your case https://ameriabank.am or https://acba.am), finds the official product documents (such as "տեղեկատվական ամփոփագիր") and/or webpages, extracts key tariff parameters, stores the retrieved data, detects changes between monitoring runs, and presents verified results with source evidence. Only publicly accessible pages and documents should be used.

The assignment is intended to demonstrate your practical engineering skills across agent design, Google ADK, tool use, RAG, document processing/OCR, validation, security, human-in-the-loop (HITL), error handling, observability, testing, and Python software engineering.

## 2. Business Scenario

The organization wants to monitor publicly available product tariffs from Armenian banks. For this assignment, choose one Armenian bank and support at least two banking products.

• Consumer loan  
• Mortgage  
• Business loan  
• Credit card  
• Deposit

The user may provide an imprecise product name, a synonym, or a name in Armenian/English. The agent should identify the intended product and locate the most authoritative available information.

Candidate Assignment • Confidential for recruitment use

PRACTICAL ASSIGNMENT | AGENTIC AI ENGINEER

Priority should be given to official bank sources, including official product pages and documents such as «տեղեկատվական ամփոփագիր», «ամփոփաթերթիկ», or an equivalent official product-information document.

## 3. Example Request

“Find the current consumer-loan tariffs for Bank X and show me the main financial conditions.”

The result should identify the official source, extract the requested tariff parameters, provide supporting evidence, report extraction/validation status, and clearly indicate uncertainty or cases requiring human review.

## 4. Expected End-to-End Flow

```text
User request / monitoring trigger
            ↓
      Understand product
            ↓
 Discover official source
            ↓
 Website / PDF retrieval
            ↓
 Document processing
   (parse or OCR fallback)
            ↓
   Clean / structure / chunk
            ↓
      Index / RAG retrieval
            ↓
   Structured extraction
            ↓
 Deterministic validation
            ↓
     HITL when required
            ↓
       Store snapshot
            ↓
 Compare with previous snapshot
            ↓
 Report tariff / detected changes
```

## 5. Core Requirements

### 5.1 ADK Agent

Implement the solution as a Google ADK agent. Clearly define:

• the agent role and instructions;  
• available tools and their responsibilities;  
• state/session usage where appropriate;

Candidate Assignment • Confidential for recruitment use

PRACTICAL ASSIGNMENT | AGENTIC AI ENGINEER

• stopping and error conditions;  
• which decisions are delegated to Gemini and which controls remain deterministic.

The LLM must not receive unrestricted direct access to databases, the filesystem, or arbitrary network operations.

### 5.2 Tool Design

Implement several focused Python tools rather than one generic function that performs the entire task. The exact decomposition is your design decision and should be justified.

```text
Possible examples:
discover_product_sources(bank_url, product_query)
download_document(url)
extract_document_content(document)
search_product_knowledge(product_query)
extract_tariff_parameters(content)
get_previous_tariff_snapshot(bank, product)
save_tariff_snapshot(result)
```

### 5.3 Official Source Discovery

Starting from an approved bank domain, discover the relevant product page and/or official product document. Product terminology may differ from the user's wording, so demonstrate a reasonable semantic, fuzzy, or hybrid matching approach.

The solution must stay within the selected official bank domain or an explicitly configured allowlist. Do not bypass authentication, CAPTCHA, access restrictions, or anti-bot protection.

### 5.4 PDF, OCR and Document Processing

Support both of the following document paths:

• Digital PDF → direct text/content extraction.  
• Scanned/image PDF → OCR fallback → extracted content.

Demonstrate reasonable cleaning and structuring: repeated headers/footers, page numbers, broken lines, duplicate content, headings/sections, tables, Armenian text, and important numerical information where applicable.

If the chosen live bank documents do not require OCR, demonstrate the OCR fallback using at least one rendered or scanned sample page.

### 5.5 Chunking and RAG

Create a small RAG knowledge layer from retrieved official product information. Explain your chunking strategy, metadata, indexing/retrieval approach, and how retrieved evidence is supplied to the model.

Candidate Assignment • Confidential for recruitment use

PRACTICAL ASSIGNMENT | AGENTIC AI ENGINEER

```text
Example metadata:
{
  "bank": "...",
  "product": "...",
  "document_name": "...",
  "source_url": "...",
  "language": "hy",
  "retrieved_at": "...",
  "section": "...",
  "page": 4
}
```

You may choose the vector/search implementation. We are evaluating whether you understand the pipeline and trade-offs, not whether you use a particular vector database.

### 5.6 Structured Tariff Extraction

For a loan product, support a structured schema containing at least:

• Արժույթ (Currency)  
• Ժամկետ (Term)  
• Գումար (Amount)  
• Անվանական տոկոսադրույք (Nominal Interest Rate)  
• Փաստացի տոկոսադրույք (Effective Interest Rate / EIR)  
• Ապահովվածություն (Collateral/Security)  
• Հայտի ուսումնասիրության վճար (Application Fee)  
• Տրամադրման վճար (Disbursement Fee)  
• Սպասարկման վճար (Service Fee)  
• Աշխատավարձը բանկով ստանալիս արտոնություններ (Salary Customer Privileges)

You may improve or normalize the schema. Missing information must be explicitly represented as missing/NOT_FOUND; the model must not invent values.

### 5.7 Evidence and Provenance

Important extracted fields must be traceable to their source. Evidence should identify enough information to verify the value, such as document/page/section or equivalent source location.

```text
Example:
Nominal interest rate: 13.5%
Source document: Consumer Loan Information Summary
Page: 3
Section: Interest Rate
```

### 5.8 Deterministic Validation

Do not rely only on Gemini to determine whether extracted data is valid. Implement deterministic checks where appropriate.

• schema and required-field validation;  
• currency/value normalization;  
• interest-rate and amount representation checks;

Candidate Assignment • Confidential for recruitment use

PRACTICAL ASSIGNMENT | AGENTIC AI ENGINEER

• valid term/duration formats;  
• approved source-domain validation;  
• file type/content-size validation;  
• explicit handling of missing values.

Pydantic or an equivalent approach may be used.

### 5.9 Tariff Change Detection

Persist a tariff snapshot and compare a new retrieval against the previous version. Report only meaningful changes.

```text
Previous nominal rate: 12.5%
Current nominal rate: 13.5%

Detected change:
Nominal interest rate: 12.5% → 13.5%
```

Normalize formatting before comparison so equivalent values such as “10 000 000 AMD” and “10,000,000 AMD” do not create false change alerts. The monitoring trigger may be scheduled or simulated.

### 5.10 Human-in-the-Loop (HITL)

Implement at least one meaningful HITL scenario, for example:

• two plausible official PDFs are found and a reviewer selects the correct one;  
• a large/unexpected tariff change requires confirmation;  
• OCR or extraction quality is insufficient;  
• two official sources contain conflicting values.

The reviewer must receive enough source evidence to make the decision. A simple CLI or lightweight web approval interface is sufficient.

### 5.11 Error Handling and Reliability

Handle realistic failures in a controlled manner, including several of the following:

• website unavailable or HTTP timeout;  
• 404/missing PDF;  
• document parsing or OCR failure;  
• Gemini/API failure;  
• invalid structured output;  
• required field missing;  
• multiple candidate documents;  
• product not found;  
• irrelevant RAG retrieval;  
• previous snapshot unavailable.

Use reasonable network timeouts. Retries must be bounded and applied only to appropriate transient failures, preferably with backoff. Do not replace failures with fabricated business data.

### 5.12 Security

Demonstrate production-minded security controls, at minimum:

Candidate Assignment • Confidential for recruitment use

PRACTICAL ASSIGNMENT | AGENTIC AI ENGINEER

• no API keys/secrets committed to source code;  
• configuration through environment or an appropriate secret mechanism;  
• input and output validation;  
• reasonable download size/type restrictions;  
• least-privilege tool design;  
• appropriate logging without unnecessary sensitive data.

### 5.13 Observability and Audit

Provide structured logging/tracing sufficient to understand a run: request, agent/tool activity, source retrieval, RAG result, extraction, validation, HITL outcome, and final status. Do not log hidden chain-of-thought.

Useful metrics may include execution time, tool failures, document retrieval failures, extraction completeness, validation failures, HITL rate, and model/token usage where available.

### 5.14 Testing and Evaluation

Include automated tests for important deterministic components, such as:

• parsing/normalization;  
• field validation;  
• tariff comparison;  
• URL/domain validation;  
• tool error handling.

Also provide a small evaluation dataset for the agent/RAG pipeline with representative questions, expected evidence/source, and expected extracted values. Explain how you would expand evaluation before production.

### 5.15 Python Engineering

• clear project/module structure;  
• type hints;  
• configuration management;  
• error handling and logging;  
• tests;  
• requirements.txt or pyproject.toml;  
• README and Git history.

## 6. Expected Result

The exact UI is your choice. The final result should be clear to a business user and should show the official source, extracted values, evidence, and detected changes.

Candidate Assignment • Confidential for recruitment use

PRACTICAL ASSIGNMENT | AGENTIC AI ENGINEER

```text
Սպառողական վարկ

Աղբյուր: Official Consumer Loan Information Summary
Վերցված է: 2026-09-XX

Արժույթ: AMD
Ժամկետ: մինչև 60 ամիս
Գումար: 300,000–10,000,000 AMD
Անվանական տոկոսադրույք: 13.5%
Փաստացի տոկոսադրույք: 14.2–15.1%
...

Detected change:
Nominal interest rate: 12.5% → 13.5%

Evidence:
Official Information Summary → Page 3 → Interest Rate section
```

## 7. Deliverables

1. Source-code repository.
2. README with setup and execution instructions.
3. Architecture diagram.
4. Short explanation of the agent/tool architecture and major design decisions.
5. Sample configuration without secrets.
6. Automated tests.
7. Small evaluation dataset and evaluation results.
8. At least two supported products from the selected bank.
9. Demonstration of normal tariff extraction.
10. Demonstration of tariff-change detection.
11. Demonstration of OCR/document-processing fallback.
12. Demonstration of at least one HITL scenario.
13. Demonstration of at least two controlled failure scenarios.
14. Short description of known limitations and what would be required before production use.
15. Full demonstration of the working solution.

Cloud deployment is not mandatory unless the required Google Cloud environment is provided. A locally runnable ADK implementation is acceptable.

## 8. Scope Guidance

The goal is a focused, working prototype—not a complete production platform. Multi-agent architecture, sophisticated UI, and cloud deployment are optional. Prefer a smaller system with clear architecture, reliable behavior, evidence, tests.

Candidate Assignment • Confidential for recruitment use

PRACTICAL ASSIGNMENT | AGENTIC AI ENGINEER

Mandatory Candidate Presentation and AI-Assisted Development

Use of AI coding assistants is permitted.

You may use AI-assisted development tools such as coding assistants, LLMs, IDE agents, or similar tools while completing this assignment. If you use them, include a short disclosure in the README describing which tools were used and for what purposes.

Regardless of how the solution was produced, you are responsible for understanding the complete submitted solution, including its code, architecture, prompts/instructions, tools, data flow, security controls, validation logic, tests, and limitations.

• Bring your own notebook/laptop containing the submitted project and a working development environment to the technical review.  
• Run and present the solution live from your notebook/laptop.  
• Be prepared to navigate and explain any part of the submitted code and architecture.  
• Be prepared to diagnose a failure or unexpected result during the review.  
• Be prepared to make a small unannounced change to the solution during the review and run the modified solution.  
• You may be asked why a particular technology or architecture choice was made and how the solution would behave if that component were removed or changed.

Candidate Assignment • Confidential for recruitment use
