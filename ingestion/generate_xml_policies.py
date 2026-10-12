"""
Generate XML files for policies 003–006, each with 4 transactions.
Transaction types:  1=NewBusiness  2=Endorsement  3=Endorsement  4=Cancellation|Renewal
"""

import os
from textwrap import dedent

OUTPUT_DIR = "/sessions/quirky-gifted-planck/mnt/insurance-xml-platform/ingestion/sample_xml"

# ── Policy definitions ────────────────────────────────────────────────────────
POLICIES = [
    # Policy 003: Midwest Haulers Corp  – OH – 3 vehicles – Cancellation at txn4
    {
        "num": "003",
        "policyNumber": "CAP-2024-334455",
        "insuredName": "Midwest Haulers Corp",
        "fein": "35-2019876",
        "street": "5500 Lakeside Industrial Pkwy",
        "city": "Columbus",
        "state": "OH",
        "zip": "43219",
        "phone": "6145550310",
        "email": "fleet@midwesthaulers.example.com",
        "billingPlan": "SEMIANNUAL",
        "premiumNB": "21750.00",
        "premiumEnd1": "23500.00",
        "premiumEnd2": "25000.00",
        "txn4Type": "Cancellation",
        "txn4Doc": "CommercialAutoPolicyCancellation",
        "radiusNB": "600",
        "vehicles": [
            {
                "vehicleId": "VEH-001", "seq": 1,
                "vin": "1FUJHHDR5MLMN0001", "year": 2021,
                "make": "Peterbilt", "model": "579",
                "bodyType": "Tractor", "gvwr": 80000,
                "garageState": "OH", "garageZip": "43219",
                "statedValue": "155000.00",
                "coverages": [
                    {"code": "BI", "desc": "Bodily Injury Liability",
                     "limitPerson": "1000000.00", "limitOcc": "2000000.00", "ded": "0.00", "prem": "4800.00"},
                    {"code": "PD", "desc": "Property Damage Liability",
                     "limitOcc": "1000000.00", "ded": "0.00", "prem": "2050.00"},
                    {"code": "COMP", "desc": "Comprehensive Physical Damage",
                     "limitOcc": "155000.00", "ded": "2500.00", "prem": "1280.00"},
                    {"code": "COLL", "desc": "Collision Physical Damage",
                     "limitOcc": "155000.00", "ded": "5000.00", "prem": "1820.00"},
                ],
                "registrants": [
                    {"seq": 1, "type": "Owner", "name": "Midwest Haulers Corp", "state": "OH", "lic": "OH-CDL-2291100"},
                    {"seq": 2, "type": "Driver", "name": "Dale R. Forsythe", "state": "OH", "lic": "OH-DL-5543221"},
                ],
            },
            {
                "vehicleId": "VEH-002", "seq": 2,
                "vin": "1FUJHHDR7MLMN0002", "year": 2020,
                "make": "Peterbilt", "model": "389",
                "bodyType": "Tractor", "gvwr": 80000,
                "garageState": "OH", "garageZip": "43219",
                "statedValue": "140000.00",
                "coverages": [
                    {"code": "BI", "desc": "Bodily Injury Liability",
                     "limitPerson": "1000000.00", "limitOcc": "2000000.00", "ded": "0.00", "prem": "4800.00"},
                    {"code": "PD", "desc": "Property Damage Liability",
                     "limitOcc": "1000000.00", "ded": "0.00", "prem": "2050.00"},
                    {"code": "COMP", "desc": "Comprehensive Physical Damage",
                     "limitOcc": "140000.00", "ded": "2500.00", "prem": "1150.00"},
                ],
                "registrants": [
                    {"seq": 1, "type": "Owner", "name": "Midwest Haulers Corp", "state": "OH", "lic": "OH-CDL-2291100"},
                    {"seq": 2, "type": "Driver", "name": "Sandra K. Yount", "state": "OH", "lic": "OH-DL-8821099"},
                ],
            },
            {
                "vehicleId": "VEH-003", "seq": 3,
                "vin": "1UYVS25311M550003", "year": 2019,
                "make": "Strick", "model": "Flatbed 48",
                "bodyType": "Trailer", "gvwr": 48000,
                "garageState": "OH", "garageZip": "43219",
                "statedValue": "28000.00",
                "coverages": [
                    {"code": "COMP", "desc": "Comprehensive Physical Damage",
                     "limitOcc": "28000.00", "ded": "1000.00", "prem": "280.00"},
                    {"code": "COLL", "desc": "Collision Physical Damage",
                     "limitOcc": "28000.00", "ded": "2000.00", "prem": "210.00"},
                ],
                "registrants": [
                    {"seq": 1, "type": "Owner", "name": "Midwest Haulers Corp", "state": "OH", "lic": "OH-CDL-2291100"},
                ],
            },
        ],
    },

    # Policy 004: Suncoast Express LLC – FL – 2 vehicles – Renewal at txn4
    {
        "num": "004",
        "policyNumber": "CAP-2024-556677",
        "insuredName": "Suncoast Express LLC",
        "fein": "59-3847201",
        "street": "12200 NW 25th St",
        "city": "Miami",
        "state": "FL",
        "zip": "33182",
        "phone": "3055550499",
        "email": "ops@suncoastexpress.example.com",
        "billingPlan": "ANNUAL",
        "premiumNB": "16800.00",
        "premiumEnd1": "18200.00",
        "premiumEnd2": "19500.00",
        "txn4Type": "Renewal",
        "txn4Doc": "CommercialAutoPolicyRenewal",
        "radiusNB": "400",
        "vehicles": [
            {
                "vehicleId": "VEH-001", "seq": 1,
                "vin": "3AKJHHDRXLSLN5001", "year": 2022,
                "make": "Freightliner", "model": "Cascadia",
                "bodyType": "Tractor", "gvwr": 80000,
                "garageState": "FL", "garageZip": "33182",
                "statedValue": "172000.00",
                "coverages": [
                    {"code": "BI", "desc": "Bodily Injury Liability",
                     "limitPerson": "1000000.00", "limitOcc": "2000000.00", "ded": "0.00", "prem": "4500.00"},
                    {"code": "PD", "desc": "Property Damage Liability",
                     "limitOcc": "1000000.00", "ded": "0.00", "prem": "1950.00"},
                    {"code": "COMP", "desc": "Comprehensive Physical Damage",
                     "limitOcc": "172000.00", "ded": "2500.00", "prem": "1420.00"},
                    {"code": "COLL", "desc": "Collision Physical Damage",
                     "limitOcc": "172000.00", "ded": "5000.00", "prem": "1980.00"},
                ],
                "registrants": [
                    {"seq": 1, "type": "Owner", "name": "Suncoast Express LLC", "state": "FL", "lic": "FL-CDL-7732100"},
                    {"seq": 2, "type": "Driver", "name": "Anthony J. Perez", "state": "FL", "lic": "FL-DL-4412009"},
                ],
            },
            {
                "vehicleId": "VEH-002", "seq": 2,
                "vin": "3AKJHHDRYLSLN5002", "year": 2021,
                "make": "Freightliner", "model": "Cascadia",
                "bodyType": "Tractor", "gvwr": 80000,
                "garageState": "FL", "garageZip": "33182",
                "statedValue": "160000.00",
                "coverages": [
                    {"code": "BI", "desc": "Bodily Injury Liability",
                     "limitPerson": "1000000.00", "limitOcc": "2000000.00", "ded": "0.00", "prem": "4500.00"},
                    {"code": "PD", "desc": "Property Damage Liability",
                     "limitOcc": "1000000.00", "ded": "0.00", "prem": "1950.00"},
                    {"code": "COMP", "desc": "Comprehensive Physical Damage",
                     "limitOcc": "160000.00", "ded": "2500.00", "prem": "1300.00"},
                    {"code": "COLL", "desc": "Collision Physical Damage",
                     "limitOcc": "160000.00", "ded": "5000.00", "prem": "1800.00"},
                ],
                "registrants": [
                    {"seq": 1, "type": "Owner", "name": "Suncoast Express LLC", "state": "FL", "lic": "FL-CDL-7732100"},
                    {"seq": 2, "type": "Driver", "name": "Luisa M. Vargas", "state": "FL", "lic": "FL-DL-9938812"},
                ],
            },
        ],
    },

    # Policy 005: Great Plains Transport – KS – 4 vehicles – Renewal at txn4
    {
        "num": "005",
        "policyNumber": "CAP-2024-778899",
        "insuredName": "Great Plains Transport LLC",
        "fein": "48-2934510",
        "street": "2200 E Douglas Ave",
        "city": "Wichita",
        "state": "KS",
        "zip": "67211",
        "phone": "3165550612",
        "email": "fleet@greatplainstransport.example.com",
        "billingPlan": "ANNUAL",
        "premiumNB": "29400.00",
        "premiumEnd1": "31000.00",
        "premiumEnd2": "33500.00",
        "txn4Type": "Renewal",
        "txn4Doc": "CommercialAutoPolicyRenewal",
        "radiusNB": "800",
        "vehicles": [
            {
                "vehicleId": "VEH-001", "seq": 1,
                "vin": "1XPBDP9X8ND900001", "year": 2023,
                "make": "Peterbilt", "model": "579",
                "bodyType": "Tractor", "gvwr": 80000,
                "garageState": "KS", "garageZip": "67211",
                "statedValue": "185000.00",
                "coverages": [
                    {"code": "BI", "desc": "Bodily Injury Liability",
                     "limitPerson": "1000000.00", "limitOcc": "2000000.00", "ded": "0.00", "prem": "5400.00"},
                    {"code": "PD", "desc": "Property Damage Liability",
                     "limitOcc": "1000000.00", "ded": "0.00", "prem": "2300.00"},
                    {"code": "COMP", "desc": "Comprehensive Physical Damage",
                     "limitOcc": "185000.00", "ded": "2500.00", "prem": "1500.00"},
                    {"code": "COLL", "desc": "Collision Physical Damage",
                     "limitOcc": "185000.00", "ded": "5000.00", "prem": "2100.00"},
                ],
                "registrants": [
                    {"seq": 1, "type": "Owner", "name": "Great Plains Transport LLC", "state": "KS", "lic": "KS-CDL-3301122"},
                    {"seq": 2, "type": "Driver", "name": "Harold B. Owens", "state": "KS", "lic": "KS-DL-6612300"},
                ],
            },
            {
                "vehicleId": "VEH-002", "seq": 2,
                "vin": "1XPBDP9X9ND900002", "year": 2022,
                "make": "Peterbilt", "model": "389",
                "bodyType": "Tractor", "gvwr": 80000,
                "garageState": "KS", "garageZip": "67211",
                "statedValue": "168000.00",
                "coverages": [
                    {"code": "BI", "desc": "Bodily Injury Liability",
                     "limitPerson": "1000000.00", "limitOcc": "2000000.00", "ded": "0.00", "prem": "5400.00"},
                    {"code": "PD", "desc": "Property Damage Liability",
                     "limitOcc": "1000000.00", "ded": "0.00", "prem": "2300.00"},
                    {"code": "COMP", "desc": "Comprehensive Physical Damage",
                     "limitOcc": "168000.00", "ded": "2500.00", "prem": "1380.00"},
                    {"code": "COLL", "desc": "Collision Physical Damage",
                     "limitOcc": "168000.00", "ded": "5000.00", "prem": "1920.00"},
                ],
                "registrants": [
                    {"seq": 1, "type": "Owner", "name": "Great Plains Transport LLC", "state": "KS", "lic": "KS-CDL-3301122"},
                    {"seq": 2, "type": "Driver", "name": "Lisa C. Drummond", "state": "KS", "lic": "KS-DL-4401988"},
                ],
            },
            {
                "vehicleId": "VEH-003", "seq": 3,
                "vin": "1UYVS25321M600001", "year": 2021,
                "make": "Utility", "model": "3000R",
                "bodyType": "Trailer", "gvwr": 45000,
                "garageState": "KS", "garageZip": "67211",
                "statedValue": "34000.00",
                "coverages": [
                    {"code": "COMP", "desc": "Comprehensive Physical Damage",
                     "limitOcc": "34000.00", "ded": "1000.00", "prem": "340.00"},
                    {"code": "COLL", "desc": "Collision Physical Damage",
                     "limitOcc": "34000.00", "ded": "2000.00", "prem": "255.00"},
                ],
                "registrants": [
                    {"seq": 1, "type": "Owner", "name": "Great Plains Transport LLC", "state": "KS", "lic": "KS-CDL-3301122"},
                ],
            },
            {
                "vehicleId": "VEH-004", "seq": 4,
                "vin": "1UYVS25321M600002", "year": 2021,
                "make": "Wabash", "model": "DuraPlate 53",
                "bodyType": "Trailer", "gvwr": 45000,
                "garageState": "KS", "garageZip": "67211",
                "statedValue": "40000.00",
                "coverages": [
                    {"code": "COMP", "desc": "Comprehensive Physical Damage",
                     "limitOcc": "40000.00", "ded": "1000.00", "prem": "400.00"},
                    {"code": "COLL", "desc": "Collision Physical Damage",
                     "limitOcc": "40000.00", "ded": "2000.00", "prem": "300.00"},
                ],
                "registrants": [
                    {"seq": 1, "type": "Owner", "name": "Great Plains Transport LLC", "state": "KS", "lic": "KS-CDL-3301122"},
                ],
            },
        ],
    },

    # Policy 006: Pacific Rim Carriers Inc – CA – 3 vehicles – Renewal at txn4
    {
        "num": "006",
        "policyNumber": "CAP-2024-990011",
        "insuredName": "Pacific Rim Carriers Inc",
        "fein": "94-7612340",
        "street": "3800 Port Commerce Blvd",
        "city": "Los Angeles",
        "state": "CA",
        "zip": "90058",
        "phone": "3235550728",
        "email": "insurance@pacificrimcarriers.example.com",
        "billingPlan": "MONTHLY",
        "premiumNB": "38200.00",
        "premiumEnd1": "40100.00",
        "premiumEnd2": "42500.00",
        "txn4Type": "Renewal",
        "txn4Doc": "CommercialAutoPolicyRenewal",
        "radiusNB": "1000",
        "vehicles": [
            {
                "vehicleId": "VEH-001", "seq": 1,
                "vin": "1XKYDP9X7NJ700001", "year": 2023,
                "make": "Kenworth", "model": "W990",
                "bodyType": "Tractor", "gvwr": 80000,
                "garageState": "CA", "garageZip": "90058",
                "statedValue": "195000.00",
                "coverages": [
                    {"code": "BI", "desc": "Bodily Injury Liability",
                     "limitPerson": "1000000.00", "limitOcc": "2000000.00", "ded": "0.00", "prem": "7200.00"},
                    {"code": "PD", "desc": "Property Damage Liability",
                     "limitOcc": "1000000.00", "ded": "0.00", "prem": "3100.00"},
                    {"code": "COMP", "desc": "Comprehensive Physical Damage",
                     "limitOcc": "195000.00", "ded": "2500.00", "prem": "1620.00"},
                    {"code": "COLL", "desc": "Collision Physical Damage",
                     "limitOcc": "195000.00", "ded": "5000.00", "prem": "2280.00"},
                ],
                "registrants": [
                    {"seq": 1, "type": "Owner", "name": "Pacific Rim Carriers Inc", "state": "CA", "lic": "CA-CDL-1122334"},
                    {"seq": 2, "type": "Driver", "name": "Wei J. Chang", "state": "CA", "lic": "CA-DL-8833009"},
                ],
            },
            {
                "vehicleId": "VEH-002", "seq": 2,
                "vin": "1XKYDP9X8NJ700002", "year": 2022,
                "make": "Kenworth", "model": "T680",
                "bodyType": "Tractor", "gvwr": 80000,
                "garageState": "CA", "garageZip": "90058",
                "statedValue": "178000.00",
                "coverages": [
                    {"code": "BI", "desc": "Bodily Injury Liability",
                     "limitPerson": "1000000.00", "limitOcc": "2000000.00", "ded": "0.00", "prem": "7200.00"},
                    {"code": "PD", "desc": "Property Damage Liability",
                     "limitOcc": "1000000.00", "ded": "0.00", "prem": "3100.00"},
                    {"code": "COMP", "desc": "Comprehensive Physical Damage",
                     "limitOcc": "178000.00", "ded": "2500.00", "prem": "1480.00"},
                    {"code": "COLL", "desc": "Collision Physical Damage",
                     "limitOcc": "178000.00", "ded": "5000.00", "prem": "2080.00"},
                ],
                "registrants": [
                    {"seq": 1, "type": "Owner", "name": "Pacific Rim Carriers Inc", "state": "CA", "lic": "CA-CDL-1122334"},
                    {"seq": 2, "type": "Driver", "name": "Rosa M. Delgado", "state": "CA", "lic": "CA-DL-5511782"},
                ],
            },
            {
                "vehicleId": "VEH-003", "seq": 3,
                "vin": "1UYVS25310M700003", "year": 2020,
                "make": "Great Dane", "model": "Everest SS",
                "bodyType": "Trailer", "gvwr": 45000,
                "garageState": "CA", "garageZip": "90058",
                "statedValue": "42000.00",
                "coverages": [
                    {"code": "COMP", "desc": "Comprehensive Physical Damage",
                     "limitOcc": "42000.00", "ded": "1000.00", "prem": "420.00"},
                    {"code": "COLL", "desc": "Collision Physical Damage",
                     "limitOcc": "42000.00", "ded": "2000.00", "prem": "315.00"},
                ],
                "registrants": [
                    {"seq": 1, "type": "Owner", "name": "Pacific Rim Carriers Inc", "state": "CA", "lic": "CA-CDL-1122334"},
                ],
            },
        ],
    },
]

# Transaction date schedules per policy num
TXN_SCHEDULES = {
    "003": [
        ("2024-04-01", "2024-03-15T10:00:00Z", "NewBusiness",    "2025-04-01"),
        ("2024-06-01", "2024-05-28T13:30:00Z", "Endorsement",    "2025-04-01"),
        ("2024-09-15", "2024-09-10T08:45:00Z", "Endorsement",    "2025-04-01"),
        ("2024-11-01", "2024-10-25T15:00:00Z", "Cancellation",   "2024-11-01"),
    ],
    "004": [
        ("2024-05-01", "2024-04-18T09:00:00Z", "NewBusiness",    "2025-05-01"),
        ("2024-07-15", "2024-07-10T11:00:00Z", "Endorsement",    "2025-05-01"),
        ("2024-11-01", "2024-10-28T14:20:00Z", "Endorsement",    "2025-05-01"),
        ("2025-05-01", "2025-03-01T08:00:00Z", "Renewal",        "2026-05-01"),
    ],
    "005": [
        ("2024-06-15", "2024-06-01T10:30:00Z", "NewBusiness",    "2025-06-15"),
        ("2024-08-01", "2024-07-25T09:00:00Z", "Endorsement",    "2025-06-15"),
        ("2024-12-01", "2024-11-20T16:00:00Z", "Endorsement",    "2025-06-15"),
        ("2025-06-15", "2025-04-15T08:00:00Z", "Renewal",        "2026-06-15"),
    ],
    "006": [
        ("2024-07-01", "2024-06-20T11:00:00Z", "NewBusiness",    "2025-07-01"),
        ("2024-09-01", "2024-08-28T10:15:00Z", "Endorsement",    "2025-07-01"),
        ("2025-01-01", "2024-12-15T09:30:00Z", "Endorsement",    "2025-07-01"),
        ("2025-07-01", "2025-05-01T08:00:00Z", "Renewal",        "2026-07-01"),
    ],
}


def coverage_xml(cov, eff_date, exp_date, indent="          "):
    limit_person = f'\n{indent}    limitPerPerson="{cov["limitPerson"]}"' if "limitPerson" in cov else ""
    return (
        f'{indent}<ObjectCoverageInformation\n'
        f'{indent}    coverageCode="{cov["code"]}"\n'
        f'{indent}    coverageDescription="{cov["desc"]}"{limit_person}\n'
        f'{indent}    limitPerOccurrence="{cov["limitOcc"]}"\n'
        f'{indent}    deductible="{cov["ded"]}"\n'
        f'{indent}    premium="{cov["prem"]}"\n'
        f'{indent}    effectiveDate="{eff_date}"\n'
        f'{indent}    expirationDate="{exp_date}"/>'
    )


def registrant_xml(reg, indent="          "):
    return (
        f'{indent}<Registrant\n'
        f'{indent}    registrantSequence="{reg["seq"]}"\n'
        f'{indent}    registrantType="{reg["type"]}"\n'
        f'{indent}    registrantName="{reg["name"]}"\n'
        f'{indent}    registrantState="{reg["state"]}"\n'
        f'{indent}    licenseNumber="{reg["lic"]}"/>'
    )


def vehicle_xml(v, eff_date, exp_date):
    regs = "\n".join(registrant_xml(r) for r in v["registrants"])
    covs = "\n\n".join(coverage_xml(c, eff_date, exp_date) for c in v["coverages"])
    return f"""\
        <Vehicle
            vehicleId="{v['vehicleId']}"
            sequenceNumber="{v['seq']}"
            vin="{v['vin']}"
            year="{v['year']}"
            make="{v['make']}"
            model="{v['model']}"
            bodyType="{v['bodyType']}"
            grossVehicleWeightRating="{v['gvwr']}"
            garageState="{v['garageState']}"
            garageZip="{v['garageZip']}"
            statedValue="{v['statedValue']}">

{regs}

{covs}

        </Vehicle>"""


def build_xml(pol, txn_num, eff_date, create_ts, txn_type, exp_date,
              doc_type, doc_version, premium, num_units, radius, vehicles):
    p = pol
    pol_eff = "2024-01-15"  # fixed for policy 001, overridden below
    # policy effective date = first transaction effective date
    sched = TXN_SCHEDULES[p["num"]]
    pol_eff = sched[0][0]
    # for renewal, new policy number suffix 2025
    pol_number = p["policyNumber"]
    if txn_type == "Renewal":
        pol_number = pol_number.replace("2024", "2025")

    vehicles_xml = "\n\n".join(vehicle_xml(v, eff_date, exp_date) for v in vehicles)

    fname = f"policy_{p['num']}_txn{txn_num}_{txn_type.lower()}.xml"
    txn_id = f"TXN-{eff_date[:4]}-{p['num']}{txn_num:03d}"

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!--
  Policy {p['num']} – Transaction {txn_num}: {txn_type}
  Insured: {p['insuredName']}  |  Policy: {pol_number}
-->
<PolicyTransaction
    transactionId="{txn_id}"
    transactionType="{txn_type}"
    transactionEffectiveDate="{eff_date}"
    transactionCreateTs="{create_ts}"
    sourceSystem="POLICY_ADMIN_V2"
    sourceFileName="{fname}">

  <ObjectDocument
      documentId="DOC-{eff_date[:4]}-{p['num']}{txn_num:03d}"
      documentType="{doc_type}"
      documentVersion="{doc_version}"
      documentEffectiveDate="{eff_date}"
      documentExpirationDate="{exp_date}">

    <Policy
        policyNumber="{pol_number}"
        policyType="CommercialAuto"
        lineOfBusiness="AUTO"
        policyEffectiveDate="{pol_eff}"
        policyExpirationDate="{exp_date}"
        policyState="{p['state']}"
        billingPlan="{p['billingPlan']}"
        premiumAmount="{premium}"
        currency="USD">

      <Insured>
        <InsuredName>{p['insuredName']}</InsuredName>
        <InsuredType>Commercial</InsuredType>
        <FEIN>{p['fein']}</FEIN>
        <Address>
          <Street>{p['street']}</Street>
          <City>{p['city']}</City>
          <State>{p['state']}</State>
          <Zip>{p['zip']}</Zip>
          <Country>US</Country>
        </Address>
        <Contact>
          <Phone>{p['phone']}</Phone>
          <Email>{p['email']}</Email>
        </Contact>
      </Insured>

      <AutoPolicy
          programCode="COMM_AUTO_FLEET"
          fleetIndicator="Y"
          numberOfUnits="{num_units}"
          radiusOfOperation="{radius}"
          primaryUse="Trucking">

{vehicles_xml}

      </AutoPolicy>
    </Policy>

    <DocumentCovered
        coveredSequence="1"
        coveredType="NamedInsured"
        coveredName="{p['insuredName']}"
        coveredState="{p['state']}"/>

  </ObjectDocument>

</PolicyTransaction>
"""


# ── Generate files ─────────────────────────────────────────────────────────
generated = []

for pol in POLICIES:
    sched = TXN_SCHEDULES[pol["num"]]
    premiums = [
        pol["premiumNB"],
        pol["premiumEnd1"],
        pol["premiumEnd2"],
        pol["premiumEnd2"],  # same premium at renewal start
    ]
    doc_types = [
        "CommercialAutoPolicyIssuance",
        "CommercialAutoPolicyEndorsement",
        "CommercialAutoPolicyEndorsement",
        pol["txn4Doc"],
    ]
    txn_types_list = ["NewBusiness", "Endorsement", "Endorsement", pol["txn4Type"]]

    for i, (eff_date, create_ts, txn_type, exp_date) in enumerate(sched, start=1):
        doc_version = i
        radius = pol["radiusNB"] if i == 1 else str(int(pol["radiusNB"]) + 200)
        num_units = len(pol["vehicles"])

        # For endorsements, only include first vehicle to simulate partial update
        if i == 2:
            veh_subset = [pol["vehicles"][0]]
        elif i == 3:
            veh_subset = pol["vehicles"][:2] if len(pol["vehicles"]) >= 2 else pol["vehicles"]
        else:
            veh_subset = pol["vehicles"]

        xml_content = build_xml(
            pol=pol,
            txn_num=i,
            eff_date=eff_date,
            create_ts=create_ts,
            txn_type=txn_type,
            exp_date=exp_date,
            doc_type=doc_types[i - 1],
            doc_version=doc_version,
            premium=premiums[i - 1],
            num_units=num_units,
            radius=radius,
            vehicles=veh_subset,
        )

        fname = f"policy_{pol['num']}_txn{i}_{txn_type.lower()}.xml"
        fpath = os.path.join(OUTPUT_DIR, fname)
        with open(fpath, "w") as f:
            f.write(xml_content)
        generated.append(fname)
        print(f"  ✓  {fname}")

print(f"\nTotal files generated: {len(generated)}")
