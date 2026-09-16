# Consumer Loans

```
consumer_loan:
  canonical_product:
    id: "ameriabank.consumer_loan.unsecured"
    name_en: "Consumer loan not secured by property"
    name_hy: "Գույքով չապահովված սպառողական վարկ"
    category: "consumer_loan"

  landing_page:
    url: "https://ameriabank.am/en/personal/loans"
    notes: >
      Ameriabank loans overview. Useful for source discovery and identifying
      the Consumer loan product among related products such as overdraft,
      credit line, secured consumer loans, and online loans.

  armenian_page:
    url: "https://ameriabank.am/personal/loans/consumer-loans/consumer-loans"
    title: "Սպառողական վարկ"
    notes: >
      Armenian product page. Contains the product description and
      "Պայմաններ և սակագներ" section, but detailed tariff data is not
      reliably exposed in the static HTML. Treat primarily as a discovery/
      product-identification source. 


  english_page:
    url: "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans"
    title: "Consumer loan"
    notes: >
      English product page. Useful for product identification, but detailed
      tariffs should be taken from the official PDFs rather than the page.
      
  known_pdf_documents:

    - role: "PRIMARY_AUTHORITATIVE"
      title: "Retail Lending Terms and Conditions (Consumer Loan)"
      document_code: "11RBD PL 72-03-95"
      edition: 65
      effective_date: "2024-10-24"
      language: "en"
      pages: 2
      url: "https://ameriabank.am/Portals/0/files/Personal/Loans/Consumer_unsecured_eng.pdf"
      notes: >
        Best source for deterministic tariff extraction. Compact structured
        table. Use this as the main authority for snapshot extraction.

    - role: "PRIMARY_ARMENIAN"
      title: "Գույքով չապահովված սպառողական վարկ"
      language: "hy"
      pages: 2
      url: "https://ameriabank.am/Portals/0/files/Personal/Loans/Consumer_unsecured_arm.pdf"
      notes: >
        Armenian counterpart of the compact lending terms. Good source for
        Armenian parsing and OCR fallback demonstration.

    - role: "SUPPORTING_RAG"
      title: "Information Guide - Consumer loan not secured by property"
      effective_date: "2024-10-24"
      language: "en"
      pages: 9
      url: "https://ameriabank.am/Portals/0/files/Personal/Loans/Consumer_loan_unsecured_eng.pdf"
      notes: >
        Longer explanatory document. Excellent for RAG/chunking and supporting
        evidence. It explicitly warns that terms in the Guide may be outdated,
        so do not rank it above the revision-controlled Retail Lending Terms.

    - role: "INFORMATION_SUMMARY_ARMENIAN"
      title: "Տեղեկատվական ամփոփագիր - Գույքով չապահովված սպառողական վարկ"
      language: "hy"
      pages: 11
      url: "https://ameriabank.am/Portals/0/files/Personal/Loans/Consumer_loan_unsecured.pdf"
      notes: >
        Exact 'տեղեկատվական ամփոփագիր' document type mentioned by the
        assignment. Good for RAG, Armenian extraction, provenance and OCR demo.    
        

  important_sections_tables:
    primary_pdf:
      - "Purpose"
      - "Client's personal details"
      - "Loan terms"
      - "Currency"
      - "Minimum and maximum loan limits"
      - "Term (months)"
      - "Annual interest rate"
      - "Annual percentage rate (APR)"
      - "Loan disbursement fee"
      - "Security"
      - "Guarantee"
      - "Forms of loan repayment"
      - "Other terms related to the interest rate"
      - "Required documents"
      - "Late payment fines and penalties"

    supporting_information_guide:
      - "Currency"
      - "Minimum and maximum loan limits outside scoring system"
      - "Minimum and maximum loan limits based on scoring system"
      - "Loan term"
      - "Repayment method"
      - "Annual interest rate"
      - "Annual percentage rate (APR)"
      - "Loan disbursement fee"
      - "Guarantee"
      - "Special scoring / specific-industry terms"
      - "Loan service fees"
      - "Required documents"
      - "APR explanation"

    extraction_notes:
      - >
        Preserve scoring and non-scoring tariff variants separately.
        Do not flatten them into one amount/rate.
      - >
        Standard nominal rate is 20%, but scoring/specific-industry cases
        can have 15%-21%.
      - >
        Standard APR is 22.2%-23.09%; scoring/specific-industry cases
        can have 16.06%-23.13%.
      - >
        Outside scoring: AMD 300,000 - AMD 10,000,000.
      - >
        Scoring: AMD 100,000 - AMD 20,000,000.
      - "Term: 60 months."
      - >
        Application fee was not identified as a separate tariff field.
        Return NOT_FOUND rather than assuming zero.  

```



# Mortgage
```
mortgage:
  canonical_product:
    id: "ameriabank.mortgage.home_purchase.secondary_market"
    name_en: "Home Purchase Loan (Secondary Market)"
    name_hy: "Հիփոթեքային վարկ երկրորդային շուկայից"
    category: "mortgage"

  landing_page:
    url: "https://ameriabank.am/en/personal/loans/mortgage-loans"
    notes: >
      Ameriabank mortgage overview/listing page. Useful for discovery because
      Ameriabank has many mortgage variants. The agent must resolve the
      secondary-market product rather than treating every mortgage as one product.

  armenian_page:
    url: "https://ameriabank.am/personal/loans/mortgage/secondary-market"
    title: "Հիփոթեքային վարկ երկրորդային շուկայից"
    notes: >
      Main Armenian secondary-market mortgage page. Explicitly states that
      property insurance is provided by the Bank and that there are no loan
      service fees.

  english_page:
    url: "https://ameriabank.am/en/personal/loans/mortgage/secondary-market"
    title: "Real estate loan for secondary market"
    notes: >
      Primary English product page. Good product/discovery source.
      Explicitly states "No loan service fees".
      
  known_pdf_documents:

    - role: "PRIMARY_AUTHORITATIVE"
      title: "Retail Lending Terms and Conditions - Home Mortgage Loan"
      document_code: "11RBD PL 72-03-98"
      language: "en"
      pages: 6
      url: "https://ameriabank.am/Portals/0/files/Personal/Loans/mortage_personal_purchase_Secondary_eng.pdf"
      notes: >
        Main structured source for tariff extraction for the general
        secondary-market home purchase loan. Use together with the product
        page for fields such as service-fee wording.

    - role: "PRIMARY_ARMENIAN"
      title: "Երկրորդային շուկայից բնակելի նշանակության անշարժ գույքի ձեռքբերման վարկ"
      document_code: "11RBD PL 72-03-98"
      language: "hy"
      pages: 6
      url: "https://ameriabank.am/Portals/0/files/Personal/Loans/mortage_personal_purchase_Secondary_arm.pdf"
      notes: >
        Armenian counterpart. Useful for Armenian parsing, evidence checking,
        and OCR fallback.

    - role: "SIMILAR_PRODUCT_HITL_CANDIDATE"
      title: "Online Home Purchase Loan (secondary market)"
      document_code: "11RBD PL 72-03-98"
      language: "en"
      url: "https://ameriabank.am/Portals/0/files/Personal/Loans/mortgage_personal_online_secondary_purchase_eng.pdf"
      notes: >
        Similar but materially distinct ONLINE secondary-market mortgage.
        Do not silently treat it as the same product. This is a very good
        deliberate HITL/source-disambiguation candidate.
        
        
        
  important_sections_tables:
    primary_pdf:
      - "Purpose"
      - "Client's personal details"
      - "Loan terms"
      - "Currency"
      - "Minimum and maximum loan limits"
      - "Loan term"
      - "Annual interest rate"
      - "Fixed / adjustable interest-rate conditions"
      - "Annual percentage rate (APR)"
      - "Loan disbursement fee"
      - "Collateral / security"
      - "Loan-to-value / LTV conditions"
      - "Property insurance"
      - "Repayment"
      - "Required documents"
      - "Additional conditions"

    product_page:
      - "Advantages"
      - "Property insurance by the Bank"
      - "No loan service fees"
      - "Terms and conditions"

    extraction_notes:
      - >
        Preserve tariff variants by currency. Do not flatten AMD/USD/EUR
        interest rates or limits.
      - >
        Preserve fixed vs adjustable-rate cases separately.
      - >
        Preserve term-dependent conditions separately.
      - >
        Preserve residency/LTV/collateral qualifiers with extracted values.
      - >
        Service fee evidence comes directly from the product page:
        "No loan service fees."
      - >
        A separate application-study fee was not clearly identified;
        return NOT_FOUND unless discovered in a newer authoritative document.
      - >
        Never substitute the "online secondary-market mortgage" document
        when the canonical product requested is the general secondary-market
        mortgage.        
```


```
source_authority:
  priority:
    - "revision-controlled Retail Lending Terms and Conditions"
    - "current official product page"
    - "official Information Guide / տեղեկատվական ամփոփագիր"
    - "official supporting/special-offer documents"

  rules:
    - "Only accept https://ameriabank.am/* as an authoritative bank source."
    - "Do not infer values that are absent."
    - "Represent absent fields as NOT_FOUND."
    - "Record document_code, edition, effective_date, URL and SHA-256."
    - "Keep tariff qualifiers/conditions attached to every extracted value."
    - "Do not treat two PDFs with the same document code as the same product automatically."
    - "Product subtype and document title/purpose must also match."
    - "If two authoritative sources conflict, trigger HITL."
    - "If a Guide warns that information may be outdated, prefer the current revision-controlled terms."
```