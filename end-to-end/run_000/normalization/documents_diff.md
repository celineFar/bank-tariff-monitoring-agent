# Document normalization diffs

This report uses a unified diff: unchanged context starts with a space, removed source content starts with `-`, and normalized content added in its place starts with `+`. No diff means normalization preserved the rendered text.

## 001_6.1.1.2._if_the_address_of_the_pledged_real_estate_is_included_in_the_list_of_properties_published_o

```diff
--- acquired-or-reconstructed
+++ normalized
@@ -2,17 +2,15 @@
 
 Source: <https://ameriabank.am/Portals/0/files/Other/insured-properties.pdf>
 
-## PDF page 1
-
 | Հասցե |
 | --- |
-| ք. Երևան, Նոր Նորք Ար. Միկոյան փող. 2/1 շենք |
-| ք. Երևան, Արաբկիր Մալխասյանց փողոց 6/1 շենք |
-| ք. Երևան, Նոր-Նորք Հ. Գյուլիքևխյան փողոց 14/2 շենք |
-| ք. Երևան, Ավան Աճառյան փողոց 39/25 շենք |
-| ք. Երևան, Արաբկիր Օրբելի եղբայրների փողոց 67/2 շենք |
-| ք. Երևան, Աջափնյակ Հ. Շիրազի փողոց 2/9 շենք |
-| ք. Երևան, Քանաքեռ-Զեյթուն Պ. Սևակի փողոց 51/2 շենք |
-| ք. Երևան, Արաբկիր Մամիկոնյանց փողոց 45/1 շենք |
-| ք.Երևան, Աջափնյակ Նորաշեն թաղամաս 47/5 շենք |
-| Ք.Երևան, Շենգավիթ, Մ. Ֆրունզեի փողոց 10/4 շենք |
+| ք. Երեւան, Նոր Նորք Ար. Միկոյան փող. 2/1 շենք |
+| ք. Երեւան, Արաբկիր Մալխասյանց փողոց 6/1 շենք |
+| ք. Երեւան, Նոր-Նորք Հ. Գյուլիքեւխյան փողոց 14/2 շենք |
+| ք. Երեւան, Ավան Աճառյան փողոց 39/25 շենք |
+| ք. Երեւան, Արաբկիր Օրբելի եղբայրների փողոց 67/2 շենք |
+| ք. Երեւան, Աջափնյակ Հ. Շիրազի փողոց 2/9 շենք |
+| ք. Երեւան, Քանաքեռ-Զեյթուն Պ. Սեւակի փողոց 51/2 շենք |
+| ք. Երեւան, Արաբկիր Մամիկոնյանց փողոց 45/1 շենք |
+| ք.Երեւան, Աջափնյակ Նորաշեն թաղամաս 47/5 շենք |
+| Ք.Երեւան, Շենգավիթ, Մ. Ֆրունզեի փողոց 10/4 շենք |
```

## 002_Terms_of_the_loan_for_purchase_of_residential_real_estate_from_primary_market

```diff
--- acquired-or-reconstructed
+++ normalized
@@ -2,9 +2,7 @@
 
 Source: <https://ameriabank.am/Portals/0/files/Personal/Loans/mortgage_personal_purchase_eng.pdf>
 
-## PDF page 1
-
-#### AMERIABANK CJSC
+### AMERIABANK CJSC
 11RBD PL 72-03-98
 Retail Lending Terms and Conditions (Home Mortgage Loan)¹
 Edition 73
@@ -13,108 +11,92 @@
 Current edition approved by Management Board resolutions # 01/15/26 as of May 27, 2026, and # 01/95/26 as of June 25, 2026.
 Home Purchase Loan (primary market)
 
+¹These terms have been previously known as Retail Lending Terms and Conditions under code 11RBD PL 72-03-01. Some of the Bank documents may contain references to these terms and conditions under the former name and code.
+
+²Depending on the creditworthiness of the borrower, term of loan and LTV ratio, a higher or lower interest rate can be applied.
+
+³The annual percentage rate (APR) may differ from the above specified values if there is any or a few of the following factors:
+\- When the property insurance is obtained by the Bank at the customer’s request
+\- When the borrower selects differentiated or mixed form of loan repayment
+\- If there are deviations from the creditworthiness criteria approved under the internal regulations of the Bank
+\- If additional property is pledged as collateral
+\- If there are other deviations
+
+⁴ Attention! The adjustable nominal interest rate may be revised no more than twice a year. Furthermore, depending on the change of the adjustable nominal interest rate, the threshold above or below which the nominal rate cannot change is ±5%.
+
+⁵ The list of developers is determined by the Bank. If the developer is not included in the Bank's list, the terms of the loans for purchase of residential real estate from secondary market will apply.
+
 ### Home Purchase Loan (primary market)
-
 | Section | Clause | AMD | USD | EUR |
 | --- | --- | --- | --- | --- |
-| 1. Purpose | 1.1. Purpose | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or (ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or (ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or (ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) |
-| 2. Customer’s personal details | 2.1. Eligible age of the customer/co-borrower/guarantor | 2.1.1. 18-70 years old, provided that the borrower's age at the time of expiry of loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70.<br>If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. | 2.1.1. 18-70 years old, provided that the borrower's age at the time of expiry of loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70.<br>If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. | 2.1.1. 18-70 years old, provided that the borrower's age at the time of expiry of loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70.<br>If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. |
-| 2. Customer’s personal details | 2.2. Residency | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia<br>For loans in foreign currency: individuals not considered residents of Armenia | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia<br>For loans in foreign currency: individuals not considered residents of Armenia | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia<br>For loans in foreign currency: individuals not considered residents of Armenia |
-| 3. Loan terms | 3.1. Currency | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR |
-| 3. Loan terms | 3.2. Minimum and maximum loan limits | 3.2.1.<br>AMD 3,000,000 - AMD 150,000,000<br>For online refinancing: AMD 3,000,000-100,000,000 | 3.2.2.<br>USD 5,000 - USD 300,000<br>Not applicable in case of online refinancing | 3.2.3.<br>EUR 5,000 - EUR 300,000<br>Not applicable in case of online refinancing |
-| 3. Loan terms | Term and interest rate | Term and interest rate | Term and interest rate | Term and interest rate |
-| 3. Loan terms | 3.3. Term (months) | 3.3.1. 60 | 3.3.1. 60 | 3.3.1. 60 |
-| 3. Loan terms | 3.4. Nominal annual interest rate² | 3.4.1. Fixed | 3.4.2. Fixed | 3.4.3. Fixed |
-| 3. Loan terms | 3.4. Nominal annual interest rate² | 13.5% | 11.0% | 8.5% |
-| 3. Loan terms | 3.5. Annual percentage rate (APR)³ | 3.5.1. Fixed | 3.5.2. Fixed | 3.5.3. Fixed |
-| 3. Loan terms | 3.5. Annual percentage rate (APR)³ | 14.39-15.76% | 11.6-13.56% | 8.86-10.71% |
-| 3. Loan terms | 3.6. Term (months) | 3.6.1. 61-360 | 3.6.1. 61-360 | 3.6.1. 61-360 |
-| 3. Loan terms | 3.7. Nominal annual interest rate² | 3.7.1. Adjustable fixed⁴ (rate can be changed starting from the 37th month) | 3.7.2. Adjustable fixed⁴ (rate can be changed starting from the 37th month) | 3.7.3. Adjustable fixed⁴ (rate can be changed starting from the 37th month) |
-
-## PDF page 2
+| \1. Purpose | 1.1. Purpose | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or (ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or (ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or (ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) |
+| \2. Customer’s personal details | 2.1. Eligible age of the customer/co-borrower/guarantor | 2.1.1. 18-70 years old, provided that the borrower's age at the time of expiry of loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70.<br>If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. | 2.1.1. 18-70 years old, provided that the borrower's age at the time of expiry of loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70.<br>If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. | 2.1.1. 18-70 years old, provided that the borrower's age at the time of expiry of loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70.<br>If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. |
+| \2. Customer’s personal details | 2.2. Residency | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia<br>For loans in foreign currency: individuals not considered residents of Armenia | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia<br>For loans in foreign currency: individuals not considered residents of Armenia | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia<br>For loans in foreign currency: individuals not considered residents of Armenia |
+| \3. Loan terms | 3.1. Currency | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR |
+| \3. Loan terms | 3.2. Minimum and maximum loan limits | 3.2.1.<br>AMD 3,000,000 - AMD 150,000,000<br>For online refinancing: AMD 3,000,000-100,000,000 | 3.2.2.<br>USD 5,000 - USD 300,000<br>Not applicable in case of online refinancing | 3.2.3.<br>EUR 5,000 - EUR 300,000<br>Not applicable in case of online refinancing |
+| \3. Loan terms | Term and interest rate | Term and interest rate | Term and interest rate | Term and interest rate |
+| \3. Loan terms | 3.3. Term (months) | 3.3.1. 60 | 3.3.1. 60 | 3.3.1. 60 |
+| \3. Loan terms | 3.4. Nominal annual interest rate² | 3.4.1. Fixed | 3.4.2. Fixed | 3.4.3. Fixed |
+| \3. Loan terms | 3.4. Nominal annual interest rate² | 13.5% | 11.0% | 8.5% |
+| \3. Loan terms | 3.5. Annual percentage rate (APR)³ | 3.5.1. Fixed | 3.5.2. Fixed | 3.5.3. Fixed |
+| \3. Loan terms | 3.5. Annual percentage rate (APR)³ | 14.39-15.76% | 11.6-13.56% | 8.86-10.71% |
+| \3. Loan terms | 3.6. Term (months) | 3.6.1. 61-360 | 3.6.1. 61-360 | 3.6.1. 61-360 |
+| \3. Loan terms | 3.7. Nominal annual interest rate² | 3.7.1. Adjustable fixed⁴ (rate can be changed starting from the 37th month) | 3.7.2. Adjustable fixed⁴ (rate can be changed starting from the 37th month) | 3.7.3. Adjustable fixed⁴ (rate can be changed starting from the 37th month) |
 
 ### Home Purchase Loan (primary market) (Continued)
-
 | Section | Clause | AMD | USD | EUR |
 | --- | --- | --- | --- | --- |
-| 3. Loan terms | 3.7. Nominal annual interest rate² | Fixed component 5.5% + variable component (base rate) | Fixed component 8% + variable component (base rate) | Fixed component 7% + variable component (base rate) |
-| 3. Loan terms | Term and interest rate in case of online refinancing | Term and interest rate in case of online refinancing | Term and interest rate in case of online refinancing | Term and interest rate in case of online refinancing |
-| 3. Loan terms | 3.8. Term (months) | 3.8.1. 61-360 | 3.8.1. 61-360 | 3.8.1. 61-360 |
-| 3. Loan terms | 3.9. Nominal annual interest rate | 3.9.1. Adjustable fixed (rate can be changed starting from the 37th month) | N/a | N/a |
-| 3. Loan terms | 3.9. Nominal annual interest rate | Fixed component 5.25% + variable component (base rate) | N/a | N/a |
-| 3. Loan terms | 3.10. Annual percentage rate (APR)³ | 3.10.1. Adjustable fixed (rate can be changed starting from the 37th month) | 3.10.2. Adjustable fixed (rate can be changed starting from the 37th month) | 3.10.3. Adjustable fixed (rate can be changed starting from the 37th month) |
-| 3. Loan terms | 3.10. Annual percentage rate (APR)³ | 14.35-15.74% | 10.47-12.39% | 8.3-10.12% |
-| 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%. | 3.11.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%. | 3.11.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%. |
-| 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%. | 3.11.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%. | 3.11.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%. |
-| 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%. | 3.11.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%. | 3.11.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%. |
-| 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.4. If the customer prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds). | 3.11.4. If the customer prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds). | 3.11.4. If the customer prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds). |
-| 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.5. In case of other deviations, the applicable interest rate may be increased by 0.25%. | 3.11.5. In case of other deviations, the applicable interest rate may be increased by 0.25%. | 3.11.5. In case of other deviations, the applicable interest rate may be increased by 0.25%. |
-| 3. Loan terms | 3.12. Lump sum disbursement fee | 3.12.1. N/A, except for non-resident individuals, for whom the lump sum loan disbursement fee is 1% of the loan amount or AMD 1 million, whichever is less | 3.12.1. N/A, except for non-resident individuals, for whom the lump sum loan disbursement fee is 1% of the loan amount or AMD 1 million, whichever is less | 3.12.1. N/A, except for non-resident individuals, for whom the lump sum loan disbursement fee is 1% of the loan amount or AMD 1 million, whichever is less |
-| 3. Loan terms | 3.13. Minimum down payment | 3.13.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.<br>3.13.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5 % of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral. | 3.13.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.<br>3.13.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5 % of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral. | 3.13.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.<br>3.13.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5 % of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral. |
-| 3. Loan terms | 3.14. Manner of disbursement | 1. Lump sum<br>2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower. | 1. Lump sum<br>2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower. | 1. Lump sum<br>2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower. |
-
-## PDF page 3
+| \3. Loan terms | 3.7. Nominal annual interest rate² | Fixed component 5.5% + variable component (base rate) | Fixed component 8% + variable component (base rate) | Fixed component 7% + variable component (base rate) |
+| \3. Loan terms | Term and interest rate in case of online refinancing | Term and interest rate in case of online refinancing | Term and interest rate in case of online refinancing | Term and interest rate in case of online refinancing |
+| \3. Loan terms | 3.8. Term (months) | 3.8.1. 61-360 | 3.8.1. 61-360 | 3.8.1. 61-360 |
+| \3. Loan terms | 3.9. Nominal annual interest rate | 3.9.1. Adjustable fixed (rate can be changed starting from the 37th month) | N/a | N/a |
+| \3. Loan terms | 3.9. Nominal annual interest rate | Fixed component 5.25% + variable component (base rate) | N/a | N/a |
+| \3. Loan terms | 3.10. Annual percentage rate (APR)³ | 3.10.1. Adjustable fixed (rate can be changed starting from the 37th month) | 3.10.2. Adjustable fixed (rate can be changed starting from the 37th month) | 3.10.3. Adjustable fixed (rate can be changed starting from the 37th month) |
+| \3. Loan terms | 3.10. Annual percentage rate (APR)³ | 14.35-15.74% | 10.47-12.39% | 8.3-10.12% |
+| \3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%. | 3.11.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%. | 3.11.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%. |
+| \3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%. | 3.11.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%. | 3.11.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%. |
+| \3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%. | 3.11.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%. | 3.11.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%. |
+| \3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.4. If the customer prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds). | 3.11.4. If the customer prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds). | 3.11.4. If the customer prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds). |
+| \3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.5. In case of other deviations, the applicable interest rate may be increased by 0.25%. | 3.11.5. In case of other deviations, the applicable interest rate may be increased by 0.25%. | 3.11.5. In case of other deviations, the applicable interest rate may be increased by 0.25%. |
+| \3. Loan terms | 3.12. Lump sum disbursement fee | 3.12.1. N/A, except for non-resident individuals, for whom the lump sum loan disbursement fee is 1% of the loan amount or AMD 1 million, whichever is less | 3.12.1. N/A, except for non-resident individuals, for whom the lump sum loan disbursement fee is 1% of the loan amount or AMD 1 million, whichever is less | 3.12.1. N/A, except for non-resident individuals, for whom the lump sum loan disbursement fee is 1% of the loan amount or AMD 1 million, whichever is less |
+| \3. Loan terms | 3.13. Minimum down payment | 3.13.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.<br>3.13.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5 % of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral. | 3.13.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.<br>3.13.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5 % of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral. | 3.13.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.<br>3.13.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5 % of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral. |
+| \3. Loan terms | 3.14. Manner of disbursement | \1. Lump sum<br>\2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower. | \1. Lump sum<br>\2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower. | \1. Lump sum<br>\2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower. |
 
 ### Home Purchase Loan (primary market) (Continued)
-
 | Section | Clause | Details |
 | --- | --- | --- |
-| 3. Loan terms | 3.15. Cashing of the loan amount by the seller from their account with the Bank after loan disbursement (where applicable) | 3.15.1.<br>AMD: Free<br>Other currency: 0.5 % |
-| 4. Forms of loan repayment | 4.1. Repayment method | 4.1.1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest) |
-| 4. Forms of loan repayment | 4.1. Repayment method | 4.1.2. Differentiated (monthly repayment of equal portions of principal amount while interest accrues to outstanding loan and decreases each month) /not applicable in case of online refinancing/ |
-| 4. Forms of loan repayment | 4.1. Repayment method | 4.1.3. Mixed (the customer may choose an individual repayment schedule based on seasonality of cash flows, provided that at least 5% of contractual loan amount is repaid each year; interest payable on monthly basis) /not applicable in case of online refinancing/ |
-| 5. Security | 5.1. Eligible collateral | 5.1.1.<br>1. The loan is secured by the real estate being purchased. The Bank may consider pledge of other real estate as additional security to the reasonable satisfaction of the Bank, as well as cash in the Bank or bonds issued by the Bank.<br>2. If the borrower wishes to purchase property under construction without registered certificate of title, the loan will be secured by other Armenia-based real estate to the reasonable satisfaction of the Bank.<br>3. If the borrower wishes to purchase property abroad, the loan will be secured by Armenia-based real estate to the reasonable satisfaction of the Bank.<br>4. In the case of online refinancing, the collateral is real estate purchased directly from the developer, which has a completion certificate and is not encumbered with any liabilities other than the refinanced loan. |
-| 5. Security | 5.2. Loan-to-value (LTV) ratio | 5.2.1. The loan is issued:<br>1. For AMD loans with a term of 61-240 months: up to 90%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client,<br>For AMD loans with a term above 240 months: up to 80%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁶ reference provided to the client, unless otherwise determined by the Bank,<br>2. For foreign currency loans with a term of 61-240 months: up to 70%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client,<br>For foreign currency loans with a term above 240 months: up to 60%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client, unless otherwise determined by the Bank,<br>3. up to 100% of the value of cash in the Bank or bonds issued by the Bank.<br>4. For up to AMD 30 million loans without creditworthiness assessment: up to 70% (if in Yerevan) and up to 60% (if in the regions of Armenia) of the price specified in the developer reference⁵ or the lower of the two: appraised market value or purchase price of pledged property (this clause does not refer to the loans issued with a purpose of transfer of existing loans from another bank/credit organization).<br>For AMD 30-50 million loans without creditworthiness assessment: up to 60% (if in Yerevan) and up to 50% (if in the regions of Armenia) of the price specified in the developer reference⁵ or the lower of the two: appraised market value or purchase price of pledged property (this clause does not refer to the loans issued with a purpose of transfer of existing loans from another bank/credit organization).<br>For AMD 50-100 million loans without creditworthiness assessment: up to 50% (if in Yerevan) and up to 40% (if in the regions of Armenia) of the price specified in the developer reference⁵ or the lower of the two: appraised market value or purchase price of pledged property (this clause does not refer to the loans issued with a purpose of transfer of existing loans from another bank/credit organization). |
-| 5. Security | 5.3. Location of the real estate to be pledged | 5.3.1. Armenia<br>5.3.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children, also regional cities of Armenia not specified in clause 5.3.1 and particular rural settlements approved by the Republic of Armenia Government decree N 968-Լ as of May 14, 2020. |
-
-## PDF page 4
+| \3. Loan terms | 3.15. Cashing of the loan amount by the seller from their account with the Bank after loan disbursement (where applicable) | 3.15.1.<br>AMD: Free<br>Other currency: 0.5 % |
+| \4. Forms of loan repayment | 4.1. Repayment method | 4.1.1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest) |
+| \4. Forms of loan repayment | 4.1. Repayment method | 4.1.2. Differentiated (monthly repayment of equal portions of principal amount while interest accrues to outstanding loan and decreases each month) /not applicable in case of online refinancing/ |
+| \4. Forms of loan repayment | 4.1. Repayment method | 4.1.3. Mixed (the customer may choose an individual repayment schedule based on seasonality of cash flows, provided that at least 5% of contractual loan amount is repaid each year; interest payable on monthly basis) /not applicable in case of online refinancing/ |
+| \5. Security | 5.1. Eligible collateral | 5.1.1.<br>\1. The loan is secured by the real estate being purchased. The Bank may consider pledge of other real estate as additional security to the reasonable satisfaction of the Bank, as well as cash in the Bank or bonds issued by the Bank.<br>\2. If the borrower wishes to purchase property under construction without registered certificate of title, the loan will be secured by other Armenia-based real estate to the reasonable satisfaction of the Bank.<br>\3. If the borrower wishes to purchase property abroad, the loan will be secured by Armenia-based real estate to the reasonable satisfaction of the Bank.<br>\4. In the case of online refinancing, the collateral is real estate purchased directly from the developer, which has a completion certificate and is not encumbered with any liabilities other than the refinanced loan. |
+| \5. Security | 5.2. Loan-to-value (LTV) ratio | 5.2.1. The loan is issued:<br>\1. For AMD loans with a term of 61-240 months: up to 90%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client,<br>For AMD loans with a term above 240 months: up to 80%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁶ reference provided to the client, unless otherwise determined by the Bank,<br>\2. For foreign currency loans with a term of 61-240 months: up to 70%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client,<br>For foreign currency loans with a term above 240 months: up to 60%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client, unless otherwise determined by the Bank,<br>\3. up to 100% of the value of cash in the Bank or bonds issued by the Bank.<br>\4. For up to AMD 30 million loans without creditworthiness assessment: up to 70% (if in Yerevan) and up to 60% (if in the regions of Armenia) of the price specified in the developer reference⁵ or the lower of the two: appraised market value or purchase price of pledged property (this clause does not refer to the loans issued with a purpose of transfer of existing loans from another bank/credit organization).<br>For AMD 30-50 million loans without creditworthiness assessment: up to 60% (if in Yerevan) and up to 50% (if in the regions of Armenia) of the price specified in the developer reference⁵ or the lower of the two: appraised market value or purchase price of pledged property (this clause does not refer to the loans issued with a purpose of transfer of existing loans from another bank/credit organization).<br>For AMD 50-100 million loans without creditworthiness assessment: up to 50% (if in Yerevan) and up to 40% (if in the regions of Armenia) of the price specified in the developer reference⁵ or the lower of the two: appraised market value or purchase price of pledged property (this clause does not refer to the loans issued with a purpose of transfer of existing loans from another bank/credit organization). |
+| \5. Security | 5.3. Location of the real estate to be pledged | 5.3.1. Armenia<br>5.3.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children, also regional cities of Armenia not specified in clause 5.3.1 and particular rural settlements approved by the Republic of Armenia Government decree N 968-Լ as of May 14, 2020. |
 
 ### Home Purchase Loan (primary market) (Continued)
-
 | Section | Clause | Details |
 | --- | --- | --- |
-| 5. Security | 5.4. Appraisal of the collateral | 5.4.1.<br>1. No appraisal is required in case of acquisition of the right to purchase property from the developer. Pledge value is considered to be equal to the price specified in the developer’s reference, unless otherwise determined by the Bank.<br>2. In case of acquisition of the title to the real estate from the developer, appraisal is performed by appraisal companies cooperating with the Bank. |
-| 5. Security | 5.5. Additional security | 5.5.1. The Bank may request guarantees of individuals and/or companies as additional security. |
-| 6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.1. The real estate being pledged is insured by the Bank in the following cases: |
-| 6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.1.1. If at the time of registration of the title to the real estate and/or at the time of reappraisal, the market value of the property is over AMD 100 million (one hundred million); or |
-| 6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.1.2. if the address of the pledged real estate is included in the list of properties published on the Bank’s website. |
-| 6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.2. The Bank obtains insurance each year for the amount of the outstanding principal throughout the loan term if any of the above specified conditions is in place (in this case, the calculation of the interest rate also covers all the possible costs, including those associated with the insurance, where applicable). |
-| 7. Required documents | 7.1. Required documents | 7.1.1. Required documents filed together with the loan application<br>• Loan application (not applicable in case of online refinancing)<br>• ID (original)<br>• Certificate of ownership/purchase right of real estate to be purchased/pledged (copy)<br>• Other documents upon the Bank’s request |
-| 7. Required documents | 7.1. Required documents | 7.1.2. Documents required after pre-approval<br>• Proof of employment and/or other income (not applicable in case of online refinancing) |
-
-## PDF page 5
+| \5. Security | 5.4. Appraisal of the collateral | 5.4.1.<br>\1. No appraisal is required in case of acquisition of the right to purchase property from the developer. Pledge value is considered to be equal to the price specified in the developer’s reference, unless otherwise determined by the Bank.<br>\2. In case of acquisition of the title to the real estate from the developer, appraisal is performed by appraisal companies cooperating with the Bank. |
+| \5. Security | 5.5. Additional security | 5.5.1. The Bank may request guarantees of individuals and/or companies as additional security. |
+| \6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.1. The real estate being pledged is insured by the Bank in the following cases: |
+| \6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.1.1. If at the time of registration of the title to the real estate and/or at the time of reappraisal, the market value of the property is over AMD 100 million (one hundred million); or |
+| \6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.1.2. if the address of the pledged real estate is included in the list of properties published on the Bank’s website. |
+| \6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.2. The Bank obtains insurance each year for the amount of the outstanding principal throughout the loan term if any of the above specified conditions is in place (in this case, the calculation of the interest rate also covers all the possible costs, including those associated with the insurance, where applicable). |
+| \7. Required documents | 7.1. Required documents | 7.1.1. Required documents filed together with the loan application<br>• Loan application (not applicable in case of online refinancing)<br>• ID (original)<br>• Certificate of ownership/purchase right of real estate to be purchased/pledged (copy)<br>• Other documents upon the Bank’s request |
+| \7. Required documents | 7.1. Required documents | 7.1.2. Documents required after pre-approval<br>• Proof of employment and/or other income (not applicable in case of online refinancing) |
 
 ### Home Purchase Loan (primary market) (Continued)
-
 | Section | Clause | Details |
 | --- | --- | --- |
-| 7. Required documents | 7.1. Required documents | • Marriage (divorce, spouse death) certificate (original) |
-| 7. Required documents | 7.1. Required documents | • Certificate of title to real estate to be pledged (original) |
-| 7. Required documents | 7.1. Required documents | • Other documents upon the Bank request |
-| 7. Required documents | 7.1. Required documents | 7.1.3. Documents required after loan approval<br>• Copies of bases of title to real estate (to be submitted upon the Bank’s request)<br>• IDs of owners of the property to be purchased/pledged (originals)<br>• Copies of marriage (divorce, spouse death) certificates of owners of the property to be pledged, to be presented if available<br>• Statement from the State Committee of Real Estate Cadaster on encumbrance of real estate (unified statement)<br>• Tax clearance certificate for the real estate<br>• Real estate insurance policy (as required)<br>• Documentary proof that the down payment was made in a non-cash manner (e.g.: original receipt, or, if paid electronically, a document showing that the electronic payment was confirmed). Such proof is not required if the payment was made from the accounts held with the Bank and the Bank specialist has exported the payment document from the system.<br>• Other documents upon the Bank’s request |
-| 8. Early repayment fee | 8.1. Early repayment fee | 8.1.1.<br>At any time during a contractual year the borrower can make an early repayment to the extent of outstanding principal amount of loan for that contractual year. A contractual year is each period of 12 months following the date of execution of credit agreement.<br>Where the amount of early repayment exceeds the specified limit, the following fees will be charged:<br>• Max 0.6% of early repayment, if made during the first year of the agreement<br>• Max 0.4% of early repayment, if made during the second year of the agreement<br>• Max 0.2% of early repayment, if made during the third year of the agreement |
-| 9. Late payment fines and penalties | 9.1. Late payment fines and penalties | 9.1.1. The interest rate specified in the loan agreement will continue to be applied to overdue loans.<br>Fine in the amount of 0.13 % of overdue loan and interest for each day of delay |
-| 10. Other fees | 10.1. Other fees | 10.1.1. Fees payable by the customers for the new loans<br>• Fee for unified statement from the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia<br>• Fees for notarization of pledge (real estate), registration of the Bank’s security interest under pledge agreement, and<br>• Appraisal fee for the real estate being pledged (as necessary)<br>10.1.2 Fees payable by the Bank for the loans refinanced online<br>• Fee for unified statement from the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia<br>• Fees for notarization of pledge (real estate), registration of the Bank’s security interest under pledge agreement, and<br>• Appraisal fee for the real estate being pledged |
-
-## PDF page 6
+| \7. Required documents | 7.1. Required documents | • Marriage (divorce, spouse death) certificate (original) |
+| \7. Required documents | 7.1. Required documents | • Certificate of title to real estate to be pledged (original) |
+| \7. Required documents | 7.1. Required documents | • Other documents upon the Bank request |
+| \7. Required documents | 7.1. Required documents | 7.1.3. Documents required after loan approval<br>• Copies of bases of title to real estate (to be submitted upon the Bank’s request)<br>• IDs of owners of the property to be purchased/pledged (originals)<br>• Copies of marriage (divorce, spouse death) certificates of owners of the property to be pledged, to be presented if available<br>• Statement from the State Committee of Real Estate Cadaster on encumbrance of real estate (unified statement)<br>• Tax clearance certificate for the real estate<br>• Real estate insurance policy (as required)<br>• Documentary proof that the down payment was made in a non-cash manner (e.g.: original receipt, or, if paid electronically, a document showing that the electronic payment was confirmed). Such proof is not required if the payment was made from the accounts held with the Bank and the Bank specialist has exported the payment document from the system.<br>• Other documents upon the Bank’s request |
+| \8. Early repayment fee | 8.1. Early repayment fee | 8.1.1.<br>At any time during a contractual year the borrower can make an early repayment to the extent of outstanding principal amount of loan for that contractual year. A contractual year is each period of 12 months following the date of execution of credit agreement.<br>Where the amount of early repayment exceeds the specified limit, the following fees will be charged:<br>• Max 0.6% of early repayment, if made during the first year of the agreement<br>• Max 0.4% of early repayment, if made during the second year of the agreement<br>• Max 0.2% of early repayment, if made during the third year of the agreement |
+| \9. Late payment fines and penalties | 9.1. Late payment fines and penalties | 9.1.1. The interest rate specified in the loan agreement will continue to be applied to overdue loans.<br>Fine in the amount of 0.13 % of overdue loan and interest for each day of delay |
+| \10. Other fees | 10.1. Other fees | 10.1.1. Fees payable by the customers for the new loans<br>• Fee for unified statement from the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia<br>• Fees for notarization of pledge (real estate), registration of the Bank’s security interest under pledge agreement, and<br>• Appraisal fee for the real estate being pledged (as necessary)<br>10.1.2 Fees payable by the Bank for the loans refinanced online<br>• Fee for unified statement from the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia<br>• Fees for notarization of pledge (real estate), registration of the Bank’s security interest under pledge agreement, and<br>• Appraisal fee for the real estate being pledged |
 
 ### Home Purchase Loan (primary market) (Continued)
-
 | Section | Clause | Details |
 | --- | --- | --- |
-| 11. Creditworthiness assessment | 11.1 Without creditworthiness assessment | -Where the loan amount is AMD 50-100 million, the loan may be issued without the assessment of creditworthiness criteria if the customer (including non-resident) has made a down payment of 50% (if in Yerevan) or 60% (if in the regions of Armenia) and more and meets the requirements of the internal regulations of the Bank<br><br>Where the loan amount is AMD 30-50 million, the loan may be issued without the assessment of creditworthiness criteria if the customer (including non-resident) has made a down payment of 40% (if in Yerevan) or 50% (if in the regions of Armenia) and more and meets the requirements of the internal regulations of the Bank.<br><br>Where the loan amount is up to AMD 30 million, the loan may be issued without the assessment of creditworthiness criteria if the customer (including non-resident) has made a down payment of 30% (if in Yerevan) or 40% (if in the regions of Armenia) and more and meets the requirements of the internal regulations of the Bank. |
-
-> ¹These terms have been previously known as Retail Lending Terms and Conditions under code 11RBD PL 72-03-01. Some of the Bank documents may contain references to these terms and conditions under the former name and code.
-
-> ²Depending on the creditworthiness of the borrower, term of loan and LTV ratio, a higher or lower interest rate can be applied.
-
-> ³The annual percentage rate (APR) may differ from the above specified values if there is any or a few of the following factors:
-- When the property insurance is obtained by the Bank at the customer’s request
-- When the borrower selects differentiated or mixed form of loan repayment
-- If there are deviations from the creditworthiness criteria approved under the internal regulations of the Bank
-- If additional property is pledged as collateral
-- If there are other deviations
-
-> ⁴ Attention! The adjustable nominal interest rate may be revised no more than twice a year. Furthermore, depending on the change of the adjustable nominal interest rate, the threshold above or below which the nominal rate cannot change is ±5%.
-
-> ⁵ The list of developers is determined by the Bank. If the developer is not included in the Bank's list, the terms of the loans for purchase of residential real estate from secondary market will apply.
+| \11. Creditworthiness assessment | 11.1 Without creditworthiness assessment | -Where the loan amount is AMD 50-100 million, the loan may be issued without the assessment of creditworthiness criteria if the customer (including non-resident) has made a down payment of 50% (if in Yerevan) or 60% (if in the regions of Armenia) and more and meets the requirements of the internal regulations of the Bank<br>Where the loan amount is AMD 30-50 million, the loan may be issued without the assessment of creditworthiness criteria if the customer (including non-resident) has made a down payment of 40% (if in Yerevan) or 50% (if in the regions of Armenia) and more and meets the requirements of the internal regulations of the Bank.<br>Where the loan amount is up to AMD 30 million, the loan may be issued without the assessment of creditworthiness criteria if the customer (including non-resident) has made a down payment of 30% (if in Yerevan) or 40% (if in the regions of Armenia) and more and meets the requirements of the internal regulations of the Bank. |
```

## 003_Terms_of_express_Home_Mortgage_Loan_Purchase_Construction_and_Renovation

```diff
--- acquired-or-reconstructed
+++ normalized
@@ -2,17 +2,29 @@
 
 Source: <https://ameriabank.am/Portals/0/files/Personal/Loans/mortgage_personal_express_eng.pdf>
 
-## PDF page 1
-
 Approved by Management Board Resolution # 08/1/01/14 as of February 4, 2014.
 Current edition approved by Management Board resolutions # 01/15/26 as of May 27, 2026, and # 01/95/26 as of June 25, 2026.
 
-### Express Home Mortgage Loan (Purchase, Construction and Renovation) ¹
+## Express Home Mortgage Loan (Purchase, Construction and Renovation) ¹
 
-#### General requirements to loan facilities
+### General requirements to loan facilities
+
+### \1. Express Home Purchase Loan (primary market)
+
+### \2. Express Home Purchase Loan (secondary market)
+
+### \3. Express Home Construction Loan
+
+### \4. Express Home Renovation Loan
+
+¹Attention! The offer of the agreement is provided to the customer following which the customer may use the 7-day cooling-off period envisaged by the Armenian laws and regulations.
+In case of failure to notarize the pledge agreements specified in the loan agreement and securing the borrower's obligations under the loan agreement, within 30 (thirty) business days upon execution of the loan agreement and acceptance by the Borrower, the Agreement shall cease to be valid (unless the loan has already been disbursed to the borrower by that date).
+
+² Attention! The adjustable nominal interest rate may be revised no more than twice a year. Furthermore, depending on the change of the adjustable nominal interest rate, the threshold above or below which the nominal rate cannot change is ± 5%.
+
+³The list of developers is determined by the Bank.
 
 ### Header Information
-
 | Column 1 | Column 2 |
 | --- | --- |
 | AMERIABANK CJSC | 11RBD PL 72-03-98 |
@@ -20,112 +32,81 @@
 | Retail Lending Terms and Conditions<br>(Home Mortgage Loan)¹ | Effective date: August 5, 2026 |
 
 ### General requirements to loan facilities
-
 | Column 1 | Column 2 | Column 3 |
 | --- | --- | --- |
-| 1. Customer’s personal details | 1.1. Eligible age of client/co-borrower | 1.1.1. 18-70, provided that the age of the borrower by the time of expiry of loan agreement will not have exceeded 70 |
-| 1. Customer’s personal details | 1.2. Residency | 1.2.1. Citizens of Armenia who are resident in Armenia |
-| 2. Terms and Conditions | 2.1. Currency | 2.1.1. AMD |
-| 2. Terms and Conditions | 2.2. Minimum and maximum loan limit | 2.2.1. AMD 3,000,000 - AMD 100,000,000 |
-| 2. Terms and Conditions | 2.3. Cashing of the loan amount by the borrower or the seller from his account with the Bank after loan disbursement (where applicable) | 2.3.1.<br>AMD: free |
-| 2. Terms and Conditions | 2.4. Lump sum disbursement fee | 2.4.1. N/A |
-| 3. Forms of loan repayment | 3.1. Repayment method | 3.1.1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest) |
-| 5. Insurance of the collateral | 5.1. Insurance of the collateral | 5.1.1. The real estate being pledged is insured by the Bank in the following cases:<br><br>5.1.1.1. If at the time of registration of the title to the real estate and/or at the time of reappraisal, the market value of the property is over AMD 100 million (one hundred million); or<br><br>5.1.1.2. if the address of the pledged real estate is included in the list of properties published on the Bank’s website.<br><br>5.1.2. The Bank obtains insurance each year for the amount of the outstanding principal throughout the loan term if any of the above specified conditions is in place (in this case, the calculation of the interest rate also covers all the possible costs, including those associated with the insurance, where applicable). |
-
-## PDF page 2
+| \1. Customer’s personal details | 1.1. Eligible age of client/co-borrower | 1.1.1. 18-70, provided that the age of the borrower by the time of expiry of loan agreement will not have exceeded 70 |
+| \1. Customer’s personal details | 1.2. Residency | 1.2.1. Citizens of Armenia who are resident in Armenia |
+| \2. Terms and Conditions | 2.1. Currency | 2.1.1. AMD |
+| \2. Terms and Conditions | 2.2. Minimum and maximum loan limit | 2.2.1. AMD 3,000,000 - AMD 100,000,000 |
+| \2. Terms and Conditions | 2.3. Cashing of the loan amount by the borrower or the seller from his account with the Bank after loan disbursement (where applicable) | 2.3.1.<br>AMD: free |
+| \2. Terms and Conditions | 2.4. Lump sum disbursement fee | 2.4.1. N/A |
+| \3. Forms of loan repayment | 3.1. Repayment method | 3.1.1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest) |
+| \5. Insurance of the collateral | 5.1. Insurance of the collateral | 5.1.1. The real estate being pledged is insured by the Bank in the following cases:<br>5.1.1.1. If at the time of registration of the title to the real estate and/or at the time of reappraisal, the market value of the property is over AMD 100 million (one hundred million); or<br>5.1.1.2. if the address of the pledged real estate is included in the list of properties published on the Bank’s website.<br>5.1.2. The Bank obtains insurance each year for the amount of the outstanding principal throughout the loan term if any of the above specified conditions is in place (in this case, the calculation of the interest rate also covers all the possible costs, including those associated with the insurance, where applicable). |
 
 ### General requirements to loan facilities (Continued)
-
 | Column 1 | Column 2 | Column 3 |
 | --- | --- | --- |
-| 6. Early repayment fee | 6.1. Early repayment fee | 6.1.1.<br>At any time during a contractual year the borrower can make an early repayment to the extent of outstanding principal amount of loan for that contractual year. A contractual year is each period of 12 months following the date of execution of credit agreement.<br>Where the amount of early repayment exceeds the specified limit, the following fees will be charged:<br>• Max 0.6% of early repayment, if made during the first year of the agreement<br>• Max 0.4% of early repayment, if made during the second year of the agreement<br>• Max 0.2% of early repayment, if made during the third year of the agreement |
-| 7. Late payment fines and penalties | 7.1. Late payment fines and penalties | 7.1.1. The interest rate specified in the loan agreement will continue to be applied to overdue loans.<br>Fine in the amount of 0.13 % of overdue loan and interest for each day of delay |
-| 8. Other fees | 8.1. Other fees payable by the customer | 8.1.1. Fee for notarization of real estate pledged as collateral<br>Fee for registration of the right of ownership/purchase and the Bank rights arising out of the pledge agreements with the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia<br>Fee for the unified reference on real estate encumbrance issued by the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia<br>Fee for the final appraisal of the real estate (if required) |
-| 9. Required documents | 9.1. Required documents | 9.1.1. Required documents filed together with the loan application<br><br>ID, public services number<br><br>9.1.2. Documents required after pre-approval<br><br>• Certificate of title to real estate to be pledged (copy)<br><br>• Initial real estate appraisal report<br><br>• Other documents upon the Bank’s request<br><br>9.1.3. Documents required after loan approval<br><br>Marriage certificate (if any) and ID of the spouse, public services number<br><br>Certificate of title to the real estate/right to purchase<br><br>Certificate of security interest registration<br><br>Unified reference on real estate encumbrance<br><br>• Documentary proof that the down payment was made in a non-cash manner (e.g.: original receipt, or, if paid electronically, a document showing that the electronic payment was confirmed). Such proof is not required if the payment was made from the accounts held with the Bank and the Bank specialist has exported the payment document from the system.<br><br>Construction permit (for construction loans)<br><br>Pro-forma invoice (for renovation and construction loans)<br><br>Other documents upon the Bank’s request |
+| \6. Early repayment fee | 6.1. Early repayment fee | 6.1.1.<br>At any time during a contractual year the borrower can make an early repayment to the extent of outstanding principal amount of loan for that contractual year. A contractual year is each period of 12 months following the date of execution of credit agreement.<br>Where the amount of early repayment exceeds the specified limit, the following fees will be charged:<br>• Max 0.6% of early repayment, if made during the first year of the agreement<br>• Max 0.4% of early repayment, if made during the second year of the agreement<br>• Max 0.2% of early repayment, if made during the third year of the agreement |
+| \7. Late payment fines and penalties | 7.1. Late payment fines and penalties | 7.1.1. The interest rate specified in the loan agreement will continue to be applied to overdue loans.<br>Fine in the amount of 0.13 % of overdue loan and interest for each day of delay |
+| \8. Other fees | 8.1. Other fees payable by the customer | 8.1.1. Fee for notarization of real estate pledged as collateral<br>Fee for registration of the right of ownership/purchase and the Bank rights arising out of the pledge agreements with the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia<br>Fee for the unified reference on real estate encumbrance issued by the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia<br>Fee for the final appraisal of the real estate (if required) |
+| \9. Required documents | 9.1. Required documents | 9.1.1. Required documents filed together with the loan application<br>ID, public services number<br>9.1.2. Documents required after pre-approval<br>• Certificate of title to real estate to be pledged (copy)<br>• Initial real estate appraisal report<br>• Other documents upon the Bank’s request<br>9.1.3. Documents required after loan approval<br>Marriage certificate (if any) and ID of the spouse, public services number<br>Certificate of title to the real estate/right to purchase<br>Certificate of security interest registration<br>Unified reference on real estate encumbrance<br>• Documentary proof that the down payment was made in a non-cash manner (e.g.: original receipt, or, if paid electronically, a document showing that the electronic payment was confirmed). Such proof is not required if the payment was made from the accounts held with the Bank and the Bank specialist has exported the payment document from the system.<br>Construction permit (for construction loans)<br>Pro-forma invoice (for renovation and construction loans)<br>Other documents upon the Bank’s request |
 
-## PDF page 3
-
-#### 1. Express Home Purchase Loan (primary market)
-
-#### 2. Express Home Purchase Loan (secondary market)
-
-### 1. Express Home Purchase Loan (primary market)
-
+### \1. Express Home Purchase Loan (primary market)
 | Column 1 | Column 2 | Column 3 |
 | --- | --- | --- |
-| 1. Purpose | 1.1. Purpose | 1.1.1. Purchase of residential property for residential, lease or investment purposes |
-| 1. Purpose | 1.2. Term (months) | 1.2.1. 61-360 |
-| 1. Purpose | 1.3. Nominal annual interest rate | 1.3.1. Adjustable fixed² (rate can be changed starting from the 37th month)<br><br>Fixed component 5.25% + variable component (base rate) |
-| 1. Purpose | 1.4. Annual percentage rate (APR) | 1.4.1. 14.08-15.57% |
-| 1. Purpose | 1.5. Minimum down payment | 1.5.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price. |
-| 2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being purchased. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank. |
-| 2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1<br>1.1. For loans with a term of 240 months, the loan amount is up to 90% of the sale price set by the developer³.<br>For loans with a term above 240 months, the loan amount is up to 80% of the sale price set by the developer⁴, unless otherwise determined by the Bank. |
-| 2. Security | 2.3. Location of the real estate to be pledged | 2.3.1. Armenia |
-| 2. Security | 2.4. Appraisal of the collateral | 2.4.1. N/A<br>The price statement provided by the Developer⁴ is taken as the basis for the collateral value. |
+| \1. Purpose | 1.1. Purpose | 1.1.1. Purchase of residential property for residential, lease or investment purposes |
+| \1. Purpose | 1.2. Term (months) | 1.2.1. 61-360 |
+| \1. Purpose | 1.3. Nominal annual interest rate | 1.3.1. Adjustable fixed² (rate can be changed starting from the 37th month)<br>Fixed component 5.25% + variable component (base rate) |
+| \1. Purpose | 1.4. Annual percentage rate (APR) | 1.4.1. 14.08-15.57% |
+| \1. Purpose | 1.5. Minimum down payment | 1.5.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price. |
+| \2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being purchased. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank. |
+| \2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1<br>1.1. For loans with a term of 240 months, the loan amount is up to 90% of the sale price set by the developer³.<br>For loans with a term above 240 months, the loan amount is up to 80% of the sale price set by the developer⁴, unless otherwise determined by the Bank. |
+| \2. Security | 2.3. Location of the real estate to be pledged | 2.3.1. Armenia |
+| \2. Security | 2.4. Appraisal of the collateral | 2.4.1. N/A<br>The price statement provided by the Developer⁴ is taken as the basis for the collateral value. |
 
-### 2. Express Home Purchase Loan (secondary market)
-
+### \2. Express Home Purchase Loan (secondary market)
 | Column 1 | Column 2 | Column 3 |
 | --- | --- | --- |
-| 1. Purpose | 1.1. Purpose | 1.1.1. Purchase of residential property for residential, lease or investment purposes. |
-| 1. Purpose | 1.2. Term (months) | 1.2.1. 61-360 |
-| 1. Purpose | 1.3. Nominal annual interest rate | 1.3.1. Adjustable fixed² (rate can be changed starting from the 37th month)<br><br>Fixed component 5.75% + variable component (base rate) |
-| 1. Purpose | 1.4. Annual percentage rate (APR) | 1.4.1. 14.66-17.11% |
-| 1. Purpose | 1.5. Minimum down payment | 1.5.1. At least 5% of the purchase price of the property |
-| 2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being purchased. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank. |
-| 2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1.<br>The loan is issued:<br>For AMD loans with a term of 61-240 months: 80% (if in Yerevan) and 70% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property,<br>For AMD loans with a term above 240 months: 70% (if in Yerevan) and 60% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property |
+| \1. Purpose | 1.1. Purpose | 1.1.1. Purchase of residential property for residential, lease or investment purposes. |
+| \1. Purpose | 1.2. Term (months) | 1.2.1. 61-360 |
+| \1. Purpose | 1.3. Nominal annual interest rate | 1.3.1. Adjustable fixed² (rate can be changed starting from the 37th month)<br>Fixed component 5.75% + variable component (base rate) |
+| \1. Purpose | 1.4. Annual percentage rate (APR) | 1.4.1. 14.66-17.11% |
+| \1. Purpose | 1.5. Minimum down payment | 1.5.1. At least 5% of the purchase price of the property |
+| \2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being purchased. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank. |
+| \2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1.<br>The loan is issued:<br>For AMD loans with a term of 61-240 months: 80% (if in Yerevan) and 70% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property,<br>For AMD loans with a term above 240 months: 70% (if in Yerevan) and 60% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property |
 
-## PDF page 4
-
-#### 3. Express Home Construction Loan
-
-#### 4. Express Home Renovation Loan
-
-### 2. Express Home Purchase Loan (secondary market) (Continued)
-
+### \2. Express Home Purchase Loan (secondary market) (Continued)
 | Column 1 | Column 2 | Column 3 |
 | --- | --- | --- |
-| 2. Security | 2.3. Location of the real estate to be pledged | 2.3.1. Armenia |
-| 2. Security | 2.4. Appraisal of the collateral | 2.4.1. Pledged property to be appraised by an appraising partner of the Bank. |
+| \2. Security | 2.3. Location of the real estate to be pledged | 2.3.1. Armenia |
+| \2. Security | 2.4. Appraisal of the collateral | 2.4.1. Pledged property to be appraised by an appraising partner of the Bank. |
 
-### 3. Express Home Construction Loan
-
+### \3. Express Home Construction Loan
 | Column 1 | Column 2 | Column 3 |
 | --- | --- | --- |
-| 1. Purpose | 1.1. Purpose | 1.1. Construction of residential property |
-| 1. Purpose | 1.2. Term (months) | 1.2.1. 61-360 |
-| 1. Purpose | 1.3. Nominal annual interest rate | 1.3.1. Adjustable fixed² (rate can be changed starting from the 37th month)<br><br>Fixed component 5.75% + variable component (base rate) |
-| 1. Purpose | 1.4. Annual percentage rate (APR) | 1.4.1. 14.65-15.9% |
-| 2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being constructed. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank. |
-| 2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1.<br>The loan is issued:<br>For AMD loans with a term of 61-240 months: 80%² (if in Yerevan) and 70% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property,<br>For AMD loans with a term above 240 months: 70%² (if in Yerevan) and 60% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property |
-| 2. Security | 2.3. Location of the real estate to be pledged | 2.3.1. Armenia |
-| 2. Security | 2.4. Appraisal of the collateral | 2.4.1. Pledged property to be appraised by an appraising partner of the Bank. |
-| 3. Term of fulfillment of conditions of loan | 3.1. Term of fulfillment of conditions of loan | 3.1.1. Loans are disbursed in tranches. Each tranche is subject to proper use of previous tranche for the intended loan purpose by the borrower except where the amount of loan is AMD 7 million or less or the loan has been transferred from another bank, in which cases the sum is disbursed lump-sum.<br>For loans over AMD 50 million contractual amount at least 3 tranches must be defined. |
+| \1. Purpose | 1.1. Purpose | 1.1. Construction of residential property |
+| \1. Purpose | 1.2. Term (months) | 1.2.1. 61-360 |
+| \1. Purpose | 1.3. Nominal annual interest rate | 1.3.1. Adjustable fixed² (rate can be changed starting from the 37th month)<br>Fixed component 5.75% + variable component (base rate) |
+| \1. Purpose | 1.4. Annual percentage rate (APR) | 1.4.1. 14.65-15.9% |
+| \2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being constructed. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank. |
+| \2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1.<br>The loan is issued:<br>For AMD loans with a term of 61-240 months: 80%² (if in Yerevan) and 70% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property,<br>For AMD loans with a term above 240 months: 70%² (if in Yerevan) and 60% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property |
+| \2. Security | 2.3. Location of the real estate to be pledged | 2.3.1. Armenia |
+| \2. Security | 2.4. Appraisal of the collateral | 2.4.1. Pledged property to be appraised by an appraising partner of the Bank. |
+| \3. Term of fulfillment of conditions of loan | 3.1. Term of fulfillment of conditions of loan | 3.1.1. Loans are disbursed in tranches. Each tranche is subject to proper use of previous tranche for the intended loan purpose by the borrower except where the amount of loan is AMD 7 million or less or the loan has been transferred from another bank, in which cases the sum is disbursed lump-sum.<br>For loans over AMD 50 million contractual amount at least 3 tranches must be defined. |
 
-### 4. Express Home Renovation Loan
-
+### \4. Express Home Renovation Loan
 | Column 1 | Column 2 | Column 3 |
 | --- | --- | --- |
-| 1. Purpose | 1.1. Purpose | 1.1. Renovation of residential property |
-| 1. Purpose | 1.2. Term (months) | 1.2.1. 61-240 |
-| 1. Purpose | 1.3. Nominal annual interest rate | 1.3.1. Adjustable fixed² (rate can be changed starting from the 37th month)<br><br>Fixed component 5.75% + variable component (base rate) |
-| 1. Purpose | 1.4. Annual percentage rate (APR) | 1.4.1. 14.65-15.9% |
-| 2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being renovated. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank. |
+| \1. Purpose | 1.1. Purpose | 1.1. Renovation of residential property |
+| \1. Purpose | 1.2. Term (months) | 1.2.1. 61-240 |
+| \1. Purpose | 1.3. Nominal annual interest rate | 1.3.1. Adjustable fixed² (rate can be changed starting from the 37th month)<br>Fixed component 5.75% + variable component (base rate) |
+| \1. Purpose | 1.4. Annual percentage rate (APR) | 1.4.1. 14.65-15.9% |
+| \2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being renovated. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank. |
 
-## PDF page 5
-
-### 4. Express Home Renovation Loan (Continued)
-
+### \4. Express Home Renovation Loan (Continued)
 | Column 1 | Column 2 | Column 3 |
 | --- | --- | --- |
-| 2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1.<br>The loan is issued:<br>For AMD loans with a term of 61-240 months: 80%² (if in Yerevan) and 70% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property,<br>For AMD loans with a term above 240 months: 70%² (if in Yerevan) and 60% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property |
-| 2. Security | 2.3. Location of the real estate to be pledged | 2.3.1. Armenia |
-| 2. Security | 2.4. Appraisal of the collateral | 2.4.1. Pledged property to be appraised by an appraising partner of the Bank. |
-| 3. Term of fulfillment of conditions of loan | 3.1. Term of fulfillment of conditions of loan | 3.1.1. Loans are disbursed in tranches. Each tranche is subject to proper use of previous tranche for the intended loan purpose by the borrower except where the amount of loan is AMD 7 million or less or the loan has been transferred from another bank, in which cases the sum is disbursed lump-sum.<br>For loans over AMD 50 million contractual amount at least 3 tranches must be defined. |
-
-> ¹Attention! The offer of the agreement is provided to the customer following which the customer may use the 7-day cooling-off period envisaged by the Armenian laws and regulations.
-In case of failure to notarize the pledge agreements specified in the loan agreement and securing the borrower's obligations under the loan agreement, within 30 (thirty) business days upon execution of the loan agreement and acceptance by the Borrower, the Agreement shall cease to be valid (unless the loan has already been disbursed to the borrower by that date).
-
-> ² Attention! The adjustable nominal interest rate may be revised no more than twice a year. Furthermore, depending on the change of the adjustable nominal interest rate, the threshold above or below which the nominal rate cannot change is ± 5%.
-
-> ³The list of developers is determined by the Bank.
+| \2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1.<br>The loan is issued:<br>For AMD loans with a term of 61-240 months: 80%² (if in Yerevan) and 70% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property,<br>For AMD loans with a term above 240 months: 70%² (if in Yerevan) and 60% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property |
+| \2. Security | 2.3. Location of the real estate to be pledged | 2.3.1. Armenia |
+| \2. Security | 2.4. Appraisal of the collateral | 2.4.1. Pledged property to be appraised by an appraising partner of the Bank. |
+| \3. Term of fulfillment of conditions of loan | 3.1. Term of fulfillment of conditions of loan | 3.1.1. Loans are disbursed in tranches. Each tranche is subject to proper use of previous tranche for the intended loan purpose by the borrower except where the amount of loan is AMD 7 million or less or the loan has been transferred from another bank, in which cases the sum is disbursed lump-sum.<br>For loans over AMD 50 million contractual amount at least 3 tranches must be defined. |
```

## 004_Mortgage_lending_terms_and_conditions_for_purchase_of_residential_real_estate_at_the_primary_market_

```diff
--- acquired-or-reconstructed
+++ normalized
@@ -2,26 +2,22 @@
 
 Source: <https://ameriabank.am/Portals/0/files/Personal/Loans/terms_flexible_mortgage_eng.pdf>
 
-## PDF page 1
-
-### Mortgage lending terms and conditions for purchase of residential real estate at the primary market with flexible opportunities offered by development companies cooperating with Ameriabank CJSC (hereinafter - the Developer)
+## Mortgage lending terms and conditions for purchase of residential real estate at the primary market with flexible opportunities offered by development companies cooperating with Ameriabank CJSC (hereinafter - the Developer)
 
 11RBD PL 72-03-104, Ed. 1
 Effective date: March 25, 2025
 
+¹Retail Lending Terms and Conditions (Home Mortgage Loan) (11RBD PL 72-03-98), approved by the Management Board resolution # 08/1/01/14 as of February 4, 2014.
+Available at https://ameriabank.am/useful-links.
+
 ### Mortgage lending terms and conditions for purchase of residential real estate at the primary market with flexible opportunities offered by development companies cooperating with Ameriabank CJSC (hereinafter - the Developer)
-
 | Category / Option | Details |
 | --- | --- |
-| 1. Purpose | 1.1. Increasing the mortgage loan portfolio, promoting sales |
-| 2. Client/Borrower | 2.1. Individuals meeting the Terms¹ established by Ameriabank CJSC (hereinafter - the Bank) |
+| \1. Purpose | 1.1. Increasing the mortgage loan portfolio, promoting sales |
+| \2. Client/Borrower | 2.1. Individuals meeting the Terms¹ established by Ameriabank CJSC (hereinafter - the Bank) |
 | Option 1. Partial or full subsidy of the interest rate by the Developer until receipt of the certificate of completion/signing of the handover act for the real estate specified by the Developer, or for a longer period, at the Developer's choice / 1. Nominal annual interest rate | 1.1. As per Terms¹ |
 | Option 1. Partial or full subsidy of the interest rate by the Developer until receipt of the certificate of completion/signing of the handover act for the real estate specified by the Developer, or for a longer period, at the Developer's choice / 2. Annual interest rate subsidized by the Developer | 2.1. 0.5%-13.5% |
 | Option 1. Partial or full subsidy of the interest rate by the Developer until receipt of the certificate of completion/signing of the handover act for the real estate specified by the Developer, or for a longer period, at the Developer's choice / 3. Annual percentage rate (APR) | 3.1. 13.83%-15.76% |
 | Option 2. Partial or full payment of the down payment by the Developer / 1. Down payment | 1.1. Minimum 10%, paid from the funds received under the interest-free target loan agreement signed between the Developer and the Borrower. The loan amount is subject to repayment by the Borrower before the Developer receives the certificate of completion/signs the handover act for the purchased real estate, unless otherwise agreed by the parties. |
 | Option 3: Partial or full payment of the down payment by the Developer and partial or full subsidy of the interest rate by the Developer until receipt of the certificate of completion/signing of the handover act for the real estate specified by the Developer, or for a longer period, at the Developer's choice / 1. Other terms and conditions | 1.1 The terms of Option 1 and 2 apply simultaneously. |
-
-> *The rest of the terms and conditions are specified in the Terms¹.
-
-> ¹Retail Lending Terms and Conditions (Home Mortgage Loan) (11RBD PL 72-03-98), approved by the Management Board resolution # 08/1/01/14 as of February 4, 2014.
-Available at https://ameriabank.am/useful-links.
+> \*The rest of the terms and conditions are specified in the Terms¹.
```

## 005_Terms_of_residential_and_commercial_real_estate_mortgage_lending_including_refinancing_campaign

```diff
--- acquired-or-reconstructed
+++ normalized
@@ -2,16 +2,18 @@
 
 Source: <https://ameriabank.am/Portals/0/files/Personal/Loans/terms_mortgage_lending_campaign_eng.pdf>
 
-## PDF page 1
-
 Approved by
 Management Board Resolution
-# 03/93/26 as of June 19, 2026
+\# 03/93/26 as of June 19, 2026
 Chairman of the Management Board-CEO
 Artak Hanesyan
 Effective date: July 1, 2026
 
-### TERMS OF RESIDENTIAL AND COMMERCIAL REAL ESTATE MORTGAGE LENDING (INCLUDING REFINANCING) CAMPAIGN
+## TERMS OF RESIDENTIAL AND COMMERCIAL REAL ESTATE MORTGAGE LENDING (INCLUDING REFINANCING) CAMPAIGN
+
+11RBD PL 72-03-98/03, Ed. 1
+
+1 Lending terms and conditions are defined in the Retail Lending Terms and Conditions (Home Mortgage Loan and Commercial Mortgage Loan) (11RBD PL 72-03-98, 11RBD PL 72-03-88). Available at https://ameriabank.am/useful-links.
 
 11RBD PL 72-03-98/03, Ed. 1
 
@@ -19,20 +21,14 @@
 | --- | --- | --- |
 | Purpose | Promoting sales of mortgage loans for residential and commercial real estate acquisition and moving to Ameriabank CJSC (hereinafter “the Bank”) existing mortgage loans issued by other banks and credit organizations operating in the Republic of Armenia. | Promoting sales of mortgage loans for residential and commercial real estate acquisition and moving to Ameriabank CJSC (hereinafter “the Bank”) existing mortgage loans issued by other banks and credit organizations operating in the Republic of Armenia. |
 | Loan type | Loans for purchase, renovation and/or construction of residential and commercial real estate (issued online and at the Bank’s branches) | Loans for purchase, renovation and/or construction of residential and commercial real estate (issued online and at the Bank’s branches) |
-| Eligible customers | 1. For newly issued loans: individuals meeting the Bank’s standard lending termsError! Bookmark not defined.<br>2. For refinancing of existing loans: individuals who have existing mortgage loans with other banks/credit organization of Armenia and duly perform their credit obligations | 1. For newly issued loans: individuals meeting the Bank’s standard lending termsError! Bookmark not defined.<br>2. For refinancing of existing loans: individuals who have existing mortgage loans with other banks/credit organization of Armenia and duly perform their credit obligations |
+| Eligible customers | \1. For newly issued loans: individuals meeting the Bank’s standard lending termsError! Bookmark not defined.<br>\2. For refinancing of existing loans: individuals who have existing mortgage loans with other banks/credit organization of Armenia and duly perform their credit obligations | \1. For newly issued loans: individuals meeting the Bank’s standard lending termsError! Bookmark not defined.<br>\2. For refinancing of existing loans: individuals who have existing mortgage loans with other banks/credit organization of Armenia and duly perform their credit obligations |
 | Campaign term | 2026 From July 1, 2026 until and inclusive December 30, 2026 | 2026 From July 1, 2026 until and inclusive December 30, 2026 |
 | Loan terms | Loans are issued in accordance with the standard lending terms and conditions1, except for the following clauses: | Loans are issued in accordance with the standard lending terms and conditions1, except for the following clauses: |
-| Nominal annual interest rate | 1. For the loans for purchase/renovation/construction of residential real estate<br>For the loans for | 2. For the loans for purchase/renovation/construction of residential real estate<br>For the loans for purchase/renovation/construction of commercial real estate |
-
-> 1 Lending terms and conditions are defined in the Retail Lending Terms and Conditions (Home Mortgage Loan and Commercial Mortgage Loan) (11RBD PL 72-03-98, 11RBD PL 72-03-88). Available at https://ameriabank.am/useful-links.
-
-## PDF page 2
-
-11RBD PL 72-03-98/03, Ed. 1
+| Nominal annual interest rate | \1. For the loans for purchase/renovation/construction of residential real estate<br>For the loans for | \2. For the loans for purchase/renovation/construction of residential real estate<br>For the loans for purchase/renovation/construction of commercial real estate |
 
 | Term | Refinancing | New loans |
 | --- | --- | --- |
-| Nominal annual interest rate | purchase/renovation/construction of commercial real estate<br><br>1.1. With an incentive: 12.9% (fixed adjustable interest rate which will be modified starting from the 37th month following the loan agreement execution; fixed component 4.9% + variable component (base rate)) | 2.1. Without an incentive: 12.9% (fixed adjustable interest rate which will be modified starting from the 37th month following the loan agreement execution; fixed component 4.9% + variable component (base rate)) |
+| Nominal annual interest rate | purchase/renovation/construction of commercial real estate<br>1.1. With an incentive: 12.9% (fixed adjustable interest rate which will be modified starting from the 37th month following the loan agreement execution; fixed component 4.9% + variable component (base rate)) | 2.1. Without an incentive: 12.9% (fixed adjustable interest rate which will be modified starting from the 37th month following the loan agreement execution; fixed component 4.9% + variable component (base rate)) |
 | Annual percentage rate (APR) | 12.05-12.45% | 13.67-13.68% |
 | Collateral-related costs | Collateral-related costs are covered by the Bank. | Collateral-related costs are covered by the Customer. |
 | Incentive and its payment | In case of loans with a possibility of providing an incentive, the client receives an incentive payment in the amount of 1% of the loan (without the taxes stipulated by the Republic of Armenia laws and regulations). Furthermore, the incentive is paid only for the loans issued in the Bank’s branches.<br>The incentive is transferred to the Customer’s current account with the Bank specified by the Customer by the Credits and Card Operations and Accounting Division, upon presentation by the loan officer, within 2 (two) business days upon registration of the Bank’s security interest over the property securing the credit obligations.<br>In case of full repayment of the credit obligations during the first 3 (three) years of the loan term, the incentive provided to the client (including the taxes defined by the Republic of Armenia laws and regulations) will be subject to return/repayment by the client within 1 (one) month. | In case of loans with a possibility of providing an incentive, the client receives an incentive payment in the amount of 1% of the loan (without the taxes stipulated by the Republic of Armenia laws and regulations). Furthermore, the incentive is paid only for the loans issued in the Bank’s branches.<br>The incentive is transferred to the Customer’s current account with the Bank specified by the Customer by the Credits and Card Operations and Accounting Division, upon presentation by the loan officer, within 2 (two) business days upon registration of the Bank’s security interest over the property securing the credit obligations.<br>In case of full repayment of the credit obligations during the first 3 (three) years of the loan term, the incentive provided to the client (including the taxes defined by the Republic of Armenia laws and regulations) will be subject to return/repayment by the client within 1 (one) month. |
```

## 006_Loan_service_fees

```diff
--- acquired-or-reconstructed
+++ normalized
@@ -2,53 +2,48 @@
 
 Source: <https://ameriabank.am/Portals/0/files/Personal/Loans/Loan_tariffs_eng.pdf>
 
-## PDF page 1
-
 Approved by
 Management Board resolution
-# ---- as of ...
+\# ---- as of ...
 Chairman of the Management Board -
 CEO
 Artak Hanesyan
-
 Ameriabank CJSC
 +(37410) 561111, +(37412) 561111 office@ameriabank.am
 
-### SERVICE FEES FOR LOANS TO INDIVIDUALS
+## SERVICE FEES FOR LOANS TO INDIVIDUALS
 
 Approved by Management Board resolution # 01/68/18 dated May 14, 2018.
 Current edition approved by resolution # .... dated ... , effective from July 14, 2026.
 
-#### General Provisions
+### General Provisions
 
-- 1. Under this document, “loan” means the loan types envisaged by the Retail Lending Terms and Conditions of the Bank.
-- 2. The changes specified in this document are made based on the client’s application, subject to its approval in accordance with the Bank’s internal regulations.
-- 3. These fees apply to changes initiated by the client. The changes made in order to ensure the client’s performance of the condition subsequent established by the Bank are not considered as the client’s initiative.
+- \1. Under this document, “loan” means the loan types envisaged by the Retail Lending Terms and Conditions of the Bank.
+- \2. The changes specified in this document are made based on the client’s application, subject to its approval in accordance with the Bank’s internal regulations.
+- \3. These fees apply to changes initiated by the client. The changes made in order to ensure the client’s performance of the condition subsequent established by the Bank are not considered as the client’s initiative.
+
+11RBD PL 72-03-29, Ed. 3
+
+- \4. The fees specified in this document do not apply to the automatically approved consumer loans secured by deposit, bonds and metal accounts in gold.
+- \5. Where several fees are applicable due to change of several terms of the same loan as per the application submitted by the client, only the highest of them shall be charged, once.
+- \6. To apply a fee(s) established by this document for modification of the same term for several loans, the total outstanding amount of those loans is considered.
+- \7. The fee amount is rounded to AMD 1,000 in favor of the client and shall be no less than the minimum amount of the respective fee (if established by this document).
+- \8. Where a new collateral or guarantor is added due to modification of a loan term(s), no fee is charged.
+- \9. In case of lines of credit and overdrafts, the outstanding loan amount means the bigger of the used amount of the line of credit/overdraft and the line of credit/overdraft limit currently available to the client.
 
 11RBD PL 72-03-29, Ed. 3
 
 | Purpose | Rates and Fees (AMD) |
 | --- | --- |
-| 1. Term extension for mortgage/investment loans | 0.1% of the outstanding loan amount, minimum AMD 50,000 |
-| 2. Granting a grace period for the principal amount of mortgage/investment loans | 0.1% of the outstanding loan amount, minimum AMD 50,000 |
-| 3. Modification of the condition subsequent for the loan | 0.05% of the outstanding loan amount, minimum AMD 10,000 |
-| 4. Change of the overdraft/line of credit account/card | AMD 30,000 |
-| 5. Change of the borrower/co-borrower/guarantor | AMD 50,000 |
-| 6. Release/substitution of the collateral | AMD 50,000 |
-| 7. Issuing consent for change of a pledged vehicle plate number | AMD 50,000<br>(VAT included) |
-| 8. Collateral-related change (including change of the collateral owner) | AMD 15,000 |
-| 9. Change of the loan repayment date | AMD 10,000 |
-| 10. Provision of loan before submitting to the Bank the document certifying state registration of the security interest | AMD 25,000 (per issue) |
-| 11. Issuing other consent not established by this document and not related to the collateral | AMD 10,000<br>(VAT included) |
-| 12. Revision/modification of another loan term not specified in this document (including interest rate revision) | 0.1% of the outstanding loan amount, minimum AMD 10,000 |
-
-## PDF page 2
-
-- 4. The fees specified in this document do not apply to the automatically approved consumer loans secured by deposit, bonds and metal accounts in gold.
-- 5. Where several fees are applicable due to change of several terms of the same loan as per the application submitted by the client, only the highest of them shall be charged, once.
-- 6. To apply a fee(s) established by this document for modification of the same term for several loans, the total outstanding amount of those loans is considered.
-- 7. The fee amount is rounded to AMD 1,000 in favor of the client and shall be no less than the minimum amount of the respective fee (if established by this document).
-- 8. Where a new collateral or guarantor is added due to modification of a loan term(s), no fee is charged.
-- 9. In case of lines of credit and overdrafts, the outstanding loan amount means the bigger of the used amount of the line of credit/overdraft and the line of credit/overdraft limit currently available to the client.
-
-11RBD PL 72-03-29, Ed. 3
+| \1. Term extension for mortgage/investment loans | 0.1% of the outstanding loan amount, minimum AMD 50,000 |
+| \2. Granting a grace period for the principal amount of mortgage/investment loans | 0.1% of the outstanding loan amount, minimum AMD 50,000 |
+| \3. Modification of the condition subsequent for the loan | 0.05% of the outstanding loan amount, minimum AMD 10,000 |
+| \4. Change of the overdraft/line of credit account/card | AMD 30,000 |
+| \5. Change of the borrower/co-borrower/guarantor | AMD 50,000 |
+| \6. Release/substitution of the collateral | AMD 50,000 |
+| \7. Issuing consent for change of a pledged vehicle plate number | AMD 50,000<br>(VAT included) |
+| \8. Collateral-related change (including change of the collateral owner) | AMD 15,000 |
+| \9. Change of the loan repayment date | AMD 10,000 |
+| \10. Provision of loan before submitting to the Bank the document certifying state registration of the security interest | AMD 25,000 (per issue) |
+| \11. Issuing other consent not established by this document and not related to the collateral | AMD 10,000<br>(VAT included) |
+| \12. Revision/modification of another loan term not specified in this document (including interest rate revision) | 0.1% of the outstanding loan amount, minimum AMD 10,000 |
```

## 007_On_the_Procedure_for_Setting_Calculation_and_Revision_of_the_Floating_Adjustable_Interest_Rate

```diff
--- acquired-or-reconstructed
+++ normalized
@@ -2,13 +2,11 @@
 
 Source: <https://www.ameriabank.am/userfiles/file/Retail/Floating_Agreement_eng.pdf>
 
-## PDF page 1
+## AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION
 
-### AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION
+This agreement (hereinafter the “Agreement”) is entered into on \[date\] in Yerevan under the laws and regulations of Armenia by and between Ameriabank Closed Joint Stock Company (incorporated under the resolution of the CBA Board dated September 8, 1992, registration number 50, certificate No 0154; address: 2 V. Sargsyan, Yerevan) hereinafter the “Bank”, represented by the authorized person acting on behalf of the Bank, and ................. hereinafter the “Client” or the “Borrower”. The Bank and the Client shall be hereinafter jointly referred to as the “Parties” and individually as the “Party”. This Agreement on Adjustable Interest Rate Setting and Calculation forms an integral part of Agreement # \[--\] (hereinafter referred to as the “Principal Agreement”).
 
-This agreement (hereinafter the “Agreement”) is entered into on [date] in Yerevan under the laws and regulations of Armenia by and between Ameriabank Closed Joint Stock Company (incorporated under the resolution of the CBA Board dated September 8, 1992, registration number 50, certificate № 0154; address: 2 V. Sargsyan, Yerevan) hereinafter the “Bank”, represented by the authorized person acting on behalf of the Bank, and …………….. hereinafter the “Client” or the “Borrower”. The Bank and the Client shall be hereinafter jointly referred to as the “Parties” and individually as the “Party”. This Agreement on Adjustable Interest Rate Setting and Calculation forms an integral part of Agreement # [--] (hereinafter referred to as the “Principal Agreement”).
-
-#### 1 SUBJECT OF THE AGREEMENT
+### 1 SUBJECT OF THE AGREEMENT
 
 1.1. The Parties hereby define the procedure for regular revision of the loan interest rate under the Principal Agreement in response to the changes in market interest rates to ensure that the interest rate determined by the Parties is consistent with the market rates to the highest possible degree at all times subject to the procedure established hereby.
 
@@ -16,13 +14,13 @@
 
 1.3. Hereby the Parties agree that the interest rate set by the Principal Agreement shall be considered adjustable and variable (hereinafter “Adjustable Rate”) as stipulated under this Agreement.
 
-#### 2 ADJUSTABLE INTEREST RATE CONSTITUENTS
+### 2 ADJUSTABLE INTEREST RATE CONSTITUENTS
 
 2.1. The Adjustable Rate defined by the Principal Agreement shall consist of the following constituents (components):
 2.1.1. Base Rate
 2.1.2. Margin (fixed component)
 
-2.2. The Adjustable Rate is a nominal interest rate calculated in accordance with this Agreement using the following formula: 𝑅𝐴 = 𝐑𝐵 + 𝐑𝐌 where RA is the Adjustable Rate, RB is the Base Rate and RM is the Margin (fixed component).
+2.2. The Adjustable Rate is a nominal interest rate calculated in accordance with this Agreement using the following formula: RA = RB + RM where RA is the Adjustable Rate, RB is the Base Rate and RM is the Margin (fixed component).
 One primary index (hereinafter “Primary Rate” and/or “Primary Index”) and one secondary index (hereinafter “Secondary Rate” and/or “Secondary Index”) of Base Rate shall be used as basis for calculation and adjusting of the Adjustable Rate, which cannot be changed during the term of the Agreement, except in cases defined in chapter 5. The Secondary Index shall be applied if the Primary Index is inaccessible and setting of the Adjustable Rate for the next period becomes impossible.
 
 2.3. The Base Rate shall be determined on the basis of the following market rates, depending on the loan currency:
@@ -32,30 +30,25 @@
 
 2.4. Where it is necessary to choose a Secondary Rate, in order to avoid significant fluctuations between interest rates calculated based on Primary and Secondary Rates and prevent either Party from acquiring unjustified economic gain or incurring loss at the expense of the other Party, calculation of interest rate based on Secondary Rate shall include an adjusting factor to balance possible differences between rates (hereinafter “Spread Adjustment"). Spread Adjustment shall be calculated by the Bank and presented to the Borrower with its amount indicated in the selection Offer. During calculation of the Adjustable Rate throughout the term of the Agreement after selection of the Secondary Rate, the Spread Adjustment shall remain unchanged and be included in calculation of interest
 
-## PDF page 2
-
 rate at all times, and accordingly, calculation of the Adjustable Rate based on Secondary Rate shall be performed using the following formula:
-
-𝐑𝐀 = 𝐑𝐵 + 𝐒A + 𝐑𝐌
-
+RA = RB + SA + RM
 where
 RA is the Adjustable Rate
 RB is the Base Rate
 SA is the Spread Adjustment
 RM is the margin (fixed component)
-
 However, regardless of application of the Spread Adjustment, if the Agreement provides for a maximum Adjustable Rate limit, the interest rate calculated on the basis of the Secondary Rate and Spread Adjustment shall not exceed the set maximum limit1.
 
 2.5. The margin (fixed component) shall be determined based on the terms of lending and shall be fixed in the loan agreement for each loan separately, on the basis of the respective loan decision adopted by the authorized body of the Bank.
 
-2.6. For the purpose of this Agreement and the Principal Agreement, the base rate of the Adjustable Rate for the Client (Borrower) at the time of execution of the Principal Agreement shall be equal to _______ percent, while the Margin (fixed component) shall be equal to _______ percent. Where the base rate of the Adjustable Rate is a negative value, the Adjustable Rate under the Principal Agreement shall be calculated based on 0 (zero).
+2.6. For the purpose of this Agreement and the Principal Agreement, the base rate of the Adjustable Rate for the Client (Borrower) at the time of execution of the Principal Agreement shall be equal to \_\_\_\_\_\_\_ percent, while the Margin (fixed component) shall be equal to \_\_\_\_\_\_\_ percent. Where the base rate of the Adjustable Rate is a negative value, the Adjustable Rate under the Principal Agreement shall be calculated based on 0 (zero).
 
-#### 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE
+### 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE
 
 3.1. Information on the yield to maturity of Armenian Government (treasury) bills can be obtained from the relevant publications (yield curve) on the official website of the CBA at the following link:
 https://www.cba.am/am/SitePages/fmofinancialmarkets.aspx
 Information on the average yield of Armenian 6-month (or if not available, closest to 6 months) Government (treasury) bills in primary auctions can be retrieved from the official website of the Armenian Securities Exchange at the following link:
-https://amx.am/am/government_bond_auctions
+https://amx.am/am/government\_bond\_auctions
 
 3.2. Information on the CME Term SOFR USD 6 Month reference rate can be retrieved from Bloomberg terminal under TSFR6M ticker (SR6M in Reuters).
 
@@ -67,9 +60,7 @@
 
 3.6. In case of inaccessibility of the Bloomberg Terminal or impossibility to check the information for any other reason, the Bank shall, upon the Borrower’s request, provide the information retrieved from the system to the Borrower by e-mail or other e-channels acceptable to the Parties and/or deliver it to the Borrower within the Bank premises. Whenever Bloomberg Terminal is not accessible, the information retrieved from Thomson Reuters Eikon shall be used as an alternative.
 
-> 1 This clause is not applicable in case of mortgage and consumer loans.
-
-## PDF page 3
+1 This clause is not applicable in case of mortgage and consumer loans.
 
 3.7. Change of any link specified in clauses 3.1, 3.2., 3.3, 3.4 ,3.5 and 3.9. above shall not affect or have any implications for this Agreement and/or its validity, except for the special cases provided for in clause 5.1 below.
 
@@ -81,7 +72,7 @@
 3.9. The revised Base Rate and information about its changes shall be published on the Bank’s official website twice a year, on the first business days of February and August.
 https://ameriabank.am/business/sme/financing/support/base-rate
 
-#### 4 THE PROCEDURE OF REGULAR REVIEW AND REVISION OF THE ADJUSTABLE INTEREST RATE
+### 4 THE PROCEDURE OF REGULAR REVIEW AND REVISION OF THE ADJUSTABLE INTEREST RATE
 
 4.1. The first revision of the Adjustable Rate in accordance with this Agreement shall be in 3 (three)2 years after execution of the Principal Agreement, except in the case defined under clause 5.1 herein, unless otherwise provided for by the imperative norms of the Republic of Armenia laws and regulations. Thereafter, the Adjustable Rate may be revised regularly every 6 (six) months. Prior to the date of the first revision, the Base Rate shall be deemed equal to the Base Rate effective on the date of execution of the Principal Agreement.
 
@@ -101,12 +92,10 @@
 
 4.7. The maximum increase threshold of the loan rate under the Principal Agreement shall not exceed the maximum decrease threshold.3
 
-> 2 The 3-year requirement is mandatory in case of mortgage loans only.
+2 The 3-year requirement is mandatory in case of mortgage loans only.
 3This clause is effective and applicable in case of mortgage and consumer loans only.
 
-## PDF page 4
-
-#### 5 EXCEPTIONAL CIRCUMSTANCES
+### 5 EXCEPTIONAL CIRCUMSTANCES
 
 5.1. Where the Primary and Secondary Indicators become inaccessible and impossible, the Parties agree that the Bank shall offer another similar indicator for the next period, relying solely on the standards defined by the CBA or the legislation of the Republic of Armenia. Adjustable Rate shall be considered inaccessible and impossible under the following exceptional circumstances.
 5.1.1. Procedure of market interest rate calculation undergoes material changes.
@@ -118,7 +107,7 @@
 
 5.2. Hereby the Borrower agrees that the Bank shall have the right to revise and adjust the Loan interest rate in favor of the Borrower at any time and any intervals during the term of the Agreement and/or the Principal Agreement.
 
-#### 6 MISCELLANEOUS
+### 6 MISCELLANEOUS
 
 6.1. This Agreement shall be binding upon and inure to the benefit of the Parties’ successors and assigns.
 
@@ -128,8 +117,8 @@
 
 6.4. The Agreement shall become effective upon signing by both Parties and shall remain in full force and effect until proper fulfillment of the liabilities of the Parties under the Agreement.
 
-#### 7 ADDRESSES AND SIGNATURES OF THE PARTIES
+### 7 ADDRESSES AND SIGNATURES OF THE PARTIES
 
 | Bank | CLIENT/BORROWER |
 | --- | --- |
-| Ameriabank CJSC<br>Address: 2 V. Sargsyan st., Yerevan<br>Authorized person<br><br>________________________________<br>(name, surname, signature)<br>Seal | ……………………….<br>Passport: ……………………………..<br>Address: ……………………………..<br><br>___________________<br>Signature |
+| Ameriabank CJSC<br>Address: 2 V. Sargsyan st., Yerevan<br>Authorized person<br>\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_<br>(name, surname, signature)<br>Seal | ............................<br>Passport: ...................................<br>Address: ...................................<br>\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_<br>Signature |
```

## 008_Terms_of_the_loan_for_purchase_of_residential_real_estate_from_primary_market

```diff
--- acquired-or-reconstructed
+++ normalized
@@ -2,9 +2,7 @@
 
 Source: <https://ameriabank.am/Portals/0/files/Personal/Loans/previous-loans/mortgage_personal_purchase_ed71_eng.pdf>
 
-## PDF page 1
-
-### AMERIABANK CJSC 11RBD PL 72-03-98
+## AMERIABANK CJSC 11RBD PL 72-03-98
 Retail Lending Terms and Conditions
 (Home Mortgage Loan)1
 Edition 71
@@ -12,65 +10,58 @@
 Approved by Management Board Resolution # 08/1/01/14 as of February 4, 2014
 Current edition approved by resolution # 03/47/26 as of March 26, 2026
 
+1These terms have been previously known as Retail Lending Terms and Conditions under code 11RBD PL 72-03-01. Some of the Bank documents may contain references to these terms and conditions under the former name and code.
+
+²Depending on the creditworthiness of the borrower, term of loan and LTV ratio, a higher or lower interest rate can be applied.
+
+³The annual percentage rate (APR) may differ from the above specified values if there is any or a few of the following factors:
+\- When the property insurance is obtained by the Bank at the customer’s request
+\- When the borrower selects differentiated or mixed form of loan repayment
+\- If there are deviations from the creditworthiness criteria approved under the internal regulations of the Bank
+\- If additional property is pledged as collateral
+\- If there are other deviations
+
+⁴ Attention! The adjustable nominal interest rate may be revised no more than twice a year. Furthermore, depending on the change of the adjustable nominal interest rate, the threshold above or below which the nominal rate cannot change is ±5%.
+
+⁵ The list of developers is determined by the Bank. If the developer is not included in the Bank's list, the terms of the loans for purchase of residential real estate from secondary market will apply.
+
 ### Home Purchase Loan (primary market)
-
 | Section | Parameter | Terms / Currency: AMD | Currency: USD | Currency: EUR |
 | --- | --- | --- | --- | --- |
-| 1. Purpose | 1.1. Purpose | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or (ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or (ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or (ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) |
-| 2. Client’s personal details | 2.1. Eligible age of the client/co-borrower/guarantor | 2.1.1. 18-70 years old, provided that the borrower’s age at the time of expiry of the loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of the agreement it will not have exceeded 70. If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. | 2.1.1. 18-70 years old, provided that the borrower’s age at the time of expiry of the loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of the agreement it will not have exceeded 70. If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. | 2.1.1. 18-70 years old, provided that the borrower’s age at the time of expiry of the loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of the agreement it will not have exceeded 70. If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. |
-| 2. Client’s personal details | 2.2. Residency | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia<br>For loans in foreign currency: individuals not considered residents of Armenia | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia<br>For loans in foreign currency: individuals not considered residents of Armenia | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia<br>For loans in foreign currency: individuals not considered residents of Armenia |
-| 3. Loan terms | 3.1. Currency | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR |
-| 3. Loan terms | 3.2. Minimum and maximum loan limits | 3.2.1. AMD 3,000,000 - AMD 150,000,000 | 3.2.2. USD 5,000 - USD 300,000 | 3.2.3. EUR 5,000 - EUR 300,000 |
-| 3. Loan terms | 3.3. Term (months) | 3.3.1. 60 | 3.3.1. 60 | 3.3.1. 60 |
-| 3. Loan terms | 3.4. Nominal annual interest rate² | 3.4.1. Fixed<br>13.5% | 3.4.2. Fixed<br>11.0% | 3.4.3. Fixed<br>8.5% |
-| 3. Loan terms | 3.5. Annual percentage rate (APR)³ | 3.5.1. Fixed<br>14.39-15.76% | 3.5.2. Fixed<br>11.6-13.56% | 3.5.3. Fixed<br>8.86-10.71% |
-| 3. Loan terms | 3.6. Term (months) | 3.6.1. 61-360 | 3.6.1. 61-360 | 3.6.1. 61-360 |
-| 3. Loan terms | 3.7. Nominal annual interest rate² | 3.7.1. Adjustable fixed⁴ (rate can be changed starting from the 37th month)<br>Fixed component 5.5% + variable component (base rate) | 3.7.2. Adjustable fixed⁴ (rate can be changed starting from the 37th month)<br>Fixed component 8% + variable component (base rate) | 3.7.3. Adjustable fixed⁴ (rate can be changed starting from the 37th month)<br>Fixed component 7% + variable component (base rate) |
-| 3. Loan terms | 3.8. Annual percentage rate (APR)³ | 3.8.1. Adjustable fixed (rate can be changed starting from the 37th month)<br>14.35-15.74% | 3.8.2. Adjustable fixed (rate can be changed starting from the 37th month)<br>10.47-12.39% | 3.8.3. Adjustable fixed (rate can be changed starting from the 37th month)<br>8.3-10.12% |
-| 3. Loan terms | 3.9. Other terms related to the interest rate | 3.9.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%<br>3.9.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%.<br>3.9.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%.<br>3.9.5. If the client prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds).<br>3.9.6. In case of other deviations, the applicable interest rate may be increased by 0.25%. | 3.9.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%<br>3.9.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%.<br>3.9.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%.<br>3.9.5. If the client prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds).<br>3.9.6. In case of other deviations, the applicable interest rate may be increased by 0.25%. | 3.9.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%<br>3.9.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%.<br>3.9.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%.<br>3.9.5. If the client prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds).<br>3.9.6. In case of other deviations, the applicable interest rate may be increased by 0.25%. |
-| 3. Loan terms | 3.10. Lump sum disbursement fee | 3.10.1. N/A, except for non-resident individuals, for whom the lump sum loan disbursement fee is 1% of the loan amount or AMD 1 million, whichever is less | 3.10.1. N/A, except for non-resident individuals, for whom the lump sum loan disbursement fee is 1% of the loan amount or AMD 1 million, whichever is less | 3.10.1. N/A, except for non-resident individuals, for whom the lump sum loan disbursement fee is 1% of the loan amount or AMD 1 million, whichever is less |
-| 3. Loan terms | 3.11. Minimum down payment | 3.11.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.<br>3.11.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5% of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral. | 3.11.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.<br>3.11.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5% of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral. | 3.11.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.<br>3.11.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5% of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral. |
-| 3. Loan terms | 3.12. Manner of disbursement | 1. Lump sum<br>2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower. | 1. Lump sum<br>2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower. | 1. Lump sum<br>2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower. |
-| 3. Loan terms | 3.13. Cashing of the loan amount by the seller from his account with the Bank after loan disbursement (where applicable) | 3.13.1.<br>AMD: Free<br>Other currency: 0.5 % | 3.13.1.<br>AMD: Free<br>Other currency: 0.5 % | 3.13.1.<br>AMD: Free<br>Other currency: 0.5 % |
-| 4. Forms of loan repayment | 4.1. Repayment method | 4.1.1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest)<br>4.1.2. Differentiated (monthly repayment of equal portions of principal amount while interest accrues to outstanding loan and decreases each month) | 4.1.1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest)<br>4.1.2. Differentiated (monthly repayment of equal portions of principal amount while interest accrues to outstanding loan and decreases each month) | 4.1.1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest)<br>4.1.2. Differentiated (monthly repayment of equal portions of principal amount while interest accrues to outstanding loan and decreases each month) |
-
-## PDF page 2
+| \1. Purpose | 1.1. Purpose | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or (ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or (ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or (ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) |
+| \2. Client’s personal details | 2.1. Eligible age of the client/co-borrower/guarantor | 2.1.1. 18-70 years old, provided that the borrower’s age at the time of expiry of the loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of the agreement it will not have exceeded 70. If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. | 2.1.1. 18-70 years old, provided that the borrower’s age at the time of expiry of the loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of the agreement it will not have exceeded 70. If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. | 2.1.1. 18-70 years old, provided that the borrower’s age at the time of expiry of the loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of the agreement it will not have exceeded 70. If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. |
+| \2. Client’s personal details | 2.2. Residency | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia<br>For loans in foreign currency: individuals not considered residents of Armenia | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia<br>For loans in foreign currency: individuals not considered residents of Armenia | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia<br>For loans in foreign currency: individuals not considered residents of Armenia |
+| \3. Loan terms | 3.1. Currency | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR |
+| \3. Loan terms | 3.2. Minimum and maximum loan limits | 3.2.1. AMD 3,000,000 - AMD 150,000,000 | 3.2.2. USD 5,000 - USD 300,000 | 3.2.3. EUR 5,000 - EUR 300,000 |
+| \3. Loan terms | 3.3. Term (months) | 3.3.1. 60 | 3.3.1. 60 | 3.3.1. 60 |
+| \3. Loan terms | 3.4. Nominal annual interest rate² | 3.4.1. Fixed<br>13.5% | 3.4.2. Fixed<br>11.0% | 3.4.3. Fixed<br>8.5% |
+| \3. Loan terms | 3.5. Annual percentage rate (APR)³ | 3.5.1. Fixed<br>14.39-15.76% | 3.5.2. Fixed<br>11.6-13.56% | 3.5.3. Fixed<br>8.86-10.71% |
+| \3. Loan terms | 3.6. Term (months) | 3.6.1. 61-360 | 3.6.1. 61-360 | 3.6.1. 61-360 |
+| \3. Loan terms | 3.7. Nominal annual interest rate² | 3.7.1. Adjustable fixed⁴ (rate can be changed starting from the 37th month)<br>Fixed component 5.5% + variable component (base rate) | 3.7.2. Adjustable fixed⁴ (rate can be changed starting from the 37th month)<br>Fixed component 8% + variable component (base rate) | 3.7.3. Adjustable fixed⁴ (rate can be changed starting from the 37th month)<br>Fixed component 7% + variable component (base rate) |
+| \3. Loan terms | 3.8. Annual percentage rate (APR)³ | 3.8.1. Adjustable fixed (rate can be changed starting from the 37th month)<br>14.35-15.74% | 3.8.2. Adjustable fixed (rate can be changed starting from the 37th month)<br>10.47-12.39% | 3.8.3. Adjustable fixed (rate can be changed starting from the 37th month)<br>8.3-10.12% |
+| \3. Loan terms | 3.9. Other terms related to the interest rate | 3.9.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%<br>3.9.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%.<br>3.9.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%.<br>3.9.5. If the client prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds).<br>3.9.6. In case of other deviations, the applicable interest rate may be increased by 0.25%. | 3.9.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%<br>3.9.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%.<br>3.9.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%.<br>3.9.5. If the client prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds).<br>3.9.6. In case of other deviations, the applicable interest rate may be increased by 0.25%. | 3.9.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%<br>3.9.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%.<br>3.9.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%.<br>3.9.5. If the client prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds).<br>3.9.6. In case of other deviations, the applicable interest rate may be increased by 0.25%. |
+| \3. Loan terms | 3.10. Lump sum disbursement fee | 3.10.1. N/A, except for non-resident individuals, for whom the lump sum loan disbursement fee is 1% of the loan amount or AMD 1 million, whichever is less | 3.10.1. N/A, except for non-resident individuals, for whom the lump sum loan disbursement fee is 1% of the loan amount or AMD 1 million, whichever is less | 3.10.1. N/A, except for non-resident individuals, for whom the lump sum loan disbursement fee is 1% of the loan amount or AMD 1 million, whichever is less |
+| \3. Loan terms | 3.11. Minimum down payment | 3.11.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.<br>3.11.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5% of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral. | 3.11.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.<br>3.11.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5% of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral. | 3.11.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.<br>3.11.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5% of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral. |
+| \3. Loan terms | 3.12. Manner of disbursement | \1. Lump sum<br>\2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower. | \1. Lump sum<br>\2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower. | \1. Lump sum<br>\2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower. |
+| \3. Loan terms | 3.13. Cashing of the loan amount by the seller from his account with the Bank after loan disbursement (where applicable) | 3.13.1.<br>AMD: Free<br>Other currency: 0.5 % | 3.13.1.<br>AMD: Free<br>Other currency: 0.5 % | 3.13.1.<br>AMD: Free<br>Other currency: 0.5 % |
+| \4. Forms of loan repayment | 4.1. Repayment method | 4.1.1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest)<br>4.1.2. Differentiated (monthly repayment of equal portions of principal amount while interest accrues to outstanding loan and decreases each month) | 4.1.1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest)<br>4.1.2. Differentiated (monthly repayment of equal portions of principal amount while interest accrues to outstanding loan and decreases each month) | 4.1.1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest)<br>4.1.2. Differentiated (monthly repayment of equal portions of principal amount while interest accrues to outstanding loan and decreases each month) |
 
 ### Home Purchase Loan (primary market) (Continued)
-
 | Section | Parameter | Terms |
 | --- | --- | --- |
-| 4. Forms of loan repayment | 4.1. Repayment method | 4.1.3. Mixed (client may choose an individual repayment schedule based on seasonality of cash flows, provided that at least 5% of contractual loan amount is repaid each year; interest payable on monthly basis) |
-| 5. Security | 5.1. Eligible collateral | 5.1.1.<br>1. The loan is secured by the real estate being purchased. The Bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the Bank, as well as cash in the Bank or bonds issued by the Bank.<br>2. If the borrower wishes to purchase property under construction without registered certificate of title, the loan will be secured by other Armenia-based real estate to the reasonable satisfaction of the Bank.<br>3. If the borrower wishes to purchase property abroad, the loan will be secured by Armenia-based real estate to the reasonable satisfaction of the Bank. |
-| 5. Security | 5.2. Loan-to-value (LTV) ratio | 5.2.1. The loan is issued:<br>1. For AMD loans with a term of 61-240 months: up to 90%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client,<br>For AMD loans with a term above 240 months: up to 80%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁶ reference provided to the client, unless otherwise determined by the Bank,<br>2. For foreign currency loans with a term of 61-240 months: up to 70%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client,<br>For foreign currency loans with a term above 240 months: up to 60%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client, unless otherwise determined by the Bank,<br>3. up to 100% of the value of cash in the Bank or bonds issued by the Bank.<br>4. In case of loans without creditworthiness assessment: up to 60%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client |
-| 5. Security | 5.3. Location of the real estate to be pledged | 5.3.1. Yerevan, regional centers of Armenia, towns where Ameriabank has branches, as well as Jrvezh, Arinj, Dzoraghbyur, Kasakh, Tsaghkadzor, Masis and Yeghvard<br>5.3.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children, also regional cities of Armenia not specified in clause 5.3.1 and particular rural settlements approved by the Republic of Armenia Government decree N 968-Լ as of May 14, 2020. |
-| 5. Security | 5.4. Appraisal of the collateral | 5.4.1.<br>1. No appraisal is required in case of acquisition of the right to purchase property from the developer. Pledge value is considered to be equal to the price specified in the developer's reference, unless otherwise determined by the Bank.<br>2. In case of acquisition of the title to the real estate from the developer, appraisal is performed by appraisal companies cooperating with the Bank. |
-| 5. Security | 5.5. Additional security | 5.5.1. The Bank may request guarantees of individuals and/or companies as additional security. |
-| 6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.1. The real estate being pledged is insured by the Bank in the following cases:<br>6.1.1.1. If at the time of registration of the title to the real estate and/or at the time of reappraisal, the market value of the property is over AMD 100 million (one hundred million); or<br>6.1.1.2. where the address of the pledged real estate is included in the list of properties published on the Bank’s website.<br>6.1.2. The Bank obtains insurance each year for the amount of the outstanding principal throughout the loan term if any of the above specified conditions is in place (in this case, the calculation of the interest rate also covers all the possible costs, including those associated with the insurance, where applicable). |
-| 7. Required documents | 7.1. Required documents | 7.1.1. Required documents filed together with the loan application<br>• Loan application<br>• ID (original)<br>• Certificate of ownership/purchase right of real estate to be purchased/pledged [copy]<br>• Other documents upon the Bank’s request<br>7.1.2. Documents required after pre-approval<br>• Proof of employment and/or other income |
-
-## PDF page 3
+| \4. Forms of loan repayment | 4.1. Repayment method | 4.1.3. Mixed (client may choose an individual repayment schedule based on seasonality of cash flows, provided that at least 5% of contractual loan amount is repaid each year; interest payable on monthly basis) |
+| \5. Security | 5.1. Eligible collateral | 5.1.1.<br>\1. The loan is secured by the real estate being purchased. The Bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the Bank, as well as cash in the Bank or bonds issued by the Bank.<br>\2. If the borrower wishes to purchase property under construction without registered certificate of title, the loan will be secured by other Armenia-based real estate to the reasonable satisfaction of the Bank.<br>\3. If the borrower wishes to purchase property abroad, the loan will be secured by Armenia-based real estate to the reasonable satisfaction of the Bank. |
+| \5. Security | 5.2. Loan-to-value (LTV) ratio | 5.2.1. The loan is issued:<br>\1. For AMD loans with a term of 61-240 months: up to 90%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client,<br>For AMD loans with a term above 240 months: up to 80%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁶ reference provided to the client, unless otherwise determined by the Bank,<br>\2. For foreign currency loans with a term of 61-240 months: up to 70%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client,<br>For foreign currency loans with a term above 240 months: up to 60%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client, unless otherwise determined by the Bank,<br>\3. up to 100% of the value of cash in the Bank or bonds issued by the Bank.<br>\4. In case of loans without creditworthiness assessment: up to 60%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client |
+| \5. Security | 5.3. Location of the real estate to be pledged | 5.3.1. Yerevan, regional centers of Armenia, towns where Ameriabank has branches, as well as Jrvezh, Arinj, Dzoraghbyur, Kasakh, Tsaghkadzor, Masis and Yeghvard<br>5.3.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children, also regional cities of Armenia not specified in clause 5.3.1 and particular rural settlements approved by the Republic of Armenia Government decree N 968-Լ as of May 14, 2020. |
+| \5. Security | 5.4. Appraisal of the collateral | 5.4.1.<br>\1. No appraisal is required in case of acquisition of the right to purchase property from the developer. Pledge value is considered to be equal to the price specified in the developer's reference, unless otherwise determined by the Bank.<br>\2. In case of acquisition of the title to the real estate from the developer, appraisal is performed by appraisal companies cooperating with the Bank. |
+| \5. Security | 5.5. Additional security | 5.5.1. The Bank may request guarantees of individuals and/or companies as additional security. |
+| \6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.1. The real estate being pledged is insured by the Bank in the following cases:<br>6.1.1.1. If at the time of registration of the title to the real estate and/or at the time of reappraisal, the market value of the property is over AMD 100 million (one hundred million); or<br>6.1.1.2. where the address of the pledged real estate is included in the list of properties published on the Bank’s website.<br>6.1.2. The Bank obtains insurance each year for the amount of the outstanding principal throughout the loan term if any of the above specified conditions is in place (in this case, the calculation of the interest rate also covers all the possible costs, including those associated with the insurance, where applicable). |
+| \7. Required documents | 7.1. Required documents | 7.1.1. Required documents filed together with the loan application<br>• Loan application<br>• ID (original)<br>• Certificate of ownership/purchase right of real estate to be purchased/pledged \[copy\]<br>• Other documents upon the Bank’s request<br>7.1.2. Documents required after pre-approval<br>• Proof of employment and/or other income |
 
 ### Home Purchase Loan (primary market) (Continued)
-
 | Section | Parameter | Terms |
 | --- | --- | --- |
-| 7. Required documents | 7.1. Required documents | • Marriage (divorce, spouse death) certificate (original)<br>• Certificate of title to real estate to be pledged (original)<br>• Other documents upon the Bank request<br>7.1.3. Documents required after loan approval<br>• Copies of bases of title to real estate (to be submitted upon the Bank’s request)<br>• IDs of owners of the property to be purchased/pledged (originals)<br>• Copies of marriage (divorce, spouse death) certificates of owners of the property to be pledged, to be presented if available<br>• Statement from the State Committee of Real Estate Cadaster on encumbrance of real estate (unified statement)<br>• Tax clearance certificate for the real estate<br>• Real estate insurance policy<br>• Documentary proof that the down payment was made in a non-cash manner (e.g.: original receipt, or, if paid electronically, a document showing that the electronic payment was confirmed). Such proof is not required if the payment was made from the accounts held with the Bank and the Bank specialist has exported the payment document from the system.<br>• Other documents upon the Bank’s request |
-| 8. Early repayment fee | 8.1. Early repayment fee | 8.1.1.<br>At any time during a contractual year the borrower can make an early repayment to the extent of outstanding principal amount of loan for that contractual year. A contractual year is each period of 12 months following the date of execution of credit agreement.<br>Where the amount of early repayment exceeds the specified limit, the following fees will be charged:<br>• Max 0.6% of early repayment, if made during the first year of the agreement<br>• Max 0.4% of early repayment, if made during the second year of the agreement<br>• Max 0.2% of early repayment, if made during the third year of the agreement |
-| 9. Late payment fines and penalties | 9.1. Late payment fines and penalties | 9.1.1. The interest rate specified in the loan agreement will continue to be applied to overdue loans.<br>Fine in the amount of 0.13% of overdue loan/interest for each overdue day |
-| 10. Other fees | 10.1. Other fees payable by the client | 10.1.1.<br>• Fee for unified statement from the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia<br>• Fees for notarization of pledge (real estate) and filing of the bank’s security interest under pledge agreement |
-
-> 1These terms have been previously known as Retail Lending Terms and Conditions under code 11RBD PL 72-03-01. Some of the Bank documents may contain references to these terms and conditions under the former name and code.
-
-> ²Depending on the creditworthiness of the borrower, term of loan and LTV ratio, a higher or lower interest rate can be applied.
-
-> ³The annual percentage rate (APR) may differ from the above specified values if there is any or a few of the following factors:
-- When the property insurance is obtained by the Bank at the customer’s request
-- When the borrower selects differentiated or mixed form of loan repayment
-- If there are deviations from the creditworthiness criteria approved under the internal regulations of the Bank
-- If additional property is pledged as collateral
-- If there are other deviations
-
-> ⁴ Attention! The adjustable nominal interest rate may be revised no more than twice a year. Furthermore, depending on the change of the adjustable nominal interest rate, the threshold above or below which the nominal rate cannot change is ±5%.
-
-> ⁵ The list of developers is determined by the Bank. If the developer is not included in the Bank's list, the terms of the loans for purchase of residential real estate from secondary market will apply.
+| \7. Required documents | 7.1. Required documents | • Marriage (divorce, spouse death) certificate (original)<br>• Certificate of title to real estate to be pledged (original)<br>• Other documents upon the Bank request<br>7.1.3. Documents required after loan approval<br>• Copies of bases of title to real estate (to be submitted upon the Bank’s request)<br>• IDs of owners of the property to be purchased/pledged (originals)<br>• Copies of marriage (divorce, spouse death) certificates of owners of the property to be pledged, to be presented if available<br>• Statement from the State Committee of Real Estate Cadaster on encumbrance of real estate (unified statement)<br>• Tax clearance certificate for the real estate<br>• Real estate insurance policy<br>• Documentary proof that the down payment was made in a non-cash manner (e.g.: original receipt, or, if paid electronically, a document showing that the electronic payment was confirmed). Such proof is not required if the payment was made from the accounts held with the Bank and the Bank specialist has exported the payment document from the system.<br>• Other documents upon the Bank’s request |
+| \8. Early repayment fee | 8.1. Early repayment fee | 8.1.1.<br>At any time during a contractual year the borrower can make an early repayment to the extent of outstanding principal amount of loan for that contractual year. A contractual year is each period of 12 months following the date of execution of credit agreement.<br>Where the amount of early repayment exceeds the specified limit, the following fees will be charged:<br>• Max 0.6% of early repayment, if made during the first year of the agreement<br>• Max 0.4% of early repayment, if made during the second year of the agreement<br>• Max 0.2% of early repayment, if made during the third year of the agreement |
+| \9. Late payment fines and penalties | 9.1. Late payment fines and penalties | 9.1.1. The interest rate specified in the loan agreement will continue to be applied to overdue loans.<br>Fine in the amount of 0.13% of overdue loan/interest for each overdue day |
+| \10. Other fees | 10.1. Other fees payable by the client | 10.1.1.<br>• Fee for unified statement from the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia<br>• Fees for notarization of pledge (real estate) and filing of the bank’s security interest under pledge agreement |
```

## 009_Terms_of_the_loan_for_purchase_of_residential_real_estate_from_primary_market

```diff
--- acquired-or-reconstructed
+++ normalized
@@ -1,92 +1,80 @@
 # Terms of the loan for purchase of residential real estate from primary market
 
 Source: <https://ameriabank.am/Portals/0/files/Personal/Loans/previous-loans/mortgage_personal_purchase_ed69_eng.pdf>
-
-## PDF page 1
 
 AMERIABANK CJSC | 11RBD PL 72-03-98
 Edition 69
 Effective date: February 4, 2026
 
-### Retail Lending Terms and Conditions
+## Retail Lending Terms and Conditions
 (Home Mortgage Loan)¹
 
 Approved by Management Board Resolution # 08/1/01/14 as of February 4, 2014
 Current edition approved by resolution # 01/15/26 as of February 2, 2026
 
-### Home Purchase Loan (primary market)
+## Home Purchase Loan (primary market)
+
+¹These terms have been previously known as Retail Lending Terms and Conditions under code 11RBD PL 72-03-01. Some of the Bank documents may contain references to these terms and conditions under the former name and code.
+
+²Depending on the creditworthiness of the borrower, term of loan and LTV ratio, a higher or lower interest rate can be applied.
+
+³The annual percentage rate (APR) may differ from the above specified values if there is any or a few of the following factors:
+\- When the property insurance is obtained by the Bank at the customer’s request
+\- When the borrower selects differentiated or mixed form of loan repayment
+\- If there are deviations from the creditworthiness criteria approved under the internal regulations of the Bank
+\- If additional property is pledged as collateral
+\- If there are other deviations
+
+⁴ Attention! The adjustable nominal interest rate may be revised no more than twice a year. Furthermore, depending on the change of the adjustable nominal interest rate, the threshold above or below which the nominal rate cannot change is ±5%.
+
+⁵ The list of developers is determined by the Bank. If the developer is not included in the Bank's list, the terms of the loans for purchase of residential real estate from secondary market will apply.
 
 ### Home Purchase Loan (primary market)
-
 | Section | Item | AMD | USD | EUR |
 | --- | --- | --- | --- | --- |
-| 1. Purpose | 1.1. Purpose | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or<br>(ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or<br>(ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or<br>(ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) |
-| 2. Client’s personal details | 2.1. Eligible age of the client/co-borrower/guarantor | 2.1.1. 18-70 years old, provided that the borrower’s age at the time of expiry of the loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of the agreement it will not have exceeded 70.<br>If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. | 2.1.1. 18-70 years old, provided that the borrower’s age at the time of expiry of the loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of the agreement it will not have exceeded 70.<br>If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. | 2.1.1. 18-70 years old, provided that the borrower’s age at the time of expiry of the loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of the agreement it will not have exceeded 70.<br>If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. |
-| 2. Client’s personal details | 2.2. Residency | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia<br>For loans in foreign currency: individuals not considered residents of Armenia | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia<br>For loans in foreign currency: individuals not considered residents of Armenia | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia<br>For loans in foreign currency: individuals not considered residents of Armenia |
-| 3. Loan terms | 3.1. Currency | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR |
-| 3. Loan terms | 3.2. Minimum and maximum loan limits | 3.2.1. AMD 3,000,000 - AMD 150,000,000 | 3.2.2. USD 5,000 - USD 300,000 | 3.2.3. EUR 5,000 - EUR 300,000 |
-| 3. Loan terms | 3.3. Term (months) | 3.3.1. 60 | 3.3.1. 60 | 3.3.1. 60 |
-| 3. Loan terms | 3.4. Nominal annual interest rate² | 3.4.1. Fixed<br>13.5% | 3.4.2. Fixed<br>11.0% | 3.4.3. Fixed<br>8.5% |
-| 3. Loan terms | 3.5. Annual percentage rate (APR)³ | 3.5.1. Fixed<br>14.39-15.76% | 3.5.2. Fixed<br>11.6-13.56% | 3.5.3. Fixed<br>8.86-10.71% |
-| 3. Loan terms | 3.6. Term (months) | 3.6.1. 61-360 | 3.6.1. 61-360 | 3.6.1. 61-360 |
-| 3. Loan terms | 3.7. Nominal annual interest rate² | 3.7.1. Adjustable fixed⁴ (rate can be changed starting from the 37th month)<br>Fixed component 5.5% + variable component (base rate) | 3.7.2. Adjustable fixed⁴ (rate can be changed starting from the 37th month)<br>Fixed component 8% + variable component (base rate) | 3.7.3. Adjustable fixed⁴ (rate can be changed starting from the 37th month)<br>Fixed component 7% + variable component (base rate) |
-| 3. Loan terms | 3.8. Annual percentage rate (APR)³ | 3.8.1. Adjustable fixed (rate can be changed starting from the 37th month)<br>14.35-15.74% | 3.8.2. Adjustable fixed (rate can be changed starting from the 37th month)<br>10.47-12.39% | 3.8.3. Adjustable fixed (rate can be changed starting from the 37th month)<br>8.3-10.12% |
-| 3. Loan terms | 3.9. Other terms related to the interest rate | 3.9.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5% | 3.9.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5% | 3.9.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5% |
-
-## PDF page 2
+| \1. Purpose | 1.1. Purpose | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or<br>(ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or<br>(ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or<br>(ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) |
+| \2. Client’s personal details | 2.1. Eligible age of the client/co-borrower/guarantor | 2.1.1. 18-70 years old, provided that the borrower’s age at the time of expiry of the loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of the agreement it will not have exceeded 70.<br>If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. | 2.1.1. 18-70 years old, provided that the borrower’s age at the time of expiry of the loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of the agreement it will not have exceeded 70.<br>If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. | 2.1.1. 18-70 years old, provided that the borrower’s age at the time of expiry of the loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of the agreement it will not have exceeded 70.<br>If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. |
+| \2. Client’s personal details | 2.2. Residency | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia<br>For loans in foreign currency: individuals not considered residents of Armenia | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia<br>For loans in foreign currency: individuals not considered residents of Armenia | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia<br>For loans in foreign currency: individuals not considered residents of Armenia |
+| \3. Loan terms | 3.1. Currency | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR |
+| \3. Loan terms | 3.2. Minimum and maximum loan limits | 3.2.1. AMD 3,000,000 - AMD 150,000,000 | 3.2.2. USD 5,000 - USD 300,000 | 3.2.3. EUR 5,000 - EUR 300,000 |
+| \3. Loan terms | 3.3. Term (months) | 3.3.1. 60 | 3.3.1. 60 | 3.3.1. 60 |
+| \3. Loan terms | 3.4. Nominal annual interest rate² | 3.4.1. Fixed<br>13.5% | 3.4.2. Fixed<br>11.0% | 3.4.3. Fixed<br>8.5% |
+| \3. Loan terms | 3.5. Annual percentage rate (APR)³ | 3.5.1. Fixed<br>14.39-15.76% | 3.5.2. Fixed<br>11.6-13.56% | 3.5.3. Fixed<br>8.86-10.71% |
+| \3. Loan terms | 3.6. Term (months) | 3.6.1. 61-360 | 3.6.1. 61-360 | 3.6.1. 61-360 |
+| \3. Loan terms | 3.7. Nominal annual interest rate² | 3.7.1. Adjustable fixed⁴ (rate can be changed starting from the 37th month)<br>Fixed component 5.5% + variable component (base rate) | 3.7.2. Adjustable fixed⁴ (rate can be changed starting from the 37th month)<br>Fixed component 8% + variable component (base rate) | 3.7.3. Adjustable fixed⁴ (rate can be changed starting from the 37th month)<br>Fixed component 7% + variable component (base rate) |
+| \3. Loan terms | 3.8. Annual percentage rate (APR)³ | 3.8.1. Adjustable fixed (rate can be changed starting from the 37th month)<br>14.35-15.74% | 3.8.2. Adjustable fixed (rate can be changed starting from the 37th month)<br>10.47-12.39% | 3.8.3. Adjustable fixed (rate can be changed starting from the 37th month)<br>8.3-10.12% |
+| \3. Loan terms | 3.9. Other terms related to the interest rate | 3.9.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5% | 3.9.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5% | 3.9.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5% |
 
 ### Home Purchase Loan (primary market) (Continued)
-
 | Section | Item | Terms and Conditions |
 | --- | --- | --- |
-| 3. Loan terms | 3.9. Other terms related to the interest rate | 3.9.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%. |
-| 3. Loan terms | 3.9. Other terms related to the interest rate | 3.9.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%. |
-| 3. Loan terms | 3.9. Other terms related to the interest rate | 3.9.5. If the client prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds). |
-| 3. Loan terms | 3.9. Other terms related to the interest rate | 3.9.6. In case of other deviations, the applicable interest rate may be increased by 0.25%. |
-| 3. Loan terms | 3.10. Lump sum disbursement fee | 3.10.1. N/A |
-| 3. Loan terms | 3.11. Minimum down payment | 3.11.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.<br>3.11.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5% of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral. |
-| 3. Loan terms | 3.12. Manner of disbursement | 1. Lump sum<br>2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower. |
-| 3. Loan terms | 3.13. Cashing of the loan amount by the seller from his account with the Bank after loan disbursement (where applicable) | 3.13.1.<br>AMD: Free<br>Other currency: 0.5 % |
-| 4. Forms of loan repayment | 4.1. Repayment method | 4.1.1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest) |
-| 4. Forms of loan repayment | 4.1. Repayment method | 4.1.2. Differentiated (monthly repayment of equal portions of principal amount while interest accrues to outstanding loan and decreases each month) |
-| 4. Forms of loan repayment | 4.1. Repayment method | 4.1.3. Mixed (client may choose an individual repayment schedule based on seasonality of cash flows, provided that at least 5% of contractual loan amount is repaid each year; interest payable on monthly basis) |
-| 5. Security | 5.1. Eligible collateral | 5.1.1.<br>1. The loan is secured by the real estate being purchased. The Bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the Bank, as well as cash in the Bank or bonds issued by the Bank.<br>2. If the borrower wishes to purchase property under construction without registered certificate of title, the loan will be secured by other Armenia-based real estate to the reasonable satisfaction of the Bank.<br>3. If the borrower wishes to purchase property abroad, the loan will be secured by Armenia-based real estate to the reasonable satisfaction of the Bank. |
-
-## PDF page 3
+| \3. Loan terms | 3.9. Other terms related to the interest rate | 3.9.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%. |
+| \3. Loan terms | 3.9. Other terms related to the interest rate | 3.9.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%. |
+| \3. Loan terms | 3.9. Other terms related to the interest rate | 3.9.5. If the client prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds). |
+| \3. Loan terms | 3.9. Other terms related to the interest rate | 3.9.6. In case of other deviations, the applicable interest rate may be increased by 0.25%. |
+| \3. Loan terms | 3.10. Lump sum disbursement fee | 3.10.1. N/A |
+| \3. Loan terms | 3.11. Minimum down payment | 3.11.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.<br>3.11.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5% of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral. |
+| \3. Loan terms | 3.12. Manner of disbursement | \1. Lump sum<br>\2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower. |
+| \3. Loan terms | 3.13. Cashing of the loan amount by the seller from his account with the Bank after loan disbursement (where applicable) | 3.13.1.<br>AMD: Free<br>Other currency: 0.5 % |
+| \4. Forms of loan repayment | 4.1. Repayment method | 4.1.1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest) |
+| \4. Forms of loan repayment | 4.1. Repayment method | 4.1.2. Differentiated (monthly repayment of equal portions of principal amount while interest accrues to outstanding loan and decreases each month) |
+| \4. Forms of loan repayment | 4.1. Repayment method | 4.1.3. Mixed (client may choose an individual repayment schedule based on seasonality of cash flows, provided that at least 5% of contractual loan amount is repaid each year; interest payable on monthly basis) |
+| \5. Security | 5.1. Eligible collateral | 5.1.1.<br>\1. The loan is secured by the real estate being purchased. The Bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the Bank, as well as cash in the Bank or bonds issued by the Bank.<br>\2. If the borrower wishes to purchase property under construction without registered certificate of title, the loan will be secured by other Armenia-based real estate to the reasonable satisfaction of the Bank.<br>\3. If the borrower wishes to purchase property abroad, the loan will be secured by Armenia-based real estate to the reasonable satisfaction of the Bank. |
 
 ### Home Purchase Loan (primary market) (Continued)
-
 | Section | Item | Terms and Conditions |
 | --- | --- | --- |
-| 5. Security | 5.2. Loan-to-value (LTV) ratio | 5.2.1. The loan is issued:<br>1. For AMD loans with a term of 61-240 months: up to 90%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client,<br>For AMD loans with a term above 240 months: up to 80%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁶ reference provided to the client, unless otherwise determined by the Bank,<br>2. For foreign currency loans with a term of 61-240 months: up to 70%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client,<br>For foreign currency loans with a term above 240 months: up to 60%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client, unless otherwise determined by the Bank,<br>3. up to 100% of the value of cash in the Bank or bonds issued by the Bank.<br>4. In case of loans without creditworthiness assessment: up to 60%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client |
-| 5. Security | 5.3. Location of the real estate to be pledged | 5.3.1. Yerevan, regional centers of Armenia, towns where Ameriabank has branches, as well as Jrvezh, Arinj, Dzoraghbyur, Kasakh, Tsaghkadzor, Masis and Yeghvard<br>5.3.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children, also regional cities of Armenia not specified in clause 5.3.1 and particular rural settlements approved by the Republic of Armenia Government decree N 968-Լ as of May 14, 2020. |
-| 5. Security | 5.4. Appraisal of the collateral | 5.4.1.<br>1. No appraisal is required in case of acquisition of the right to purchase property from the developer. Pledge value is considered to be equal to the price specified in the developer's reference, unless otherwise determined by the Bank.<br>2. In case of acquisition of the title to the real estate from the developer, appraisal is performed by appraisal companies cooperating with the Bank. |
-| 5. Security | 5.5. Additional security | 5.5.1. The Bank may request guarantees of individuals and/or companies as additional security. |
-| 6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.1. The real estate being pledged is insured by the Bank in the following cases:<br>6.1.1.1. If at the time of registration of the title to the real estate and/or at the time of reappraisal, the market value of the property is over AMD 100 million (one hundred million); or<br>6.1.1.2. where the address of the pledged real estate is included in the list of properties published on the Bank’s website.<br><br>6.1.2. The Bank obtains insurance each year for the amount of the outstanding principal throughout the loan term if any of the above specified conditions is in place (in this case, the calculation of the interest rate also covers all the possible costs, including those associated with the insurance, where applicable). |
-| 7. Required documents | 7.1. Required documents | 7.1.1. Required documents filed together with the loan application<br>• Loan application<br>• ID (original)<br>• Certificate of ownership/purchase right of real estate to be purchased/pledged [copy]<br>• Other documents upon the Bank’s request<br><br>7.1.2. Documents required after pre-approval<br>• Proof of employment and/or other income |
-
-## PDF page 4
+| \5. Security | 5.2. Loan-to-value (LTV) ratio | 5.2.1. The loan is issued:<br>\1. For AMD loans with a term of 61-240 months: up to 90%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client,<br>For AMD loans with a term above 240 months: up to 80%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁶ reference provided to the client, unless otherwise determined by the Bank,<br>\2. For foreign currency loans with a term of 61-240 months: up to 70%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client,<br>For foreign currency loans with a term above 240 months: up to 60%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client, unless otherwise determined by the Bank,<br>\3. up to 100% of the value of cash in the Bank or bonds issued by the Bank.<br>\4. In case of loans without creditworthiness assessment: up to 60%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client |
+| \5. Security | 5.3. Location of the real estate to be pledged | 5.3.1. Yerevan, regional centers of Armenia, towns where Ameriabank has branches, as well as Jrvezh, Arinj, Dzoraghbyur, Kasakh, Tsaghkadzor, Masis and Yeghvard<br>5.3.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children, also regional cities of Armenia not specified in clause 5.3.1 and particular rural settlements approved by the Republic of Armenia Government decree N 968-Լ as of May 14, 2020. |
+| \5. Security | 5.4. Appraisal of the collateral | 5.4.1.<br>\1. No appraisal is required in case of acquisition of the right to purchase property from the developer. Pledge value is considered to be equal to the price specified in the developer's reference, unless otherwise determined by the Bank.<br>\2. In case of acquisition of the title to the real estate from the developer, appraisal is performed by appraisal companies cooperating with the Bank. |
+| \5. Security | 5.5. Additional security | 5.5.1. The Bank may request guarantees of individuals and/or companies as additional security. |
+| \6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.1. The real estate being pledged is insured by the Bank in the following cases:<br>6.1.1.1. If at the time of registration of the title to the real estate and/or at the time of reappraisal, the market value of the property is over AMD 100 million (one hundred million); or<br>6.1.1.2. where the address of the pledged real estate is included in the list of properties published on the Bank’s website.<br>6.1.2. The Bank obtains insurance each year for the amount of the outstanding principal throughout the loan term if any of the above specified conditions is in place (in this case, the calculation of the interest rate also covers all the possible costs, including those associated with the insurance, where applicable). |
+| \7. Required documents | 7.1. Required documents | 7.1.1. Required documents filed together with the loan application<br>• Loan application<br>• ID (original)<br>• Certificate of ownership/purchase right of real estate to be purchased/pledged \[copy\]<br>• Other documents upon the Bank’s request<br>7.1.2. Documents required after pre-approval<br>• Proof of employment and/or other income |
 
 ### Home Purchase Loan (primary market) (Continued)
-
 | Section | Item | Terms and Conditions |
 | --- | --- | --- |
-| 7. Required documents | 7.1. Required documents | • Marriage (divorce, spouse death) certificate (original)<br>• Certificate of title to real estate to be pledged (original)<br>• Other documents upon the Bank request<br><br>7.1.3. Documents required after loan approval<br>• Copies of bases of title to real estate (to be submitted upon the Bank’s request)<br>• IDs of owners of the property to be purchased/pledged (originals)<br>• Copies of marriage (divorce, spouse death) certificates of owners of the property to be pledged, to be presented if available<br>• Statement from the State Committee of Real Estate Cadaster on encumbrance of real estate (unified statement)<br>• Tax clearance certificate for the real estate<br>• Real estate insurance policy<br>• Documentary proof that the down payment was made in a non-cash manner (e.g.: original receipt, or, if paid electronically, a document showing that the electronic payment was confirmed). Such proof is not required if the payment was made from the accounts held with the Bank and the Bank specialist has exported the payment document from the system.<br>• Other documents upon the Bank’s request |
-| 8. Early repayment fee | 8.1. Early repayment fee | 8.1.1.<br>At any time during a contractual year the borrower can make an early repayment to the extent of outstanding principal amount of loan for that contractual year. A contractual year is each period of 12 months following the date of execution of credit agreement.<br>Where the amount of early repayment exceeds the specified limit, the following fees will be charged:<br>• Max 0.6% of early repayment, if made during the first year of the agreement<br>• Max 0.4% of early repayment, if made during the second year of the agreement<br>• Max 0.2% of early repayment, if made during the third year of the agreement |
-| 9. Late payment fines and penalties | 9.1. Late payment fines and penalties | 9.1.1. The interest rate specified in the loan agreement will continue to be applied to overdue loans.<br>Fine in the amount of 0.13% of overdue loan/interest for each overdue day |
-| 10. Other fees | 10.1. Other fees payable by the client | 10.1.1.<br>• Fee for unified statement from the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia<br>• Fees for notarization of pledge (real estate) and filing of the bank’s security interest under pledge agreement |
-
-> ¹These terms have been previously known as Retail Lending Terms and Conditions under code 11RBD PL 72-03-01. Some of the Bank documents may contain references to these terms and conditions under the former name and code.
-
-> ²Depending on the creditworthiness of the borrower, term of loan and LTV ratio, a higher or lower interest rate can be applied.
-
-> ³The annual percentage rate (APR) may differ from the above specified values if there is any or a few of the following factors:
-- When the property insurance is obtained by the Bank at the customer’s request
-- When the borrower selects differentiated or mixed form of loan repayment
-- If there are deviations from the creditworthiness criteria approved under the internal regulations of the Bank
-- If additional property is pledged as collateral
-- If there are other deviations
-
-> ⁴ Attention! The adjustable nominal interest rate may be revised no more than twice a year. Furthermore, depending on the change of the adjustable nominal interest rate, the threshold above or below which the nominal rate cannot change is ±5%.
-
-> ⁵ The list of developers is determined by the Bank. If the developer is not included in the Bank's list, the terms of the loans for purchase of residential real estate from secondary market will apply.
+| \7. Required documents | 7.1. Required documents | • Marriage (divorce, spouse death) certificate (original)<br>• Certificate of title to real estate to be pledged (original)<br>• Other documents upon the Bank request<br>7.1.3. Documents required after loan approval<br>• Copies of bases of title to real estate (to be submitted upon the Bank’s request)<br>• IDs of owners of the property to be purchased/pledged (originals)<br>• Copies of marriage (divorce, spouse death) certificates of owners of the property to be pledged, to be presented if available<br>• Statement from the State Committee of Real Estate Cadaster on encumbrance of real estate (unified statement)<br>• Tax clearance certificate for the real estate<br>• Real estate insurance policy<br>• Documentary proof that the down payment was made in a non-cash manner (e.g.: original receipt, or, if paid electronically, a document showing that the electronic payment was confirmed). Such proof is not required if the payment was made from the accounts held with the Bank and the Bank specialist has exported the payment document from the system.<br>• Other documents upon the Bank’s request |
+| \8. Early repayment fee | 8.1. Early repayment fee | 8.1.1.<br>At any time during a contractual year the borrower can make an early repayment to the extent of outstanding principal amount of loan for that contractual year. A contractual year is each period of 12 months following the date of execution of credit agreement.<br>Where the amount of early repayment exceeds the specified limit, the following fees will be charged:<br>• Max 0.6% of early repayment, if made during the first year of the agreement<br>• Max 0.4% of early repayment, if made during the second year of the agreement<br>• Max 0.2% of early repayment, if made during the third year of the agreement |
+| \9. Late payment fines and penalties | 9.1. Late payment fines and penalties | 9.1.1. The interest rate specified in the loan agreement will continue to be applied to overdue loans.<br>Fine in the amount of 0.13% of overdue loan/interest for each overdue day |
+| \10. Other fees | 10.1. Other fees payable by the client | 10.1.1.<br>• Fee for unified statement from the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia<br>• Fees for notarization of pledge (real estate) and filing of the bank’s security interest under pledge agreement |
```
