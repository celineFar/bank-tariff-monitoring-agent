# Semantic extraction audit

Product: **consumer_loan**  
Model: **gemini-3.7-flash**

Before Gemini extraction, a deterministic extraction planner groups requested fields (for example rates, fees, or eligibility), ranks accepted evidence by its source-discovery role, keywords, and authority precedence, and enforces configured item/character limits. It does not decide whether a tariff value is true and it does not use an LLM.

**NOT SENT TO SEMANTIC LLM** therefore means the evidence was accepted by source discovery but was not included in any bounded field packet after that deterministic ranking and size/count limiting. It was not rejected as false or irrelevant.

In the document overlays below, only exact quotations cited by successful `found` results are highlighted. Text that was inspected but not cited remains visually unchanged.

## Field outcomes

---

<a id="ex-010"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-010] product_name — EXTRACTED</strong></div>

```json
"Installment financing for product purchase and service provision"
```
---

<a id="ex-002"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-002] category — EXTRACTED</strong></div>

```json
"consumer_loan"
```
---

<a id="ex-011"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-011] purpose — EXTRACTED</strong></div>

```json
[
  "Purchasing products",
  "Service provision",
  "Acquisition of solar systems"
]
```
---

<a id="ex-009"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-009] loan_amount — EXTRACTED</strong></div>

```json
[
  {
    "conditions": [
      {
        "dimension": "currency",
        "value": "AMD"
      }
    ],
    "value": {
      "range": {
        "currency": "AMD",
        "max": 6000000.0,
        "min": 50000.0
      },
      "type": "absolute"
    }
  }
]
```
---

<a id="ex-008"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-008] interest_rate — EXTRACTED</strong></div>

```json
[
  {
    "conditions": [],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": 21.5,
      "min": 0.0,
      "rate_type": "fixed"
    }
  }
]
```
---

<a id="ex-005"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-005] effective_rate — EXTRACTED</strong></div>

```json
[
  {
    "conditions": [
      {
        "dimension": "purpose",
        "value": "purchase of goods and services"
      }
    ],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": 24.0,
      "min": 0.0,
      "rate_type": "unknown"
    }
  },
  {
    "conditions": [
      {
        "dimension": "purpose",
        "value": "purchase of solar panels and water heaters"
      }
    ],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": 17.0,
      "min": 0.0,
      "rate_type": "unknown"
    }
  }
]
```
---

<a id="ex-015"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-015] term — EXTRACTED</strong></div>

```json
[
  {
    "conditions": [
      {
        "dimension": "application_channel",
        "value": "seller's premises"
      },
      {
        "dimension": "purpose",
        "value": "purchasing products"
      }
    ],
    "value": {
      "max_months": 60,
      "min_months": 6
    }
  },
  {
    "conditions": [
      {
        "dimension": "application_channel",
        "value": "online remote consumer finance system"
      },
      {
        "dimension": "purpose",
        "value": "purchasing products"
      }
    ],
    "value": {
      "max_months": 36,
      "min_months": 6
    }
  },
  {
    "conditions": [
      {
        "dimension": "purpose",
        "value": "service provision"
      }
    ],
    "value": {
      "max_months": 24,
      "min_months": 6
    }
  },
  {
    "conditions": [
      {
        "dimension": "purpose",
        "value": "acquisition of solar systems"
      }
    ],
    "value": {
      "max_months": 120,
      "min_months": 6
    }
  }
]
```
---

<a id="ex-007"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-007] fees — EXTRACTED</strong></div>

```json
[
  {
    "description": "Monthly account service fee: As specified in the Cooperation Agreement between the Company and the Bank",
    "scope": "product",
    "amount": null,
    "currency": null,
    "rate_pct": null,
    "conditions": []
  },
  {
    "description": "Disbursement fee (lump-sum)/down payment: As specified in the Cooperation Agreement between the Company and the Bank",
    "scope": "product",
    "amount": null,
    "currency": null,
    "rate_pct": null,
    "conditions": []
  },
  {
    "description": "Fee for the service, payment of interest and other charges: in case of payment via the Bank’s remote banking system (no fee charged)",
    "scope": "product",
    "amount": 0.0,
    "currency": null,
    "rate_pct": null,
    "conditions": [
      {
        "dimension": "payment_channel",
        "operator": "eq",
        "value": "Bank's remote banking system"
      }
    ]
  },
  {
    "description": "Fee for the service, payment of interest and other charges: if paid via payment terminals and ATMs owned by the Bank (according to the Terms and Conditions of Transactions through Payment Terminals 11RBD/12CIB PL 72-16)",
    "scope": "general_loan_service",
    "amount": null,
    "currency": null,
    "rate_pct": null,
    "conditions": [
      {
        "dimension": "payment_channel",
        "operator": "eq",
        "value": "Payment terminals and ATMs owned by the Bank"
      }
    ]
  },
  {
    "description": "Fee for the service, payment of interest and other charges: if paid via payment terminals owned by other companies (according to the tariffs of the respective company)",
    "scope": "general_loan_service",
    "amount": null,
    "currency": null,
    "rate_pct": null,
    "conditions": [
      {
        "dimension": "payment_channel",
        "operator": "eq",
        "value": "Payment terminals owned by other companies"
      }
    ]
  },
  {
    "description": "Fee for the service, payment of interest and other charges: if paid at the Bank’s branches (according to Ameriabank CJSC Tariffs for Individuals 11RBD PL 72-01-01)",
    "scope": "general_loan_service",
    "amount": null,
    "currency": null,
    "rate_pct": null,
    "conditions": [
      {
        "dimension": "payment_channel",
        "operator": "eq",
        "value": "Bank branches"
      }
    ]
  }
]
```
Explanation: Extracted product-specific fees (monthly account service fee, disbursement fee, and remote repayment fee waiver) along with general service fees for repayment through branch/terminal channels.

---

<a id="ex-012"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-012] repayment — EXTRACTED</strong></div>

```json
[
  "Annuity (equal monthly installments consisting of a portion of debt and a portion of interest) where interest rate is applied",
  "Equal monthly installments schedule (equal monthly installments consisting of a portion of debt and a portion of fee) where a fee is applied"
]
```
Explanation: The product provides two repayment options: annuity installments when interest rate is applied, and an equal monthly installments schedule when a fee is applied.

---

<a id="ex-006"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-006] eligibility — EXTRACTED</strong></div>

```json
[
  "Citizens and non-citizens of Armenia who are resident in Armenia",
  "Eligible age: From 20 to 66 years inclusive"
]
```
Explanation: Eligible customers are citizens and non-citizens of Armenia residing in Armenia, aged 20 to 66 inclusive.

---

<a id="ex-014"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-014] residency_requirements — EXTRACTED</strong></div>

```json
[
  "Citizens and non-citizens of Armenia who are resident in Armenia",
  "Actually resident in the Republic of Armenia for 183 and more days during the tax year (Tax Code, Article 25)"
]
```
Explanation: Borrowers must be resident in Armenia, defined as being actually resident in the Republic of Armenia for 183 or more days during the tax year.

---

<a id="ex-001"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-001] age_requirements — EXTRACTED</strong></div>

```json
"From 20 to 66 years inclusive"
```
Explanation: Eligible age is explicitly documented as from 20 to 66 years inclusive.

---


<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>application_channel — NOT STATED</strong></div>

```json
null
```
Explanation: The provided evidence does not contain explicit base product application channel terms.

---


<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>special_conditions — NOT STATED</strong></div>

```json
null
```
Explanation: No specific special conditions for the base consumer finance product are documented in the provided evidence.

---

<a id="ex-013"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-013] required_documents — EXTRACTED</strong></div>

```json
[
  "Identity document",
  "Public services number (social card)",
  "Ownership certificate of the property (for solar panels/systems, upon request)",
  "Electricity and gas bills for the most recent 6 months (for solar panels/systems, upon request)"
]
```
Explanation: Official terms require an identity document and public services number (social card) across standard goods and service finance. For solar system financing, the bank may also request a property ownership certificate and the most recent 6 months of electricity and gas bills.

---

<a id="ex-003"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-003] collateral — EXTRACTED</strong></div>

```json
[
  "The purchased item serves as a collateral."
]
```
---


<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>income_verification_required — NOT STATED</strong></div>

```json
null
```
---


<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>creditworthiness_assessment_required — NOT STATED</strong></div>

```json
null
```
---

<a id="ex-004"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-004] credit_limit — EXTRACTED</strong></div>

```json
[
  {
    "type": "absolute",
    "range": {
      "min": 200000,
      "max": 6000000,
      "currency": "AMD"
    }
  }
]
```
---


<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>grace_period_days — NOT STATED</strong></div>

```json
null
```
---


<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>revolving — NOT STATED</strong></div>

```json
null
```
---


<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>linked_account_or_card — NOT STATED</strong></div>

```json
null
```
## Extraction overlay

### Label index

| Label | Field | Status |
|---|---|---|
| `EX-010` | `product_name` | `found` |
| `EX-002` | `category` | `found` |
| `EX-011` | `purpose` | `found` |
| `EX-009` | `loan_amount` | `found` |
| `EX-008` | `interest_rate` | `found` |
| `EX-005` | `effective_rate` | `found` |
| `EX-015` | `term` | `found` |
| `EX-007` | `fees` | `found` |
| `EX-012` | `repayment` | `found` |
| `EX-006` | `eligibility` | `found` |
| `EX-014` | `residency_requirements` | `found` |
| `EX-001` | `age_requirements` | `found` |
| `—` | `application_channel` | `not_stated` |
| `—` | `special_conditions` | `not_stated` |
| `EX-013` | `required_documents` | `found` |
| `EX-003` | `collateral` | `found` |
| `—` | `income_verification_required` | `not_stated` |
| `—` | `creditworthiness_assessment_required` | `not_stated` |
| `EX-004` | `credit_limit` | `found` |
| `—` | `grace_period_days` | `not_stated` |
| `—` | `revolving` | `not_stated` |
| `—` | `linked_account_or_card` | `not_stated` |

---

## Consumer Finance | Loans | Ameriabank

Source: <https://ameriabank.am/en/personal/loans/consumer-loans/consumer-finance>

## Consumer finance

Installment loans at the points of sale will make  
your shopping experience quick and hassle-free

We offer a quick and convenient option for purchasing household appliances, computer equipment, smartphones, mobile devices, furniture, and other goods for everyday life. Now, you can buy goods by obtaining an installment loan directly in the store ¹ just in a few minutes, without visiting the Bank.

### 50,000 - 6,000,000 AMD

<mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Loan amount<sup title="loan_amount"><a href="#ex-009">EX-009</a></sup></mark>

### 6 - 60 months

<mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Loan term<sup title="term"><a href="#ex-015">EX-015</a></sup></mark>

### 0 - 21.5%

<mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Annual nominal interest rate<sup title="interest_rate"><a href="#ex-008">EX-008</a></sup></mark>  
<mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Annual percentage rate: 0 - 24%<sup title="effective_rate"><a href="#ex-005">EX-005</a></sup></mark>

- 9-month interest-free consumer finance

- Consumer finance limit: AMD 50.000 – 6.000.000

- Finance term: 60 months

- Annual nominal interest rate: 0% during the first 9 months,
- 22.5% starting from the 10th month

- Annual effective interest rate: 0-24%

- Product type: The offer is valid for construction materials.

- Term of the campaign: 15/01/26 - 30/09/26, inclusive

For more details click  
here

All

Appliances

Furniture

Automobile industry

Healthcare

Trainings

Solar system

Travel services

Sports

Construction and heating

Other

### ZIGZAG

ZIGZAG LLC

### VEGA

VEGA WORLD LLC

### VLV

VI EL VI CENTER LLC

### NOR TUN

BARSIS LLC

### BEKO

ED-SPO LLC

### SOLARTEAM

«Solartim» LLC

### PRIME AUTO GROUP

«PRAYM AUTO GROUP» LLC

### AVARD COMPUTERS

«AVARDGEYMING» LLC

### NOTEBOOK CENTRE

«Praym Store» LLC

### MOB - X

GABRELYAN KNKUSH ARAMAISI IE

### META STORE

«Meta Store» LLC

### SOTKA

Varpetyan Hovhannes Hakobi IE

### SIM RACING CLUB

«Hovhannisyan Ara Arturi» IE

### TORNADO ELECTRONICS

Hovhannisyan Grigor Aghasu IE

### FON X

«Mikayelyan Artak Ashoti» IE

### ARTSAKH MOBILE

«Simonyan Erik Artemi» IE

### HT MOBILE

«Aramayis Badalyan» LLC

### MOBILE ZONE

«Fayn Shop» LLC

### TECHHOUSE

«Techhouse» LLC

### MOBILE GROUP

«Mobile Group.EY EM» LLC

### ICITY.AM

«Ay Siti» LLC

### IDEVICE

Harutyunyan Hayk Armeni IE

### DIGIHUB

«BEST ELECTRONICS» LLC

### ICASE

Markosyan Arman Kareni IE

### MOBILE TIME ELECTRONICS

ANAHIT MANDALYAN FRANTSIKI

### TECHNO HOUSE

«Techno House» LLC

### CLOUD 7

«7 Klaud» LLC

### MULTI WELLNESS

«Multi Uelnes» Center» LLC

### UNIQUE TRAVEL

«Yunik Trevl» LLC

### FOUR SEASONS YVN

«FOUR SEASONS EVN» LLC

### SHADE

«SHADE» LLC

### MONIKA FURNITURE

«PARG GROUP» LLC

### AR-GO KAHUYQ

«ALBERT GROUP» LLC

### CARPETS

VARDANYAN ARAYIK SASHIKI IE

### BEKO ASHTARAK

«DINSO» LLC

### BUILDING MATERIAL

«Bilding Material» LLC

### LEVVARD

«LEVVARD Group» LLC

### AKCENT

«Fyuchr Stayl» LLC

### MEGAVA

«MEGAVA» LLC

### Noy Energy

«NOYAVAN» LLC

### VIA NOVA TRAVEL

«Via Nova Travel» LLC

### IKEA Homplex

«ANTA» LLC

### LADY ZONE

«Leydi-Zon» LLC

### EUROBAZA

YUNIVERSAL PROJEKT LLC

### PC ELECTRONICS

PI-SI ELECTRONICS LLC

### VENUS

VENUS-EL LLC

### DECORA GROUP

DEKORA-GROUP LLC

### ELDORADO

ELMARKET LLC

### MOBILIFE

MOBILIFE LLC

### GSA ELECTRONICS

JI ES EY LLC

### BL

BI EL LLC

### OSKAR ELECTRONICS

OSKAR ELECTRONICS LLC

### DECOR

KHACHATRYAN ARTUR MAMIKONI IE

### Z-MIX

«TEKHNIKAT» LLC

### SOLARON

PROFPANEL LLC

### VERSAL

VERSAL GROUP LLC

### FREENERGY

FRINERJI LLC

### AUTO MAX

ARPANIV LLC

### ANI KAHUYQ

ANI MARKOSYAN MARTIKI IE

### ASHLEY HOMESTORE

INTERFUR LLC

### DAV KAHUYQ

KONSTANTIN GAVALJYAN TIGRANI IE

### KAHUYQ MALL

MK GROUP LLC

### ALL CELL

NRANE LLC

### SHTIGEN

SHTIGEN LLC

### LOUVRE

SARGSYAN NORAYR TRDATI IE

### FURNITURE WORLD

FURNITUREI ASHKHARH LLC

### R&amp;V COMFORT

KOMFORT R EV V LLC

### SHKAFF

HRASHK GROUP LLC

### VLV KAPAN

MAYDAV LLC

### VLV ARMAVIR

AGEVART LLC

### ARMALIS

«VUD HOM» LLC

### ARMALIS

SARDARYAN SAYAT SAMVELI IE

### BEKO APARAN

DSA LLC

### TSIATSAN

GAR GRIG LLC

### LEADER

STEPANYAN HMAYAK ONIKI IE

### ALEX DECOR

GEVORGYAN TIGRAN ALBERTI IE

### ECO STEP

DV INVEST JV LLC

### FULL HOUSE

FUL HOUSE MARKET LLC

### PLASMA ELECTRONICS

PLAZMA-VAN LLC

### SKILL AM

Z ES TOP LLC

### SUNNY CITY

RENYUABL KOKASYS KORPOREYSHN LLC

### NATURALGAS

BARSEGHYAN ARA SRAPIONI IE

### FURNITURE

VANMETAGHAR LLC

### BEST ELECTRONICS

HOVAKIMYAN ARAYIK NORIKI IE

### AR LEO

AR. LEO LLC

### OJAKH

EDGAR EV NAZELI LLC

### TOP FLOOR

TOP-TEKH LLC

### BEKO IJEVAN

KIRAKOSYAN ZOHRAB ROSTOMI IE

### EL HOUSE

M-ELECTRONICS LLC

### SHIN MALL

SHINMALL LLC

### AG MOBILE

AG MOBILE LLC

### CHRONOGRAPH

VOTCH VORLD LLC

### MK

GHAZARYAN MANUK ARMENAKI IE

### VELHOFF

VELHOFF LLC

### BABY TOYS

OTARYAN GARIK ISAHAKI IE

### L&amp;R

EGHIAZARYAN HAYK TORNIKI IE

### HRASHQ AYGI

HRASHK AYGI LLC

### GSS SOLAR

JIESES LLC

### MIX ELECTRONICS

KARAMYAN GOR SAMVELI IE

### BAROCCO

ARMAN MURADYAN ASHOTI IE

### TECHNO STORE

HRANT GRIGORYAN LLC

### LUYS

LAYTING GROUP LLC

### SALMAST

VIEMEYJ VUD LLC

### VESTA

PRITI UEY LLC

### GLOBAL BEAUTY

GLOBAL BYUTI LLC

### EUROSTAN-UYUT

EVROSTAN-UYUT LLC

### ECO VILLE

EKOVIL LLC

### MULTI SOLAR

MULTI SOLAR LLC

### VOLODYA

KALASHYAN VOLODYA ABBASI IE

### TSIATSAN

NAREK HOVSEPYAN BARKHUDARI IE

### KAKADU

ALEKSANYAN GARNIK IE

### BEST ALAVERDI

KARAPETYAN ARMEN ROBERTI IE

### SEVAN KAHUYQ

KHACHATRYAN MERI ARTAKI IE

### OHM ENERGY

DI OHM ENERGY LLC

### ROYAL STAR

ROYAL STAR LLC

### ORANGE FITNESS

KINETIK CJSC

### ICE WATCH

VIELEY IMPORTS LLC

### KAERCHER

KERKHER LLC

### DUBAI

MAKSIM GIKINYAN OHANI IE

### VESTA PLUS

HAYR EV ORDI BEKNAZARYANNER LLC

### LIMA ELECTRONICS

VARDANYAN NELI ROBERTI IE

### JYSK

HOMBEYS LLC

### EIFEL

STALKER LLC

### BEKO ARTASHAT - GSA ELECTRONICS

EMGE LLC

### AQUATEK, KLAIK

VALENSIA JV LLC

### TERMO-AR

TERMO—AR LLC

### ART GLOBAL

ART GLOBAL LLC

### R&amp;R

GALSTYAN MUSHEGH RAFIKI IE

### LEV-VAG

KHACHATRYAN VAHAGN KORYUNI IE

### LEV-VAG

LEV-VAG LLC

### ELITE SHINANYUT

ASLANYANNER&#x27; LLC

### NOR EJ

ANDREASYAN GARIK VARDANI IE

### R&amp;G, S&amp;G

GEVORGYAN KHACHATUR SHAVARSHI IE

### ANIVNERI ASHKHARH

MARSHAL LEND LLC

### VLV ECHMIATSIN

KISVEL LLC

### SHEN TUN

ARGAM AVETISYAN VARUZHANI IE

### SOLAR.AM

SOLAR.AM LLC

### VESTA SEVAN

GAGIK KARAPETYAN LLC

### BEAUTY GARDEN

MOVSISYAN MISAK MKRTCHI IE

### ARMADA MALL

VARDAN SAMVELYAN AMRAYU IE

### FABRICA FURNITURE

ALIK KHACHATRYAN VACHAGANI IE

### PC ELECTRONICS / ASHTARAK

MAY PI-SI ELECTRONICS LLC

### SOLAR CENTRE

SOLAR TSENTR LLC

### GAMMA FURNITURE

DAVIT GAVALJYAN TIGRANI IE

### THE LITTLE PRINCE

ARIANA 17 LLC

### TECHNO EL

TECHNO EL LLC

### SUNMODE

«ARMTREYDKOMPANI» LLC

### OJAKH

ISRAYELYAN LLC

### SHEN TUN / ABOVYAN

PATUHAN EYEM LLC

### MELISA FURNITURE

OPYAN EGHBAYRNER LLC

### VIVA ELECTRONICS

NAR-AV LLC

### SOLAR HOME

SOLAR HOM KONSALTING SERVICE LLC

### UYUT

UYUT CENTER LLC

### FURNITURE

KRISTINE AVANESYAN VOLODYAYI IE

### TAKE AWAY

TEYK YVEY LLC

### WINNER SOLAR

ARMEN-MAR LLC

### MANANA TECHNOLOGY

MANANA GREYN LLC

### VARPET

REVANSHSHIN LLC

### SOLARA

SOLARA LLC

### TVT

IMPEKS LLC

### GOLDSHIN

GOLDSHIN LLC

### MAX SHIN

MAKS SHIN LLC

### YERAZ KIDS CENTER

NAREKATSI HIBOKRAT LLC

### YERAZ KIDS CENTER

SAN LAZZARO LLC

### AXER

AKSER LLC

### VAHE ELECTRONICS

VAHE ELECTRONICS LLC

### VOLTA

VOLTA - YU LLC

### NOR &amp; MAR

NORAYR GEVORGYAN ROBERTI IE

### KERAMA MARAZZI

LIA-KAF LLC

### BRAINSKILLS

BREYNSKILS LLC

### ARDATECH

ARDATEK LLC

### IMOBILE

ANDRANIK TASHCHYAN SAMVELI IE

### INTERIER GROUP

INTERIER GROUP LLC

### MAGUS HOME

MAGUS HOM LLC

### RV COMPUTERS

LILIT ATANESYAN MIRANI IE

### L MOBILE

KHACHATRYAN LEVON VARDANI IE

### PRODECOR

PRODEKOR LLC

### UCOM

YUKOM CJSC

### RAY ENERGY

AYTI PARK BNAKELI HAMALIR LLC

### ARSTILBEKO

DAV-ART LLC

### DOMEN GROUP

DOMEN GROUP LLC

### MAZDA

SKAY MOTORS LLC

### MG

ENERGY MOTORS LLC

### SUZUKI

MAGYAR AUTO LLC

### QVANT TOUR

KVANT LLC

### EXTERIOR

EKSTERIER GROUP LLC

### SHELBY TOUR

SHELBI LLC

### CASTELO

ES.AY.ES SHELBI MOTORS LLC

### COMPUTEX

DANIELYANTS KHACHIK IE

### M - SHIN

MDM LLC

### MOBILE SERVICE

RAFAYEL BARSEGHYAN LEVONI IE

### KAHUYQ.AM

ARAM KARAPETYAN HARUTYUNI IE

### ECO COMFORT

EKO KOMFORT LLC

### BEKO EJMIATSIN

BABAYAN ZINAIDA VAHRAMI IE

### MIX MOBILE

TIGRAN MKHITARYAN MKHITARI IE

### ALASHKERT

HAYKAZ VARDANYAN MAKSIMI IE

### GR GROUP

ZET-PROFIL LLC

### HONDA

GRAND MOTORS LLC

### AQUA SYSTEM

MARI EV GEV LLC

### ISPACE

EY ES BI SI LLC

### ALLO STORE

ZHORA GRIGORYAN FELIKSI IE

### MOBO

ASYA DALLAKYAN HENRIKI IE

### EVAN

EVAN LLC

### FURNITURE

ARTAK GALSTYAN LEVONI IE

### UNITED TECHNICAL SERVICE

YUNAYTED TEKHNIKAL SERVICE LLC

### AR.LEO GROUP

AR. LEO GROUP LLC

### IBOLIT

MOBIGO LLC

### RED STORE

NOUTBUK STORE LLC

### JAHER.AM

AVETIK HARUTYUNYAN GAGIKI IE

### VIP MOBILE

ARTYOM AFRIKYAN MAMIKONI IE

### AS SOLAR

ARSIM GROUP LLC

### 3D PLANET

LIFE MOBILE LLC

### ARMEN MUSIC

ARMEN HARUTYUNYAN ASHOTI IE

### AR-GO KAHUYQ

VACHAGAN HAKOBYAN YURII IE

### Q TERMINAL

KYU TERMINAL LLC

### BELLA CASA, HOME DECOR

PENOTECHS LLC

### TECHNO EL

TECHNOMIKS LLC

### NOVACOLOR

EFBI GROUP LLC

### MOBILE CITY

KAREN GHARIBYAN ROBERTI IE

### BEKO ABOVYAN

HOM MARKET LLC

### V.T. MOBILE

ASHIK VARDANYAN VARDANI IE

### MY MOBI

DAVIT ZAKARYAN MHERI IE

### LOREST CLINIC

LOREST LLC

### LOREZZI

LORETSTSI LLC

### T AND L

TIGRAN BAZOYAN ARTURI IE

### HIKVISON GSS

LYOVA KIRAKOSYAN TSOLAKI IE

### ICENTRE

TECHNOPLAST LLC

### REZON YEREVAN

REZON LLC

### ACCORD

SARGIS EV DAVIT ASLANYANNER LLC

### BOGART

I.T.K.-RUS LLC

### VS MOBILE

VI ES MOBILE LLC

### INTERMALL

INTERMALL LLC

### INEX

STEPANYAN ROBERT HAMBARDZUMI IE

### HILCO

HILKO LLC

### MY TOY

MAYTOY LLC

### 7 WAYS TOUR

VARDAN HAKOBYAN LYUDVIGI IE

### MY YEREVAN MOBILE

VAGNER LLC

### NARDOS SHINANYUT

GEVORGYAN GAGIK ARAMI IE

### VN MOBILE

BALABEKYAN VAZGEN EMILI IE

### SMART WAVE

SMARTVEYV LLC

### DESIGNO HOME

HASMIK KHACHATRYAN VACHENI IE

### ANIVNER - ANVAHETSER

MURADYAN SARGIS ARKADII IE

### WOOD LAND

AROGHJSPASRKUM LLC

### PRESTIGE FURNITURE

DAYANTS LLC

### MARIA KAHUYQ

GYULUMYAN LEVON SERGEYI IE

### SHATEN KAHUYQ

JULIETTA ARMAGHANYAN RAFIKI IE

### MOBILE CITY

DUSTR EMMA LLC

### SCOOTER CITY

GAGIK SUKIASYAN SARGSI IE

### TIME ARMENIA

TAYMLES LLC

### SKY AND MORE

SKAY YND MOR LLC

### ANY WISH TOUR

ENI VISH LLC

### MOBILE HOUSE

MOBILE LUP LLC

### ARMENIAN CODE ACADEMY

BUTKAMP LLC

### HOMI, BAKER

EYJI GROUP LLC

### ANIE TRAVEL

ANI TRAVEL LLC

### MAMAS AND PAPAS

DAVMAR LLC

### GAOS FURNITURE

RICHATO LLC

### AVARD COMPUTERS

AVARD LLC

### ZINVORI TUN

ZINVORI TUN BHK

### GEKA MOBILE

GEKA MOBILE LLC

### HAK AND GAG

GAGIK YAZHYAN SURENI IE

### LORE TRAVEL

LORE TRAVEL LLC

### BASRA

MIRZOYANS LLC

### EXRADE

EKSREYD LLC

### ORIGIN STORE

OLLA LLC

### MOBILE MARKET

VAHAN BABAJANYAN MISHAYI IE

### ARMALIS

VARDKES HARUTYUNYAN KARENI IE

### LVN

VARDANYAN ARTAK RUBIKI IE

### GRANIT CITY

GRANIT SITI LLC

### CONCERN-ENERGOMASH

KONTSERN-ENERGOMASH CJSC

### ISTYLE

NEKO LLC

### STYLE STUDIO

GRIGOR SHABOYAN IE

### GALLERIA

ARAKELYAN ANAHIT MIKHAYELI IE

### ARMLED

ARMLED LLC

### DECOSTA

VAMAR GROUP LLC

### ZMIX ELECTRONICS

LUSINE KARAPETYAN MIASNIKI IE

### VENLO

VENLO SHOP LLC

### SEKO

SAMVEL SEKOYAN MKRTCHI IE

### 33 TOUR

NARMAR GROUP LLC

### MOBI LINE

DAIRMANJYAN HAYKANUSH HARUTYUNI IE

### GORTSUP ACADEMY

BIZNESI EV KARIERAYI ACADEMY LLC

### MTECH COMPUTERS

MTEKH LLC

### ANDRANIK GILIKYAN ANVADOGHER

ANDRANIK GILIKYAN VARDANI IE

### INTERMALL FURNITURE

INTERMALL FRNICHR LLC

### DOMUS

DOMUS CJSC

### VEG FURNITURE

VEG FURNITURE LLC

### MEGA ELECTRONICS

MEGA ELEKTRONIKA LLC

### NEXT

NEKST ELEKTRONIKKS LLC

### ART COMPANY

ART KOMPANI LLC

### KLAIK

VALENSIA JV LLC

### MILANO FURNITURE

LILIT HUNANYAN IE

### PIXEL

PIKSELS LLC

### IQ MOBILE

TECHNOAM LLC

### TAPIK

TATEVIK KHORENI MKRTCHYAN IE

### MK LUXURY FURNITURE

RUM 99 LLC

### «MOBILE CENTER»

MOBILE CENTER ART LLC

### VLV GYUMRI

KHNKOYANNER LLC

### APP ZONE

TECHNOZON 24 LLC

### MSM PROFF

PS VUD LLC

### SMARTPHON

VAN IN LLC

### LIKE MOBILE

ANZHELIKA TER-NERSESYAN IE

### ICASE

AYKES LLC

### ARAGARTS SPORT

APARANI ARAGATS LLC

### SMART SOLUTIONS

SMART SOLUSHNS LLC

### MERI-KRIST

MERI-KRIST LLC

### HDM SHTRIKH

HDM SHTRIKH LLC

### TOUCH-MASTER

TOCH-MASTER LLC

### BANGI TOUR

BANGI LLC

### VARIO

TONIK ALFATANYAN SURENI IE

### MY MOBILE

PAYTSAR LAZRYAN ANDRANIKI IE

### DOM STROY

GHSG GROUP LLC

### IBOLIT

MS TREYDING LLC

### DUSON

PROMAS LLC

### MOBILE HOME

MIKAYEL ISKANDARYAN DAVITI IE

### BARON FURNITURE

TIGRAN MIKAYELYAN SARGSI IE

### ISERIES

BAGRAT HARUTYUNYAN SURENI IE

### BEST SMILE

BEST SMAYL LLC

### LA SOLAR RETAIL

ELEY SOLAR RETAIL LLC

### ARI MOBILE

MISHA MURADYAN RUBENI IE

### EAGLE

ROMAN DADAYAN TOLIKI IE

### VIP TRAVEL

VIAYPI TRAVEL LLC

### ZAINI CENTER

DZAYNI CENTER LLC

### IDEAL HAMAKARG

NORK HOM RETAIL LLC

### MOBILE CITY

GALOYAN STEPAN SEROBI IE

### MY NOTEBOOK

ARM-ARM GROUP LLC

### IDEAL STORE

ARSHAK HAMBARDZUMYAN BORISI IE

### SELFIE MOBILE

SELFI GROUP LLC

### MASTER MOBILE

BALABEKYAN MKHITAR ARSENI IE

### V AND V

VI YND VI ELECTRONICS LLC

### RUBEN STORE / ELF DECOR

RUBEN EV EGHBAYRNER LLC

### IBOLIT

TEK TITANS LLC

### IDROID

MARGARYAN SPARTAK KHACHIKI IE

### MODERN KAHUYQ

MODERN FURNITURE LLC

### SOLID HOUSE

SOLID HOUSE LLC

### AS MOBILE

LUSINE SEYRANYAN SAMVELI IE

### PROLIFE

GYMAKSI LLC

### QYUBIT

KYUBIT LLC

### COMPSTORE

SERYOZHA HARUTYUNYAN SAMVELI IE

### BECO NEW

E YND S 90 LLC

### TEAM TELECOM

TELEKOM ARMENIA OJSC

### NOUT.AM

NOUT.AM LLC

### VEGA SOLAR

VEGA WORLD LLC

### OLYMPAVAN

OLIMPAVAN LLC

### OHANYAN

OHANYAN SASUN VLADIMIRI IE

### REVEL TOUR

REVEL TUR LLC

### ELDORADO GYUMRI

PAHEST ELECTRONICS LLC

### PETAK

STEPANYAN KAREN SAHAKI IE

### SHIN COMFORT

VOLONTE LLC

### COMFAREA

EVROIMPORT LLC

### HVAC

EYCH VI EY SI GROUP LLC

### H&amp;H FURNITURE

KOSTANYAN HENRIK LYOVAYI IE

### Homplex mall

HOMPLEKS HIPER MALL LLC

### NET-X SYSTEMS

AY TI ES GROUP LLC

### DERAR FURNITURE

ARDER LLC

### FINE MOBILE

SLAVANA LLC

### ELEMENT

«M.M. ELECTRONICS» LLC

### EVAN

GHAZARYAN SARIBEK ARMENAKI IE

### PC ELECTRONICS

«LEAMAYA» LLC

### BEST MOBILE

ARMINE ADOYAN ARTURI IE

### LIFENET

«Life Electronics» LLC

### PROMOBILE

«Pro 555» LLC

### MOBITIME

VARDEVANYAN HAYK TOMIKI IE

### IP MOBILE

«Esayan KHachatur Vardani» IE

### ARGAVAND KAHUYQ

«A-D Furniture» LLC

### YOUR MOBILE

«Davit Vardanyan LLC

### BUYLAPTOP

«LAPTOPSTORE» LLC

### NAVASARDYAN ASHOT KARLENI

«NAVASARDYAN ASHOT KARLENI» IE

### I CELL

GHaribyan Ashot Lyudvigi IE

### MEKSTEP

«ZHAMANAKAKITS MASNAGITUTYUNNERI ACADEMY» LLC

### XOXANJ

Arsen Asatryan Rafiki IE

### TERMOSHIN

«Termoshin» LLC

### Abach Barbershop

«Abach» LLC

### CARRIX

«MAY BID» LLC

### LEMON DESIGN

«Lemon Design LLC

### PILATESS HOUSE

«FORM» LLC

### SAGHOYAN VARDAN ONIKI IE

Saghoyan Vardan Oniki IE

### VANLUXE

«VANLYUKS» LLC

### SOLAR HOLDING

«SOLAR HOLDING» LLC

### ISHOP

«AYSHOP STORE LLC

### THE GYM

«DY GYM» LLC

### RA SOLAR

«RA SOLAR» LLC

### IP MOBILE

VARZHAPETYAN PETIK SEDRAKI IE

### GEVORGYAN ABEL SMBATI IE

GEVORGYAN ABEL SMBATI IE

### PRIME ENERGY

«Prime Tek» LLC

### ARMENIAN HELICOPTERS

«ARMENIAN HELICOPTERS»

### GYM KIDS

«Gym Kids» LLC

### ARMAT ACADEMY

KARAMYAN YULIYA SURENI IE

### MED SHOP

«MED SHOP» LLC

### Pro sounds and light

«PRO-DZAYN EV LUYS» LLC

### ABRICO TRAVEL

«Destineyshn Travel Group» LLC

### ELUNA DENTAL

Gasparyan Ara SHurayi IE

### PROFSHIN

«PROFSHIN MARKET» LLC

### GREEN OPTION

«GRIN OPSHON» LLC

### TITAN GYM

«TITAN GYM» LLC

### ART GYM

«ART GYM» LLC

### PULS FIT

«PULS FIT» LLC

### ISHOP

HOVHANNISYAN SEYRAN SAMVELI IE

### HILLS

«Zorakhach» LLC

### ISMART

HUNANYAN KAREN LYOVAYI IE

### MULTI SOLAR

«SOLAR MULTI SERVICE» LLC

### RESET

«Avrora Health» LLC

### TRIP FEST

«TRIPFEST» LLC

### YEPREMYAN ARMAN ARAYIKI IE

EPREMYAN ARMAN ARAYIKI IE

### NEW MOBILE

Tonoyan Ani Vachagani IE

### TIRES / RIMS

«Vardanyan Nerses» LLC

### FAST ENERGY

«Fast Energy Systems» LLC

### DOMMI

Baghramyan Vardan Hakobi IE

- FAQ

- <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Purchasing products<sup title="purpose"><a href="#ex-011">EX-011</a></sup></mark>

- <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Service provision<sup title="purpose"><a href="#ex-011">EX-011</a></sup></mark>

- <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Acquisition of solar systems<sup title="purpose"><a href="#ex-011">EX-011</a></sup></mark>

- Payment methods

- Credit history and score

- Useful information

- Previous terms

What documents are needed to apply for an installment purchase?

To make a purchase on installment, take your identification document and social card or identification card with you when going to the store.

<mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">What payment methods can I use to repay the loan for a purchase made on installment?<sup title="category"><a href="#ex-002">EX-002</a></sup></mark>

After making a purchase on installment through Ameriabank, you can make regular repayments and other relevant payments using the most convenient methods for you: via payment terminals, money transfer from other banks, at our bank branches, and of course through Ameriabank’s online system on the Bank’s website.

Who can use the offered installment option?

Installment financing is available for resident individuals aged 20 to 66, both with and without citizenship of the Republic of Armenia.

What products can I purchase through installment?

Products eligible for installment financing include household and computer equipment, smartphones, solar systems, furniture, and more.

How is the payable amount transferred in case of an installment purchase?

The approved installment financing amount is transferred to the store in non-cash form based on your instruction as stipulated in the contract.

How is the financing decision made?

The decision on installment financing, the maximum loan amount, as well as the grounds for rejection, are determined through assessment of the customer&#x27;s creditworthiness.

Grounds for rejecting installment financing may include:

a) poor credit history,

b) unreliable information provided.

Can I cancel the installment?

Yes, within 7 (seven) working days (unless a longer period is specified in the contract), you can cancel the provided financing without any justification by unilaterally terminating the contract.

In that case, the buyer is obliged to pay the lender interest for the use of the credit amount, which is calculated based on the annual effective interest rate specified in the credit agreement.

No other compensation is provided for termination of the financing contract.

### Purchasing products

| Section | Item | Terms |
| --- | --- | --- |
| Customer’s personal details | Eligible age | <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">From 20 to 66 years inclusive<sup title="age_requirements, eligibility"><a href="#ex-001">EX-001</a> <a href="#ex-006">EX-006</a></sup></mark> |
| Customer’s personal details | Customer | <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Citizens and non-citizens of Armenia who are resident in Armenia ¹<sup title="eligibility, residency_requirements"><a href="#ex-006">EX-006</a> <a href="#ex-014">EX-014</a></sup></mark> |
| Terms of finance | Currency | AMD |
| Terms of finance | Finance limit | If applying at the seller’s premises (hereinafter “the Company”)<br>Mobile phone/computer equipment: AMD 50,000 - AMD 1,000,000<br>Household appliances: AMD 50,000 - AMD 3,600,000<br>Furniture, construction materials, home improvement products and heating systems: AMD 50,000 - AMD 6,000,000<br>Household items, spare parts for cars and other goods: AMD 50,000 - AMD 2,400,000<br>If applying online via the remote consumer finance system of the Bank (irrespective of the product): AMD 50,000 - AMD 1,500,000 |
| Terms of finance | Term (months) | <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">If applying at the Company&#x27;s premises - 6-60. A term exceeding 48 months may be set only in case of furniture, construction materials, home improvement products and heating systems.<br>If applying online via the remote consumer finance system of the Bank (irrespective of the product): 6-36 months<sup title="term"><a href="#ex-015">EX-015</a></sup></mark> |
| Terms of finance | Nominal annual interest rate | Fixed |
| Terms of finance | Nominal annual interest rate | As specified in the Cooperation Agreement between the Company and the Bank |
| Terms of finance | Monthly account service fee | As specified in the Cooperation Agreement between the Company and the Bank |
| Terms of finance | Disbursement fee (lump-sum)/down payment | As specified in the Cooperation Agreement between the Company and the Bank |
| Repayment methods | Repayment method | <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">1. Annuity (equal monthly installments consisting of a portion of debt and a portion of interest) where interest rate is applied<br>2. Equal monthly installments schedule (equal monthly installments consisting of a portion of debt and a portion of fee) where a fee is applied<sup title="repayment"><a href="#ex-012">EX-012</a></sup></mark> |
| Security | Eligible collateral | <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">The purchased item serves as a collateral.<sup title="collateral"><a href="#ex-003">EX-003</a></sup></mark> |
| Security | Maximum LTV ratio | 100% |
| Required documents | Documents | • Identity document<br>• Public services number (social card) |
| Fines and penalties | Late payment fines and penalties (principal and interest) | In case of breach of the due date under the agreement, the Client shall pay to the Bank a fine<br>• In the amount of 0.13% of overdue amount and interest for each day of delay<br>• No fines and penalties are applied in case of prepayment. |
| Fee for the service, payment of interest and other charges | In case of payment via the Bank’s remote banking system | No fee is charged |
| Fee for the service, payment of interest and other charges | If paid via payment terminals and ATMs owned by the Bank | According to the Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16) ² |
| Fee for the service, payment of interest and other charges | If paid via payment terminals owned by other companies | According to the tariffs of the respective company |
| Fee for the service, payment of interest and other charges | If paid at the Bank’s branches | According to Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01) ³ . |
| Other fees | Payable by the Company | As specified in the Cooperation Agreement between the Company and the Bank |
| Coverage | Coverage | Republic of Armenia |

> <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Individuals resident in Armenia (hereinafter referred to as “resident individuals”) are those individuals who have been actually resident in the Republic of Armenia for 183 and more days during the tax year (Tax Code, Article 25).<sup title="residency_requirements"><a href="#ex-014">EX-014</a></sup></mark>

> Ameriabank CJSC Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16), approved by Management Board Resolution # 01/110/15 as of September 4, 2015). Available at https://ameriabank.am/useful-links.

> Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01, approved by Management Board Resolution # 03/59/15 as of May 27, 2015). Available at https://ameriabank.am/useful-links.

**Row-level citation labels:**

- `t1:row:5`: EX-008 cites combined row evidence; the exact quote could not be localized to one cell.
- `t1:row:7`: EX-007 cites combined row evidence; the exact quote could not be localized to one cell.
- `t1:row:8`: EX-007 cites combined row evidence; the exact quote could not be localized to one cell.
- `t1:row:12`: EX-013 cites combined row evidence; the exact quote could not be localized to one cell.
- `t1:row:16`: EX-007 cites combined row evidence; the exact quote could not be localized to one cell.
- `t1:row:17`: EX-007 cites combined row evidence; the exact quote could not be localized to one cell.
- `t1:row:18`: EX-007 cites combined row evidence; the exact quote could not be localized to one cell.
- `t1:row:19`: EX-007 cites combined row evidence; the exact quote could not be localized to one cell.

### Service provision

| Section | Item | Terms |
| --- | --- | --- |
| Customer’s personal details | Eligible age | From 20 to 66 years inclusive |
| Customer’s personal details | Customer | Citizens and non-citizens of Armenia who are resident in Armenia ¹ |
| Terms of finance | Currency | AMD |
| Terms of finance | Finance limit | If applying at the service provider&#x27;s premises (hereinafter “the Company”):<br>Minimum: AMD 50,000<br>Maximum: AMD 1,800,000<br>If applying via remote consumer finance system of the Bank:<br>Minimum: AMD 50,000<br>Maximum: AMD 1,500,000 |
| Terms of finance | Term (months) | <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">If applying at the Company&#x27;s premises or via remote consumer finance system of the Bank: 6-24<sup title="term"><a href="#ex-015">EX-015</a></sup></mark> |
| Terms of finance | Nominal annual interest rate | Fixed |
| Terms of finance | Nominal annual interest rate | As specified in the Cooperation Agreement between the Company and the Bank |
| Terms of finance | Monthly account service fee | As specified in the Cooperation Agreement between the Company and the Bank |
| Terms of finance | Disbursement fee (lump-sum)/down payment | As specified in the Cooperation Agreement between the Company and the Bank |
| Repayment methods | Repayment method | 1. Annuity (equal monthly installments consisting of a portion of debt and a portion of interest) where interest rate is applied<br>2. Equal monthly installments schedule (equal monthly installments consisting of a portion of debt and a portion of fee) where a fee is applied. |
| Required documents | Documents | • Identity document<br>• Public services number (social card) |
| Fines and penalties | Late payment fines and penalties (principal and interest) | In case of breach of the due date under the agreement, the Client shall pay to the Bank a fine<br>- In the amount of 0.13% of overdue amount and interest for each day of delay<br>- No fines and penalties are applied in case of prepayment. |
| Fee for the service, payment of interest and other charges | In case of payment via the Bank’s remote banking system | No fee is charged |
| Fee for the service, payment of interest and other charges | If paid via payment terminals and ATMs owned by the Bank | According to the Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16) ² |
| Fee for the service, payment of interest and other charges | In case of payments via payment terminals owned by other companies | According to the tariffs of the respective company |
| Fee for the service, payment of interest and other charges | If paid at the Bank’s branches | According to Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01) ³ . |
| Other fees | Payable by the Company | As specified in the Cooperation Agreement between the Company and the Bank |
| Coverage | Coverage | Republic of Armenia |

> Individuals resident in Armenia (hereinafter referred to as “resident individuals”) are those individuals who have been actually resident in the Republic of Armenia for 183 and more days during the tax year (Tax Code, Article 25).

> Ameriabank CJSC Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16), approved by Management Board Resolution # 01/110/15 as of September 4, 2015). Available at https://ameriabank.am/useful-links.

> Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01, approved by Management Board Resolution # 03/59/15 as of May 27, 2015). Available at https://ameriabank.am/useful-links.

### Acquisition of solar systems

| Section | Item | Terms |
| --- | --- | --- |
| Customer’s personal details | Eligible age | From 20 to 66 years inclusive |
| Customer’s personal details | Customer | Citizens and non-citizens of Armenia who are resident in Armenia ¹ |
| Terms of finance | Currency | AMD |
| Terms of finance | Credit limit | <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Minimum: AMD 200,000<br>Maximum: AMD 6,000,000<sup title="credit_limit"><a href="#ex-004">EX-004</a></sup></mark> |
| Terms of finance | Term (months) | <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">6-120<sup title="term"><a href="#ex-015">EX-015</a></sup></mark> |
| Terms of finance | Nominal annual interest rate | Fixed |
| Terms of finance | Nominal annual interest rate | As specified in the Cooperation Agreement between the company selling solar panels/water heating systems (hereinafter “the Company”) and the Bank |
| Terms of finance | Monthly account service fee | As specified in the Cooperation Agreement between the Company and the Bank |
| Terms of finance | Disbursement fee (lump-sum)/down payment | As specified in the Cooperation Agreement between the Company and the Bank |
| Repayment methods | Repayment method | 1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest) where interest rate is applied<br>2. Equal monthly installments schedule (equal monthly installments consisting of a portion of loan and a portion of fee) where a fee is applied. |
| Security | Eligible collateral | <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">The purchased item serves as a collateral.<sup title="collateral"><a href="#ex-003">EX-003</a></sup></mark> |
| Security | Maximum LTV ratio | 100% |
| Required documents | Documents | 1. Identity document<br>2. Public services number (social card) 3.The bank can request an ownership certificate of the property and electricity and gas bills for the most recent 6 months. |
| Fines and penalties | Late payment fines and penalties (principal and interest) | In case of breach of the due date under the agreement, the Client shall pay to the Bank a fine:<br>- In the amount of 0.13% of overdue amount and interest for each day of delay<br>- No fines and penalties are applied in case of prepayment. |
| Fee for the service, payment of interest and other charges | In case of payment via the Bank’s remote banking system | No fee is charged |
| Fee for the service, payment of interest and other charges | If paid via payment terminals and ATMs owned by the Bank | According to the Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16) ² |
| Fee for the service, payment of interest and other charges | In case of payments via payment terminals owned by other companies | According to the tariffs of the respective company |
| Fee for the service, payment of interest and other charges | If paid at the Bank’s branches | According to Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01) ³ . |
| Other fees | Payable by the Company | As specified in the Cooperation Agreement between the Company and the Bank |
| Coverage | Coverage | Republic of Armenia |

> Individuals resident in Armenia (hereinafter referred to as “resident individuals”) are those individuals who have been actually resident in the Republic of Armenia for 183 and more days during the tax year (Tax Code, Article 25).

> Ameriabank CJSC Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16), approved by Management Board Resolution # 01/110/15 as of September 4, 2015). Available at https://ameriabank.am/useful-links.

> Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01, approved by Management Board Resolution # 03/59/15 as of May 27, 2015). Available at https://ameriabank.am/useful-links.

**Row-level citation labels:**

- `t3:row:12`: EX-013 cites combined row evidence; the exact quote could not be localized to one cell.

1. Via payment terminals  
2. By money transfer from another bank  
3. At bank branches  
4. With the MyAmeria app

### Payment methods

| Payment Method | Fee |
| --- | --- |
| Via Ameriabank CJSC payment terminals | A pplicable service fee according to the document |
| Via Easy Pay, TelCell, MobiDram, Idram, UPay payment terminals | MobiDram, idram – 200 AMD<br>Easy Pay – 300 AMD<br>TelCell – 400 AMD<br>UPay – up to 35,000 AMD: 200 AMD, above 35,001 AMD: 0.6%<br>HayPost – 300 AMD |
| Cash payment at the bank | 500 AMD (per transaction) |
| With the MyAmeria app | 0 AMD |

YOU HAVE THE RIGHT TO COMMUNICATE WITH THE FINANCIAL INSTITUTION USING YOUR PREFERRED METHOD – BY POSTAL MAIL OR ELECTRONICALLY. RECEIVING INFORMATION ELECTRONICALLY IS THE MOST CONVENIENT: IT IS AVAILABLE 24/7, AVOIDS RISKS OF LOSING PAPER DOCUMENTS, AND ENSURES CONFIDENTIALITY.

CREDIT HISTORY AND CREDIT SCORE SUMMARY (SCORE) INFORMATION

This document presents the information required by RA legislation regarding credit history and credit score summary (score), the factors affecting it, and their use in the lending process by Ameriabank CJSC (hereinafter referred to as the &quot;Bank&quot;).

Credit history is the information created/processed by a credit bureau regarding a customer&#x27;s financial obligations, reflecting the customer&#x27;s debts, payments, payment habits, and the dynamics/history of this information.

Credit history includes, in particular, the identification data of the customer, the amount of each obligation, annual interest rate, outstanding balance, payment frequency and due dates, delays in payments, guarantees provided for third parties, depersonalized information about obligations of related parties, as well as data on inquiries made about the credit history.

As a rule, credit history is used by financial institutions to assess a customer&#x27;s ability to assume/maintain financial obligations, act as a guarantor, evaluate lending opportunities either at the initiative of the customer or the Bank, or provide loan offers to the customer.

Based on the customer&#x27;s consent, the Bank submits an inquiry to ACRA Credit Reporting. Credit history information is reflected in a credit report that contains the customer&#x27;s credit history for the previous 5 years as of the date of inquiry.

The customer can review their credit history at http://www.acra.am/.

The credit score is a numerical evaluation of the customer&#x27;s creditworthiness and reliability.

The Bank uses its own creditworthiness and reliability evaluation system for lending purposes, with the main influencing factors listed below:

- Credit history: The number and amount of active loans, frequency of loan applications, and a positive credit history (no delays, high-quality servicing) can help improve the score and lead to loan approval. A poor credit history (delays, long-term delinquencies) may lower the score and result in rejection or stricter conditions.

- Employment, income, and work experience: Having stable employment/income can increase the score and lead to approval. Unstable or irregular income/employment may lower the score and lead to rejection or stricter terms.

- Credit burden: A high debt-to-income ratio can negatively impact the score, while a low credit burden can help improve the score and lead to approval.

- FICO Score: A FICO score is a statistical scoring model based on credit history used globally to assess credit risk. Details at acra.am.

- Other information characterizing the customer

The importance of credit history and score

Credit history and credit score play a critical role in the decision-making process for loan approval, allowing banks and credit organizations to assess the level of credit risk and predict the customer’s likelihood of proper repayment.

Incorrect or incomplete credit history

If the credit history contains errors or incomplete data, the customer may apply to ACRA Credit Reporting CJSC (credit bureau) or the financial organization that provided the incorrect data.

For inquiries to ACRA Credit Reporting CJSC, the procedure and detailed description are available at acra.am.

If the incorrect or incomplete data was transferred by the Bank, the customer may submit a request via any of the following methods:

- By emailing the Bank’s official email address

- By calling the Bank at 010/012 561111

- By sending a message via the Bank’s Internet/Mobile Banking system

- By submitting a written application at any branch of the Bank

The Bank processes the customer&#x27;s request in accordance with the RA legislation and/or internal legal regulations of the Bank, within the defined timeframes.

Steps to improve credit history and credit score

To improve credit history and score, it is necessary to eliminate the root causes as soon as possible, particularly:

- Make regular loan payments according to the schedule, avoiding even a single day’s delay

- Reduce the number and amount of guarantees provided; if possible, ensure repayment of overdue guaranteed obligations

- Ease the credit burden by paying off overdue obligations

- Avoid frequent applications for new loans, as credit history inquiries (except those for loan monitoring) may negatively impact the score

More detailed information about credit history (including errors or incompleteness) and/or credit score can be found at the respective sections of the following websites:

- acra.am – Contact and Support – FAQ

- abcfinance.am – Home – Life Situations – Credit History: A Brief Guide to the Essentials

- abcfinance.am – Home – News – What is a SCORE and how to improve it?

- Consumer Finance Terms

- Be informed when taking a loan

- <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Information summary on installment financing for product purchase and service provision<sup title="product_name"><a href="#ex-010">EX-010</a></sup></mark>

- Terms and conditions

- Main conditions of installment financing services for individuals provided by Ameriabank CJSC

- Consumer Finance Terms (valid from 16.03.25 to 16.08.26)

- Consumer Finance Terms (valid from 25.09.25 to 15.03.26)

- Information summary on installment financing for product purchase and service provision (valid from 07.05.25 to 24.09.25)

### Overdraft

The overdraft provided by payment cards allows you to use the credit funds provided by the Bank without first depositing money into the card account.

### Credit line

A credit line is a convenient way to have available funds in case of unplanned expenses and unplanned purchases.

### MyPay

---

## here

Source: <https://ameriabank.am/Portals/0/files/consumer-finance/partners/nor_tun_eng.pdf>

## &quot;BARSIS&quot; LLC / NOR TUN

All other terms and conditions apply as per Consumer Finance Terms /11 RBD PL 72-34/ (approved by Management Board resolution # 01/35/17 as of November 22, 2017).

| Column 1 | Column 2 |
| --- | --- |
| Currency | AMD |
| Consumer finance limit | 50,000 – 6,000,000 |
| Down payment | N/A |
| Term (months) | 60 |
| Nominal annual interest rate | 0% during the first 9 months, 22.5% starting from the 10th month |
| Annual percentage rate (APR) | 0-24% |
| Loan account monthly service fee<br>(calculated based on the finance amount) | 0% |
| Disbursement fee (lump sum) | N/A |
| Repayment method | Annuity (equal monthly installments consisting of the sum of a portion of loan and a portion of interest) |
| Collateral | N/A |
| Max loan-to-value ratio | - |
| Required documents | • Identity document<br>• Public services number (social card) |
| Product type | The offer is valid for construction materials. |
| Validity period | 14/07/26 - 12/01/27, inclusive |

---

## document

Source: <https://ameriabank.am/Portals/0/files/Other/Payment_terminals_arm.pdf>

Հաստատվել է`  
Տնօրինության 06.04.2023 թ.  
թիվ 02/41/23 որոշմամբ  
Տնօրինության Նախագահ –  
Գլխավոր տնօրենի`  
Արտակ Հանեսյան

Ամերիաբանկ ՓԲԸ  
+37410 561111, office@ameriabank.am

## Վճարային տերմինալով գործարքների իրականացման պայմաններ

Ընդունվել է Բանկի Տնօրինության 04.09.2015 թ. թիվ 01/110/15 որոշմամբ,  
գործող խմբագրությունը` 06.04.2023թ. թիվ 02/41/23 որոշմամբ եւ ուժի մեջ է ներքեւում նշված ամսաթվից:

11RBD/12CIB PL 72-16, Խմբ. 8  
Ուժի մեջ է` 03.05.2023թ-ից

¹ Բանկային/քարտային հաշվի համալրում, վարկի մարումներ եւ վճարումներ հնարավոր է իրականացնել միայն ՀՀ դրամով` 1.000, 2,000, 5.000, 10.000, 20.000 եւ 50,000 ՀՀ դրամ դրամանիշերով/թղթադրամներով կամ 100, 200, 500 ՀՀ դրամ մետաղադրամներով: Արտարժույթով հաշիվների համալրման դեպքում տերմինալ մուտքագրված ՀՀ դրամով գումարը կփոխարկվի ՀՀ դրամի քարտային հաշվին վերջինիս հաշվեգրման պահին Բանկում անկանխիկ գործարքների համար գործող փոխարժեքով:

² Տերմինալի միջոցով Հաճախորդը չի կարող համալրել բանկային արտարժութային հաշիվը:

³ Իրավաբանական անձ հանդիսացող Հաճախորդների դեպքում միջնորդավճար չի գործում։

### Տերմինալով վճարման հնարավորություն ունեցող ծառայությունների ցանկը եւ գանձվող միջնորդավճարների չափերը

11RBD/12CIB PL 72-16, Խմբ. 8  
Ուժի մեջ է` 03.05.2023թ-ից

11RBD/12CIB PL 72-16, Խմբ. 8  
Ուժի մեջ է` 03.05.2023թ-ից

11RBD/12CIB PL 72-16, Խմբ. 8  
Ուժի մեջ է` 03.05.2023թ-ից

11RBD/12CIB PL 72-16, Խմբ. 8  
Ուժի մեջ է` 03.05.2023թ-ից

11RBD/12CIB PL 72-16, Խմբ. 8  
Ուժի մեջ է` 03.05.2023թ-ից

### 1. Բանկային/քարտային հաշվի համալրում ¹

| 1. Բանկային/քարտային հաշվի համալրում ¹ |  |
| --- | --- |
| 1.1. Բանկային/քարտային հաշվի համալրման նվազագույն սահմանաչափ | 100 ՀՀ դրամ |
| 1.2. Բանկային²/քարտային հաշվի համալրման առավելագույն սահմանաչափ | 399,900 ՀՀ դրամ |
| 1.3. Վարկերի մարման նվազագույն սահմանաչափ | 100 ՀՀ դրամ |
| 1.4. Վարկերի մարման առավելագույն սահմանաչափ | 399,900 ՀՀ դրամ |
| 1.5. Բանկային/քարտային հաշվի համալրման գործարքի դիմաց գանձվող միջնորդավճար | Չի սահմանվում |
| 1.6. Երեւան քաղաքում գործող վճարային տերմինալների միջոցով Բանկի նկատմամբ ցանկացած վարկային եւ ապառիկ ֆինանսավորման պարտավորությունների մարման գործարքի դիմաց գանձվող միջնորդավճար³ | 100 ՀՀ դրամ |
| 1.7. Երեւան քաղաքից դուրս գործող վճարային տերմինալների միջոցով Բանկի նկատմամբ ցանկացած վարկային եւ ապառիկ ֆինանսավորման պարտավորությունների մարման գործարքի դիմաց գանձվող միջնորդավճար | Չի սահմանվում |

### Տերմինալով վճարման հնարավորություն ունեցող ծառայությունների ցանկը և գանձվող միջնորդավճարների չափերը

| Հ/Հ | Ծառայությունը մատուցող | Ծառայության անվանում | Մատուցվող ծառայության տեսակ | Միջնորդավճար (գանձվում է հաճախորդից) |
| --- | --- | --- | --- | --- |
|  | Բջջային օպերատորներ | Բջջային օպերատորներ | Բջջային օպերատորներ | Բջջային օպերատորներ |
| 1. | «ՏԵԼԵԿՈՄ ԱՐՄԵՆԻԱ» ՓԲԸ | Team մոբայլ | Բջջային կապ | 0% |
| 2. | «ՅՈՒՔՈՄ» ՓԲԸ | Յուքոմ մոբայլ | Բջջային կապ | 0% |
| 3. | «ՄՏՍ Հայաստան» ՓԲԸ | ՎիվաՍել ՄՏՍ մոբայլ | Բջջային կապ | 0% |
| 4. | «Ղարաբաղ-Տելեկոմ» ՓԲԸ | Ղարաբաղ Տելեկոմ մոբայլ | Բջջային կապ | 100-999` 30 ՀՀ դրամ,<br>1000 դրամ եւ ավել` 3% |
| 5. | ПАО &quot;Мобильные ТелеСистемы&quot; | MTS Russia | Բջջային կապ | 5% |
| 6. | ПАО &quot;ВымпелКом&quot; | Beeline Russia | Բջջային կապ | 5% |
| 7. | ПАО &quot;Мегафон&quot; | MegaFon Russia | Բջջային կապ | 5% |
| 8. | Նովա Տեխնոլոջի ԲԸ | BeelineGeo | Բջջային կապ | 3% |
| 9. | Նովա Տեխնոլոջի ԲԸ | Geocell | Բջջային կապ | 3% |
| 10. | Նովա Տեխնոլոջի ԲԸ | Magti99 | Բջջային կապ | 3% |
| 11. | Նովա Տեխնոլոջի ԲԸ | MagtiBani | Բջջային կապ | 3% |
| 12. | Նովա Տեխնոլոջի ԲԸ | MagtiBali | Բջջային կապ | 3% |
|  | Կոմունալ ծառայություններ | Կոմունալ ծառայություններ | Կոմունալ ծառայություններ | Կոմունալ ծառայություններ |
| 13. | «Երեւան Ջուր» ՓԲԸ | Վեոլիա ջուր | Ջրամատակարարում | 0% |
| 14. | «Լոռի-Ջրմուղկոյուղի» ՓԲԸ | Լոռի ջուր | Ջրամատակարարում | 0% |
| 15. | «Շիրակ-Ջրմուղկոյուղի» ՓԲԸ | Շիրակ ջուր | Ջրամատակարարում | 0% |
| 16. | «Նորակունք» ՓԲԸ | Նոր ակունք | Ջրամատակարարում | 0% |
| 17. | «Հայջրմուղկոյուղի»ՓԲԸ | Arm water | Ջրամատակարարում | 0% |

### Տերմինալով վճարման հնարավորություն ունեցող ծառայությունների ցանկը և գանձվող միջնորդավճարների չափերը (շարունակություն)

| Հ/Հ | Ծառայությունը մատուցող | Ծառայության անվանում | Մատուցվող ծառայության տեսակ | Միջնորդավճար (գանձվում է հաճախորդից) |
| --- | --- | --- | --- | --- |
| 18. | Ջրօգտագործողների ընկերություն | Մարզային ջրամատակարարում | Ջրամատակարարում | 0% |
| 19. | Ջրօգտագործողների ընկերություն | Մարզային ջրամատակարարում (սպասարկում) | Ջրամատակարարում | 0% |
| 20. | «Հայաստանի էլեկտրական Ցանցեր» ՓԲԸ | Էլեկտրոցանց ֆիզիկական անձանց համար | Էլեկտրամատակարարում | 0% |
| 20. | «Հայաստանի էլեկտրական Ցանցեր» ՓԲԸ | Էլեկտրոցանց իրավաբանական անձանց համար | Էլեկտրամատակարարում իրավաբանական անձանց համար | 0% |
| 21. | «Գազպրոմ Արմենիա» ՓԲԸ | Գազ | Գազամատակարարում | 0% |
| 22. | «Գազպրոմ Արմենիա» ՓԲԸ | Գազի սպասարկում | Սպասարկում | 0% |
| 23. | «ՔրոսսՆեթ»ՍՊԸ | Cross.am | Ֆիքսված հեռախոսակապ | 0% |
| 24. | «Ջի Էն Սի ԱԼՖԱ» ՓԲԸ (Ռոստելեկոմ) | Ռոստելեկոմ | Ֆիքսված հեռախոսակապ | 0% |
| 25. | «Յուքոմ» ՓԲԸ | Յուքոմ ֆիքսված | Ֆիքսված հեռախոսակապ | 0% |
| 26. | «ՏԵԼԵԿՈՄ ԱՐՄԵՆԻԱ» ՓԲԸ | Team ֆիքսված | Ֆիքսված հեռախոսակապ | 0% |
| 27. | «Արցախէներգո» ՓԲԸ | Արցախ Էներգո ֆիզիկական անձանց համար | Էլեկտրամատակարարում | 0% |
| 28. | «Արցախէներգո» ՓԲԸ | Արցախ Էներգո իրավաբանական անձանց համար | Էլեկտրամատակարարում | 0% |
| 29. | «Արցախգազ» ՓԲԸ | Արցախ գազ - սպասարկում | Սպասարկում | 0% |
| 30. | «Արցախգազ» ՓԲԸ | Արցախ գազ - սպառում | Գազամատակարարում | 0% |
| 31. | Ջրմուղ-կոյուղի ՓԲԸ | Արցախ ջուր | Ջրամատակարարում | 0% |
|  | Հեռուստատեսություն | Հեռուստատեսություն | Հեռուստատեսություն | Հեռուստատեսություն |
| 32. | «Ինտերակտիվ Թիվի» ՍՊԸ | Ինտերակտիվ | Կաբելային հեռուստատեսություն | 0% |
| 33. | «Արմինկոնետ» ՓԲԸ | ArmincoVoip | Կաբելային հեռուստատեսություն | 0% |

### Տերմինալով վճարման հնարավորություն ունեցող ծառայությունների ցանկը և գանձվող միջնորդավճարների չափերը (շարունակություն)

| Հ/Հ | Ծառայությունը մատուցող | Ծառայության անվանում | Մատուցվող ծառայության տեսակ | Միջնորդավճար (գանձվում է հաճախորդից) |
| --- | --- | --- | --- | --- |
| 34. | «ՅՈՒՔՈՄ» ՓԲԸ | Յուքոմ | Կաբելային հեռուստատեսություն | 0% |
| 35. | «ՏԵԼԵԿՈՄ ԱՐՄԵՆԻԱ» ՓԲԸ | Team ինտերնետ | Կաբելային հեռուստատեսություն | 0% |
| 36. | «Ջի Էն Սի ԱԼՖԱ» ՓԲԸ | Ռոստելեկոմ | Կաբելային հեռուստատեսություն | 0% |
| 37. | «ԱՐԹ-ԹԻՎԻ-ՆԵԹ» ՍՊԸ | Art TV Net | Հանրային էլեկտրոնային հաղորդակցություն | 0% |
| 38. | Շանթ ՍՊԸ | Shant Digital TV | Թվային հեռուստատեսություն | 0% |
| 39. | НКО ККРЦ | NtvPlusRussia | Արբանյակային հեռուստատեսություն | 5% |
|  | Ինտերնետ եւ IP հեռախոսակապ | Ինտերնետ եւ IP հեռախոսակապ | Ինտերնետ եւ IP հեռախոսակապ | Ինտերնետ եւ IP հեռախոսակապ |
| 40. | «ՎԵԲ» ՍՊԸ | Web.am internet | Ինտերնետ կապ | 0% |
| 41. | «Յուքոմ» ՓԲԸ | Յուքոմ | Ինտերնետ կապ | 0% |
| 42. | «Այքան Քոմունիքեյշնս» ՓԲԸ | Icon | Ինտերնետ կապ | 0% |
| 43. | «Արմինկո-ՆԿ» ՍՊԸ | ArmincoNK | Ինտերնետ կապ | 0% |
| 44. | «Ջի Էն Սի ԱԼՖԱ» ՓԲԸ | Ռոստելեկոմ | Ինտերնետ կապ | 0% |
| 45. | «Ղարաբաղ տելեկոմ» ՓԲԸ | Ղարաբաղ տելեկոմ ինտերնետ | Ինտերնետ կապ | 100-999` 30 ՀՀ դրամ,<br>1000 դրամ եւ ավել` 3% |
| 46. | «ԱՐՑԱԽԿԱՊ» ՓԲԸ | Արցախկապ | Ինտերնետ կապ | 0% |
| 47. | «ԷՖ ՆԵԹ» ՍՊԸ | Family Network | Ինտերնետ կապ եւ TV | 0% |
|  | Առեւտրային կազմակերպություններ | Առեւտրային կազմակերպություններ | Առեւտրային կազմակերպություններ | Առեւտրային կազմակերպություններ |
| 48. | «Օրիֆլեյմ քոսմեթիքս» ՍՊԸ | Օրիֆլեյմ | Հաշվի համալրում | 0% |
| 49. | «Ֆաբերլիկ Զակավկազյե» ՍՊԸ | Ֆաբերլիկ | Հաշվի համալրում | 0,5% |
| 50. | Մանչո Գրուպ ՍՊԸ | Մանչո Գրուպ | Միջնորդական ծառայություն | 0% |
| 51. | «Ռեսթարթ Մարքեթինգ» ՍՊԸ | Crossroad | Ապրանքների վաճառք | 0% |

### Տերմինալով վճարման հնարավորություն ունեցող ծառայությունների ցանկը և գանձվող միջնորդավճարների չափերը (շարունակություն)

| Հ/Հ | Ծառայությունը մատուցող | Ծառայության անվանում | Մատուցվող ծառայության տեսակ | Միջնորդավճար (գանձվում է հաճախորդից) |
| --- | --- | --- | --- | --- |
| 52. | Դերենիկ Հայրապետյան Գարեգինի ԱՁ | List.am | On-line ծառայություն | 0% |
| 53. | Էյ էմ Ավտոմատիվ ՍՊԸ | Auto.am | On-line ծառայություն | 0% |
| 54. | ՋԻՋԻՏԱՔՍԻ ՓԲԸ | GGTaxi | Տաքսի ծառայություն | 0% |
| 55. | «Գլոբբինգ» ՍՊԸ | Globbing | Բեռնափոխադրում | 3% |
| 56. | «ՇԻՓԷՔՍ» ՓԲԸ | Shipex | Բեռնափոխադրում | 0% |
| 57. | «Զ ԷՍ ՏՈՊ» ՍՊԸ | Skill | Ուսուցում | 0% |
| 58. | «Տոմսարկղ» ՍՊԸ | Tomsarkgh.am | Տոմսերի վաճառքի օնլայն հարթակ | 0% |
| 59. | «Վելվիո» ՍՊԸ | Yerevan Ride | Հեծանիվների վարձակալություն | 0% |
| 60. | «Միմո» ՍՊԸ | Mimo Bike | Հեծանիվների վարձակալություն | 0% |
|  | Պետական տուրքեր եւ վճարումներ | Պետական տուրքեր եւ վճարումներ | Պետական տուրքեր եւ վճարումներ | Պետական տուրքեր եւ վճարումներ |
| 61. | ՀՀ Ճանապարհային ոստիկանություն | ՃՈ տեղական համարանիշ<br>ՃՈ արձանագրված խախտումներ<br>ՃՈ արտասահմանյան համարանիշ | Ճանապարհային տուգանքի վճարում | 300 դր. |
| 62. | «ՀՀ արտաքին գործերի նախարարություն» | ՀՀ արտաքին գործերի նախարարություն | Պետական տուրքերի վճարում | 200 դր |
| 63. | «ՀՀ ԿԱ Անշարժ գույքի կադաստրի պետ. կոմիտե» | Անշարժ գույքի կադաստրի պետ. կոմիտե | Պետական տուրքերի վճարում | 300 դր. |
| 64. | «ԹԵԼ-ՍԵԼ» ՓԲԸ | Պետական ռեգիստր | Պետական ռեգիստրի վճարումներ | 200 դր |
| 65. | «Սայնվայզ» ՍՊԸ | Էկենգ | Էլեկտրոնային/թվային ստորագրության ակտիվացման վճար | 300 դր |
| 66. | «Պարկինգ Սիթի Սերվիս» ՍՊԸ | Պարկինգ | Ավտոկայանատեղի վճարում | 100-999` 0 դրամ, 1,000--12,000` 200 դրամ |
| 67. | «Պարկինգ Սիթի Սերվիս» ՍՊԸ | Պարկինգ տուգանք | Ավտոկայանատեղի տուգանքի վճարում | 200 դր |

### Տերմինալով վճարման հնարավորություն ունեցող ծառայությունների ցանկը և գանձվող միջնորդավճարների չափերը (շարունակություն)

| Հ/Հ | Ծառայությունը մատուցող | Ծառայության անվանում | Մատուցվող ծառայության տեսակ | Միջնորդավճար (գանձվում է հաճախորդից) |
| --- | --- | --- | --- | --- |
| 68. | «Ծարավ աղբյուր» համատիրություն | «Ծարավ աղբյուր» համատիրություն | Պետական վճարումներ | 200 դր. |
| 69. | ՀՀ ոստիկանության անձնագրային եւ վիզաների վարչություն | OVIR | Պետական վճարումներ | 100-1100` 60 ՀՀ դրամ,<br>1101 դրամ եւ ավել` 120 ՀՀ դրամ |
| 70. | Պետական ռեգիստրի վճարումներ | Պետռեգիստր | Պետական վճարումներ | 200 դր. |
|  | Ֆինանսներ | Ֆինանսներ | Ֆինանսներ | Ֆինանսներ |
| 71. | «Իդրամ» ՍՊԸ | Idram | Վիրտուալ դրամապանակ | 100-1,000` 30 ՀՀ դրամ,<br>1,001-4,999` 2%<br>5,000 դրամ եւ ավել` 1% |
| 72. | «Տրիանգ» ՍՊԸ | Webmoney | Վիրտուալ դրամապանակ | 3% |
| 73. | «Յանդեքս» ՓԲԸ | Yandex.Money | Վիրտուալ դրամապանակ | 3% |
| 74. | «Քիվի» ԲԸ | Qiwi | Վիրտուալ դրամապանակ | 3% |
| 75. | «Մոբիդրամ» ՓԲԸ | Mobidram | Վիրտուալ դրամապանակ | 100-1000` 30 ՀՀ դրամ,<br>1,001-4,999` 2%<br>5,000 դրամ եւ ավել` 1% |
| 76. | «Յուփեյ» ՓԲԸ | Upay | Վիրտուալ դրամապանակ | 100-1000` 30 ՀՀ դրամ,<br>1,001-4,999` 2%<br>5,000 դրամ եւ ավել` 1% |
| 77. | «Թել-Սել» ՓԲԸ | Twallet | Վիրտուալ դրամապանակ | 0% |
|  | Ապահովագրություն | Ապահովագրություն | Ապահովագրություն | Ապահովագրություն |
| 78. | Ռեսո ԱՓԲԸ | Reso | Ապահովագրական ծառայություններ | 300 դր. |
| 79. | Արմենիա ԱՓԲԸ | Armenia Insurance | Ապահովագրական ծառայություններ | 300 դր. |
| 80. | Սիլ ինշուրանս ԱՓԲԸ | SilInsurance | Ապահովագրական ծառայություններ | 300 դր. |
| 81. | Ռոսգոսստրախ ԱՓԲԸ | Rosgosstrakh | Ապահովագրական ծառայություններ | 300 դր. |
| 82. | Նաիրի ԱՓԲԸ | Nairi Inshurance | Ապահովագրական ծառայություններ | 300 դր. |

---

## Consumer Finance Terms

Source: <https://ameriabank.am/Portals/0/files/Personal/Consumer_finance_terms_eng.pdf>

³ Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01, approved by Management Board Resolution # 03/59/15 as of May 27, 2015). Available at https://ameriabank.am/useful-links.

### AMERIABANK CJSC - Consumer Finance Terms (Purchase of Goods)

| Category | Terms | Details |
| --- | --- | --- |
| Document Details | Document Reference | AMERIABANK CJSC 11RBD PL 72-34<br>Edition 17 |
| Document Details | Approval Information | Consumer Finance Terms (Purchase of Goods)<br>Approved by Management Board resolution #02/116/26 as of July 30, 2026<br>Chairman of the Management Board - CEO Artak Hanesyan<br>Approved by Management Board Resolution # 01/35/17 as of November 22, 2017<br>Current edition approved by resolution #02/116/26 as of July 30, 2026, effective from August 17, 2026 |
| Customer&#x27;s personal details | Eligible age | From 20 to 66 years inclusive |
| Customer&#x27;s personal details | Customer | Citizens and non-citizens of Armenia who are resident in Armenia¹ |
| Terms of finance | Currency | AMD |
| Terms of finance | Finance limit | If applying at the seller&#x27;s premises (hereinafter &quot;the Company&quot;)<br>Mobile phone/computer equipment: AMD 50,000 - AMD 1,000,000<br>Household appliances: AMD 50,000 - AMD 3,600,000<br>Furniture, construction materials, home improvement products and heating systems: AMD 50,000 - AMD 6,000,000<br>Household items, spare parts for cars and other goods: AMD 50,000 - AMD 2,400,000<br>If applying online via the remote consumer finance system of the Bank (irrespective of the product): AMD 50,000 - AMD 1,500,000 |
| Terms of finance | Term (months) | If applying at the Company&#x27;s premises - 6-60. A term exceeding 48 months may be set only in case of furniture, construction materials, home improvement products and heating systems.<br>If applying online via the remote consumer finance system of the Bank (irrespective of the product): 6-36 months |
| Terms of finance | Nominal annual interest rate | Fixed<br>As specified in the Cooperation Agreement between the Company and the Bank |
| Terms of finance | Monthly account service fee | As specified in the Cooperation Agreement between the Company and the Bank |
| Terms of finance | Disbursement fee (lump-sum)/down payment | As specified in the Cooperation Agreement between the Company and the Bank |
| Repayment methods | Repayment method | <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">1. Annuity (equal monthly installments consisting of a portion of debt and a portion of interest) where interest rate is applied<br>2. Equal monthly installments schedule (equal monthly installments consisting of a portion of debt and a portion of fee) where a fee is applied<sup title="repayment"><a href="#ex-012">EX-012</a></sup></mark> |
| Security | Eligible collateral | The purchased item serves as a collateral. |
| Security | Maximum LTV ratio | 100% |
| Required documents | Documents | • Identity document<br>• Public services number (social card) |
| Fines and penalties | Late payment fines and penalties (principal and interest) | In case of breach of the due date under the agreement, the Client shall pay to the Bank a fine<br>• In the amount of 0.13% of overdue amount and interest for each day of delay<br>• No fines and penalties are applied in case of prepayment. |
| Fee for the service, payment of interest and other charges | In case of payment via the Bank&#x27;s remote banking system | No fee is charged |
| Fee for the service, payment of interest and other charges | If paid via payment terminals and ATMs owned by the Bank | According to the Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16)² |
| Fee for the service, payment of interest and other charges | If paid via payment terminals owned by other companies | According to the tariffs of the respective company |
| Fee for the service, payment of interest and other charges | If paid at the Bank&#x27;s branches | According to Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01)³. |
| Other fees | Payable by the Company | As specified in the Cooperation Agreement between the Company and the Bank |
| Coverage | Coverage | Republic of Armenia |

> ¹ Individuals resident in Armenia (hereinafter referred to as &quot;resident individuals&quot;) are those individuals who have been actually resident in the Republic of Armenia for 183 and more days during the tax year (Tax Code, Article 25).

> ² Ameriabank CJSC Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16), approved by Management Board Resolution # 01/110/15 as of September 4, 2015). Available at https://ameriabank.am/useful-links.

> ³ Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01, approved by Management Board Resolution # 03/59/15 as of May 27, 2015). Available at https://ameriabank.am/useful-links.

### AMERIABANK CJSC - Consumer Finance Terms (Provision of Services)

| Category | Terms | Details |
| --- | --- | --- |
| Document Details | Document Reference | AMERIABANK CJSC 11RBD PL 72-34<br>Edition 17 |
| Document Details | Approval Information | Consumer Finance Terms (Provision of Services)<br>Approved by Management Board resolution #02/116/26 as of July 30, 2026<br>Chairman of the Management Board - CEO Artak Hanesyan<br>Approved by Management Board Resolution #01/35/17 as of November 22, 2017<br>Current edition approved by resolution #02/116/26 as of July 30, 2026, effective from August 17, 2026 |
| Customer&#x27;s personal details | Eligible age | From 20 to 66 years inclusive |
| Customer&#x27;s personal details | Customer | Citizens and non-citizens of Armenia who are resident in Armenia¹ |
| Terms of finance | Currency | AMD |
| Terms of finance | Finance limit | If applying at the service provider&#x27;s premises (hereinafter &quot;the Company&quot;):<br>Minimum: AMD 50,000<br>Maximum: AMD 1,800,000<br>If applying via remote consumer finance system of the Bank:<br>Minimum: AMD 50,000<br>Maximum: AMD 1,500,000 |
| Terms of finance | Term (months) | If applying at the Company&#x27;s premises or via remote consumer finance system of the Bank: 6-24 |
| Terms of finance | Nominal annual interest rate | Fixed<br>As specified in the Cooperation Agreement between the Company and the Bank |
| Terms of finance | Monthly account service fee | As specified in the Cooperation Agreement between the Company and the Bank |
| Terms of finance | Disbursement fee (lump-sum)/down payment | As specified in the Cooperation Agreement between the Company and the Bank |
| Repayment methods | Repayment method | 1. Annuity (equal monthly installments consisting of a portion of debt and a portion of interest) where interest rate is applied<br>2. Equal monthly installments schedule (equal monthly installments consisting of a portion of debt and a portion of fee) where a fee is applied. |
| Required documents | Documents | • Identity document<br>• Public services number (social card) |
| Fines and penalties | Late payment fines and penalties (principal and interest) | In case of breach of the due date under the agreement, the Client shall pay to the Bank a fine<br>- In the amount of 0.13% of overdue amount and interest for each day of delay<br>- No fines and penalties are applied in case of prepayment. |
| Fee for the service, payment of interest and other charges | In case of payment via the Bank&#x27;s remote banking system | No fee is charged |
| Fee for the service, payment of interest and other charges | If paid via payment terminals and ATMs owned by the Bank | According to the Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16)² |
| Fee for the service, payment of interest and other charges | In case of payments via payment terminals owned by other companies | According to the tariffs of the respective company |
| Fee for the service, payment of interest and other charges | If paid at the Bank&#x27;s branches | According to Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01)³. |
| Other fees | Payable by the Company | As specified in the Cooperation Agreement between the Company and the Bank |
| Coverage | Coverage | Republic of Armenia |

> ¹ Individuals resident in Armenia (hereinafter referred to as &quot;resident individuals&quot;) are those individuals who have been actually resident in the Republic of Armenia for 183 and more days during the tax year (Tax Code, Article 25).

> ² Ameriabank CJSC Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16), approved by Management Board Resolution # 01/110/15 as of September 4, 2015). Available at https://ameriabank.am/useful-links.

### AMERIABANK CJSC - Terms of Consumer Finance (Purchase and Installation of Solar Panels/Water Heating Systems)

| Category | Terms | Details |
| --- | --- | --- |
| Document Details | Document Reference | AMERIABANK CJSC 11RBD PL 72-34<br>Edition 17 |
| Document Details | Approval Information | Terms of Consumer Finance (Purchase and Installation of Solar Panels/Water Heating Systems)<br>Approved by Management Board resolution #02/116/26 as of July 30, 2026<br>Chairman of the Management Board - CEO Artak Hanesyan<br>Approved by Management Board Resolution #01/35/17 as of November 22, 2017<br>Current edition approved by resolution #02/116/26 as of July 30, 2026, effective from August 17, 2026 |
| Customer&#x27;s personal details | Eligible age | From 20 to 66 years inclusive |
| Customer&#x27;s personal details | Customer | Citizens and non-citizens of Armenia who are resident in Armenia¹ |
| Terms of finance | Currency | AMD |
| Terms of finance | Credit limit | <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Minimum: AMD 200,000<br>Maximum: AMD 6,000,000<sup title="credit_limit"><a href="#ex-004">EX-004</a></sup></mark> |
| Terms of finance | Term (months) | 6-120 |
| Terms of finance | Nominal annual interest rate | Fixed<br>As specified in the Cooperation Agreement between the company selling solar panels/water heating systems (hereinafter &quot;the Company&quot;) and the Bank |
| Terms of finance | Monthly account service fee | As specified in the Cooperation Agreement between the Company and the Bank |
| Terms of finance | Disbursement fee (lump-sum)/down payment | As specified in the Cooperation Agreement between the Company and the Bank |
| Repayment methods | Repayment method | 1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest) where interest rate is applied<br>2. Equal monthly installments schedule (equal monthly installments consisting of a portion of loan and a portion of fee) where a fee is applied. |
| Security | Eligible collateral | The purchased item serves as a collateral. |
| Security | Maximum LTV ratio | 100% |
| Required documents | Documents | 1. Identity document<br>2. Public services number (social card)<br>3. The bank can request an ownership certificate of the property and electricity and gas bills for the most recent 6 months. |
| Fines and penalties | Late payment fines and penalties (principal and interest) | In case of breach of the due date under the agreement, the Client shall pay to the Bank a fine:<br>- In the amount of 0.13% of overdue amount and interest for each day of delay<br>- No fines and penalties are applied in case of prepayment. |
| Fee for the service, payment of interest and other charges | In case of payment via the Bank&#x27;s remote banking system | No fee is charged |
| Fee for the service, payment of interest and other charges | If paid via payment terminals and ATMs owned by the Bank | According to the Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16)² |
| Fee for the service, payment of interest and other charges | In case of payments via payment terminals owned by other companies | According to the tariffs of the respective company |
| Fee for the service, payment of interest and other charges | If paid at the Bank&#x27;s branches | According to Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01)³. |
| Other fees | Payable by the Company | As specified in the Cooperation Agreement between the Company and the Bank |
| Coverage | Coverage | Republic of Armenia |

> ¹ Individuals resident in Armenia (hereinafter referred to as &quot;resident individuals&quot;) are those individuals who have been actually resident in the Republic of Armenia for 183 and more days during the tax year (Tax Code, Article 25).

> ² Ameriabank CJSC Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16), approved by Management Board Resolution # 01/110/15 as of September 4, 2015). Available at https://ameriabank.am/useful-links.

> ³ Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01, approved by Management Board Resolution # 03/59/15 as of May 27, 2015). Available at https://ameriabank.am/useful-links.

**Row-level citation labels:**

- `document:2:744c784c8603:page:3:table:0:row:13`: EX-013 cites combined row evidence; the exact quote could not be localized to one cell.

---

## Information summary on installment financing for product purchase and service provision

Source: <https://ameriabank.am/Portals/0/files/Personal/Loans/Leaflet_consumer_finance_eng.pdf>

## INFORMATION GUIDE TO INSTALLMENT LOANS FOR PURCHASE OF GOODS AND SERVICES

Effective date: September 25, 2025

Terms and conditions specified in the Guide may change from time to time. More details at:  
ameriabank.am | 010 56 11 11

The Bank is supervised by the Central Bank of Armenia.

## Purpose

The purpose of installment loans is purchase of goods or services by individuals.

## Essential Terms of Installment Loans for Purchase of Goods.

1 Individuals resident in Armenia (hereinafter referred to as “resident individuals”) are those individuals who have been actually resident in the Republic of Armenia for 183 and more days during the tax year (Tax Code, Article 25).

## Essential Terms of Installment Loans for Purchase of Services

2 Individuals resident in Armenia (hereinafter referred to as “resident individuals”) are those individuals who have been actually resident in the Republic of Armenia for 183 and more days during the tax year (Tax Code, Article 25).

## Essential Terms of Installment Loans for Purchase of Solar Panels and Water Heaters

3 Individuals resident in Armenia (hereinafter referred to as “resident individuals”) are those individuals who have been actually resident in the Republic of Armenia for 183 and more days during the tax year (Tax Code, Article 25).

## Service Fee

The fee is charged if the modification is requested by the client. Where several fees are chargeable for the same modification, the highest fee is charged and only once.

## Required documents

## Statements

We will provide to you the statements of your credit accounts through communication channels and at frequency agreed between you and us and/or in accordance with the Armenian laws and regulations. The statements can be provided by mail, email, Internet-Bank or in person in any branch office of the Bank.

### Attention!

ELECTRONIC CHANNELS ARE THE MOST CONVENIENT WAY TO GET INFORMATION. THEY ARE AVAILABLE 24/7, FREE FROM THE RISK OF LOSS OF INFORMATION STORED ON PAPER AND MORE CONFIDENTIAL.

## Attention!

WHEN YOU APPLY FOR FINANCE, THE BANK PROVIDES TO YOU A PERSONAL LEAFLET ON ESSENTIAL TERMS OF CONSUMER CREDIT CONTAINING THE INDIVIDUAL CREDIT TERMS OFFERED TO YOU.

## Attention!

THE INTEREST RATE ON YOUR CREDIT CANNOT EXCEED THE DOUBLE OF THE BANK RATE ANNOUNCED BY THE CENTRAL BANK OF ARMENIA.

## Attention!

LOAN INTEREST IS CALCULATED AT THE NOMINAL INTEREST RATE. THE LATTER SHOWS THE ANNUAL INTEREST ACCRUED AS PERCENTAGE OF THE OUTSTANDING CREDIT. INTEREST IS CALCULATED IN THE CURRENCY OF THE LOAN ON A DAILY BASIS IN RELATION TO THE LOAN OUTSTANDING AT EACH PARTICULAR TIME. BASED ON A 365-DAY CALENDAR YEAR.

ANNUAL PERCENTAGE RATE SHOWS THE COST OF CREDIT IN CASE OF PROPER AND TIMELY PERFORMANCE OF ALL CONTRACTUAL OBLIGATIONS.

APR is calculated by the following formula:  
A = ∑ (n=1 to N) [K_n / (1 + i)^(D_n / 365)]

The amount of interest is determined based on nominal annual interest rate and chosen credit repayment option.

Credit and interest payments are performed based on annuity scheme where the amount of monthly payment is calculated as follows:  
R= P x r / (1–1/(1 +r)n), where

- R – monthly repayment for the loan
- P – loan principal
- n – total number of payments during the whole term of loan (number of months)
- r – monthly interest rate, which is equal to 1/12 of the annual interest rate under the loan agreement at the time of provision of the loan
- • Annuity

## Attention!

IF YOU FAIL TO PERFORM YOUR PAYMENT OBLIGATIONS WHEN DUE OR DO NOT PERFORM THEM PROPERLY, OVERDUE AMOUNTS SHALL BEAR FINES AND PENALTIES AS DEFINED BY AGREEMENT, AND THE INFORMATION ABOUT YOUR OVERDUE LIABILITIES WILL BE REPORTED TO CREDIT BUREAU WITHIN 3 BUSINESS DAYS. YOU HAVE THE RIGHT TO OBTAIN YOUR CREDIT HISTORY FROM THE CREDIT BUREAU ONCE A YEAR, AT NO COST.

Overdue liabilities are paid in the following succession:

- 1. Fines and penalties
- 2. Interest
- 3. Principal

YOUR BAD CREDIT HISTORY MAY AFFECT YOUR FUTURE LOAN APPLICATIONS.

## Early repayment

In case of installment loans, you can perform your credit obligations before the due date irrespective of whether or not such option is envisaged under your credit agreement.

## Change of interest rates

THE BANK HAS THE RIGHT TO CHANGE THE INTEREST RATES AT ANY TIME DEPENDING ON VOLATILITY OF INTEREST RATES ON FUNDS BORROWED AND/OR ALLOCATED BY THE BANK ON FINANCIAL MARKET, AND/OR OCCURRENCE OF PRECONDITIONS FOR CHANGE OF ANNUAL INTEREST RATE OF YOUR CREDIT. IN CASE OF UNILATERAL CHANGE OF NOMINAL INTEREST RATE THE BANK SHALL INFORM YOU IN THE MANNER DEFINED UNDER YOUR CREDIT AGREEMENT (AT LEAST 7 DAYS IN ADVANCE). SUCH NOTICE WILL BE DELIVERED VIA THE PREFERRED COMMUNICATION CHANNEL SPECIFIED IN THE CREDIT AGREEMENT AND SERVE AS BASIS FOR APPLICATION OF THE NEW INTEREST RATE FROM THE DATE SPECIFIED THEREIN. IF NOT CONSENTING TO THE NEW INTEREST RATE, YOU CAN TERMINATE THE RESPECTIVE AGREEMENT OR COVENANT IN WHICH CASE YOU WILL BE REQUIRED TO PERFORM YOUR LIABILITIES UNDER SUCH AGREEMENT OR COVENANT AS OF THE DATE OF TERMINATION TO THE FULL EXTENT.

YOU CAN TERMINATE YOUR CREDIT AGREEMENT WITHOUT HAVING TO PROVIDE EXPLANATION ANY TIME WITHIN 7 DAYS AFTER EXECUTION, UNLESS A LONGER PERIOD IS ENVISAGED UNDER THE CREDIT AGREEMENT (COOLING-OFF PERIOD). THIS BEING THE CASE, YOU WILL BE REQUIRED TO PAY INTEREST AT THE ACTUAL ANNUAL PERCENTAGE RATE SPECIFIED UNDER YOUR CREDIT AGREEMENT.

NO OTHER COMPENSATION FOR TERMINATION OF CREDIT AGREEMENT CAN BE DEMANDED FROM THE BORROWER.

## What may help you to get your application approved

- • Long-standing relationship between the Bank and the client
- • Amount of your income
- • Good credit history
- • Other

## Why your application might be rejected

- • The information (documents and other data) provided by you is not trustworthy or complete.
- • Your declared income is not sufficient to repay the obligations.
- • You have bad credit history, overdue and/or classified liabilities (including liabilities to third parties).
- • Other

## Loan decision

You need not visit the Bank to get an installment loan. All you have to do is approach our partner selling the item you want to purchase. The financing process is automated. Your application is processed and reviewed by an automated software based on your credit score.

If your application is approved and you:

- • Confirm your intention to get the credit within 7 calendar days after you are notified, you get the credit.

YOU HAVE THE RIGHT TO CONTACT OR MAINTAIN CORRESPONDENCE WITH THE FINANCIAL INSTITUTION VIA YOUR PREFERRED CHANNEL: REGULAR MAIL OR ELECTRONIC CHANNELS. ELECTRONIC CHANNELS ARE THE MOST CONVENIENT WAY TO GET INFORMATION. THEY ARE AVAILABLE 24/7, FREE FROM THE RISK OF LOSS OF INFORMATION STORED ON PAPER AND MORE CONFIDENTIAL.

### Essential Terms of Installment Loans for Purchase of Goods.

| Column 1 | Column 2 | Column 3 |
| --- | --- | --- |
| Client&#x27;s personal details | Eligible age | From 20 до 66 inclusive |
| Client&#x27;s personal details | Eligible clients | Citizens and non-citizens of Armenia who are resident in Armenia1 |
| Terms of finance | Currency of finance | AMD |
| Terms of finance | Financing limit | 50,000-6,000,000 |
| Terms of finance | Term of finance (in months) | 6-60 |
| Terms of finance | Nominal annual interest rate | 0%-21.5% |
| Terms of finance | Annual percentage rate (APR) | 0%-24% |
| Terms of finance | Monthly account service fee | N/A |
| Debt repayment options | Repayment | In case of interest: annuity, equal monthly payments consisting of a portion of loan and a portion of interest<br>Equal monthly installments schedule (equal monthly installments consisting of a portion of debt and a portion of fee) where a fee is applied |
| Security | Eligible collateral | The purchased item serves as a collateral. |
| Security | Maximum “loan to value” ratio | 100% |

**Row-level citation labels:**

- `document:3:d390a42c11fa:page:1:table:0:row:6`: EX-005 cites combined row evidence; the exact quote could not be localized to one cell.

### Essential Terms of Installment Loans for Purchase of Goods. (Continued)

| Column 1 | Column 2 | Column 3 |
| --- | --- | --- |
| Fee for service, payment of interest and other charges | For non-cash payments | AMD 0 |
| Fee for service, payment of interest and other charges | For payments via Ameriabank CJSC payment kiosks | A fee applicable according to the document |
| Fee for service, payment of interest and other charges | For payments via other payment kiosks or ATMs | According to the tariffs of the relevant company operating the payment kiosk or ATM: https://ameriabank.am/en/ |
| Fee for service, payment of interest and other charges | For cash payments within Ameriabank premises | According to the Bank’s tariffs for individuals:<br>https://ameriabank.am/en/ |
| Fines and penalties | Late payment fines and penalties (principal and interest) | In case of failing to make payment when due under the loan agreement, the customer shall be required to pay a penalty in the amount of 0.13% of the overdue loan or interest for each day beyond terms.<br>No fines or penalties are charged in case of repayment before the due date. |

### Essential Terms of Installment Loans for Purchase of Services

| Column 1 | Column 2 | Column 3 |
| --- | --- | --- |
| Client&#x27;s personal details | Eligible age | From 20 до 66 inclusive |
| Client&#x27;s personal details | Eligible clients | Citizens and non-citizens of Armenia who are resident in Armenia2 |
| Terms of finance | Currency of finance | AMD |
| Terms of finance | Financing limit | 50,000-1,800,000 |
| Terms of finance | Term of finance (in months) | 6-24 |
| Terms of finance | Nominal annual interest rate | 0%-21.5% |
| Terms of finance | Annual percentage rate (APR) | 0%-24% |
| Terms of finance | Monthly account service fee | N/A |

### Essential Terms of Installment Loans for Purchase of Services (Continued)

| Column 1 | Column 2 | Column 3 |
| --- | --- | --- |
| Debt repayment options | Repayment | In case of interest: annuity, equal monthly payments consisting of a portion of loan and a portion of interest<br>Equal monthly installments schedule (equal monthly installments consisting of a portion of debt and a portion of fee) where a fee is applied |
| Security | Eligible collateral | N/A |
| Security | Maximum “loan to value” ratio | N/A |
| Fee for service, payment of interest and other charges | For non-cash payments | AMD 0 |
| Fee for service, payment of interest and other charges | For payments via Ameriabank CJSC payment kiosks | Fee applicable according to the document |
| Fee for service, payment of interest and other charges | For payments via other payment kiosks or ATMs | According to the tariffs of the relevant company operating the payment kiosk or ATM: https://ameriabank.am/en/ |
| Fee for service, payment of interest and other charges | For cash payments within Ameriabank premises | According to the Bank’s tariffs for individuals:<br>https://ameriabank.am/en/ |
| Fines and penalties | Late payment fines and penalties (principal and interest) | In case of failing to make payment when due under the loan agreement, the customer shall be required to pay a penalty in the amount of 0.13% of the overdue loan or interest for each day beyond terms.<br>No fines or penalties are charged in case of repayment before the due date. |

### Essential Terms of Installment Loans for Purchase of Solar Panels and Water Heaters

| Column 1 | Column 2 | Column 3 |
| --- | --- | --- |
| Client&#x27;s personal details | Eligible age | From 20 до 66 inclusive |
| Client&#x27;s personal details | Eligible clients | Citizens and non-citizens of Armenia who are resident in Armenia3 |
| Terms of finance | Currency of finance | AMD |
| Terms of finance | Financing limit | 200,000-6,000,000 |

### Essential Terms of Installment Loans for Purchase of Solar Panels and Water Heaters (Continued)

| Column 1 | Column 2 | Column 3 |
| --- | --- | --- |
| Terms of finance | Term of finance (in months) | 6-96 |
| Terms of finance | Nominal annual interest rate | 0%-15.5% |
| Terms of finance | Annual percentage rate (APR) | 0%-17% |
| Terms of finance | Monthly account service fee | N/A |
| Debt repayment options | Repayment | In case of interest: annuity, equal monthly payments consisting of a portion of loan and a portion of interest<br>Equal monthly installments schedule (equal monthly installments consisting of a portion of debt and a portion of fee) where a fee is applied |
| Security | Eligible collateral | The purchased item serves as a collateral. |
| Security | Maximum “loan to value” ratio | 100% |
| Fee for service, payment of interest and other charges | For non-cash payments | AMD 0 |
| Fee for service, payment of interest and other charges | For payments via Ameriabank CJSC payment kiosks |  |
| Fee for service, payment of interest and other charges | For payments via other payment kiosks or ATMs | According to the tariffs of the relevant company operating the payment kiosk or ATM: https://ameriabank.am/en/ |
| Fee for service, payment of interest and other charges | For cash payments within Ameriabank premises | According to the Bank’s tariffs for individuals:<br>https://ameriabank.am/en/ |
| Fines and penalties | Late payment fines and penalties (principal and interest) | In case of breach of the due date under the agreement, the Client will be required to pay a penalty in the amount of 0.13% of overdue loan or interest for each day beyond terms.<br>No fines or penalties are charged in case of repayment before the due date. |

**Row-level citation labels:**

- `document:3:d390a42c11fa:page:4:table:0:row:2`: EX-005 cites combined row evidence; the exact quote could not be localized to one cell.

### Service Fee

| Purpose | Rates &amp; Fees |
| --- | --- |
| Modification of finance terms | AMD 15,000 |
| Change of the repayment date | AMD 5,000 |

### Required documents

| Column 1 | Column 2 |
| --- | --- |
| Documents required for installment loan application | Personal identification documents (originals):<br>a non-biometric passport, biometric passport,<br>identification card, personal public services number of Armenia<br>Other documents as necessary or appropriate |

### Provision of statements, information and copies of documents

| Provision of statements, information and copies of documents | Rates &amp; Fees |
| --- | --- |
| Provision of up to 1 year-old account statements, copies of account statements or other documents kept in electronic form | Free |
| Provision of more than 1 year-old account statements or copies of account statements or provision of other documents kept in electronic form | AMD 5,000 per annual statement per account, VAT included |
| Provision of copies of documents kept in paper or backdated more than 1 year and kept in electronic form | AMD 5,000 per document, VAT included |
| Provision of references: To holders of 3+ months old accounts | AMD 3,000, VAT included |
| Provision of references: To holders of less than 3 months old accounts | AMD 5,000, VAT included |

---

## Terms and conditions

Source: <https://ameriabank.am/Portals/0/files/Personal/web-info-eng.pdf>

Ameriabank CJSC  
+37410 561111, office@ameriabank.am

## TERMS AND CONDITIONS OF PROFILE OPENING AND MAINTENANCE ON AMERIABANK&#x27;S WEBSITE

Approved by the Management Board resolution # 03/184/17 dated December 7, 2017  
Current edition was approved by the Management Board resolution # 01/23/24 dated February 12, 2024  
Effective from the date specified below:

### 1. General Provisions

1.1. These terms and conditions (hereinafter the “Terms”) govern the relationships in connection with profile opening on Ameriabank CJSC (hereinafter the “Bank” www.ameriabank.am) website, its maintenance, use, as well as usage of loan and related banking services through such profile.

1.2. Your profile is a system (hereinafter “System”) designed to enable you to use loan services through the web. It enables you to submit loan applications, information required for taking a loan, references, consents and other documents through distance channels, get the Bank&#x27;s decision on approval or rejection of the loan and sign loan agreements. The System is used for communication between the Bank and the Client during the lending process.

### 2. Creating and Using a Profile

2.1. In order to create a profile, you should fill out your personal data specified in clause 2.2 herein and set a password meeting the minimum security requirements of the Bank. The Bank will send one-time password(s) (OTP) to your mobile number and/or your email address. You should enter the OTP to activate/verify your profile in the System.

2.2. Personal data means:  
2.2.1. For individuals:

- • Your first and last names (in English)
- • Email address
- • Personal public service number (social card number)
- • Mobile number

2.2.2. For legal entities and individual entrepreneurs (companies):

- • Company name in English
- • TIN
- • Email address
- • Mobile number

Please note that you may use the personal public service number (social card number), TIN, mobile number and email address for creating one user only.

2.3. To log in into your profile, please

- • type your mobile number and the password in the System (for individuals)
- • type your TIN and the password in the System (for legal entities)

If you have forgotten your password or wish to change it, press the relevant button and follow the actions that will be sent to your mobile and/or your email address.

2.4. You may change the data (other than TIN) you specified in your profile at any time. To change the number of your social card/personal public services number, email address and mobile number, you should apply to the Bank by one of the following channels:

- • at the Bank’s branch or via the Bank’s Internet/Mobile Banking system, if you are a customer of the Bank,

11RBD/12CIB RL 72-01-11, ed. 6  
Effective date: February 15, 2024.

- • at the Bank’s branch, if you are not a customer of the Bank

2.5. By pressing “I agree”, “I accept”, “I confirm” or any similar button denoting your consent you confirm that you understand that you are electronically submitting your consent and expressing your intention to be bound by the respective agreements, applications, transactions and other documents, as well as to pay for such transactions. Your consent and your intention apply, in particular, to all those actions and records that you make in your profile.

2.6. Such actions and records may include but are not limited to the following:  
2.6.1. Uploading of documents, which means that you&#x27;ve submitted the respective documents to the Bank. Furthermore, uploading of a document will mean that you confirm that such documents are valid, true to the original and any information contained therein is accurate and true.  
2.6.2. Typing the code in the “Enter the code” field, pressing “Accept and sign” or other similar buttons, typing “V” in the relevant fields which will mean that you have read, got familiar with, agreed to, accepted and signed the respective agreements, terms, consents, other documents and texts and agree to perform the conditions stipulated thereunder, in a proper and timely manner.  
2.6.3. Other actions and records on your profile, which result in respective implications of such actions and records.

2.7. You are liable for the authenticity, completeness and accuracy of the actions in your profile and their consequences. We will treat any action you perform in your profile as a direct and true expression of your will. The Bank shall not be held liable for any misprints and other mistakes made by you.

2.8. You shall:  
2.8.1. keep confidential information required for signing into your profile, not disclose the passwords, codes and other data required for opening and use of your profile or otherwise make them known to third parties, and not perform any actions which may lead to such information becoming accessible to third parties,  
2.8.2. promptly give notice to the Bank of any unauthorized login into your profile or such attempt and/or any unauthorized transaction through your profile or such attempt,  
2.8.3. reimburse all the costs, losses and damages that the Bank may incur as a result of non-performance or improper performance of your obligations by you or execution of any instruction received by the Bank from you through your profile.

2.9. The Bank has the right to:  
2.9.1. change at its sole discretion the services provided to you through your profile and/or the manner and/or procedure of their provision giving you the respective notice in person or publishing the notice on its website,  
2.9.2. suspend provision of services through your profile at its sole discretion, whether temporarily, in full or in part, in order to carry out technical maintenance of the System or ensure security, reliability and smooth operation of the System,  
2.9.3. suspend or terminate use of your profile if it is used in violation of these Terms, or if the Bank has reason to suspect that your profile is used by third parties,  
2.9.4. not execute or suspend execution of the payment orders submitted by you through your profile or impose other limitations on the use of your profile due to anti money laundering and terrorism finance combating considerations and other reasons stipulated under the Republic of Armenia laws, if the validity and/or legality of such payment orders is not apparent.

### 3. Submitting a loan application and executing a loan agreement

3.1. In order to submit a loan application, you should fill in the required information in your profile. In a few minutes after you submit the loan application, you will receive a bank message about the loan approval, loan refusal or the necessity for additional review.

3.2. If the loan is approved, you should accept/sign the loan terms within 7 (seven) calendar days after loan approval. Otherwise, your loan application will be automatically canceled.

3.3. There are two ways you may accept/sign the loan terms:

- • Through your profile
- • By visiting the Bank

11RBD/12CIB RL 72-01-11, ed. 6  
Effective date: February 15, 2024.

### 4. Accepting the terms of the loan and other related services through your profile

4.1. If you choose to accept the terms of the loan and other related services through your profile, the Bank will need to verify your identity. For identification, individuals should have an active payment card issued by Ameriabank CJSC. Legal entities and individual entrepreneurs should have a bank account with Ameriabank CJSC, an ID card issued in accordance with the Armenian laws and regulations and a reader used for working with the ID card, putting an electronic digital signature on electronic documents and using online services. You should fill out the number and validity period of your card (issued by Ameriabank) in the relevant field (applicable to individuals). We will send an SMS message to your mobile number available in our records, providing you with a one-time password. If you enter the one-time password correctly, you&#x27;ll be considered a properly identified customer. Once you accept the terms of the loan and other related services, the loan amount will be transferred to your existing or a newly opened account in accordance with the provisions of your loan agreement.

### 5. Accepting the terms of the loan and other related services during visit to the Bank

5.1. If you choose to accept the terms of the loan and other related services during your visit to the Bank, the Bank will need to verify your identity. For identification, you should approach the Bank and submit your identification document. Once you sign the terms of the loan and other related services, the loan amount will be transferred to your existing or a newly opened account in accordance with the provisions of your loan agreement.

### 6. Other terms

6.1. We may place our logo or the logo of our partner, firm name and other items protected by copyright on your profile. All such items are protected by the Armenian laws and international treaties, and their illegal use may lead to penalty sanctions against you.

6.2. You agree to bear all costs and expenses the Bank may incur if you use you profile improperly or violate these Terms.

6.3. Consent to these Terms is not binding upon the Bank and does not create an obligation to provide you a loan or another service.

6.4. These Terms will become effective for you from the moment you accept them. Any amendments to the Terms shall become effect from the moment you&#x27;re given a respective notice, including publication of such information on the Bank&#x27;s website.

11RBD/12CIB RL 72-01-11, ed. 6  
Effective date: February 15, 2024.

---

## Main conditions of installment financing services for individuals provided by Ameriabank CJSC

Source: <https://ameriabank.am/Portals/0/files/basic_conditions_of_installment_financing-service_eng.pdf>

Ameriabank CJSC  
+(37410) 561111, +(37412) 561111, office@ameriabank.am

## Terms and Conditions of Consumer Finance Service

Approved by Management Board Resolution # 01/157/20 as of December 29, 2020.  
This edition was approved by the Resolutions # 01/20/26 and #03/30/26 as of February 27, 2026 and February 12, 2026, with effect from March 16, 2026.

### Contents

- 1. Terms and Definitions..................................................................................................................................................................1
- 2. General Provisions.......................................................................................................................................................................2
- 3. Main Terms of the Credit, calculations and Payments.................................................................................................................4
- 4. Specifics of Buying Products on Credit. ......................................................................................................................................5
- 5. Communication between the Parties, Exchange of Information. .................................................................................................7
- 6. Early termination of the Installment Debt Repayment Agreement. Prepayment of the Credit. ...................................................8

### 1. Terms and Definitions

1.1. Bank or We - Ameriabank CJSC.

1.2. General Terms and Conditions - General Terms and Conditions of Service for Individuals (11RBD RL 72-01-01)1.

1.3. Consumer Finance Tariffs - Terms of Consumer Finance2, as well as other terms of consumer finance services applicable under the campaigns held by the Bank, which may differ from these terms or apply in addition to them.

1.4. Company - A legal entity or an individual entrepreneur cooperating with the Bank, which provides services, performs works and/or sells goods to individuals.

1.5. Product - Products sold by the Company, including Solar Panels, the purchase of which may be financed by the Bank in accordance with the Consumer Finance Tariffs and these terms and conditions.

1.6. Solar Panels - Solar plants, water heaters and other similar items.

1.7. Company Services - Services provided and/or works performed by the Company, the purchase of which may be financed by the Bank in accordance with the Consumer Finance Tariffs and these terms and conditions.

1.8. Customer or You - An individual purchasing Products or Services from the Company under installment arrangements in accordance with these terms and conditions.

1.9. Party or Parties - The Bank or the Customer whenever used in singular, and the Bank and the Customer together whenever used in plural.

1.10. Consumer Finance Service - The service provided by the Bank, including the following actions performed in accordance with these terms and conditions and the Consumer Finance Tariffs:  
1.10.1. Signing an Installment Sale Agreement / Paid Services Agreement/ Mixed Agreement,  
1.10.2. Assignment of monetary claim under the Installment Sale Agreement/ Paid Services Agreement/ Mixed Agreement by the Company to the Bank and acquisition of the assigned monetary claim by the Bank,  
1.10.3. Acceptance of Offer (execution of Installment Debt Repayment Agreement)

1.11. Installment Sale Agreement - Agreement signed between the Company and the Customer in the form approved by the Bank, according to which the Company sells the Product to the Customer on the installment plan. From the time the Product is delivered to the Customer up to the payment, it is considered pledged at the Company to secure respective payment obligations of the Customer.

1.12. Paid Services Agreement - Agreement signed between the Company and the Customer in the form approved by the Bank, according to which the Company provides Services to the Customer, and the Customer agrees to pay for the Service received.

1 General Terms and Conditions of Service for Individuals (11RBD RL 72-01-01), approved by Management Board Resolution # 02/03/15 as of February 4, 2015. Available at https://ameriabank.am/en/useful-links

2 Ameriabank CJSC Terms of Consumer Finance (11RBD PL 72-34), approved by Management Board Resolution # 01/35/17 as of November 22, 2017. Available at https://ameriabank.am/en/useful-links

1.13. Mixed Agreement - Agreement signed between the Company and the Customer in the form approved by the Bank, according to which the Company sells the Product and provides Services to the Customer on the installment plan. Furthermore, from the time the Product is delivered to the Customer until performance of the Customer’s obligations under the Mixed Agreement, the Product purchased shall be considered pledged at the Company to secure performance of the Customer’s payment obligations under such agreement.

1.14. Solar Panels Supply and Works Agreement - Agreement signed between the Company and the Customer in the form approved by the Bank, according to which the Company supplies Solar Panels to the Customer and performs related installation, configuration, testing and commissioning works on the installment plan. Furthermore, from the time the Product is delivered to the Customer until performance of the Customer’s obligations under the Mixed Agreement, the Product purchased shall be considered pledged at the Company to secure performance of the Customer’s payment obligations under such agreement.

1.15. Installment Purchase Agreement - Installment Sale Agreement, Paid Services Agreement, Mixed Agreement and/or Solar Panels Supply and Works Agreement.

1.16. Installment Debt Repayment Agreement - Installment Debt Repayment Agreement executed between the Bank and the Customer in the form approved by the Bank via Acceptance of the Offer by the Bank in accordance with these terms and conditions. The Installment Debt Repayment Agreement, these terms and conditions and the Consumer Finance Tariffs together stipulate the terms of how the Customer is supposed to return the amount of the Company’s claim arising out of the Installment Purchase Agreement to the Bank in case the Company assigns such claim to the Bank.

1.17. Offer - Written offer to enter into an Installment Debt Repayment Agreement presented by the Customer to the Bank in the form approved by the Bank, and where it is technically possible to provide consumer finance at the Company’s premises in paperless manner, also the Bank’s respective template on making inquiries for the purpose of processing the personal data and on the manner of approval of the documents under consumer finance, along with the Installment Debt Repayment Agreement, with indication of the essential terms of the Credit if financed by the Bank, including those specified in clause 3.1 of these terms and conditions.

1.18. Acceptance - Act of accepting the Offer by the Bank in accordance with the rules prescribed by these terms and conditions and the Offer. Acceptance of the Offer by the Bank results in execution of an Installment Debt Repayment Agreement between the Bank and the Customer.

1.19. Credit - The amount owed by the Customer to the Bank as of the effective date of the Agreement.

1.20. Interest rate - Nominal annual interest rate specified in the Installment Debt Repayment Agreement.

1.21. Interest - The amount of interest accrued on the Credit at the set interest rate.

1.22. Service Fee - The service fee specified in the Installment Debt Repayment Agreement.

1.23. Schedule - The schedule for repayment of the Credit, Interest and the Service Fee specified in Annex 1 to the Installment Debt Repayment Agreement forming an integral part thereto.

1.24. Fines and penalties - Fines and penalties under the Installment Debt Repayment Agreement payable for non-performance or improper performance of the payment obligations under the Installment Debt Repayment Agreement.

### 2. General Provisions

2.1. These Terms and Conditions set out the main conditions of the relationships arising in connection with provision of the Consumer Finance Service by the Bank to the individuals. The Bank may also provide consumer finance to the Customer online, in which case the Customer, by selecting on the Company’s website the Product(s) and/or the Company’s service(s) payable under consumer finance or by opening the link and/or QR code sent to the Customer by the Company, generated by the Company’s employee and containing the Product(s) and/or the Company’s service(s) payable by the Customer under consumer finance, as well as the price of the Product(s) and/or service(s), is redirected to the Bank’s online consumer finance domain to proceed with the finance process. The Bank may set a validity term for the link and/or QR code.

2.2. These terms and conditions constitute Service Terms as defined in the General Terms and Conditions. The General Terms and Conditions apply to the legal relationships governed by these terms and conditions to the extent that these terms and conditions do not provide otherwise.

2.3. These terms and conditions are an invitation to make an Offer, and the legal relationship between the Parties under these terms and conditions arises / enters into force upon submission of the Offer by you to the Bank in accordance with these terms and conditions and the Consumer Finance Tariffs on terms satisfactory to the Bank, as well as upon acceptance of the Offer by the Bank. Once the Offer is accepted by the Bank, the Offer, these terms and conditions and the Consumer Finance Tariffs together shall constitute one and the same agreement concluded between the Parties, valid until the full and proper performance of the obligations under the Installment Debt Repayment Agreement by the Parties.

2.4. If submitted in paper, the Offer shall be made in 2 (two) counterparts equal in legal effect. The Customer and the Bank receive one counterpart each. The offer submitted online, as well as the offer submitted at the Company’s premises (where it is technically possible to sign/seal the documents between the Parties in electronic manner) is made in electronic form and becomes available to the Customer when sent by the Bank to the Customer’s email.

2.5. The Installment Debt Repayment Agreement is considered to be signed on the day when the Bank sends the Acceptance notice, with the venue being the location of the Bank. The Acceptance shall be performed by sending an SMS about acceptance of the Offer by the Bank to any of your mobile numbers specified in the Offer within 5 (five) calendar days (term for acceptance) upon signing of the Offer by you, unless otherwise agreed in connection with the manner and timing for acceptance of the Offer.

2.6. Where the Bank sends the Acceptance notice to any of your mobile numbers specified in the Offer, the Acceptance notice shall be deemed received by you provided that you have not notified the Bank in writing about the change of the respective mobile numbers.

2.7. In case of sending the Acceptance notice, other notices and information to your contact data specified in the Offer, the risk of Third party access to them shall be borne by you.

2.8. The Bank’s actions towards performance of the terms of the agreement specified in the Acceptance notice within the time frames defined for the Acceptance shall be deemed Acceptance of the Offer submitted in paper.

2.9. The Offer may not be recalled within the term set for acceptance.

2.10. Signing of the Installment Debt Repayment Agreement proves that the Company’s assigns its monetary claim to the Customer to the Bank, such claim arising out of the Installment Purchase Agreement signed between the Customer and the Company and specified in the Installment Debt Repayment Agreement. According to the terms therein contained, the Bank agrees to enable the Customer to pay the amount of the respective debt in installments, and the Customer agrees to repay it together with the interest and the service fees. The Acceptance shall be at the same time a notice on the assignment of the monetary claim specified in the Offer, hence from the time of its receipt you shall be considered to have been notified about the assignment to the Bank of the Company’s monetary claim arising out of the relevant agreement signed with the Company and specified in the Offer.

2.11. Any and all references to the Installment Debt Repayment Agreement shall include the Offer, these terms and conditions and the Consumer Finance Tariffs forming an integral part of the Installment Debt Repayment Agreement, unless otherwise explicitly stated.

2.12. If any portion of any condition or provision of the Installment Debt Repayment Agreement is held by a relevant authority to be invalid or unenforceable, for any reason, such provision shall have a limited interpretation and shall not affect the validity of other provisions and conditions of the Installment Debt Repayment Agreement, which shall continue in force and be enforceable to the maximum extent allowed by the Legislation.

2.13. Any amendment to these terms and conditions that may apply to the relationships between the Parties shall be made via a respective reference in the Offer or via covenants signed in addition to the Installment Debt Repayment Agreement which may be executed at any stage of the service upon mutual consent of the Parties.

2.14. We shall provide information about non-performance or improper performance of the your payment obligations under the Installment Debt Repayment Agreement to the Credit Bureau and/or the credit registry of the central bank of Armenia within 3 (three) business days in accordance with the approved procedure. You understand and confirm that you are aware that information on overdue obligations, submitted to the Credit Bureau, may affect your credit history and future attempts to get financial instruments in an adverse manner.

2.15. Where the Party’s obligations under the Installment Debt Repayment Agreement are secured by collateral, and such collateral has been damaged or destroyed, that Party shall within the term agreed with the Bank restore the collateral or replace it with other equivalent collateral to the reasonable satisfaction of the other Party, even if such damage or destruction was the result of force majeure.

2.16. We have the right to revise these terms and conditions and the Consumer Finance Tariffs unilaterally by notifying you in the manner prescribed by the General Terms and Conditions.

2.17. The amount of the Credit under the Installment Debt Repayment Agreement may be refinanced out of the Bank borrowings, which will make it possible to apply a lower Interest Rate and/or Service Fee rate to the eligible Customers, as compared to the rate that would apply without refinancing, all other things being equal (the exact Interest Rate and/or Service Fee shall be specified in the Offer). In such cases, if, nonetheless, refinancing is rejected or canceled (terminated) or terms of refinancing are modified due to non-compliance of the credit with the terms of refinancing, and/or absence of available funds at the refinancing organization, and/or change of the interest rate on the loan issued to the Bank by the refinancing organization, and/or termination of the agreement executed between the Bank and the refinancing organization, and/or for other reasons prescribed by the agreement, the Bank has the right to revise the Interest Rate and/or the Service Fee unilaterally during the term of the Installment Debt Repayment Agreement so as to align it with the rate that would apply in the absence of refinancing. Where the Interest Rate and/or the Service Fee are modified in the cases specified above, their maximum size shall be determined by the Offer. In any case, the revised Interest Rate and/or the Service Fee may not exceed the maximum size of the Interest Rate and/or the Service Fee envisaged under the Consumer Finance Tariffs, and the annual percentage rate changed as a result of the Interest Rate and/or the Service Fee revision may not exceed the maximum annual percentage rate specified in the Consumer Finance Tariffs. We shall notify you about the change specified herein in accordance with these terms and conditions at least 7 (seven) business days in advance. Such notice shall be a basis for application of the revised Interest Rate and/or the Service Fee from the date specified in the notice.

2.18. The following changes (including but not limited to) in circumstances shall not be considered material and hence shall not be used as a basis for termination or modification of the Installment Debt Repayment Agreement pursuant to the Legislation governing material change of circumstances: (i) current or pending deterioration of the Customer’s financial condition, including due to changes in market conditions or market environment, financial or other crisis, such threat or its worsening, (ii) loss of the Customer’s property or sources of income, any fluctuations in their composition and/or frequency and/or volume; and/or changes in any circumstances affecting the Customer’s paying capacity; changes in the scope or termination of any benefits provided by any Government agency or other entities (including, but not limited to subsidy, refinancing, cofinancing for any part of obligation or terms of refund/financing of any expenses aimed at performance of any part of obligation, tax or customs benefits), (iii) volatility of exchange rates and/or restrictions related to border controls.

### 3. Main Terms of the Credit, calculations and Payments.

3.1. The specific terms of the Credit, including, but not limited to, the amount of the Credit, nominal annual interest rate, annual percentage rate, Service Fees, total cost, Fines and Penalties, the collateral securing performance of the obligations under the Installment Debt Repayment Agreement, as well as the Customer-preferred means of the communication between the Parties under the Installment Debt Repayment Agreement shall be specified in the Offer.

3.2. The Credit shall be provided in a cashless form lump-sum. The Credit repayment method shall be annuity, i.e. equal installments consisting of a portion of Credit, a portion of Interest and a portion of the Service Fee.

3.3. The Interest shall accrue on the outstanding amount of the Credit daily on the basis of a 365-day year. The Service Fees shall accrue on the amount of the Credit monthly at the beginning of each month.

3.4. The size of the annual percentage rate and the total cost specified in the Offer shall be determined as of the date when the Offer is made and may be revised during the duration of the Installment Debt Repayment Agreement by the Bank in the cases and in accordance with the procedure specified in these terms and conditions. Such revision may result from the change in the size of the Service Fees, repayment of the Credit by the Customer before the date specified in the Installment Debt Repayment Agreement or due to the change of other components included in their calculation.

3.5. The Customer shall repay the amount of the Credit, Interest and Service Fees to the Bank in accordance with the Schedule.

3.6. The Amount of the Credit, Interest and Service Fees shall be deemed paid from the time such amounts are paid to the Bank’s teller or are credited to the Bank’s correspondent account.

3.7. Any payment you make under the Installment Debt Repayment Agreement shall be used for the repayment of your indebtedness under the Installment Debt Repayment Agreement in a succession determined by the Bank.

3.8. You give your consent and instruction for the Bank to allow any third party applying to the Bank, that will possess information about your credit obligations to the extent satisfactory to the Bank, to repay your credit obligations. In such cases, the Third Party may gain access to information about you that contains banking secrecy.

3.9. The Bank has a right to charge the amounts payable to the Bank by you under the Installment Debt Repayment Agreement (including the amount of the Credit and/or Interest and/or Service Fees and/or Fines and Penalties (if any), and/or other

amounts payable to the Bank under the Installment Debt Repayment Agreement) to any account (if any) you hold with the Bank, including current, card and deposit accounts, through direct debiting without your further instruction or consent. The Bank shall be entitled to charge the specified amounts directly on the date such amounts become due and/or on the dates following that date, until actual payment (including payment through direct debiting) date. Where there are no sufficient funds on your AMD accounts for direct debiting of the payable amounts, the Bank shall charge the respective amounts to your accounts in other currency by converting the payable amounts to the required currency at the then effective rate of the Bank. The Bank shall exercise the right specified in this clause at its sole discretion and you may not further refer to or rely upon this clause for (i) disputing accrual of the fines and penalties envisaged under the Installment Debt Repayment Agreement for non-performance or improper performance of your payment obligations under the Installment Debt Repayment Agreement and (ii) charging of such fines and penalties by the Bank.

3.10. Liabilities under this Installment Debt Repayment Agreement can be subject to offset only upon consent of the Bank.

3.11. The Bank has the right to assign the monetary claim to the Customer arising out of the Installment Debt Repayment Agreement and its rights over the collateral to the third parties. Starting from the time the monetary claim is assigned to the Third parties, the accrual of the Interest and the Service Fees shall terminate, unless otherwise stated in the assignment notice sent to you. From the time of the monetary claim assignment, any other terms of the Installment Debt Repayment Agreement relating to such monetary claim (including your rights and responsibilities) shall continue to apply in the same manner to the person that has acquired such monetary claim except for the terms the validity of which was the result of the special creditor status under the Installment Debt Repayment Agreement, including availability of special banking permit (license).

### 4. Specifics of Buying Products on Credit.

4.1. In case of buying Products in the scope of Consumer Finance Service, you shall pledge the Product specified in the Offer at the Company to secure proper performance of the obligations under the Installment Debt Repayment Agreement, such pledge effective from the time the Installment Debt Repayment Agreement comes into force. In such case, you shall act as a pledgor.

4.2. The pledged Product shall not be transferred to the Bank but shall remain in your possession.

4.3. You have the right to possess and use the pledged Product as per its intended purpose and freely manage the Product after performance of the payment obligations to the Bank in full.

4.4. If the Product purchased comes with a warranty, the warranty service of the sold Product will be carried out by the Company in accordance with the warranty certificate and the rules/conditions set by the Company.

4.5. The delivery of the Product purchased by you through consumer finance received from the Bank will be carried out by the Company in the manner agreed between the Company and you.

4.6. The LTV (Credit amount to the value of collateral) ratio shall be specified in the Offer. The Bank doesn’t plan revaluation of the collateral, termination of the pledge or imposing additional pledge requirement during the validity term of the Installment Debt Repayment Agreement, hence the LTV ratio shall remain unchanged during the term of the Installment Debt Repayment Agreement. Nonetheless, in some cases if there is any change in the LTV ratio that occurs due to the circumstances not envisaged at the time of execution of the Installment Debt Repayment Agreement, and such change results in the change in the Installment Debt Repayment Agreement terms, you shall be notified about the specified change via execution of an amendment to the Installment Debt Repayment Agreement signed with the Bank to incorporate the change in the respective terms of the Installment Debt Repayment Agreement. Where revision of the LTV ratio does not result in the change of the Installment Debt Repayment Agreement terms, the Bank shall notify you in writing or verbally as requested by you, within 5 (five) business days upon submission of such request.

4.7. The Bank has the right to:  
4.7.1. check the availability, condition, maintenance conditions of the Product used as collateral, for which you shall ensure the necessary environment and not prevent the Bank from exercising this right;  
4.7.2. request you to take appropriate measures to ensure proper maintenance of the Product used as collateral and to terminate any action likely to result in its destruction or damage to it;  
4.7.3. obtain insurance of the Solar Panels used as collateral against the risks determined by the Bank, such insurance being on the terms and conditions satisfactory to the Bank through an acceptable insurance company, and the Customer being specified as a beneficiary. The notice on the insurance shall be sent to you by the Bank or the respective insurance company. The list of insurance companies acceptable for the Bank and their essential terms of

insurance are accessible at the Bank’s website3. The terms must be also provided by insurance companies at the time of signing of insurance agreement, in the manner stipulated by the Legislation (in paper or electronic form or via specifying the public source where such terms may be obtained). The Bank or the respective insurance company shall notify you about the fact of insurance by providing the essential terms of insurance or indicating the public source where such terms are available. In case of failure to receive the notice within 10 (ten) days, you shall apply to the Bank for obtaining the terms or request the Bank to provide the contact data of the insurer for obtaining the terms from the insurer. You shall read the essential terms and shall bear the risk of all possible adverse consequences for the failure to read them. Unavailability of the links to the terms specified herein or failure to read the essential terms of insurance for any reason shall not, in any way, affect the terms of the Installment Debt Repayment Agreement and/or their interpretation.  
4.7.4. Your right to claim insurance compensation for the Solar Panels pledged as collateral (from the time such right arises), as well as the amount of the insurance compensation transferred in the name of the beneficiary, i.e. you, in connection with the Solar Panels used as collateral (from the time such amount is transferred to the Bank) shall be pledged by you in favor of the Bank by virtue of the Installment Debt Repayment Agreement, to secure proper performance of you obligations under the Installment Debt Repayment Agreement, including the amount of the Credit, Interest, Service Fees and other payments under the Installment Debt Repayment Agreement. By signing the Installment Debt Repayment Agreement, you give your unconditional and irrevocable consent that, upon the consent (discretion) of the Bank, the amount of the insurance compensation received in connection with the Solar Panels used as collateral and your right to claim such compensation may be used solely for performance of your obligations under the Installment Debt Repayment Agreement (including early repayment) or renovation/restoration of the Solar Panels used as collateral, based on their pledge in favor of the Bank.  
4.7.5. The Bank shall determine the cases and conditions for execution and termination of the insurance contracts, which the scope of which the Bank shall also have the right to terminate the insurance contracts for the Solar Panels used as collateral signed in accordance with this clause, in the event (inter alia) the Bank assigns its monetary claim to the third parties in accordance with these terms and conditions. The Bank shall determine at its sole discretion whether to exercise its right to obtain insurance for the Solar Panels as specified in this clause. Absence of the insurance, whether in whole or in part, shall not be considered as a breach of its obligations and/or negligence by the Bank. In addition, in no event such circumstances may be referred to as a basis for claiming compensation of the damages in case of loss, destruction, damage of the Solar Panels used as collateral, etc., in which case the Bank shall not be held liable in any manner since the Bank may obtain insurance for the Solar Panels used as collateral to mitigate its own risks while acting in the capacity of a pledgee. All costs of obtaining insurance for the Solar Panels used as collateral shall be borne by you via reimbursing to the Bank of the costs incurred by the latter. In such case, the insurance costs shall be included in the Service Fee.  
4.7.6. The Bank has the right to receive from and provide to the insurer any information in relation to the insurance of the Solar Panels used as collateral that contains insurance secrecy.

4.8. We will not be liable for:  
4.8.1. The quality of the Product, the term of delivery of the Product to you, as well as for the breach of such term by the Company. Any complaint and/or demand and/or question regarding the Company’s products should be submitted to the Company in the manner established by the latter.  
4.8.2. The updatedness, completeness and accuracy of the information posted on the Company’s website, the Company’s products, their availability/being in stock, specifications, features, prices, purchase possibilities and order, any discrepancy/change in any information posted on the Company’s website, as well as the impossibility of the actual sale of the Product for any reason at the time of purchase. You cannot file any claim to the Bank in relation to the above specified, including demanding compensation for the losses, expenses or lost profits incurred as a result of any and all cases listed in this clause

4.9. You shall:  
4.9.1. maintain the pledged Product properly and refrain from actions which may result in deterioration of the quality or destruction of the pledged Product;

3 List of insurance companies: https://ameriabank.am/en/useful-links

4.9.2. take necessary measures to protect the pledged Product (including from the unauthorized actions and claims of third parties) and forthwith notify the Bank about any adverse events resulting in deterioration of the condition of the pledged Product or about any unauthorized actions;  
4.9.3. upon the Bank’s request, in case of non-performance or improper performance of the obligations under the Installment Debt Repayment Agreement, provide the pledged Product to the Bank, based on an acceptance act, for the latter to change its storage location;  
4.9.4. upon the Bank’s request notify the Bank about the location of the Product used as collateral and allow the Bank to check the availability and conditions of the Product;

4.10. In case of failure in performance or improper performance of obligations under this Installment Debt Repayment Agreement by you, the Bank, subject to the Legislation, shall be entitled to enforce its security interest in the pledged Product, once the liabilities become overdue.

4.11. In case of failure in performance or improper performance of obligations under the Installment Debt Repayment Agreement by you, the Bank has the right to foreclose on the pledged Product and sell it through a judicial procedure or by any out-of-court method not prohibited by the Legislation. Moreover, the Bank has the right to sell the pledged Product on behalf of you at the public auction (hereinafter the “Auction”) in accordance with the Legislation.

4.12. In case you fail to perform your obligations under the Installment Debt Repayment Agreement or perform them improperly, the Bank shall give written notice to you in a due manner, and, where required so by the Legislation, to the registering authority as well, notifying about the enforcement of the pledged Product through an out-of-court procedure (hereinafter the “Enforcement Notice”), after which the Bank shall have the right to take reasonable measures to store, maintain and protect the pledged Product. You shall not hinder the Bank in such actions and shall ensure that the Bank has a possibility to dismantle and transport the pledged Product. You shall provide the pledged Product to the Bank, on the basis of an acceptance act, together with all the related accessories and supporting documents (data sheets, technical specifications, quality certificates, user manual, etc.) and other documents required by the Bank. Furthermore, the transfer of the pledged Product and execution of an acceptance act in accordance with this clause shall not be deemed enforcement of the pledged Product and in no event it may be construed and/or interpreted as the enforcement of the pledged Product by such transfer or execution of the acceptance act.

4.13. 2 (Two) months after the delivery of the Enforcement Notice to you and, where required so by the Installment Debt Repayment Agreement, to the registering authority, the Bank shall sell the pledged Product in accordance with the Legislation by any method not prohibited by the Legislation.

4.14. You may incur additional expenses in case of the sale of the pledged Product. After the enforcement and sale costs, including taxes, have been repaid out of the proceeds of sale of the pledged Product, the Bank shall withhold the full amount of its claims under the Installment Debt Repayment Agreement and return the rest of the proceeds to you.

4.15. Should the proceeds from the sale of the pledged Product be insufficient to repay the Bank’s claims in full volume, the Bank may foreclose on your property in the manner stipulated in the Legislation.

4.16. From the time of enforcement and sale of the pledged Product, and origination of the new owner’s title to the Product used as collateral, your rights over the collateral shall terminate.

4.17. In case of non-performance of the obligations under the Enforcement Notice in full and in the time frames specified in the notice, upon expiry of the specified period such obligations (outstanding Credit balance, Interest accrued by that time, Service Fees, Fines and Penalties and other charges) shall be deemed overdue liabilities as defined under the Legislation, i.e. you shall be entitled to terminate the out-of-court enforcement and sale of the Product used as collateral once they perform the overdue liabilities in full.

4.18. You confirm that in addition to this chapter of these terms and conditions, you have also read the procedure established by Legislation for the out-of-court enforcement of collateral, and fully understand and accept the consequences arising out of the application of the same by the Bank.

### 5. Communication between the Parties, Exchange of Information.

5.1. You agree that the Bank may apply the manner of notification specified in the Installment Debt Repayment Agreement in any communication with you, as well as in case of non-performance or improper performance of obligations by you, including for delivery of extrajudicial enforcement notices, court notices/claims/advance claims/materials/documents.

5.2. The Bank shall give you at least 1 (one) day prior notice about outstanding liabilities in the manner specified by you in the Offer (by SMS and electronically), as well as about sending the information on non-performance or improper performance of the payment obligations under the Installment Debt Repayment Agreement you to the Credit Bureau and/or the Credit Registry of the Central Bank of Armenia in the established manner.

5.3. The Bank has the right to study your financial condition and to request relevant documents and information, and you agree to facilitate conducting of such study, if necessary, and to provide all the required documents and information within the time frame set by the Bank.

5.4. By submitting your personal identification documents to the Company’s employee for the purpose of obtaining consumer finance, you agree that, in order to ensure the accurate completion of the Application , the personal details contained in the personal identification documents submitted by you will be generated automatically instead of manual input thereof, for which purpose the Company’s employee will send inquiries to the organizations running the respective databases and place the obtained into the appropriate fields of the Application.  
The consent contained herein will remain valid for the entire duration of the legal relationship between you and the Bank, subject to the Customer’s verbal request to obtain consumer finance from the Bank. The Client acknowledges and agrees that the information specified in this clause is provided to the Bank.

5.5. Hereby the Parties agree that in case you make a partial repayment of the Credit before the due date, the Bank shall make the new repayment schedule available to you via Online/Mobile Banking system (if any) or shall provide it to you, at your request and discretion, either in person on the Bank premises or send it to your email address. Notwithstanding the way of delivery, the new repayment schedule shall be provided to you bearing the signature of the Bank’s authorized representative and the Bank’s stamp, without your signature.

5.6. You hereby authorize the Bank to provide any information in the scope of provision of the consumer finance service to you and in connection with it and receive such information, including the agreement package, throughout the term of the Installment Debt Repayment Agreement, irrespective of whether it contains banking and/or trade secret or not.

### 6. Early termination of the Installment Debt Repayment Agreement. Prepayment of the Credit.

6.1. The Bank has the right to demand from you to repay the Credit, Interest accrued as of the payment date, Services Fees, Fines and Penalties and other amounts payable to the Bank under the Installment Debt Repayment Agreement (if any), whether with termination of the Installment Debt Repayment Agreement or without it, by giving at least 7 (seven) business days advance notice to you in the manner prescribed by the Installment Debt Repayment Agreement if:  
6.1.1. the data (documents and other information) provided at any time by you are found to be untrustworthy or false;  
6.1.2. you fail to perform any obligation (including payment obligations) under the Installment Debt Repayment Agreement or perform them improperly;  
6.1.3. you are found to have or have had overdue financial commitments and/or classified indebtedness to the Bank and/or to Third parties;  
6.1.4. there are circumstances expressly evidencing that the amount of the Credit, Interest and Service Fees will not be repaid within the term specified in the Installment Debt Repayment Agreement (including bankruptcy or preconditions for bankruptcy);  
6.1.5. your assets (property) are under or become subject to lien or arrest or become otherwise encumbered under the Legislation and are not immediately released;  
6.1.6. there are judicial, criminal, administrative, insolvency or other proceedings initiated against you by Government authorities, which are likely to affect your financial standing and/or stability in a materially adverse manner;  
6.1.7. there are other grounds stipulated in the Legislation and/or the General Terms and Conditions.

6.2. You have the right to:  
6.2.1. Perform the payment obligations under the Installment Debt Repayment Agreement fully or in part without paying any fines and penalties; in case of early settlement of payment obligations under the Installment Debt Repayment Agreement, the total credit cost shall be proportionally reduced by the amount of the Interest (calculated on a daily basis) and Service fees (calculated on monthly basis).  
6.2.2. Terminate the Installment Debt Repayment Agreement during the cooling-off period provided for by the Legislation, at your sole discretion, for no reason, in accordance with the procedure stipulated by the Legislation.

6.3. Where you terminate the Installment Debt Repayment Agreement before the due date based on termination of the Installment Purchase Agreement, you shall make settlements with the Bank and the Company within 2 (two) business days and sign a settlements act (hereinafter – the Act). Such Act shall state whether or not the parties have any claims and obligations to each other, and where there are such claims and obligations, the Act shall define the amount and Parties thereof. You shall pay to the Bank and/or the Company any amount payable under the Act (if any) within 1 (one) business day upon signing of the Act.

---

## Consumer Finance Terms

Source: <https://ameriabank.am/Portals/0/files/Personal/previous/Consumer_finance_terms_ed16_eng.pdf>

1 Individuals resident in Armenia (hereinafter referred to as “resident individuals”) are those individuals who have been actually resident in the Republic of Armenia for 183 and more days during the tax year (Tax Code, Article 25).

2 Ameriabank CJSC Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16), approved by Management Board Resolution # 01/110/15 as of September 4, 2015). Available at https://ameriabank.am/useful-links.

3 Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01, approved by Management Board Resolution # 03/59/15 as of May 27, 2015). Available at https://ameriabank.am/useful-links.

1 Individuals resident in Armenia (hereinafter referred to as “resident individuals”) are those individuals who have been actually resident in the Republic of Armenia for 183 and more days during the tax year (Tax Code, Article 25).

2 Ameriabank CJSC Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16), approved by Management Board Resolution # 01/110/15 as of September 4, 2015). Available at https://ameriabank.am/useful-links.

3 Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01, approved by Management Board Resolution # 03/59/15 as of May 27, 2015). Available at https://ameriabank.am/useful-links.

1 Individuals resident in Armenia (hereinafter referred to as “resident individuals”) are those individuals who have been actually resident in the Republic of Armenia for 183 and more days during the tax year (Tax Code, Article 25).

2 Ameriabank CJSC Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16), approved by Management Board Resolution # 01/110/15 as of September 4, 2015). Available at https://ameriabank.am/useful-links.

3 Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01, approved by Management Board Resolution # 03/59/15 as of May 27, 2015). Available at https://ameriabank.am/useful-links.

### AMERIABANK CJSC 11RBD PL 72-34
Consumer Finance Terms (Purchase of Goods) Edition 16
Approved by Management Board Resolution # 01/35/17 as of November 22, 2017
Current edition approved by resolution #03/30/26 as of February 27, 2026, effective from March 16, 2026

| Category | Parameter | Terms and Conditions |
| --- | --- | --- |
| Customer’s personal details | Eligible age | From 20 to 66 years inclusive |
| Customer’s personal details | Customer | Citizens and non-citizens of Armenia who are resident in Armenia1 |
| Terms of finance | Currency | AMD |
| Terms of finance | Finance limit | If applying at the seller’s premises (hereinafter “the Company”)<br>Mobile phone/computer equipment: AMD 50,000 - AMD 1,000,000<br>Household appliances: AMD 50,000 - AMD 3,600,000<br>Furniture, construction materials, home improvement products and heating systems: AMD 50,000 - AMD 6,000,000<br>Household items, spare parts for cars and other goods: AMD 50,000 - AMD 2,400,000<br>If applying online via the remote consumer finance system of the Bank (irrespective of the product): AMD 50,000 - AMD 1,000,000 |
| Terms of finance | Term (months) | If applying at the Company&#x27;s premises - 6-60. A term exceeding 48 months may be set only in case of furniture, construction materials, home improvement products and heating systems.<br>If applying online via the remote consumer finance system of the Bank (irrespective of the product): 6-36 months |
| Terms of finance | Nominal annual interest rate | Fixed<br>As specified in the Cooperation Agreement between the Company and the Bank |
| Terms of finance | Monthly account service fee | As specified in the Cooperation Agreement between the Company and the Bank |
| Terms of finance | Disbursement fee (lump-sum)/down payment | As specified in the Cooperation Agreement between the Company and the Bank |
| Repayment methods | Repayment method | 1. Annuity (equal monthly installments consisting of a portion of debt and a portion of interest) where interest rate is applied<br>2. Equal monthly installments schedule (equal monthly installments consisting of a portion of debt and a portion of fee) where a fee is applied |
| Security | Eligible collateral | The purchased item serves as a collateral. |
| Security | Maximum LTV ratio | 100% |
| Required documents | Documents | • Identity document<br>• Public services number (social card) |
| Fines and penalties | Late payment fines and penalties (principal and interest) | In case of breach of the due date under the agreement, the Client shall pay to the Bank a fine<br>• In the amount of 0.13% of overdue amount and interest for each day of delay<br>• No fines and penalties are applied in case of prepayment. |
| Fee for the service, payment of interest and other charges | In case of payment via the Bank’s remote banking system | No fee is charged |
| Fee for the service, payment of interest and other charges | If paid via payment terminals and ATMs owned by the Bank | According to the Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16)2 |
| Fee for the service, payment of interest and other charges | If paid via payment terminals owned by other companies | According to the tariffs of the respective company |
| Fee for the service, payment of interest and other charges | If paid at the Bank’s branches | According to Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01)3. |
| Other fees | Payable by the Company | As specified in the Cooperation Agreement between the Company and the Bank |
| Coverage | Coverage | Republic of Armenia |

### AMERIABANK CJSC 11RBD PL 72-34
Consumer Finance Terms (Provision of Services) Edition 16
Approved by Management Board Resolution # 01/35/17 as of November 22, 2017
Current edition approved by resolution #03/30/26 as of February 27, 2026, effective from March 16, 2026

| Category | Parameter | Terms and Conditions |
| --- | --- | --- |
| Customer’s personal details | Eligible age | From 20 to 66 years inclusive |
| Customer’s personal details | Customer | Citizens and non-citizens of Armenia who are resident in Armenia1 |
| Terms of finance | Currency | AMD |

### Consumer Finance Terms (Provision of Services) (Continued)

| Category | Parameter | Terms and Conditions |
| --- | --- | --- |
| Terms of finance | Finance limit | If applying at the service provider&#x27;s premises (hereinafter “the Company”):<br>Minimum: AMD 50,000<br>Maximum: AMD 1,800,000<br>If applying via remote consumer finance system of the Bank:<br>Minimum: AMD 50,000<br>Maximum: AMD 1,000,000 |
| Terms of finance | Term (months) | If applying at the Company&#x27;s premises or via remote consumer finance system of the Bank: 6-24 |
| Terms of finance | Nominal annual interest rate | Fixed<br>As specified in the Cooperation Agreement between the Company and the Bank |
| Terms of finance | Monthly account service fee | As specified in the Cooperation Agreement between the Company and the Bank |
| Terms of finance | Disbursement fee (lump-sum)/down payment | As specified in the Cooperation Agreement between the Company and the Bank |
| Repayment methods | Repayment method | 1. Annuity (equal monthly installments consisting of a portion of debt and a portion of interest) where interest rate is applied<br>2. Equal monthly installments schedule (equal monthly installments consisting of a portion of debt and a portion of fee) where a fee is applied. |
| Required documents | Documents | • Identity document<br>• Public services number (social card) |
| Fines and penalties | Late payment fines and penalties (principal and interest) | In case of breach of the due date under the agreement, the Client shall pay to the Bank a fine<br>- In the amount of 0.13% of overdue amount and interest for each day of delay<br>- No fines and penalties are applied in case of prepayment. |
| Fee for the service, payment of interest and other charges | In case of payment via the Bank’s remote banking system | No fee is charged |
| Fee for the service, payment of interest and other charges | If paid via payment terminals and ATMs owned by the Bank | According to the Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16)2 |
| Fee for the service, payment of interest and other charges | In case of payments via payment terminals owned by other companies | According to the tariffs of the respective company |
| Fee for the service, payment of interest and other charges | If paid at the Bank’s branches | According to Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01)3. |
| Other fees | Payable by the Company | As specified in the Cooperation Agreement between the Company and the Bank |
| Coverage | Coverage | Republic of Armenia |

### AMERIABANK CJSC 11RBD PL 72-34
Terms of Consumer Finance (Purchase and Installation of Solar Panels/Water Heating Systems) Edition 16
Approved by Management Board Resolution # 01/35/17 as of November 22, 2017
Current edition approved by resolution #03/30/26 as of February 27, 2026, effective from March 16, 2026

| Category | Parameter | Terms and Conditions |
| --- | --- | --- |
| Customer’s personal details | Eligible age | From 20 to 66 years inclusive |
| Customer’s personal details | Customer | Citizens and non-citizens of Armenia who are resident in Armenia1 |
| Terms of finance | Currency | AMD |
| Terms of finance | Credit limit | Minimum: AMD 200,000<br>Maximum: AMD 6,000,000 |
| Terms of finance | Term (months) | 6-120 |
| Terms of finance | Nominal annual interest rate | Fixed<br>As specified in the Cooperation Agreement between the company selling solar panels/water heating systems (hereinafter “the Company”) and the Bank |
| Terms of finance | Monthly account service fee | As specified in the Cooperation Agreement between the Company and the Bank |
| Terms of finance | Disbursement fee (lump-sum)/down payment | As specified in the Cooperation Agreement between the Company and the Bank |
| Repayment methods | Repayment method | 1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest) where interest rate is applied<br>2. Equal monthly installments schedule (equal monthly installments consisting of a portion of loan and a portion of fee) where a fee is applied. |
| Security | Eligible collateral | The purchased item serves as a collateral. |
| Security | Maximum LTV ratio | 100% |
| Required documents | Documents | 1. Identity document<br>2. Public services number (social card)<br>3. The bank can request an ownership certificate of the property and electricity and gas bills for the most recent 6 months. |

### Terms of Consumer Finance (Purchase and Installation of Solar Panels/Water Heating Systems) (Continued)

| Category | Parameter | Terms and Conditions |
| --- | --- | --- |
| Fines and penalties | Late payment fines and penalties (principal and interest) | In case of breach of the due date under the agreement, the Client shall pay to the Bank a fine:<br>- In the amount of 0.13% of overdue amount and interest for each day of delay<br>- No fines and penalties are applied in case of prepayment. |
| Fee for the service, payment of interest and other charges | In case of payment via the Bank’s remote banking system | No fee is charged |
| Fee for the service, payment of interest and other charges | If paid via payment terminals and ATMs owned by the Bank | According to the Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16)2 |
| Fee for the service, payment of interest and other charges | In case of payments via payment terminals owned by other companies | According to the tariffs of the respective company |
| Fee for the service, payment of interest and other charges | If paid at the Bank’s branches | According to Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01)3. |
| Other fees | Payable by the Company | As specified in the Cooperation Agreement between the Company and the Bank |
| Coverage | Coverage | Republic of Armenia |

---

## Consumer Finance Terms

Source: <https://ameriabank.am/Portals/0/files/Personal/previous/Consumer_finance_terms_ed15_eng.pdf>

## AMERIABANK CJSC | 11RBD PL 72-34<br>Consumer Finance Terms (Purchase of Goods)<br>Edition 15<br>Effective date: May 26, 2025

Approved by Management Board Resolution # 01/35/17 as of November 22, 2017  
Current edition approved by resolution # 01/142/25 as of September 5, 2025, effective from the date specified above.

## AMERIABANK CJSC | 11RBD PL 72-34<br>Consumer Finance Terms (Provision of Services)<br>Edition 15<br>Effective date: September 25, 2025

Approved by Management Board Resolution # 01/35/17 as of November 22, 2017  
Current edition approved by resolution # 01/142/25 as of September 5, 2025, effective from the date specified above.

## AMERIABANK CJSC | 11RBD PL 72-34<br>Terms of Consumer Finance (Purchase and Installation of Solar Panels/Water Heating Systems)<br>Edition 15<br>Effective date: September 25, 2025

Approved by Management Board Resolution # 01/35/17 as of November 22, 2017  
Current edition approved by resolution # 01/142/25 as of September 5, 2025, effective from the date specified above.

### Consumer Finance Terms (Purchase of Goods)

| Category | Parameter | Terms and Conditions |
| --- | --- | --- |
| Customer&#x27;s personal details | Eligible age | From 20 to 66 years inclusive |
| Customer&#x27;s personal details | Customer | Citizens and non-citizens of Armenia who are resident in Armenia1 |
| Terms of finance | Currency | AMD |
| Terms of finance | Finance limit | If applying at the seller’s premises (hereinafter “the Company”)<br>Mobile phone/computer equipment: AMD 50,000 - AMD 1,000,000<br>Household appliances: AMD 50,000 - AMD 3,600,000<br>Furniture, construction materials, home improvement products and heating systems: AMD 50,000 - AMD 6,000,000<br>Household items, spare parts for cars and other goods: AMD 50,000 - AMD 2,400,000<br>If applying online via the Company’s website (irrespective of the product): AMD 50,000 - AMD 1,000,000 |
| Terms of finance | Term (months) | 6-60. A term exceeding 48 months may be set only in case of furniture, construction materials, home improvement products and heating systems.<br>If applying online via the Company’s website (irrespective of the product): 6-36 months |
| Terms of finance | Nominal annual interest rate | Fixed<br>As specified in the Cooperation Agreement between the Company and the Bank |
| Terms of finance | Monthly account service fee | As specified in the Cooperation Agreement between the Company and the Bank |
| Terms of finance | Disbursement fee (lump-sum)/down payment | As specified in the Cooperation Agreement between the Company and the Bank |
| Repayment methods | Repayment method | 1. Annuity (equal monthly installments consisting of a portion of debt and a portion of interest) where interest rate is applied<br>2. Equal monthly installments schedule (equal monthly installments consisting of a portion of debt and a portion of fee) where a fee is applied |
| Security | Eligible collateral | The purchased item serves as a collateral. |
| Security | Maximum LTV ratio | 100% |
| Required documents | Documents | • Identity document<br>• Public services number (social card) |
| Fines and penalties | Late payment fines and penalties (principal and interest) | In case of breach of the due date under the agreement, the Client shall pay to the Bank a fine<br>• In the amount of 0.13% of overdue amount and interest for each day of delay<br>• No fines and penalties are applied in case of prepayment. |
| Fee for the service, payment of interest and other charges | In case of payment via the Bank’s remote banking system | No fee is charged |
| Fee for the service, payment of interest and other charges | If paid via payment terminals and ATMs owned by the Bank | According to the Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16)2 |
| Fee for the service, payment of interest and other charges | If paid via payment terminals owned by other companies | According to the tariffs of the respective company |
| Fee for the service, payment of interest and other charges | If paid at the Bank’s branches | According to Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01)3. |
| Other fees | Payable by the Company | As specified in the Cooperation Agreement between the Company and the Bank |
| Coverage | Coverage | Republic of Armenia |

> 1 Individuals resident in Armenia (hereinafter referred to as “resident individuals”) are those individuals who have been actually resident in the Republic of Armenia for 183 and more days during the tax year (Tax Code, Article 25).

> 2 Ameriabank CJSC Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16), approved by Management Board Resolution # 01/110/15 as of September 4, 2015). Available at https://ameriabank.am/useful-links.

### Consumer Finance Terms (Provision of Services)

| Category | Parameter | Terms and Conditions |
| --- | --- | --- |
| Customer&#x27;s personal details | Eligible age | From 20 to 66 years inclusive |
| Customer&#x27;s personal details | Customer | Citizens and non-citizens of Armenia who are resident in Armenia1 |
| Terms of finance | Currency | AMD |
| Terms of finance | Finance limit | Minimum: AMD 50,000<br>Maximum: AMD 1,800,000 |
| Terms of finance | Term (months) | 6-24 |
| Terms of finance | Nominal annual interest rate | Fixed<br>As specified in the Cooperation Agreement between the service company (hereinafter “the Company”) and the Bank |
| Terms of finance | Monthly account service fee | As specified in the Cooperation Agreement between the Company and the Bank |
| Terms of finance | Disbursement fee (lump-sum)/down payment | As specified in the Cooperation Agreement between the Company and the Bank |
| Repayment methods | Repayment method | 1. Annuity (equal monthly installments consisting of a portion of debt and a portion of interest) where interest rate is applied<br>2. Equal monthly installments schedule (equal monthly installments consisting of a portion of debt and a portion of fee) where a fee is applied. |
| Required documents | Documents | • Identity document<br>• Public services number (social card) |
| Fines and penalties | Late payment fines and penalties (principal and interest) | In case of breach of the due date under the agreement, the Client shall pay to the Bank a fine<br>- In the amount of 0.13% of overdue amount and interest for each day of delay<br>- No fines and penalties are applied in case of prepayment. |
| Fee for the service, payment of interest and other charges | In case of payment via the Bank’s remote banking system | No fee is charged |
| Fee for the service, payment of interest and other charges | If paid via payment terminals and ATMs owned by the Bank | According to the Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16)2 |
| Fee for the service, payment of interest and other charges | In case of payments via payment terminals owned by other companies | According to the tariffs of the respective company |
| Fee for the service, payment of interest and other charges | If paid at the Bank’s branches | According to Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01)3. |
| Other fees | Payable by the Company | As specified in the Cooperation Agreement between the Company and the Bank |
| Coverage | Coverage | Republic of Armenia |

> 1 Individuals resident in Armenia (hereinafter referred to as “resident individuals”) are those individuals who have been actually resident in the Republic of Armenia for 183 and more days during the tax year (Tax Code, Article 25).

> 2 Ameriabank CJSC Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16), approved by Management Board Resolution # 01/110/15 as of September 4, 2015). Available at https://ameriabank.am/useful-links.

> 3 Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01, approved by Management Board Resolution # 03/59/15 as of May 27, 2015). Available at https://ameriabank.am/useful-links.

### Terms of Consumer Finance (Purchase and Installation of Solar Panels/Water Heating Systems)

| Category | Parameter | Terms and Conditions |
| --- | --- | --- |
| Customer&#x27;s personal details | Eligible age | From 20 to 66 years inclusive |
| Customer&#x27;s personal details | Customer | Citizens and non-citizens of Armenia who are resident in Armenia1 |
| Terms of finance | Currency | AMD |
| Terms of finance | Credit limit | Minimum: AMD 200,000<br>Maximum: AMD 6,000,000 |
| Terms of finance | Term (months) | 6-120 |
| Terms of finance | Nominal annual interest rate | Fixed<br>As specified in the Cooperation Agreement between the company selling solar panels/water heating systems (hereinafter “the Company”) and the Bank |
| Terms of finance | Monthly account service fee | As specified in the Cooperation Agreement between the Company and the Bank |
| Terms of finance | Disbursement fee (lump-sum)/down payment | As specified in the Cooperation Agreement between the Company and the Bank |
| Repayment methods | Repayment method | 1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest) where interest rate is applied<br>2. Equal monthly installments schedule (equal monthly installments consisting of a portion of loan and a portion of fee) where a fee is applied. |
| Security | Eligible collateral | The purchased item serves as a collateral. |
| Security | Maximum LTV ratio | 100% |
| Required documents | Documents | 1. Identity document<br>2. Public services number (social card)<br>3. The bank can request an ownership certificate of the property and electricity and gas bills for the most recent 6 months. |
| Fines and penalties | Late payment fines and penalties (principal and interest) | In case of breach of the due date under the agreement, the Client shall pay to the Bank a fine<br>- In the amount of 0.13% of overdue amount and interest for each day of delay<br>- No fines and penalties are applied in case of prepayment. |
| Fee for the service, payment of interest and other charges | In case of payment via the Bank’s remote banking system | No fee is charged |
| Fee for the service, payment of interest and other charges | If paid via payment terminals and ATMs owned by the Bank | According to the Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16)2 |
| Fee for the service, payment of interest and other charges | In case of payments via payment terminals owned by other companies | According to the tariffs of the respective company |
| Fee for the service, payment of interest and other charges | If paid at the Bank’s branches | According to Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01)3. |
| Other fees | Payable by the Company | As specified in the Cooperation Agreement between the Company and the Bank |
| Coverage | Coverage | Republic of Armenia |

> 1 Individuals resident in Armenia (hereinafter referred to as “resident individuals”) are those individuals who have been actually resident in the Republic of Armenia for 183 and more days during the tax year (Tax Code, Article 25).

> 2 Ameriabank CJSC Terms and Conditions of Transactions through Payment Terminals (11RBD/12CIB PL 72-16), approved by Management Board Resolution # 01/110/15 as of September 4, 2015). Available at https://ameriabank.am/useful-links.

> 3 Ameriabank CJSC Tariffs for Individuals (11RBD PL 72-01-01, approved by Management Board Resolution # 03/59/15 as of May 27, 2015). Available at https://ameriabank.am/useful-links.

---

## https://ameriabank.am/en/API/WebsitesCreative/MyContentManager/API/Init?portalId=0&tabId=6131&moduleId=43423

Source: <https://ameriabank.am/en/API/WebsitesCreative/MyContentManager/API/Init?portalId=0&tabId=6131&moduleId=43423>

---

## https://ameriabank.am/en/API/WebsitesCreative/MyContentManager/API/Init?portalId=0&tabId=6131&moduleId=54605

Source: <https://ameriabank.am/en/API/WebsitesCreative/MyContentManager/API/Init?portalId=0&tabId=6131&moduleId=54605>

---

## https://ameriabank.am/en/API/WebsitesCreative/MyContentManager/API/Init?portalId=0&tabId=6131&moduleId=58572

Source: <https://ameriabank.am/en/API/WebsitesCreative/MyContentManager/API/Init?portalId=0&tabId=6131&moduleId=58572>

---

## https://ameriabank.am/en/API/WebsitesCreative/MyContentManager/API/Init?portalId=0&tabId=6131&moduleId=54239

Source: <https://ameriabank.am/en/API/WebsitesCreative/MyContentManager/API/Init?portalId=0&tabId=6131&moduleId=54239>

---

## https://ameriabank.am/en/API/WebsitesCreative/MyContentManager/API/Init?portalId=0&tabId=6131&moduleId=54578

Source: <https://ameriabank.am/en/API/WebsitesCreative/MyContentManager/API/Init?portalId=0&tabId=6131&moduleId=54578>

## Planner audit

- `ev_f5e1aebee996c3a0a0aeab47` / `document:1:59f29da194a8:page:1:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c106172123a4e6ef97e9022b` / `document:1:59f29da194a8:page:1:block:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_16068f837b8bab32ab94c5e5` / `document:1:59f29da194a8:page:1:block:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2dd0b537c04799eb6386473c` / `document:1:59f29da194a8:page:1:block:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c5fb526a6eb1a04f6eceb77c` / `document:1:59f29da194a8:page:1:block:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7ce4ba5545c0d3def4fde1d3` / `document:1:59f29da194a8:page:1:note:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b1909c82bfe050f36c6796e1` / `document:1:59f29da194a8:page:1:note:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_8d631d14db293f98516497a5` / `document:1:59f29da194a8:page:1:note:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a744b40e50123ae54b82bc61` / `document:1:59f29da194a8:page:1:table:0:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c06a0e8386819e99b3d2371b` / `document:1:59f29da194a8:page:1:table:0:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_120d8e61a89328c20a325d4c` / `document:1:59f29da194a8:page:1:table:0:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_862e6cc865ec98dde7f10e56` / `document:1:59f29da194a8:page:1:table:0:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_65f1e7e5202a964af9cb891f` / `document:1:59f29da194a8:page:1:table:0:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_43cfa89f2df72f166b37fe67` / `document:1:59f29da194a8:page:1:table:0:row:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_59bffdd682a079aeadd0f290` / `document:1:59f29da194a8:page:1:table:0:row:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_255806deb8ba97d15b009665` / `document:1:59f29da194a8:page:2:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7678c67b4851960ac0f5ae3e` / `document:1:59f29da194a8:page:2:block:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0fa5f76f00eb911fb3147922` / `document:1:59f29da194a8:page:2:table:0:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7423ef478d20f3b772cb7c13` / `document:1:59f29da194a8:page:2:table:0:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_de0ae7a514694c064fefd4b3` / `document:1:59f29da194a8:page:2:table:0:row:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_340f189044996453c1a1c9a3` / `document:1:59f29da194a8:page:2:table:0:row:11` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4133ef8566d648aa95f5fa21` / `document:1:59f29da194a8:page:2:table:0:row:12` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_60483727e4685437e32b4f2e` / `document:1:59f29da194a8:page:2:table:0:row:13` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_cf96f9f0f8f9ae0b0798d145` / `document:1:59f29da194a8:page:2:table:0:row:14` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_69affb45471e1d0a3c30a183` / `document:1:59f29da194a8:page:2:table:0:row:15` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5a167bf1c9c1bf0a43bef530` / `document:1:59f29da194a8:page:2:table:0:row:16` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_410060692a8e8ed474f7f4a8` / `document:1:59f29da194a8:page:2:table:0:row:17` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_cb884dbc8b0d02723b630b51` / `document:1:59f29da194a8:page:2:table:0:row:18` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_38ffbaa18b60ae62e3ddcdf3` / `document:1:59f29da194a8:page:2:table:0:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0ed0b413cbd247bc185266ef` / `document:1:59f29da194a8:page:2:table:0:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_214388b1080da8934215a998` / `document:1:59f29da194a8:page:2:table:0:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9fd794a36df87521e78f75c7` / `document:1:59f29da194a8:page:2:table:0:row:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_383cd638055544b4d2228cb8` / `document:1:59f29da194a8:page:2:table:0:row:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_372fbaf9c05948f6dcd2d3f6` / `document:1:59f29da194a8:page:2:table:0:row:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4f6bb445aa2ddc0c1e9d0aae` / `document:1:59f29da194a8:page:2:table:0:row:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c11bd5e872a34db94be7422e` / `document:1:59f29da194a8:page:2:table:0:row:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_8dcaae19a0b4cc5a75f78109` / `document:1:59f29da194a8:page:3:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fc0c15c4fd642765303e9179` / `document:1:59f29da194a8:page:3:table:0:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e507e48417ca0f4448fa87db` / `document:1:59f29da194a8:page:3:table:0:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ac15e29dba3bf4bde5baf53d` / `document:1:59f29da194a8:page:3:table:0:row:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e90e2ed1bdc56d68dae107f2` / `document:1:59f29da194a8:page:3:table:0:row:11` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b999cf22a6e1fc7480cc8e1e` / `document:1:59f29da194a8:page:3:table:0:row:12` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2d944be32831e827f6437381` / `document:1:59f29da194a8:page:3:table:0:row:13` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4becae18fb0850cc5d6da78f` / `document:1:59f29da194a8:page:3:table:0:row:14` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c49a284ad8caf99b63d4ddb1` / `document:1:59f29da194a8:page:3:table:0:row:15` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_661f8fb6b74f791129bc3196` / `document:1:59f29da194a8:page:3:table:0:row:16` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2ff6ef80ef59c5358e6aeb9b` / `document:1:59f29da194a8:page:3:table:0:row:17` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_baf8df7351493a4144f44ea4` / `document:1:59f29da194a8:page:3:table:0:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5fcf5add984c98aebb49b606` / `document:1:59f29da194a8:page:3:table:0:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a113f36cf467a2c470925349` / `document:1:59f29da194a8:page:3:table:0:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_98b262ff8977e752ff35f1c7` / `document:1:59f29da194a8:page:3:table:0:row:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_53ff41de68da4946f336d3ad` / `document:1:59f29da194a8:page:3:table:0:row:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d50ab34c42cbc7849835c17f` / `document:1:59f29da194a8:page:3:table:0:row:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3a95f151a7d5db247376f43a` / `document:1:59f29da194a8:page:3:table:0:row:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1ca6b15a7f8384ea041e525b` / `document:1:59f29da194a8:page:3:table:0:row:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_99a58807bb4c2885e7165e9b` / `document:1:59f29da194a8:page:4:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_8fcf1610565039fce0e18eb8` / `document:1:59f29da194a8:page:4:table:0:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_62454cd438e9bb452646fead` / `document:1:59f29da194a8:page:4:table:0:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_54eb264308f3203d77f7b938` / `document:1:59f29da194a8:page:4:table:0:row:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_81825eac3f22d2dadb5908ca` / `document:1:59f29da194a8:page:4:table:0:row:11` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0f43cc56008897ed1978539f` / `document:1:59f29da194a8:page:4:table:0:row:12` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b941a068a5c34b68d2e798e9` / `document:1:59f29da194a8:page:4:table:0:row:13` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d9b2dd8056c25ed7982bcd2b` / `document:1:59f29da194a8:page:4:table:0:row:14` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_205222268efe391bddff9e93` / `document:1:59f29da194a8:page:4:table:0:row:15` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_473fcb82c1b4e3420685b445` / `document:1:59f29da194a8:page:4:table:0:row:16` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e82e798293a02473fe718017` / `document:1:59f29da194a8:page:4:table:0:row:17` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b76c2fecee30c03fae0d8128` / `document:1:59f29da194a8:page:4:table:0:row:18` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fe11c53c647f469a86d221d5` / `document:1:59f29da194a8:page:4:table:0:row:19` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_813ca121fa92f5daccbcc0ae` / `document:1:59f29da194a8:page:4:table:0:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_992528f402162e602affaeb4` / `document:1:59f29da194a8:page:4:table:0:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0712078d5bea71e5bb169c38` / `document:1:59f29da194a8:page:4:table:0:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_cfced8c64059f0635bb175f0` / `document:1:59f29da194a8:page:4:table:0:row:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e12ad8593e7447a18a671ecf` / `document:1:59f29da194a8:page:4:table:0:row:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_bcc651a3cd5ad225cc0e9a88` / `document:1:59f29da194a8:page:4:table:0:row:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_15485d220a71715cd6cb7f15` / `document:1:59f29da194a8:page:4:table:0:row:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b99d7c9aca0b708ff2095f0f` / `document:1:59f29da194a8:page:4:table:0:row:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_71ee70c6b911d0581c345818` / `document:1:59f29da194a8:page:5:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_bc83c78af08d07d6b346e691` / `document:1:59f29da194a8:page:5:table:0:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_30aca4399138ba6884b8b044` / `document:1:59f29da194a8:page:5:table:0:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e2003b172a3821357c55c3c1` / `document:1:59f29da194a8:page:5:table:0:row:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3376810f6e40440b48bda7c0` / `document:1:59f29da194a8:page:5:table:0:row:11` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d8657234e6390cbf8adad640` / `document:1:59f29da194a8:page:5:table:0:row:12` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d4f7ddc81d2ae32934371dc2` / `document:1:59f29da194a8:page:5:table:0:row:13` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2c5d9f56652d78a8889fed5f` / `document:1:59f29da194a8:page:5:table:0:row:14` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_655b1f45ff32790478e28ad3` / `document:1:59f29da194a8:page:5:table:0:row:15` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7a290ec4ac12f9d0e940f5fc` / `document:1:59f29da194a8:page:5:table:0:row:16` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_cfad7ab880e5a31c2a3438c5` / `document:1:59f29da194a8:page:5:table:0:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_80b21bfe8f33b70a54dd7e5f` / `document:1:59f29da194a8:page:5:table:0:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_dd1b7016c93cc0c331f78ae8` / `document:1:59f29da194a8:page:5:table:0:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a4c88b0106f74ad835053a66` / `document:1:59f29da194a8:page:5:table:0:row:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_95dfcdc673939899fe6e5520` / `document:1:59f29da194a8:page:5:table:0:row:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_41e03f9250dd40b8f6d8bc93` / `document:1:59f29da194a8:page:5:table:0:row:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_467a5b47299fd6a4de0e35af` / `document:1:59f29da194a8:page:5:table:0:row:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e49c6b139f2b6c0a6e88deb1` / `document:1:59f29da194a8:page:5:table:0:row:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b83dc04b68f0d6f684e4336f` / `document:1:59f29da194a8:page:6:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e9bef4768d8ae3839b529577` / `document:1:59f29da194a8:page:6:table:0:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e333faabd8ce3ae55b3bbf84` / `document:1:59f29da194a8:page:6:table:0:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_238b3505ceb0a466820a19c1` / `document:1:59f29da194a8:page:6:table:0:row:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4bf770345be7cbe4d0466e74` / `document:1:59f29da194a8:page:6:table:0:row:11` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2fe5a0a7a9892773986855b2` / `document:1:59f29da194a8:page:6:table:0:row:12` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_510a7c01874be5225ec78de7` / `document:1:59f29da194a8:page:6:table:0:row:13` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_be507038c9b55a7356015612` / `document:1:59f29da194a8:page:6:table:0:row:14` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_770ae158319f8a9db29b3822` / `document:1:59f29da194a8:page:6:table:0:row:15` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6193ef26be317a43a8b049a1` / `document:1:59f29da194a8:page:6:table:0:row:16` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e3381a73707e21a756a350b1` / `document:1:59f29da194a8:page:6:table:0:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_68165d30886d7ce7e97b4cb7` / `document:1:59f29da194a8:page:6:table:0:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fd80400457b1c36af2c0484e` / `document:1:59f29da194a8:page:6:table:0:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4d30026277d3314b901c2f18` / `document:1:59f29da194a8:page:6:table:0:row:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e936383b7d3b35f4fca0a43d` / `document:1:59f29da194a8:page:6:table:0:row:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_837571106a3dbdea3de409f1` / `document:1:59f29da194a8:page:6:table:0:row:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a9937a295fbd1c7384546ceb` / `document:1:59f29da194a8:page:6:table:0:row:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f815926cf58ab44e412e09b9` / `document:1:59f29da194a8:page:6:table:0:row:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f7abf63d8b25d273933f1cc4` / `document:2:744c784c8603:page:1:table:0:note:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_15545ae0d678861277135cfa` / `document:2:744c784c8603:page:1:table:0:note:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_582bca74f1f6a0cfb6776500` / `document:2:744c784c8603:page:1:table:0:note:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9016901658b7cb885dcd1145` / `document:2:744c784c8603:page:1:table:0:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_637a118ac9812c15030d6c4d` / `document:2:744c784c8603:page:1:table:0:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f04ddf8b6ac3157a95f40563` / `document:2:744c784c8603:page:1:table:0:row:10` — **EXTRACTED: repayment**; packets: fees_and_repayment
- `ev_2a36a5140d412090109325c4` / `document:2:744c784c8603:page:1:table:0:row:11` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_23c0bfab1961af7371e2bbff` / `document:2:744c784c8603:page:1:table:0:row:12` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9fb1cc9937d873129c809d7a` / `document:2:744c784c8603:page:1:table:0:row:13` — **SENT, NOT CITED**; packets: required_documents
- `ev_60ad8d6a04cbd2aed19ab96b` / `document:2:744c784c8603:page:1:table:0:row:14` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9ffaf55e2f70bcea57926803` / `document:2:744c784c8603:page:1:table:0:row:15` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5d0423adf936207ce32c393d` / `document:2:744c784c8603:page:1:table:0:row:16` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3709513bb64b1e6e15f4882a` / `document:2:744c784c8603:page:1:table:0:row:17` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fdc5fe5dd23736aaa95ca7c2` / `document:2:744c784c8603:page:1:table:0:row:18` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c514655bfd9f2cac7b2002ee` / `document:2:744c784c8603:page:1:table:0:row:19` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3350d0624a87b92f898acab3` / `document:2:744c784c8603:page:1:table:0:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2a0a1826d9dc17dd3d71d7b1` / `document:2:744c784c8603:page:1:table:0:row:20` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_81f97bf80a6211e1f6d25e51` / `document:2:744c784c8603:page:1:table:0:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_86796ad0f395548ca835ad5b` / `document:2:744c784c8603:page:1:table:0:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3d6f8030c39b1c59483d22de` / `document:2:744c784c8603:page:1:table:0:row:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_49c6048e9d937376789cfb9d` / `document:2:744c784c8603:page:1:table:0:row:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d4f686bf75a7a49135f10ee8` / `document:2:744c784c8603:page:1:table:0:row:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c0a7774cd0dedd8424de2547` / `document:2:744c784c8603:page:1:table:0:row:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c20776baa48e0ed34893e556` / `document:2:744c784c8603:page:1:table:0:row:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_edb91fa9354162c8263582a5` / `document:2:744c784c8603:page:2:table:0:note:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d84a5036df4990515df3fd1c` / `document:2:744c784c8603:page:2:table:0:note:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0607aa1d824dec77229eba5e` / `document:2:744c784c8603:page:2:table:0:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_279d8eaa7e656b523b6d0825` / `document:2:744c784c8603:page:2:table:0:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_69dd3ce76524445705095430` / `document:2:744c784c8603:page:2:table:0:row:10` — **SENT, NOT CITED**; packets: fees_and_repayment
- `ev_e5764f5228a5d4d03fb2c605` / `document:2:744c784c8603:page:2:table:0:row:11` — **SENT, NOT CITED**; packets: required_documents
- `ev_a5bd57728fb86c99fb0af87a` / `document:2:744c784c8603:page:2:table:0:row:12` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f2914504083ce328b7c913ae` / `document:2:744c784c8603:page:2:table:0:row:13` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5c39d7b202ee23d3224c1a34` / `document:2:744c784c8603:page:2:table:0:row:14` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4074b7fd5ab64e6b29a50307` / `document:2:744c784c8603:page:2:table:0:row:15` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_081e38288b6bd5f8a2639817` / `document:2:744c784c8603:page:2:table:0:row:16` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a7039e817b78f4ee90a197ee` / `document:2:744c784c8603:page:2:table:0:row:17` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2e72eaca926d6da9fcbe70a5` / `document:2:744c784c8603:page:2:table:0:row:18` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_bd447c5edbb53810338aedf5` / `document:2:744c784c8603:page:2:table:0:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_40b5a9ba4b84301a59c4c30a` / `document:2:744c784c8603:page:2:table:0:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_8815486f5bd43e5155413cde` / `document:2:744c784c8603:page:2:table:0:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ddea834ed5095f45b06b4012` / `document:2:744c784c8603:page:2:table:0:row:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a90bb61e504a298b9c843dd0` / `document:2:744c784c8603:page:2:table:0:row:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e7e2444a48a06537add47792` / `document:2:744c784c8603:page:2:table:0:row:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a2eb819ca10a8e683930f8e2` / `document:2:744c784c8603:page:2:table:0:row:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7838504f7ecc4384fc0a06bc` / `document:2:744c784c8603:page:2:table:0:row:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4ae44b557d86e2aab1ca6ead` / `document:2:744c784c8603:page:3:note:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ee0f7718b35fc7cb3fa3d7a1` / `document:2:744c784c8603:page:3:table:0:note:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f2276941db7a74044d9281ec` / `document:2:744c784c8603:page:3:table:0:note:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_416d61985a1d9dc2a835d51d` / `document:2:744c784c8603:page:3:table:0:note:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1a731c6d0d3006d70428f190` / `document:2:744c784c8603:page:3:table:0:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e68a1cf1d84ee546cc31279b` / `document:2:744c784c8603:page:3:table:0:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_caea16c8ace4f5a38b0f80f2` / `document:2:744c784c8603:page:3:table:0:row:10` — **SENT, NOT CITED**; packets: fees_and_repayment
- `ev_6897f4528919b48d92a6b166` / `document:2:744c784c8603:page:3:table:0:row:11` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f4136d20cceb2fc5b1c1a5ea` / `document:2:744c784c8603:page:3:table:0:row:12` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0fb3216c4ac927eb33e0406f` / `document:2:744c784c8603:page:3:table:0:row:13` — **EXTRACTED: required_documents**; packets: required_documents
- `ev_b76701b00038e58dc1f6fb15` / `document:2:744c784c8603:page:3:table:0:row:14` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b6dfcd977559a15da35d35c4` / `document:2:744c784c8603:page:3:table:0:row:15` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a647ee0651898897bc2cdac3` / `document:2:744c784c8603:page:3:table:0:row:16` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d35c2359c10c895e5e0041fe` / `document:2:744c784c8603:page:3:table:0:row:17` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_89a2b4d0d99e7ada34d01ebf` / `document:2:744c784c8603:page:3:table:0:row:18` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3723e374df02ac3723a99ebe` / `document:2:744c784c8603:page:3:table:0:row:19` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1fe4edb7f53353daafb5da14` / `document:2:744c784c8603:page:3:table:0:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_76216aff3ea1bc5b8b45e5bf` / `document:2:744c784c8603:page:3:table:0:row:20` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_492a1194002f339129ddb9ee` / `document:2:744c784c8603:page:3:table:0:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d1ab5273fd49fbff8b0a1cc0` / `document:2:744c784c8603:page:3:table:0:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5f7d5d991f002d7a1d493ace` / `document:2:744c784c8603:page:3:table:0:row:5` — **EXTRACTED: credit_limit**; packets: product_details
- `ev_b9aba5fdcb33b4078d04c653` / `document:2:744c784c8603:page:3:table:0:row:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c38fb5c25531be6c108408ec` / `document:2:744c784c8603:page:3:table:0:row:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e9711f913716d837711fb17c` / `document:2:744c784c8603:page:3:table:0:row:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0bbe4f9b55fdaeaa03627d93` / `document:2:744c784c8603:page:3:table:0:row:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_596dc79ddc8a4dd64b0b965a` / `document:3:d390a42c11fa:page:1:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9b8e23c137881c7625d66d92` / `document:3:d390a42c11fa:page:1:block:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_09ae5dd544427b5cb5210c9c` / `document:3:d390a42c11fa:page:1:block:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fac4816602ceaa0056f7db7c` / `document:3:d390a42c11fa:page:1:block:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2552e3de8716cf68cce8c26d` / `document:3:d390a42c11fa:page:1:block:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0d4a9d685918ba26a56a3fb2` / `document:3:d390a42c11fa:page:1:block:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_bd6d26187f9c464a1e71f037` / `document:3:d390a42c11fa:page:1:block:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7e98a10d869166aa325b5c12` / `document:3:d390a42c11fa:page:1:note:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f49de9e6a13b4370263dcbd7` / `document:3:d390a42c11fa:page:1:table:0:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a0922d4e1b4b2004947735da` / `document:3:d390a42c11fa:page:1:table:0:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5a2f8716dddd6322843341dd` / `document:3:d390a42c11fa:page:1:table:0:row:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_aecbbe042f4788f1e0b52d03` / `document:3:d390a42c11fa:page:1:table:0:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b3a61da5758449e73b806abe` / `document:3:d390a42c11fa:page:1:table:0:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b7fe6326d09a79a02bc77643` / `document:3:d390a42c11fa:page:1:table:0:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_67e821ec0b9bb63f4d7355b0` / `document:3:d390a42c11fa:page:1:table:0:row:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_13a611012a4eafaeaadb23db` / `document:3:d390a42c11fa:page:1:table:0:row:6` — **EXTRACTED: effective_rate**; packets: core_financial
- `ev_329cb941c24bc91032aac416` / `document:3:d390a42c11fa:page:1:table:0:row:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2b32354cd42af6951c5a582b` / `document:3:d390a42c11fa:page:1:table:0:row:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ea209d3f457d0b5b55276e3c` / `document:3:d390a42c11fa:page:1:table:0:row:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a2b30d4bed88b4972a29539d` / `document:3:d390a42c11fa:page:2:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5e1fa03e2adaf55e8f52a20e` / `document:3:d390a42c11fa:page:2:note:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_24544d7bfc88bde5392ecc27` / `document:3:d390a42c11fa:page:2:table:0:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c7b2ef9fafcfdb73f8b157fd` / `document:3:d390a42c11fa:page:2:table:0:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3ba15ac9f0778cf1eaf06f97` / `document:3:d390a42c11fa:page:2:table:0:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_639a738345a5fc3261a9a05d` / `document:3:d390a42c11fa:page:2:table:0:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5c886948794d4e739ba681b1` / `document:3:d390a42c11fa:page:2:table:0:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_33188d4028b59755220d30fe` / `document:3:d390a42c11fa:page:2:table:1:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_540f795e1210522a53b458a0` / `document:3:d390a42c11fa:page:2:table:1:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6ce05d5a7673a1fae6543e72` / `document:3:d390a42c11fa:page:2:table:1:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0d6374e308f855af948cc686` / `document:3:d390a42c11fa:page:2:table:1:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0a73b525b398a6521dcfd22f` / `document:3:d390a42c11fa:page:2:table:1:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_036a982174bfed28d83a6b69` / `document:3:d390a42c11fa:page:2:table:1:row:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2bdef33b0305ce1834ee95f4` / `document:3:d390a42c11fa:page:2:table:1:row:6` — **SENT, NOT CITED**; packets: core_financial
- `ev_b63d0e80c970260c04a7d99f` / `document:3:d390a42c11fa:page:2:table:1:row:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b16eceb2ecd56eff37dc7a80` / `document:3:d390a42c11fa:page:3:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_dd696d67dc401e3ab43df457` / `document:3:d390a42c11fa:page:3:note:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_bec88db51f0600e81dfb0b64` / `document:3:d390a42c11fa:page:3:table:0:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9705328e8678c5725793eb2a` / `document:3:d390a42c11fa:page:3:table:0:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_027a6b16ce1b99b2c3a79d76` / `document:3:d390a42c11fa:page:3:table:0:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5a10881dd7e48e38671f8431` / `document:3:d390a42c11fa:page:3:table:0:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_87242795dad20a14dcee11f5` / `document:3:d390a42c11fa:page:3:table:0:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5a19d002187bb4b037d47e33` / `document:3:d390a42c11fa:page:3:table:0:row:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0b703a13b457e2c6ab388b36` / `document:3:d390a42c11fa:page:3:table:0:row:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_78ce39ff6981d1617fa98a2d` / `document:3:d390a42c11fa:page:3:table:0:row:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3f251ce9e02deac0bd217e88` / `document:3:d390a42c11fa:page:3:table:1:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a94f792beeda94e3c9d6cbc0` / `document:3:d390a42c11fa:page:3:table:1:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_20e2c0cc11af354660acf54a` / `document:3:d390a42c11fa:page:3:table:1:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2392152a00a12464836c463f` / `document:3:d390a42c11fa:page:3:table:1:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5f4cebafd1028afd68e644d4` / `document:3:d390a42c11fa:page:4:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0c43a09272f09b221583eeb8` / `document:3:d390a42c11fa:page:4:table:0:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b8b4f31282c5afcf96167b2e` / `document:3:d390a42c11fa:page:4:table:0:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0b7c2a3cadca022ccf2a3302` / `document:3:d390a42c11fa:page:4:table:0:row:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_69df7c28bce383780167d6d3` / `document:3:d390a42c11fa:page:4:table:0:row:11` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0ea1d54177e5c5a92a82700d` / `document:3:d390a42c11fa:page:4:table:0:row:2` — **EXTRACTED: effective_rate**; packets: core_financial
- `ev_d21035d1d46844494197227e` / `document:3:d390a42c11fa:page:4:table:0:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b7928bbc4d93fa9f91c72668` / `document:3:d390a42c11fa:page:4:table:0:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d8a89204bf789cb8c0007204` / `document:3:d390a42c11fa:page:4:table:0:row:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4d22c77319208b727e23fbef` / `document:3:d390a42c11fa:page:4:table:0:row:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f2dcf8ea057f8d304b7b1432` / `document:3:d390a42c11fa:page:4:table:0:row:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_59e82cbac6b0a1c4a0d06cdd` / `document:3:d390a42c11fa:page:4:table:0:row:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4be41295778db87160516d3d` / `document:3:d390a42c11fa:page:4:table:0:row:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f4f579414c8362eaaa99294d` / `document:3:d390a42c11fa:page:4:table:1:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_31d2cada52f2eb351feefd78` / `document:3:d390a42c11fa:page:4:table:1:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_92dd7842b659b49902aa1eda` / `document:3:d390a42c11fa:page:5:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0355d73c98e78b408287d6aa` / `document:3:d390a42c11fa:page:5:block:1` — **SENT, NOT CITED**; packets: required_documents
- `ev_470fb033bb1504d622a5a97c` / `document:3:d390a42c11fa:page:5:block:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_30a158691c0e5aefd28852c4` / `document:3:d390a42c11fa:page:5:block:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c5c4aed5262c04d3ebb46bc9` / `document:3:d390a42c11fa:page:5:block:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6bfd63aef0be44a84e284d72` / `document:3:d390a42c11fa:page:5:block:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_714d41d8260728f4720a5610` / `document:3:d390a42c11fa:page:5:block:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_36d86a8c5bb5710eb2431078` / `document:3:d390a42c11fa:page:5:block:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_849a04e52d8b2a7399e70438` / `document:3:d390a42c11fa:page:5:table:0:row:0` — **SENT, NOT CITED**; packets: required_documents
- `ev_3741be8530eb0c69ab618887` / `document:3:d390a42c11fa:page:5:table:1:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_dc0f1b5049359fed73b72140` / `document:3:d390a42c11fa:page:5:table:1:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_231d23c465ff96da90f26fed` / `document:3:d390a42c11fa:page:5:table:1:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b1978d20106c5f9f95af2e54` / `document:3:d390a42c11fa:page:5:table:1:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_87d9474bb2767eb5ba3c7542` / `document:3:d390a42c11fa:page:5:table:1:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4986395b8a91e65a3ed568c8` / `document:3:d390a42c11fa:page:6:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_02b0bd5f9023ea8aadbfd3da` / `document:3:d390a42c11fa:page:6:block:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1b0c7b57ec4177580f0895e3` / `document:3:d390a42c11fa:page:6:block:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a5cea93a493337d38deab7ea` / `document:3:d390a42c11fa:page:6:block:11` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_765feec0fa8fb785cf2348b7` / `document:3:d390a42c11fa:page:6:block:12` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1c1684b9cfeb5f5e415be9ec` / `document:3:d390a42c11fa:page:6:block:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7e8445e50228c88a17f68d8b` / `document:3:d390a42c11fa:page:6:block:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c1519602792daac48a83ada7` / `document:3:d390a42c11fa:page:6:block:4` — **SENT, NOT CITED**; packets: core_financial
- `ev_8e0828936794e60f0cd4fd04` / `document:3:d390a42c11fa:page:6:block:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_db5f769ad8bf0d54885c8bbc` / `document:3:d390a42c11fa:page:6:block:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ac01cfd44445871fc5098b6c` / `document:3:d390a42c11fa:page:6:block:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_cab547afe6acb281e7fe6a4c` / `document:3:d390a42c11fa:page:6:block:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_63ec0d092c1c76c38ee15e0d` / `document:3:d390a42c11fa:page:6:block:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f95764bdc53298566796cd7b` / `document:3:d390a42c11fa:page:7:block:0` — **SENT, NOT CITED**; packets: required_documents
- `ev_ccee0e8c8a4a9b641c767e00` / `document:3:d390a42c11fa:page:7:block:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ec4145b066d3be92913016ec` / `document:3:d390a42c11fa:page:7:block:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7e0b9e5b8260acbc5dbf3cb9` / `document:3:d390a42c11fa:page:7:block:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9a6d1b3e5cae3a2a0de99ae0` / `document:3:d390a42c11fa:page:7:block:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_91d9169630816e59991db1e1` / `document:3:d390a42c11fa:page:7:block:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_bf6703750e4d2e9c73fc4b2c` / `document:3:d390a42c11fa:page:7:block:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fbe1c7e5005e7be4851371c6` / `document:3:d390a42c11fa:page:7:block:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f409c547248d746e0d690886` / `document:3:d390a42c11fa:page:7:block:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_dc226867c843a404a00f7b35` / `document:3:d390a42c11fa:page:7:block:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0156bf119230c63d81d171f4` / `document:3:d390a42c11fa:page:7:block:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9b17e756b763134c72693869` / `document:3:d390a42c11fa:page:8:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_43fcbacf483fb96c2c511e27` / `document:3:d390a42c11fa:page:8:block:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_371005d328609fe99a6ce07b` / `document:3:d390a42c11fa:page:8:block:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_66c122dcc8e3e3a7079b22fe` / `document:3:d390a42c11fa:page:8:block:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_43902ad48c5b7a0e07b68886` / `document:3:d390a42c11fa:page:8:block:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_be65c0affb45217279772447` / `document:4:a493b9a9acf6:page:1:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_14fc8b87a3a793825efec67f` / `document:4:a493b9a9acf6:page:1:block:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e12c8e80836a56d7ce153490` / `document:4:a493b9a9acf6:page:1:block:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_064a1e1079b7b83d3f681c56` / `document:4:a493b9a9acf6:page:1:block:11` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_bca0eec656c9c12f782b9664` / `document:4:a493b9a9acf6:page:1:block:12` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_30d3ff4d21bae8b41af3d8a0` / `document:4:a493b9a9acf6:page:1:block:13` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0b4fadab125c292cee6dec5b` / `document:4:a493b9a9acf6:page:1:block:14` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a6be0b2dbe9f52f8ea8cece1` / `document:4:a493b9a9acf6:page:1:block:15` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_80336f27598fd9cf230d96db` / `document:4:a493b9a9acf6:page:1:block:16` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2e665ba68b061b819f829334` / `document:4:a493b9a9acf6:page:1:block:17` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1cb283d19ad4365eac173c2d` / `document:4:a493b9a9acf6:page:1:block:18` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f6b0bce6c00d3dfff208fcc7` / `document:4:a493b9a9acf6:page:1:block:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_918f92428b85d8ea70f6faff` / `document:4:a493b9a9acf6:page:1:block:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c0d0767acb24ace895fa2197` / `document:4:a493b9a9acf6:page:1:block:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_8c450b87eb0ea232717315fb` / `document:4:a493b9a9acf6:page:1:block:5` — **SENT, NOT CITED**; packets: required_documents
- `ev_4c5f61af891de175a09f6cc6` / `document:4:a493b9a9acf6:page:1:block:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b79eda9a1f6ec5cc9af415f0` / `document:4:a493b9a9acf6:page:1:block:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6fbef747b9c51fb168394b4d` / `document:4:a493b9a9acf6:page:1:block:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_89ec74a22fe6e3345ac087c4` / `document:4:a493b9a9acf6:page:1:block:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5fc8d69d7438c9180cb5bebb` / `document:4:a493b9a9acf6:page:2:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_80e8f69a62645dc7b8de5b71` / `document:4:a493b9a9acf6:page:2:block:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e5524fa5c0cf8a2e4e789807` / `document:4:a493b9a9acf6:page:2:block:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_15edfcf5c39f61fb937da7ae` / `document:4:a493b9a9acf6:page:2:block:11` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_660293b5d2159ed376359d56` / `document:4:a493b9a9acf6:page:2:block:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_90c21c1eda37f80efd85de85` / `document:4:a493b9a9acf6:page:2:block:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_91a9fd9c3ded9999182ad988` / `document:4:a493b9a9acf6:page:2:block:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e60ff44e3e8238635c93b72e` / `document:4:a493b9a9acf6:page:2:block:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5fb65acc3f95c9e52ba8c02a` / `document:4:a493b9a9acf6:page:2:block:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6a111a95cf3747d045ffc885` / `document:4:a493b9a9acf6:page:2:block:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_bc3ccacf78b8208e9dc01bbe` / `document:4:a493b9a9acf6:page:2:block:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_70a36bebf04d42804cac7579` / `document:4:a493b9a9acf6:page:2:block:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_871e00f4d79f034948c75e61` / `document:4:a493b9a9acf6:page:3:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2bf8b308e6817e2915aab163` / `document:4:a493b9a9acf6:page:3:block:1` — **SENT, NOT CITED**; packets: core_financial, product_details
- `ev_d57cb9bef32b394c1ce958ee` / `document:4:a493b9a9acf6:page:3:block:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_bbfbc94b1bdefd703d903d82` / `document:4:a493b9a9acf6:page:3:block:3` — **SENT, NOT CITED**; packets: core_financial
- `ev_b915a294c9adf8a15cd8c46f` / `document:4:a493b9a9acf6:page:3:block:4` — **SENT, NOT CITED**; packets: eligibility_and_documents
- `ev_d3d8094c85fd0aaca9d7db47` / `document:4:a493b9a9acf6:page:3:block:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_331509bdfb8f3dae0c28932f` / `document:4:a493b9a9acf6:page:3:block:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_cdff656f07d80899d376aa7b` / `document:4:a493b9a9acf6:page:3:block:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ffa7cfe2fe3dbb4592adc1a7` / `document:4:a493b9a9acf6:page:3:block:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a73f2f2586b278f90468736c` / `document:4:a493b9a9acf6:page:3:block:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_995fbbaa9643ca888643ab57` / `document:5:9fe19e644854:page:1:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1972c8d4530441dd325ffc86` / `document:5:9fe19e644854:page:1:block:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3b2e586abc90d49c54fac8b6` / `document:5:9fe19e644854:page:1:block:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_26f6620918da163ed03b4473` / `document:5:9fe19e644854:page:1:block:11` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b2a2995963c5b2d78f737dd3` / `document:5:9fe19e644854:page:1:block:12` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5d0b56ea4172e9261aaebfc8` / `document:5:9fe19e644854:page:1:block:13` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2b2ad92fd1e827f475c047f4` / `document:5:9fe19e644854:page:1:block:14` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e20e3aeb4cbee93461e5dea4` / `document:5:9fe19e644854:page:1:block:15` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_945a17542ba19db4a404d22f` / `document:5:9fe19e644854:page:1:block:16` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_da474a8dd500876562df1188` / `document:5:9fe19e644854:page:1:block:17` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d4eb1bbd94e76f6185c699a1` / `document:5:9fe19e644854:page:1:block:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fa5e58ccb9689a13f5daa778` / `document:5:9fe19e644854:page:1:block:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_dfbc85ddbecadc50752709d8` / `document:5:9fe19e644854:page:1:block:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7c875e05d4494fabdd0dec6d` / `document:5:9fe19e644854:page:1:block:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7eb82506ea08f73a0bf1cb93` / `document:5:9fe19e644854:page:1:block:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4f5acd27a5c4fbb40edbfc62` / `document:5:9fe19e644854:page:1:block:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d57c60b960d2c7daa08a1b57` / `document:5:9fe19e644854:page:1:block:8` — **SENT, NOT CITED**; packets: eligibility_and_documents
- `ev_d5d2f367a72769cc2bbbfab7` / `document:5:9fe19e644854:page:1:block:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_12a716a1b274a371310e029a` / `document:5:9fe19e644854:page:1:note:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_93a4eb8a87c3cc6a4cc093ba` / `document:5:9fe19e644854:page:1:note:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d721d7054ebd0dbe24e93b59` / `document:5:9fe19e644854:page:2:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_992be8c1b64636ff3e7fb2ee` / `document:5:9fe19e644854:page:2:block:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_66e9f9767a0769dbedde26f1` / `document:5:9fe19e644854:page:2:block:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7cc0ad170f3754a4db991e85` / `document:5:9fe19e644854:page:2:block:11` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_961e3e05ab4c1a8e57260b59` / `document:5:9fe19e644854:page:2:block:12` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fbbef92011795912adfcce6d` / `document:5:9fe19e644854:page:2:block:13` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c1e89fec84aa092499a8bbd6` / `document:5:9fe19e644854:page:2:block:14` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f86b797d6c669594aa9b8ee9` / `document:5:9fe19e644854:page:2:block:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_62fb9e9fc8ba4e482f4dcacb` / `document:5:9fe19e644854:page:2:block:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6d1a87ac235237c4a36eeead` / `document:5:9fe19e644854:page:2:block:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d4ebfb33b9cb717e797b24f3` / `document:5:9fe19e644854:page:2:block:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d9f464bcf459f7d9e1f44366` / `document:5:9fe19e644854:page:2:block:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ec4e074c18923dce397cd633` / `document:5:9fe19e644854:page:2:block:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6b64f8b6aa84da510c1302b5` / `document:5:9fe19e644854:page:2:block:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a19787f7f93cf6020efa4557` / `document:5:9fe19e644854:page:2:block:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1c45e7e5a4a6f99371877b4c` / `document:5:9fe19e644854:page:3:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f01008288be031b904644a65` / `document:5:9fe19e644854:page:3:block:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e9ba5fe15f036e8e38a47586` / `document:5:9fe19e644854:page:3:block:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c9c4d493df6cc72c0c7de09e` / `document:5:9fe19e644854:page:3:block:11` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ee2e7be5eea2d2e8ca1fdac5` / `document:5:9fe19e644854:page:3:block:12` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_dba5246f5308cd15a143eefb` / `document:5:9fe19e644854:page:3:block:13` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f72f218ef25cc72a62be3caf` / `document:5:9fe19e644854:page:3:block:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_630c2f5d3e9db3445adfe7d6` / `document:5:9fe19e644854:page:3:block:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0b41399f3ea8d39a7467f3e5` / `document:5:9fe19e644854:page:3:block:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_918ccf0c368389553952d430` / `document:5:9fe19e644854:page:3:block:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b2b409768bbb095d05f4e1e6` / `document:5:9fe19e644854:page:3:block:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b63bf0be16fb7f3b1bd9bf90` / `document:5:9fe19e644854:page:3:block:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_cafd76510cf5ffb29a86efbf` / `document:5:9fe19e644854:page:3:block:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1a0f3842d81f96a30b200466` / `document:5:9fe19e644854:page:3:block:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9bb3ba043c55b689adcc5a8e` / `document:5:9fe19e644854:page:4:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e6b3b0fac81381fe6da938a3` / `document:5:9fe19e644854:page:4:block:1` — **SENT, NOT CITED**; packets: eligibility_and_documents
- `ev_b17c5d500189e529b6746657` / `document:5:9fe19e644854:page:4:block:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_14be47544a418328081abef8` / `document:5:9fe19e644854:page:4:block:11` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_df90a77b43d23367e821fa09` / `document:5:9fe19e644854:page:4:block:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f8e7159667a774cd48eed4df` / `document:5:9fe19e644854:page:4:block:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_8b1990ff0dfcfdfb8e6be46b` / `document:5:9fe19e644854:page:4:block:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1618aef093a867734bf791f3` / `document:5:9fe19e644854:page:4:block:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_677ae662079f691a13cf1729` / `document:5:9fe19e644854:page:4:block:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_344e3aad345590397e6857bf` / `document:5:9fe19e644854:page:4:block:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1dd757df30cd6195d9c33b10` / `document:5:9fe19e644854:page:4:block:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9f5fc78b1bab2b8f59f72623` / `document:5:9fe19e644854:page:4:block:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fbb5d7c6ace0835d6787867c` / `document:5:9fe19e644854:page:5:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a49e206d6e42f7de3424228c` / `document:5:9fe19e644854:page:5:block:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_61530404641c458dfdeb6a94` / `document:5:9fe19e644854:page:5:block:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fbd070424423eb50c608c065` / `document:5:9fe19e644854:page:5:block:2` — **SENT, NOT CITED**; packets: eligibility_and_documents
- `ev_2282ced05298c959b8789f5e` / `document:5:9fe19e644854:page:5:block:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9f032c7b192768d1eb95ee0d` / `document:5:9fe19e644854:page:5:block:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d07d96d74c5c37c9d71ac537` / `document:5:9fe19e644854:page:5:block:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d425824468071805bfb13be5` / `document:5:9fe19e644854:page:5:block:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d249e01f100d951a1c084c4f` / `document:5:9fe19e644854:page:5:block:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a3edd01dbd9a009539da77d0` / `document:5:9fe19e644854:page:5:block:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e7dca81188a6f6e42150f8e2` / `document:5:9fe19e644854:page:5:block:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_eedebf2eec79ebf03e45d290` / `document:5:9fe19e644854:page:6:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ac8fb6f8ab92d90cb7b1d9d4` / `document:5:9fe19e644854:page:6:block:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_28658bfdeb96eb8c9ada4314` / `document:5:9fe19e644854:page:6:block:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_49ab53ce27165989e31fd8bc` / `document:5:9fe19e644854:page:6:note:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_11b175f8198906718497f4cc` / `document:5:9fe19e644854:page:7:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_92adf051e912ea6b2ad87a39` / `document:5:9fe19e644854:page:7:block:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_06d1971a9c605c8b01a61397` / `document:5:9fe19e644854:page:7:block:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a60a28691f87354cc58fbecb` / `document:5:9fe19e644854:page:7:block:11` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_17ce5d9b2321c7485b6aa95f` / `document:5:9fe19e644854:page:7:block:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_66ce4c25f0165f0e2596ee37` / `document:5:9fe19e644854:page:7:block:3` — **SENT, NOT CITED**; packets: required_documents
- `ev_326180a8258406ce2320e170` / `document:5:9fe19e644854:page:7:block:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_17d091a499d8a368732de473` / `document:5:9fe19e644854:page:7:block:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5b21d429f72653a612f2d085` / `document:5:9fe19e644854:page:7:block:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_777f7b4b78517e5fc5c7686c` / `document:5:9fe19e644854:page:7:block:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5d6b8678fe4480db9cbe5e87` / `document:5:9fe19e644854:page:7:block:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_cb9e3b00aac567a22e9a791c` / `document:5:9fe19e644854:page:7:block:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_081b4d0776993ea7372d57ac` / `document:5:9fe19e644854:page:8:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b97dc934101cb8dc11778afa` / `document:5:9fe19e644854:page:8:block:1` — **SENT, NOT CITED**; packets: required_documents
- `ev_5503a196f3a567b3cb0bd88e` / `document:5:9fe19e644854:page:8:block:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_bb5adc0fbf09388320515903` / `document:5:9fe19e644854:page:8:block:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f3614e549112e4dba6b70257` / `document:5:9fe19e644854:page:8:block:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_869b217f28796562b6b50e0b` / `document:5:9fe19e644854:page:8:block:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_223ad046810988c49860e6ac` / `document:5:9fe19e644854:page:8:block:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_08787e1af88a33cfb21c85a4` / `document:5:9fe19e644854:page:8:block:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_101a056e561ab51b953da3a2` / `document:5:9fe19e644854:page:9:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6a9f73075051ea3926225b42` / `document:6:9f06ff021155:page:1:note:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9c7834d42f668f1e66070d75` / `document:6:9f06ff021155:page:1:note:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_dc413332ac36a8338eadcf96` / `document:6:9f06ff021155:page:1:note:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_386f8fc5402323cf07b21a2c` / `document:6:9f06ff021155:page:1:table:0:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c86eb9b4c41b5f14a644b84b` / `document:6:9f06ff021155:page:1:table:0:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_07e104b838ffd9ac05ae3d9c` / `document:6:9f06ff021155:page:1:table:0:row:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9f6c5a367b769b2ef1bb408f` / `document:6:9f06ff021155:page:1:table:0:row:11` — **SENT, NOT CITED**; packets: required_documents
- `ev_51b593d36727c78d5236588d` / `document:6:9f06ff021155:page:1:table:0:row:12` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_cd2cf4e4bf2eb9939e3beba6` / `document:6:9f06ff021155:page:1:table:0:row:13` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_244c167463fa01f505af044d` / `document:6:9f06ff021155:page:1:table:0:row:14` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6fa6aaf84a812da1f7a8755b` / `document:6:9f06ff021155:page:1:table:0:row:15` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e292979e9ad5b2e4d0b238c0` / `document:6:9f06ff021155:page:1:table:0:row:16` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2bd3e47c0c2212211956de82` / `document:6:9f06ff021155:page:1:table:0:row:17` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_83429129464a1433a45c687a` / `document:6:9f06ff021155:page:1:table:0:row:18` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_24fc80483f228e8316aa297b` / `document:6:9f06ff021155:page:1:table:0:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_27cc15411c9688a782bf9381` / `document:6:9f06ff021155:page:1:table:0:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2b367241fffc68f12c34b363` / `document:6:9f06ff021155:page:1:table:0:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d564e424f651ca406c9dd813` / `document:6:9f06ff021155:page:1:table:0:row:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b039bf15cb2dc6ab19dde73e` / `document:6:9f06ff021155:page:1:table:0:row:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2e2a8b73dddb6ed86e00c812` / `document:6:9f06ff021155:page:1:table:0:row:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b7bbf53eb833f041dd703e82` / `document:6:9f06ff021155:page:1:table:0:row:8` — **SENT, NOT CITED**; packets: fees_and_repayment
- `ev_81b08a0cbafa46f5f62ec556` / `document:6:9f06ff021155:page:1:table:0:row:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_dfaa41000bf1dd4bf5eeaffe` / `document:6:9f06ff021155:page:1:table:1:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_684358ce4dd2b912ec392e22` / `document:6:9f06ff021155:page:1:table:1:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f0b3a86e9db42d5a491af175` / `document:6:9f06ff021155:page:1:table:1:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6f8e6913c47b879c9fd2691f` / `document:6:9f06ff021155:page:2:note:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e92a4d9960f98b21b595c299` / `document:6:9f06ff021155:page:2:note:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b7e4fc13114f0b5bd348c547` / `document:6:9f06ff021155:page:2:note:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_bd1cd3dc87ded99356348f74` / `document:6:9f06ff021155:page:2:table:0:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3ac891e4e0bc6d9ea2f6c95e` / `document:6:9f06ff021155:page:2:table:0:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b2838106ec96285d87d069f6` / `document:6:9f06ff021155:page:2:table:0:row:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_50a534110a1854861c9e609c` / `document:6:9f06ff021155:page:2:table:0:row:11` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6d8b18507231e93b400713ef` / `document:6:9f06ff021155:page:2:table:0:row:12` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7c7087809e15087dd7626e54` / `document:6:9f06ff021155:page:2:table:0:row:13` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3dcb6b4ea9569ee0566bdb1d` / `document:6:9f06ff021155:page:2:table:0:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_efb18409742129bdfcc43b91` / `document:6:9f06ff021155:page:2:table:0:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_452a2f354d8433938512da93` / `document:6:9f06ff021155:page:2:table:0:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_59152d33292c8fc51fb483c4` / `document:6:9f06ff021155:page:2:table:0:row:5` — **SENT, NOT CITED**; packets: fees_and_repayment
- `ev_b45dd7e13f55b6e1b660121a` / `document:6:9f06ff021155:page:2:table:0:row:6` — **SENT, NOT CITED**; packets: required_documents
- `ev_57a569f8346d7c9a4e623f62` / `document:6:9f06ff021155:page:2:table:0:row:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f2288bb8090a9f670a1eb6b4` / `document:6:9f06ff021155:page:2:table:0:row:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c03428f47412582413a1766d` / `document:6:9f06ff021155:page:2:table:0:row:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_97ffd481fd979baa1b64f22a` / `document:6:9f06ff021155:page:2:table:1:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6d64147d981a81b54d984dce` / `document:6:9f06ff021155:page:2:table:1:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5fd927e152bfd83bddc152d2` / `document:6:9f06ff021155:page:2:table:1:row:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ed7a063244c9ed10edec7959` / `document:6:9f06ff021155:page:2:table:1:row:11` — **SENT, NOT CITED**; packets: required_documents
- `ev_47db104421cf26fe206906e9` / `document:6:9f06ff021155:page:2:table:1:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6e8c9c44d4450919941b528f` / `document:6:9f06ff021155:page:2:table:1:row:3` — **SENT, NOT CITED**; packets: product_details
- `ev_df08fba0eac92e58809db7e4` / `document:6:9f06ff021155:page:2:table:1:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4f55f7f3974a44e40c604247` / `document:6:9f06ff021155:page:2:table:1:row:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_763ff788e33bde68a7a9c7ac` / `document:6:9f06ff021155:page:2:table:1:row:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_395f2a98f422a83f4761f379` / `document:6:9f06ff021155:page:2:table:1:row:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_39ebf582a1d1f7ef9f3408ab` / `document:6:9f06ff021155:page:2:table:1:row:8` — **SENT, NOT CITED**; packets: fees_and_repayment
- `ev_52919f1e1261cb7bd446ff09` / `document:6:9f06ff021155:page:2:table:1:row:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_06e8f2f53242fcae85fb81de` / `document:6:9f06ff021155:page:3:note:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e943a9b5eb73452e4a2f3f3e` / `document:6:9f06ff021155:page:3:note:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_97b6b9eb2839d0bdc3360124` / `document:6:9f06ff021155:page:3:note:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1d0d611d84549aa4ee334c67` / `document:6:9f06ff021155:page:3:table:0:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f8d0abff3a84b0c5b992373a` / `document:6:9f06ff021155:page:3:table:0:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d8bc11f6d4b27ed00f240169` / `document:6:9f06ff021155:page:3:table:0:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_366900ff0a24d50b3c1b71a5` / `document:6:9f06ff021155:page:3:table:0:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7f656d969bc01a71e2c7ee0e` / `document:6:9f06ff021155:page:3:table:0:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_60fc7da1e41707344bab0fd6` / `document:6:9f06ff021155:page:3:table:0:row:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d0fbf589f039239fa33b6d0e` / `document:6:9f06ff021155:page:3:table:0:row:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fbd6b79fb711df23be6aeec3` / `document:7:c3d8a29c3331:page:1:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_616f63bc774144c6b1a2e743` / `document:7:c3d8a29c3331:page:1:block:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e3c019905d43bb4a367a73d0` / `document:7:c3d8a29c3331:page:1:table:0:note:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ac6f30e42688266811c01b76` / `document:7:c3d8a29c3331:page:1:table:0:note:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2e5e2f45dadfbe05a4496bff` / `document:7:c3d8a29c3331:page:1:table:0:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_380fcdc2b8d109c896016c1a` / `document:7:c3d8a29c3331:page:1:table:0:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7120519d38431c8c0f4dcb1f` / `document:7:c3d8a29c3331:page:1:table:0:row:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2c829172588fb1bd37af4b4a` / `document:7:c3d8a29c3331:page:1:table:0:row:11` — **SENT, NOT CITED**; packets: required_documents
- `ev_51eb65bc6c71b7d17ef9b6a6` / `document:7:c3d8a29c3331:page:1:table:0:row:12` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_510353c0110e32930b24a642` / `document:7:c3d8a29c3331:page:1:table:0:row:13` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_60eb0eb99774836ccb2b5c89` / `document:7:c3d8a29c3331:page:1:table:0:row:14` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2799f6a42c165f54e7ccd904` / `document:7:c3d8a29c3331:page:1:table:0:row:15` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_32a4c38c82cae9a47aac084a` / `document:7:c3d8a29c3331:page:1:table:0:row:16` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6abbfda7a708ab6051b2624d` / `document:7:c3d8a29c3331:page:1:table:0:row:17` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e801ccd43f2dff1f524bbf1d` / `document:7:c3d8a29c3331:page:1:table:0:row:18` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_496d6851ed9e6b027fb2773d` / `document:7:c3d8a29c3331:page:1:table:0:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_dbc4f007bb723f5b8fe8334f` / `document:7:c3d8a29c3331:page:1:table:0:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b4acda720620c121e4dbb071` / `document:7:c3d8a29c3331:page:1:table:0:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_59824f13ecbed1f0dc0b978d` / `document:7:c3d8a29c3331:page:1:table:0:row:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e5bad46a6ecc4e27d4be011d` / `document:7:c3d8a29c3331:page:1:table:0:row:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a8892d122bcc17d446a9d9ca` / `document:7:c3d8a29c3331:page:1:table:0:row:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4755d15a97fe1cf1e37987ee` / `document:7:c3d8a29c3331:page:1:table:0:row:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_27d7c732db4d7c3fc0343fce` / `document:7:c3d8a29c3331:page:1:table:0:row:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c31351495ec4eefc23280b34` / `document:7:c3d8a29c3331:page:2:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6d1f817b0461268eb2a36e69` / `document:7:c3d8a29c3331:page:2:block:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fc211b84da5bc7df6771c9cd` / `document:7:c3d8a29c3331:page:2:table:0:note:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6aa32f4580cf39fb36ed70ef` / `document:7:c3d8a29c3331:page:2:table:0:note:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_74fbef0109720c09e03242e1` / `document:7:c3d8a29c3331:page:2:table:0:note:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_298caf82dcee585b53f20980` / `document:7:c3d8a29c3331:page:2:table:0:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0d14b51b380f31d220131b5b` / `document:7:c3d8a29c3331:page:2:table:0:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f4aaf837b0cb80dcea844029` / `document:7:c3d8a29c3331:page:2:table:0:row:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fc8ab7a76453639b807d4232` / `document:7:c3d8a29c3331:page:2:table:0:row:11` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_08d82ac7bfe30c71dd5676f0` / `document:7:c3d8a29c3331:page:2:table:0:row:12` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3ff04a20ddcee3f208f30dfe` / `document:7:c3d8a29c3331:page:2:table:0:row:13` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3a5633533f7a112f5c13c634` / `document:7:c3d8a29c3331:page:2:table:0:row:14` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_31b5818efc3a9b475391d3c6` / `document:7:c3d8a29c3331:page:2:table:0:row:15` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_65eecee8711eaf56562c22e9` / `document:7:c3d8a29c3331:page:2:table:0:row:16` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_058fc5296388d0b69450e1cc` / `document:7:c3d8a29c3331:page:2:table:0:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6583e47615e504d965e57eb6` / `document:7:c3d8a29c3331:page:2:table:0:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ec7c897aa95ef6682866f3fe` / `document:7:c3d8a29c3331:page:2:table:0:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_05f88da3e956c010b5ff1ab0` / `document:7:c3d8a29c3331:page:2:table:0:row:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1a90c5bc44fd84ec948a8821` / `document:7:c3d8a29c3331:page:2:table:0:row:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c65b867a44e31cb934546fca` / `document:7:c3d8a29c3331:page:2:table:0:row:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e3b82e8cd8df34c170c05582` / `document:7:c3d8a29c3331:page:2:table:0:row:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a7c6ceec5f51032577f48335` / `document:7:c3d8a29c3331:page:2:table:0:row:9` — **SENT, NOT CITED**; packets: required_documents
- `ev_ad7d44d6819f3eaae8ef0d1e` / `document:7:c3d8a29c3331:page:3:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4b8bd8aadf14524f28aa43e8` / `document:7:c3d8a29c3331:page:3:block:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6567dc3c5231c4af5f9383b4` / `document:7:c3d8a29c3331:page:3:table:0:note:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_59e0d416443946d4e863353b` / `document:7:c3d8a29c3331:page:3:table:0:note:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_985e50f50b786ebcaa3039b9` / `document:7:c3d8a29c3331:page:3:table:0:note:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1cd2f7843de1a050f821e784` / `document:7:c3d8a29c3331:page:3:table:0:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2d981a3419dc454a4fed0163` / `document:7:c3d8a29c3331:page:3:table:0:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_cbe750af0b3dc6add1d25e12` / `document:7:c3d8a29c3331:page:3:table:0:row:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f2b929a43aa426d25f80d7b8` / `document:7:c3d8a29c3331:page:3:table:0:row:11` — **SENT, NOT CITED**; packets: required_documents
- `ev_27fdf0ba92b7874a75d08e16` / `document:7:c3d8a29c3331:page:3:table:0:row:12` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e101879f26578f5fb72e624e` / `document:7:c3d8a29c3331:page:3:table:0:row:13` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_af2cb77658307fddaabab15f` / `document:7:c3d8a29c3331:page:3:table:0:row:14` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_99b2a9a8dd914bb8d17abc33` / `document:7:c3d8a29c3331:page:3:table:0:row:15` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_422f9d2e1a6270609e6804db` / `document:7:c3d8a29c3331:page:3:table:0:row:16` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f3bed1185e234fff06ca1a02` / `document:7:c3d8a29c3331:page:3:table:0:row:17` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_204966fab3c3f86ffa537977` / `document:7:c3d8a29c3331:page:3:table:0:row:18` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_75e25a5bc3c7d67dce5fe0f1` / `document:7:c3d8a29c3331:page:3:table:0:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_519921576d5209c9fecd1506` / `document:7:c3d8a29c3331:page:3:table:0:row:3` — **SENT, NOT CITED**; packets: product_details
- `ev_2094e2bf1103f463dc22273d` / `document:7:c3d8a29c3331:page:3:table:0:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_502bc7ce25f613956fc2dd9d` / `document:7:c3d8a29c3331:page:3:table:0:row:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a3980dd8fd2745ec712caa89` / `document:7:c3d8a29c3331:page:3:table:0:row:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_88e88118a19019bb7eb196d2` / `document:7:c3d8a29c3331:page:3:table:0:row:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ab461244a12c1200709dd1b3` / `document:7:c3d8a29c3331:page:3:table:0:row:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5495328bc31903d11183b46e` / `document:7:c3d8a29c3331:page:3:table:0:row:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_494367c324cdb6aa51cf233f` / `b456` — **SENT, NOT CITED**; packets: identity, product_details
- `ev_e211d1ffcbbb0f97b425c016` / `b457` — **EXTRACTED: purpose**; packets: identity, product_details
- `ev_deb4d3bbe6996a7603db1fd5` / `b458` — **EXTRACTED: purpose**; packets: identity, product_details
- `ev_4c60f5fdd46fe4e1b36697cb` / `b459` — **EXTRACTED: purpose**; packets: identity, product_details
- `ev_b6a9925e1a65d2392447d178` / `b460` — **SENT, NOT CITED**; packets: identity, product_details
- `ev_b861cb318bd7375ba907b380` / `b461` — **SENT, NOT CITED**; packets: identity, product_details
- `ev_fca41fac6216a76505500eaf` / `b462` — **SENT, NOT CITED**; packets: identity, product_details
- `ev_2ea93725618d1de10d9ef0fe` / `b463` — **SENT, NOT CITED**; packets: identity, product_details
- `ev_f5f4ab884224df8f80e85e8d` / `b464` — **SENT, NOT CITED**; packets: identity, product_details
- `ev_489582b8304f35bdb297134b` / `b466` — **EXTRACTED: category**; packets: identity, product_details
- `ev_4b3666969773a931f37c57b3` / `b468` — **SENT, NOT CITED**; packets: identity, product_details
- `ev_0148c3f71cc72b882ab17224` / `b470` — **SENT, NOT CITED**; packets: identity
- `ev_53ec97a4ea7997951ffc51bb` / `b472` — **SENT, NOT CITED**; packets: identity
- `ev_2fc6d4397cbde95e53e62bc8` / `b474` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5984fe5b04fbefbac5b01d38` / `b479` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1b456bb86d1950f6bf82a205` / `b480` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a0c63bb4eddc79932d19a99c` / `b481` — **SENT, NOT CITED**; packets: core_financial
- `ev_7bc3882a6e4dc77f4836463f` / `b482` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c214b9bc2ee204f9b11f1c60` / `b486` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_34497ad24b598565961de3c2` / `b488` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5b47e8560b2f76835d7faeba` / `b489` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_88ecb2138ee6471ed49533f5` / `b490` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_65ee35aa3280f89dd19bee4a` / `b491` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1743c68cf586852164c22b3f` / `b492` — **SENT, NOT CITED**; packets: core_financial
- `ev_3a4597aab82375e7f034e625` / `b493` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6cd4ffc86649cd496487b9fe` / `b494` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d4f9d2e5dcfaaf2091d2bb5e` / `b495` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_53939a6819c55798cbae77ce` / `b496` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_22df520dc7efd00ebb9b8f8e` / `b497` — **SENT, NOT CITED**; packets: identity
- `ev_7aade2d945dece0c8681d4dc` / `b498` — **SENT, NOT CITED**; packets: required_documents
- `ev_ec63df3234f23da18e142fd8` / `b499` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_06452138ecb8c22f35f83fa8` / `b500` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_61e4bcd330a6b20fe5a0956d` / `b501` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c9f36c182c14b6a9fec4da64` / `b502` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_67fa4b4111f33a95dc5b0fb1` / `b503` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1df0ed91add75592a862d29d` / `b504` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ba7fed5195cf63ee41ae0093` / `b505` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e0875ed240b1f39a6ac0ec58` / `b506` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6081b32c00838ccd5bde25a0` / `b507` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_81321d9a5c8cbc04216a84cb` / `b508` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6a462f61b2f0f13991c9078c` / `b509` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6c76140caf1abee92e1a8677` / `b510` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c0e5519d0026c0f55c794727` / `b511` — **SENT, NOT CITED**; packets: eligibility_and_documents
- `ev_3e5b54afa08b38dbe038a568` / `b512` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_664aa3cfb4ea90595a8e67e5` / `b513` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f5c5af2d17fcfef65fea122e` / `b514` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ed80c4578c1535e427e4d975` / `b515` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_55ef50bf3320da9df7097114` / `b516` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2a4a2a9c17cf69b665f24a1e` / `b517` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_14f8fd266bdd24bae4a2710b` / `b518` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_62fc86907bedee50a584309b` / `b519` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_425af231c2f7763348163448` / `b520` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7dad633a3773971e9a5c695f` / `b521` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3c8b0119978ec99d6340db25` / `b522` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5539c71828dc6295116a069b` / `b523` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_54f48a916f9d26aa1c89416b` / `b524` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f12e45a1e3288c873e07a924` / `b525` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d7a0d6516b628becfe65f3ad` / `b526` — **EXTRACTED: product_name**; packets: identity
- `ev_f50b6de5434f9fe0b1fee954` / `b527` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_58d8b3f72d40df2b0303e34b` / `b528` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ab52386bb84d0154a400d10d` / `b529` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6f43dc1705065f5d2e986f2a` / `b530` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_36c8099de01f61f4634d9ed1` / `b531` — **SENT, NOT CITED**; packets: identity
- `ev_2e6c2a96dff304ef3b5eff7f` / `b532` — **SENT, NOT CITED**; packets: identity
- `ev_e7621322980119c6250c4695` / `b534` — **SENT, NOT CITED**; packets: identity
- `ev_1adb2223b514f8f817b38e1f` / `b536` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9db4e2bbda4847b6365a5ccf` / `t1:note:0` — **EXTRACTED: residency_requirements**; packets: eligibility_and_documents
- `ev_369b987713cad5235e808069` / `t1:note:1` — **SENT, NOT CITED**; packets: eligibility_and_documents
- `ev_778ee053c84d58f83ff0de2e` / `t1:note:2` — **SENT, NOT CITED**; packets: eligibility_and_documents
- `ev_39b3130967b00e8e70ab97db` / `t1:row:0` — **EXTRACTED: age_requirements, eligibility**; packets: eligibility_and_documents
- `ev_6e6f7017e519a2836b059735` / `t1:row:1` — **EXTRACTED: eligibility, residency_requirements**; packets: eligibility_and_documents
- `ev_9459ba0c0708b9fcd1086155` / `t1:row:10` — **EXTRACTED: collateral**; packets: eligibility_and_documents, identity, product_details
- `ev_f9694eee3ea5db334d87fb18` / `t1:row:11` — **SENT, NOT CITED**; packets: product_details
- `ev_a4cd4808b0bd0963bd8e88e3` / `t1:row:12` — **EXTRACTED: required_documents**; packets: required_documents
- `ev_838438dd28d32228811b9e96` / `t1:row:15` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0940267a97f1ef0e0e5c9046` / `t1:row:16` — **EXTRACTED: fees**; packets: fees_and_repayment
- `ev_efcac1ab57c7899ff4caee37` / `t1:row:17` — **EXTRACTED: fees**; packets: fees_and_repayment
- `ev_9aa7847ace31d0a8250475d5` / `t1:row:18` — **EXTRACTED: fees**; packets: fees_and_repayment
- `ev_805cd27b0174ea3e17a12201` / `t1:row:19` — **EXTRACTED: fees**; packets: fees_and_repayment
- `ev_32c91312f784a509556a760a` / `t1:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_05e6eee4a3b9aaaa14812391` / `t1:row:20` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1fdefbc97c7a7063a9bf00cb` / `t1:row:21` — **SENT, NOT CITED**; packets: eligibility_and_documents
- `ev_6422510fa60303f660a1a761` / `t1:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_de3011bdc342a7a7ac350fe6` / `t1:row:4` — **EXTRACTED: term**; packets: core_financial
- `ev_17b3ebed7a1d3cbc479d4768` / `t1:row:5` — **EXTRACTED: interest_rate**; packets: core_financial
- `ev_b5a021ec9c9e271d457d2e1d` / `t1:row:6` — **SENT, NOT CITED**; packets: core_financial
- `ev_22fcc320ae4d5eedf74a6a26` / `t1:row:7` — **EXTRACTED: fees**; packets: fees_and_repayment
- `ev_e1f341d3ac1d9e094ae8c4d8` / `t1:row:8` — **EXTRACTED: fees**; packets: fees_and_repayment
- `ev_4c064c16be8cecd9f1e51422` / `t1:row:9` — **EXTRACTED: repayment**; packets: fees_and_repayment
- `ev_e1e603628867fef0d68a28c6` / `t2:note:0` — **SENT, NOT CITED**; packets: eligibility_and_documents
- `ev_8ddbb36c90477f1979a500a7` / `t2:note:1` — **SENT, NOT CITED**; packets: eligibility_and_documents
- `ev_d15f11a8d66346742540bafd` / `t2:note:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_34e9d62e1501c3f471957bdd` / `t2:row:0` — **SENT, NOT CITED**; packets: eligibility_and_documents
- `ev_c7d4eda46ea0daaaa916d79a` / `t2:row:1` — **SENT, NOT CITED**; packets: eligibility_and_documents
- `ev_6d733381befced18187ddd9a` / `t2:row:10` — **SENT, NOT CITED**; packets: required_documents
- `ev_0f238f5cc597767b3e84c5d5` / `t2:row:13` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_bdbeef829856d054b646b83c` / `t2:row:14` — **SENT, NOT CITED**; packets: fees_and_repayment
- `ev_c3c2c8c29c7b12feda00dbd5` / `t2:row:15` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_08ed718bd4392fd6600bfba7` / `t2:row:16` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_26859524960dbeb2508e3738` / `t2:row:17` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_262d19983903c412fe6e9514` / `t2:row:18` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4cad1ec896ece8089ebe44a4` / `t2:row:19` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_492cb457a0a328c18d452e7d` / `t2:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_229407157a41a27a42851c51` / `t2:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_8862e5b2b660031993c251af` / `t2:row:4` — **EXTRACTED: term**; packets: core_financial
- `ev_a1d4f4bb7bd4e2bd2657e149` / `t2:row:5` — **SENT, NOT CITED**; packets: core_financial
- `ev_1a6749f7fd519d23ecb5c5b3` / `t2:row:6` — **SENT, NOT CITED**; packets: core_financial
- `ev_4ea59bf0d8b643c98e3e8aae` / `t2:row:7` — **SENT, NOT CITED**; packets: fees_and_repayment
- `ev_129ceaac62c7c41bc3dfce3d` / `t2:row:8` — **SENT, NOT CITED**; packets: fees_and_repayment
- `ev_f1499ebd3e2d6f242e2439bd` / `t2:row:9` — **SENT, NOT CITED**; packets: fees_and_repayment
- `ev_4e26899b884b9b58624b7837` / `t3:note:0` — **SENT, NOT CITED**; packets: eligibility_and_documents
- `ev_542face9ee61f6678ed2cd16` / `t3:note:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_63695248b7b51cb04e6fb72f` / `t3:note:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7ad3498375e83b3fbe9a6a4f` / `t3:row:0` — **SENT, NOT CITED**; packets: eligibility_and_documents
- `ev_01cca1dcc7db03acbe27d6b9` / `t3:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_acca6558fb9936077db77ce7` / `t3:row:10` — **EXTRACTED: collateral**; packets: eligibility_and_documents, identity, product_details
- `ev_636a888df7b22fff409182a5` / `t3:row:11` — **SENT, NOT CITED**; packets: product_details
- `ev_786f5651203022b64eb1a35c` / `t3:row:12` — **EXTRACTED: required_documents**; packets: required_documents
- `ev_4fd8142e594fe212befe2fb4` / `t3:row:15` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_73d43a0deca616bb47986a5b` / `t3:row:16` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9ae59bf3e54abf4b9458f864` / `t3:row:17` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2de1712263cbca981bf579f4` / `t3:row:18` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_35e171fb1d5a6477d7961e29` / `t3:row:19` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5cea39939a89b72f12ba760d` / `t3:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4a9b27fba27c7e6469cb5f3f` / `t3:row:20` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fae0483abf4a0449c3e7b075` / `t3:row:21` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_595a4e700e106c5cc1cda536` / `t3:row:3` — **EXTRACTED: credit_limit**; packets: product_details
- `ev_8cb0d624d7a65a073a09ee2d` / `t3:row:4` — **EXTRACTED: term**; packets: core_financial
- `ev_4c28e7884360958adc02ea38` / `t3:row:5` — **SENT, NOT CITED**; packets: core_financial
- `ev_7ee0d67af2b16437261235a3` / `t3:row:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c9f0b593d9e1afb4a8df501f` / `t3:row:7` — **SENT, NOT CITED**; packets: fees_and_repayment
- `ev_22710f1f4ff57abd498cdd8d` / `t3:row:8` — **SENT, NOT CITED**; packets: fees_and_repayment
- `ev_4c26f588d2dc893ad72406fd` / `t3:row:9` — **SENT, NOT CITED**; packets: fees_and_repayment
- `ev_f1a1b6248c854806f4bfffdf` / `t4:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a8fb9aaf4d4b7cae573d7f73` / `t4:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2057ae28c50f0c1357baeb8f` / `t4:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_31f3bb0b123ad8ba2ef0becf` / `t4:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_aca509cec9d6a084392093f6` / `b100` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1e1d7b70a2948fd5ab19d238` / `b101` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b2141e6b64492a000730f1bf` / `b102` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_497c6ab525a8d9bc3a9cdbd2` / `b103` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b998d9dd85f0b5a141c8182d` / `b104` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_473488f828788d1358d96496` / `b105` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5cfa943323b8a099cf8496f1` / `b106` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d044b0e2a00dd809fd17ff6a` / `b107` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7f305f780e0b42ed95c09ed7` / `b108` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_de099f2eb3130a1d9e2e237e` / `b109` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_aaf1d03114d7cc88c0870096` / `b110` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_23878e82f3c1fe64fd7df85c` / `b111` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_28334271b27b64a5bc15c98d` / `b112` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_eeec5a1110ac631d3f9a7a11` / `b113` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d55cbb6a77eb9fa3821e4db8` / `b114` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b9e4c12583c467673dfd3286` / `b115` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_196f933e6fe4e8b2a650373f` / `b116` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6a4d0a133960e44915b6cb6e` / `b117` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_32da4798743417b7e3220a4a` / `b118` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_dbcfb1af658245ec8b86de1d` / `b119` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_eed4ff31658dafdd163e67c8` / `b120` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0d0378216e34fa137672acd5` / `b121` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0b75eb108b1ba16a38ebbc56` / `b122` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_88d68399d9861dd61350f3b4` / `b123` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_dd7dd59b27bf1da4e0f4e34d` / `b124` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6bad8e0281e5b6547763a882` / `b125` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1d40be36162af7a2e8302d7c` / `b126` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_08642c8ab8afebb42dfd300d` / `b127` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f4bd9b4dc7d18d5fa3cf749f` / `b128` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b31c04954b235f17a69624cd` / `b129` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_54c16bbcb8f36d24c7a56331` / `b130` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0f21d1d62037cc8cd829c7c8` / `b131` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_59b1ab2511cfbf51e20d93df` / `b132` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5e7bf51946ccf4593252904f` / `b133` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d856e70cf20ec42ae7ae6346` / `b134` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a1c0c398877dc643db9d9a04` / `b135` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_64b1ada00ab1cd2d9864f279` / `b136` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2effa4e9d5d035b4c6d36412` / `b137` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_af3e907b5dad44296cb142c2` / `b138` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a47e578cb259ca14d34c5c9f` / `b139` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_664e74a08000d190883334c6` / `b140` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ed68447493630e6df4d67a61` / `b141` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9bdf80bc5ae2ac9571730c36` / `b142` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e87d0f96266118f8c93a2c5d` / `b143` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d7b63660de9c3aab17211e66` / `b144` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7faa3b1bc7ca6890c2ade887` / `b145` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b5a84ad3f77eb9a8407bdc15` / `b146` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fbf3d69e2211ec36b61dc2d0` / `b147` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e6785ca07e81e52a58c78c83` / `b148` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_463c8a78b779d258131820a6` / `b149` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_34249f813d4d62da43cba18b` / `b150` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_455af502a87f69e243e8014a` / `b151` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f7c703cd815fae1a00b5f912` / `b152` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7421b50cb9e098bdc545f856` / `b153` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0ee21d48a2226d381ded6125` / `b154` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_710eeb8efe7d573c73c6cd11` / `b155` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0585a56573e9ecb1ce5bafc1` / `b156` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_54dd0a050dc605be46b93819` / `b157` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f0d304a577a283dfb323b3f2` / `b158` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_101f724956c446e13ad607d9` / `b159` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_323b2b32dc6cd809b76a3088` / `b16` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_20b51151acb483ca3f89f8e1` / `b160` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b0959656e7e36fe759e9eea5` / `b161` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b53fde948a979d3589acd8fd` / `b162` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0231799008f5aff77e1bd680` / `b163` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_751dbd6b99eefb8ee768afd3` / `b164` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f89a2d49803d0e61ff3d6083` / `b165` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e68e6ef5b489bbf8f3c8c794` / `b166` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f01f58760dcb3df1b330ca2a` / `b167` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3bef8c3b53ab39841264fb43` / `b168` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_980d54ed6db740018d1154c0` / `b169` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_014d8e180ab17f3e294f42f0` / `b170` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_de725c508f9572d1e75849ae` / `b171` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_8e233b5d50dffb207c2b040e` / `b172` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e75d9317fb1bfa598e167963` / `b173` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b02607b18cb7814b337a6691` / `b174` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_bfee424087e97b02b46e798d` / `b175` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0f01e09400c3e4e06919aea6` / `b176` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2f58371fcd8086746be320d3` / `b177` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_aeae7fc7038443fe4d00acc1` / `b178` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c8dbd383155a8f32fcf4aeaf` / `b179` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_8fabff79796097d2a25a05da` / `b180` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a7e05bc0b802b349da02534b` / `b181` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_83fb2b78626dd3131d4f0293` / `b182` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_bc3e4cdb0b45fe95e9b89de7` / `b183` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_82a02473411e9786f2addc28` / `b184` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2ffbe4ca104bb42766a8dcae` / `b185` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3ea724d790d94254052c3909` / `b186` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d04f7c4ae1877d3d7b0b2705` / `b187` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2add59f46fb66be419200c92` / `b188` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e3f1d567d6ad09e76c07829b` / `b189` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ab1f83feea765c5c73bc45da` / `b19` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_8d329943e36154db3c1eede2` / `b190` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_151696eeae9717a632cb80f5` / `b191` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ace4f0285494d79d26b0cf68` / `b192` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_39c02bb54549d841740e4087` / `b193` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2ac8c08605c3510177b63a86` / `b194` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c6e8963b88d4128d9e4a3e0b` / `b195` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ef475eb195e331cb4acade13` / `b196` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c2ef080c9b24908d156caf62` / `b197` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3545cb8fe1761179a619a7f6` / `b198` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_77b5b1391551271ae76fef69` / `b199` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_97869829029530b7fe47407b` / `b20` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b52662c32ee7f6af0d09d043` / `b200` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_55e7fcfaa4f6565aaafefef0` / `b201` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3039f84c9702e54d29cada1a` / `b202` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_05e9e8779a5ad533d2b30066` / `b203` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_53fd7fdc04fb07d861d32162` / `b204` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_48b4f4266ab88800e259c4ef` / `b205` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e8de5c4428b1513197d51b50` / `b206` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_776d0a3edba09ab499f4d9c8` / `b207` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a74ee20de63426ca6641c091` / `b208` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2468843e9c0b545976d78773` / `b209` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d69c5238befbc9606e5a03bb` / `b21` — **EXTRACTED: loan_amount**; packets: core_financial
- `ev_0008f842ead9faaf0813a58b` / `b210` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_20a1075ad314a40116a9490a` / `b211` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6af3e96c1c9d1560184ea353` / `b212` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_338abd127a268b0bdbbd438f` / `b213` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_acaf3585b6ee7b0fb6fbc533` / `b214` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ce784579b8ede7ca72fab9fc` / `b215` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6a3d205d8574d7e9bf096ac6` / `b216` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_45102809a5957ececf9ab156` / `b217` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0ad175f7c718b37427a4e7f5` / `b218` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_164477d71ba6b88487165af7` / `b219` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f348b07aeefff42a02d7248f` / `b22` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e357e574ac982a6f62c9c6cd` / `b220` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3346c27d0b5f9b0fdf9d956f` / `b221` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7a7bd80b6be60fcfde77f588` / `b222` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1bcd09c0c3ca96d41fae19f2` / `b223` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1a05ae903483d27ee9bbbee9` / `b224` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9ac54196db26875d00dca8e3` / `b225` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4d64bfeefd217135d819de36` / `b226` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2c0d1a6e22f88b27f4b2600d` / `b227` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e4ad12f1b77b0f7d09ea187e` / `b228` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_02ca3d530809e771749a4c55` / `b229` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3219de088135ae741376bcee` / `b23` — **EXTRACTED: term**; packets: core_financial
- `ev_c33517e244eb7e85a9eaf2da` / `b230` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0d3ed7ce3113c38dd97e9f47` / `b231` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fe6e23cc5b5a2945ae7b1e21` / `b232` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_df2c0cc8e89fdbb836f9c07e` / `b233` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_06811f8cf78e9a11fa671e27` / `b234` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_46b373c61b995f4c70cca23a` / `b235` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e5f71e8a81f45b5f72a4be12` / `b236` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_44d50fe75ff43cf545753fb1` / `b237` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_cfcad1410306a989487fc1f9` / `b238` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_832d240e0c5cc1dc02873700` / `b239` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_815ce7f33902b40daffd0e58` / `b24` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f4b92e26c8765b933d682065` / `b240` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6bb75cbb53d1e817084ee0df` / `b241` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f31655f2d1fab5f6a35ca947` / `b242` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b2eeef49246cd9b0908b8d62` / `b243` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_94512069fd537f960c96e615` / `b244` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_45d07f60ee8e4af2998cea93` / `b245` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0db3d88d08852c20d94e9906` / `b246` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0a7fb6300fee2616c7ddeb30` / `b247` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a01bed008b0270352da7f26f` / `b248` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4a60083ac8c28d62e6d501a2` / `b249` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a5ef1e910308e340f8e40ffa` / `b25` — **EXTRACTED: effective_rate, interest_rate**; packets: core_financial
- `ev_34f9c907cbb896c4779ffcad` / `b250` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_36e9386ce23f7ac7cb02af71` / `b251` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f2e3b7ad580d6f4ae734de5f` / `b252` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_8e37e73fd95ad3f486e7a360` / `b253` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_67b824d262a6fb2d2696e8f6` / `b254` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_61481148e01cfa8cd7b06db4` / `b255` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_79e23b3057cb1b3d2b712c8d` / `b256` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_66e9685464a27d9bb7890dd3` / `b257` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_893e3d7352eee1656272377d` / `b258` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_88460534226491a6e432d53c` / `b259` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a33281d71cc59032cbabcbba` / `b260` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3e9653609f1b59e5ad51231c` / `b261` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0b47859d6ba3d6d5b55a7fbc` / `b262` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_982d1ef02e5255522e8fda76` / `b263` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_dd61073b3c0524c4a207047d` / `b264` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7ebf0f3eaa7b7d83aca0a9a7` / `b265` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1a2f1dc8f8fe69719d061dd8` / `b266` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3f6135618ffd2e621b99da03` / `b267` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_696483b4bfaaf4bb9dc5a620` / `b268` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e06587e9b32ef22af00871ec` / `b269` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7361cf6bda53a8c576b89598` / `b270` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2af548f0d0c0593393598864` / `b271` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_8d90d0db7b5a871803349963` / `b272` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6932df59b652ce5642243827` / `b273` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b513f160751fc07e5463f10e` / `b274` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_394ef1ee888aa477a3d46615` / `b275` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2e5e7f6ae6f8324cdf8ac406` / `b276` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7c3574bda214d0f4905e0ce7` / `b277` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5884ca30de53c16c7f4b08a2` / `b278` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_20ab85568851d4d2248a413d` / `b279` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d9696dc206f41a75d795ce3f` / `b280` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_eedf39652939c092ebb5f7e4` / `b281` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ffb21f16a6582ed93b197e00` / `b282` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4627b1f1af9ec6f6d2dddc8a` / `b283` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fd9fd5051f02c5ad7a831762` / `b284` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d89ef24f1de7f293b0954f5b` / `b285` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7c4cd8d78d4f961523eef0c7` / `b286` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_bd4efc83277342eb6b111a7c` / `b287` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_97c2e7634d3e03ff206b3c09` / `b288` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_cf49c030032f21ef90007c02` / `b289` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_721cf17df596bff2f0908702` / `b290` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_88c2908eb41aaad3bcdb809f` / `b291` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_319569b4b96587ee85c76428` / `b292` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fb630423f2296cb8ab058e05` / `b293` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1583346f9667bff6f6396682` / `b294` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ab1c47d88537646c419b3a9d` / `b295` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c84aa3a14ca07a3b455ed415` / `b296` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_dd82507397c937a3e66158ce` / `b297` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_38daf289636df05c75cbd944` / `b298` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9f2a3e00cf42136bad10021e` / `b299` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b492be599741b84f2a271cd7` / `b300` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b5909287d2d8242ada7579a3` / `b301` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3ca44e4a68b9d172e8f368d0` / `b302` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1ded5fc9b126451abca2b91c` / `b303` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ae6c82f00046fec1ba126901` / `b304` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_75c1b2cf9d760ac9268b4e04` / `b305` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ae12bdb601bda2bfd6a5dfdc` / `b306` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b73f8c3d8ed7c3a00e994e50` / `b307` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f471f002d1bb6758e8f3136f` / `b308` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c94a5c18e235e0e046b75141` / `b309` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9480d95584a4f17c324a3c92` / `b310` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_880b68b51e0f106020a8dbec` / `b311` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_16eff90faf70fb3b03a6b11b` / `b312` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_73d5b7b2beec2399f7ee8322` / `b313` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d60c417a64c19ff7e120c036` / `b314` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_55099892e6eee554d1be0b21` / `b315` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d87ce26d67f0dcd148219378` / `b316` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ae0c720273da183b1a889391` / `b317` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6bdda4e43ab0fe41ce6443da` / `b318` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ac3903d676deefc099fbe2ab` / `b319` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_58174ad4aef18a20c7ccc426` / `b320` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0946baa377e860cb106bd975` / `b321` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a0bdcc37abb6e6701b3626a3` / `b322` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5d6fda7eeae16643e68fb4ae` / `b323` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c046a8bb4de30bbfaf759b4f` / `b324` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_bc25538115d8c72564fd53f3` / `b325` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_77f45f60bc71697265318522` / `b326` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_411c1180e0c6535c9286b0a7` / `b327` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_25724ad2efd2a8bfd003735a` / `b328` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_13d5a8d10032c1b34a292603` / `b329` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_8aee76597bd2122a8d8b006c` / `b330` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_49cce28278bef44e993f854a` / `b331` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3ad267932bf306dc4177d365` / `b332` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ca3675ea1fc4cf73095886b5` / `b333` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_849fca6bb9a9c4872e8551b9` / `b334` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_8d76aae67245cde47f6fbc6c` / `b335` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4b0c53edbf673878adfd5e63` / `b336` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5a62a325025acdf2e58356bf` / `b337` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d0487dae98fcc76ad37ad109` / `b338` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f4d65cd3f6ea8b279754f523` / `b339` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5a1c4cbd2767159c1a6f48cf` / `b340` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_8178faa4a539301fff5e4a90` / `b341` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b0a4686a0b935ac67aff00a6` / `b342` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c5d97c2195ea87a8f06f8a32` / `b343` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0c90c23beca256a73199a42c` / `b344` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_12a3646e193867a2280e056d` / `b345` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9f996e5f9a1376d108b5d415` / `b346` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d52aa19f3c6a8844170a3432` / `b347` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2b8548c6b9a1df5a6cf35ce1` / `b348` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_cbd1647294f4608186a5179e` / `b349` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f88b566ebc981225c1dac6e6` / `b350` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f5c19d8e410cfe748c5cfdcd` / `b351` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_80ce79b5beb886efca8d2093` / `b352` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_95b5946d2309920dee7b2f94` / `b353` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1687da6db2b74e69cfe66585` / `b354` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a9a7485f88a3f70c0a1b0877` / `b355` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5001e7ff55daf42c6d92a0bc` / `b356` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_62eb86793a351aedff5e4db3` / `b357` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_09527eab684c8ee6a551081d` / `b358` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f43bd95cac03055c790c2aa2` / `b359` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5e3b587f2c41faafd96c01e2` / `b360` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_702223d9180807e91106dc72` / `b361` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_728f47b4cf60ddf1ae3af465` / `b362` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e0c2ba0a5bcca1c906b65c6a` / `b363` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b4b78f56a5203e0f5efcdcba` / `b364` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e39a3d3edff8a1fc0365b7af` / `b365` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7cd0f4c68081f5e6a35c265c` / `b366` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9f91ffab4075fa82add99913` / `b367` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c5cd614ba169678b6911e482` / `b368` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d985cddf715742cec2b81c17` / `b369` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_80e4ea9084deba455826a89d` / `b37` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b0c72ac66e7644636c1710c7` / `b370` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fd78385661879ffaf24312e2` / `b371` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_78b8d3271ce46a794bee4d30` / `b372` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e4a2d1527733e3f1eb5404cf` / `b373` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_849e33d3bf4a47de298001df` / `b374` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1e74e6f8857b6b0fe07d1da4` / `b375` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_8dda03ab43276ced9204ef24` / `b376` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2e0456aa6a2367edbfc4b09e` / `b377` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a138ba59f9ab47f23e04ce4f` / `b378` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9cc085f605801df1fccee1a0` / `b379` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6e2e09cee15893f56635a579` / `b38` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_790975b49c579f34988aa41f` / `b380` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_00137fe97cf987b3201e84a6` / `b381` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c8cf382b135ac3a7c0d6707a` / `b382` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9dc47390ac1d1ce5d4c9a45e` / `b383` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_80530218bafc6d9d178b1070` / `b384` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_055b7dc4201eb8c30bc37f1c` / `b385` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c085ace53297719dabb4682f` / `b386` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_37f86082fc2c62c23954099d` / `b387` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fab7281114b9735046bf33c3` / `b388` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_eda7a3c55df146a94bde8fd8` / `b389` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_89fd2b01311538d6a4149360` / `b39` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1497a6d7ba944c8811a380f8` / `b390` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9744c6b9739a5824b9c7c723` / `b391` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7e606bc005fcbd76cb936f2d` / `b392` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ac939827f617220806d3a43e` / `b393` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5a58f0c4319b60a416584a72` / `b394` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_692a1a10cf1e0ecd25d1b6c5` / `b395` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_19c89726a00807c83b61609d` / `b396` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_08aa8aeba80bf18970fbe7d6` / `b397` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_57667ac86352ab94c44ddaf1` / `b398` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_8bbd4ce1d49943bcea0394c4` / `b399` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c084b51cfd3e6937b7325368` / `b40` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_283ac57ba2c2e79e6748d062` / `b400` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_05f770d815101434eb050b19` / `b401` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c7def84444b18d535b1f2fea` / `b402` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4409219f09bc351688c14457` / `b403` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_cba0c1387096f1b1c48e7cd4` / `b404` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_123d5c12b89bda57aff47ebc` / `b405` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5566a6ade332feb4d9d628cf` / `b406` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_cf0fb26a4f49da62ed7842ce` / `b407` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fbb2039399ebca8bea6f43d4` / `b408` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5af724003ad3ea3b8dff6757` / `b409` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_34ea113a27aab89fb4971f52` / `b41` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5786f2e5c1113f162d9e62e8` / `b410` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_434b0c73717e46f4555a73e0` / `b411` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_72032bce93b63eacaf20c3bf` / `b412` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_32b575c560f0ea1f6b3fee1f` / `b413` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_294b7879045bd02182543d77` / `b414` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1ca2c14c7f3887d54875b33e` / `b415` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9a81c07f1d1b579a2ff2baa3` / `b416` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0ad2a11adfdc204562f94935` / `b417` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d811aeab7b95507d775dde49` / `b418` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b7fefe503b3df77e17c68127` / `b419` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f45f93640d61edc3d7cfa194` / `b42` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e0813247bf37a861a181dbb5` / `b420` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6dbc3a805b6e8b87d5eaf12f` / `b421` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_944b2a8313c9fe8dd6078c76` / `b422` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1080df31b058992c3d2fe316` / `b423` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_8d0b04a7506e35c0564ce859` / `b424` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d97fdba82b92c020ad178e6d` / `b425` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_eec4c6f3936697b38e2f08d0` / `b426` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_bcfd8a1f688920066f121b9b` / `b427` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5bec5a63a50fda732148707b` / `b428` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0bc991bebfe919a76386a788` / `b429` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_df1e6136e1e7cef0c92e8060` / `b43` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1ebf774cb22a6138137808f4` / `b430` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3b12a06fd17e95f6271b825c` / `b431` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2cc1b84e1a745e56465ea950` / `b432` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1cfc092db54dd9e446851b27` / `b433` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c991332433b74c5888f16f84` / `b434` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_07eee0aabebb9e504bb466b5` / `b435` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e731297081dd777d6b85f9e9` / `b436` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ab26d1479d5347665f41f9ed` / `b437` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_23fced9d3b6f5b4bb3c4cf9e` / `b438` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_696df96a0652427cf14b8569` / `b439` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_684031277ce038a0140fc9c1` / `b44` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e334968edea37691aff1c796` / `b440` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2dd5cb108a7fb353f59416ed` / `b441` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c818ba12e73df7bceb5e74c6` / `b442` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c935dba43bbe503693a029fc` / `b443` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a589d8e23032c29db708b7e9` / `b444` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b02f7a89065d6b05be50c2a0` / `b445` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_40c74d38a578724d7658e9df` / `b446` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6880f8b4941c12ccc3298e36` / `b447` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d33f8992ed05f146db8c7e8a` / `b448` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4c38d493cca9898462126cc8` / `b449` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_035c1f5aeedf15e2a0203203` / `b45` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9b4fa35f15d2d3e9edfe1e75` / `b450` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_071f1fc81617e4b9b9c5b1d5` / `b451` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4db00996fb297bc7218482e8` / `b452` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5f8e3ed2a728f356cff98e21` / `b453` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b795d2613729e4397b8dbbcd` / `b454` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ef5b1915fd6ef788a135fab7` / `b46` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2659dccadab741279620018d` / `b465` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d431efbaa608b01204c46dd1` / `b467` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_87c970430a52dd495eb9c4de` / `b469` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6643575f49b1aa72a90d4585` / `b47` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9b637481f384dfc5d34382a3` / `b471` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5654456b53969bf489481198` / `b473` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_99b13d3723cda534ff04a254` / `b475` — **SENT, NOT CITED**; packets: core_financial
- `ev_0b1ea4040a20462579a01e8d` / `b476` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_18162b48201f24406533affa` / `b477` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2c668e2290ec725b5ad5e14a` / `b478` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fa2086a4cbcbaaf2db6089b1` / `b48` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a78e6d781e8b1bb5d901956c` / `b49` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ee64da1f1cbbcbb727ac3581` / `b50` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_24f61a66c0bfd930d4478b17` / `b51` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_20a28cdc9dd764da205be725` / `b52` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1d4b70677309cbd05513b2df` / `b53` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_298992ad2c818a529a7b0f97` / `b533` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b02ecd3eddf60a58efcf04fe` / `b535` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f036d5d681c5c6857402f4e6` / `b54` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a05c25f5381169e80b1e94d8` / `b55` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_47d1e8d170d9cdd42c3aae5a` / `b56` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4cb0fd9f00f2a80bc7e4f1b2` / `b57` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_27254d4d3fc9fdd471c77110` / `b58` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e2ae31e8736712d582b67b55` / `b59` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c18c1728532e5e8bd258313a` / `b60` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9ef53fe19a3ad509ded2906a` / `b61` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4e04f45e8b3dcbf89bfbe7d1` / `b62` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0b9815ea4bcb82a33189b4c8` / `b63` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_150a2cfe65b193ecc25864ce` / `b64` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4085cac86a87b84cf39addfe` / `b65` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_60e773a8541e306f4cc2b10d` / `b66` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d23202edac18048958dbb3ce` / `b67` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7c71fc2ecddb8eff455b3660` / `b68` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9aa7983d0718fd7e75cfa0c7` / `b69` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_3487bdc75cdd49a9ea555f81` / `b70` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5cefa3f6540fb2b7a13ba6f6` / `b71` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b421ce6d1de6f73c4dad426c` / `b72` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c2700fc6725203e86e649279` / `b73` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_927e9d0c7d9dfa473c749daa` / `b74` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_5fc7dd316ba66d62c7cc78d6` / `b75` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_34ff29a626f0315e338673ff` / `b76` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_45a578dee0b39882f2fe0898` / `b77` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_26e00a39664b9a6dbf34821f` / `b78` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_a377141ca646914b70103d02` / `b79` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1c54d75899303eee9ad829a7` / `b80` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_216c14de5d6e43b123145015` / `b81` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1743babed3bfe4eeb52763a3` / `b82` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_9898a558186390a39afa6e9e` / `b83` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_83d2c2a5f2fc866f3e2d84d7` / `b84` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e2d4eccb79173a13436869d7` / `b85` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e58e06138e00bc0783bff870` / `b86` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_e8aeb11f8a225ddd9a79f3e3` / `b87` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_0211206f9818a3b37b2707ab` / `b88` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ea1f04a50322d25f1a83ea3b` / `b89` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_83248bf1dbde530dbd8f5f22` / `b90` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_03cb1cd8156e7ea8da74fe29` / `b91` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_40445c969f1182b19235a268` / `b92` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7c7bbe99f43d1439c0b7fab1` / `b93` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_95ddc4797d40b80ff7c3b222` / `b94` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b9157c8783916e75a73f9050` / `b95` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1a3560d1cbcdc8da362a5495` / `b96` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_99672f159f3ef0edbe20e4a0` / `b97` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_272ab0a5e455280a5e248171` / `b98` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2b8eb5a4a48200619c90794f` / `b99` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_853da357a912cf61bec49e68` / `document:0:7c14c23cc9de:page:1:block:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fac058e60419638c5db03519` / `document:0:7c14c23cc9de:page:1:block:1` — **SENT, NOT CITED**; packets: eligibility_and_documents
- `ev_8f3148a90954140df449dfae` / `document:0:7c14c23cc9de:page:1:table:0:row:0` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_d80fb1def0737c78e6adc438` / `document:0:7c14c23cc9de:page:1:table:0:row:1` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_82e61e3c4e211e4d591522b8` / `document:0:7c14c23cc9de:page:1:table:0:row:10` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_76496be0fa0b99e7bb2a0c33` / `document:0:7c14c23cc9de:page:1:table:0:row:11` — **SENT, NOT CITED**; packets: required_documents
- `ev_2e32ab07db4a8d52c4d30fb1` / `document:0:7c14c23cc9de:page:1:table:0:row:12` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_b82fd28e943d92acd88ee161` / `document:0:7c14c23cc9de:page:1:table:0:row:13` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_fb4e4a445a5eb99e2e15dbc6` / `document:0:7c14c23cc9de:page:1:table:0:row:2` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_77b589e6d956107f94a11036` / `document:0:7c14c23cc9de:page:1:table:0:row:3` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_f94852be8c61dfda7e7ec977` / `document:0:7c14c23cc9de:page:1:table:0:row:4` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ef02c1c30b539245d6332aff` / `document:0:7c14c23cc9de:page:1:table:0:row:5` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_1c3a521ff24d162779095388` / `document:0:7c14c23cc9de:page:1:table:0:row:6` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_81e5b9ee114d5835b1bce6ab` / `document:0:7c14c23cc9de:page:1:table:0:row:7` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_30806be82bc1000bb8901412` / `document:0:7c14c23cc9de:page:1:table:0:row:8` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_07b0ba11b1752f1e004e37b3` / `document:0:7c14c23cc9de:page:1:table:0:row:9` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_29a059d602bd0db6dfa43dcc` / `b28` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_868b52ee799f2105416aa5c9` / `b29` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_320f15b4c640f6dd5fa549d2` / `b30` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_2a946b43d5392bb6982e9f8f` / `b31` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_ca4b759a2bfbd69841f92b5f` / `b32` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_6ffe43483915c5f74cb81411` / `b33` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_c7fd12a9e43c1b94830a65af` / `b34` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_7e2e2579798c6e6af9e61f45` / `b35` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
- `ev_4b5e23005533ba071a717e1f` / `b17` — **NOT SENT TO SEMANTIC LLM**; packets: (none)
