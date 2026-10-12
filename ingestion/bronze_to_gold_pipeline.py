"""
bronze_to_gold_pipeline.py
──────────────────────────
Local simulation of the Insurance XML Platform's Bronze → Silver → Gold pipeline.
Replaces AWS Glue + Athena + dbt with pure-Python + SQLite so the full
data flow can be demonstrated without cloud dependencies.

Stages
  1. XML SHREDDER  (Bronze)   – Parse all XMLs → populate 6 Bronze tables in SQLite
  2. STAGING       (Silver)   – Simple CTEs that clean / type-cast Bronze
  3. SILVER        (Silver)   – Joins producing one row per grain
  4. GOLD          (Gold)     – Aggregated analytical tables
  5. REPORT                   – Print summary to console + write CSV exports

Usage:
  python bronze_to_gold_pipeline.py
"""

import os
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
import csv

# ── Config ─────────────────────────────────────────────────────────────────
XML_DIR  = Path("/sessions/quirky-gifted-planck/mnt/insurance-xml-platform/ingestion/sample_xml")
DB_PATH  = Path("/sessions/quirky-gifted-planck/mnt/insurance-xml-platform/local_warehouse.db")
CSV_DIR  = Path("/sessions/quirky-gifted-planck/mnt/insurance-xml-platform/gold_exports")
CSV_DIR.mkdir(parents=True, exist_ok=True)
LOAD_TS  = datetime.now(timezone.utc).isoformat()

# ── Helpers ─────────────────────────────────────────────────────────────────

def s(v): return v.strip() if v else None
def f(v):
    try: return float(v) if v else None
    except: return None
def i_val(v):
    try: return int(v) if v else None
    except: return None

# ── SQLite setup ─────────────────────────────────────────────────────────────

def create_schema(conn):
    conn.executescript("""
    -- ───────────────────────────── BRONZE ────────────────────────────────
    DROP TABLE IF EXISTS br_policy_transaction;
    CREATE TABLE br_policy_transaction (
        transaction_id              TEXT PRIMARY KEY,
        transaction_type            TEXT,
        transaction_effective_date  TEXT,
        transaction_create_ts       TEXT,
        source_system               TEXT,
        source_file_name            TEXT,
        source_load_ts              TEXT
    );

    DROP TABLE IF EXISTS br_policy_transaction_policy;
    CREATE TABLE br_policy_transaction_policy (
        transaction_id          TEXT,
        policy_number           TEXT,
        policy_type             TEXT,
        line_of_business        TEXT,
        policy_effective_date   TEXT,
        policy_expiration_date  TEXT,
        policy_state            TEXT,
        billing_plan            TEXT,
        premium_amount          REAL,
        currency                TEXT,
        insured_name            TEXT,
        insured_type            TEXT,
        fein                    TEXT,
        insured_street          TEXT,
        insured_city            TEXT,
        insured_state           TEXT,
        insured_zip             TEXT,
        insured_country         TEXT,
        insured_phone           TEXT,
        insured_email           TEXT,
        source_load_ts          TEXT
    );

    DROP TABLE IF EXISTS br_policy_auto;
    CREATE TABLE br_policy_auto (
        transaction_id          TEXT,
        policy_number           TEXT,
        program_code            TEXT,
        fleet_indicator         TEXT,
        number_of_units         INTEGER,
        radius_of_operation     INTEGER,
        primary_use             TEXT,
        source_load_ts          TEXT
    );

    DROP TABLE IF EXISTS br_policy_auto_vehicle;
    CREATE TABLE br_policy_auto_vehicle (
        transaction_id              TEXT,
        vehicle_id                  TEXT,
        sequence_number             INTEGER,
        vin                         TEXT,
        vehicle_year                INTEGER,
        make                        TEXT,
        model                       TEXT,
        body_type                   TEXT,
        gross_vehicle_weight_rating INTEGER,
        garage_state                TEXT,
        garage_zip                  TEXT,
        stated_value                REAL,
        source_load_ts              TEXT
    );

    DROP TABLE IF EXISTS br_policy_vehicle_registrants;
    CREATE TABLE br_policy_vehicle_registrants (
        transaction_id          TEXT,
        vehicle_id              TEXT,
        registrant_sequence     INTEGER,
        registrant_type         TEXT,
        registrant_name         TEXT,
        registrant_state        TEXT,
        license_number          TEXT,
        source_load_ts          TEXT
    );

    DROP TABLE IF EXISTS br_object_coverage_information;
    CREATE TABLE br_object_coverage_information (
        transaction_id          TEXT,
        vehicle_id              TEXT,
        coverage_code           TEXT,
        coverage_description    TEXT,
        limit_per_person        REAL,
        limit_per_occurrence    REAL,
        deductible              REAL,
        premium                 REAL,
        effective_date          TEXT,
        expiration_date         TEXT,
        source_load_ts          TEXT
    );
    """)
    conn.commit()
    print("✓ Bronze schema created")


# ── Stage 1: XML Shredder → Bronze ──────────────────────────────────────────

def shred_xml_to_bronze(conn):
    xml_files = sorted(XML_DIR.glob("*.xml"))
    loaded = 0

    for xml_path in xml_files:
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except ET.ParseError as e:
            print(f"  ✗ Parse error {xml_path.name}: {e}")
            continue

        txn_id   = s(root.get("transactionId"))
        txn_type = s(root.get("transactionType"))
        txn_eff  = s(root.get("transactionEffectiveDate"))
        txn_ts   = s(root.get("transactionCreateTs"))
        src_sys  = s(root.get("sourceSystem"))
        src_file = s(root.get("sourceFileName"))

        # Skip duplicates (re-runnable)
        existing = conn.execute(
            "SELECT 1 FROM br_policy_transaction WHERE transaction_id=?", (txn_id,)
        ).fetchone()
        if existing:
            continue

        conn.execute(
            "INSERT INTO br_policy_transaction VALUES (?,?,?,?,?,?,?)",
            (txn_id, txn_type, txn_eff, txn_ts, src_sys, src_file, LOAD_TS)
        )

        for obj_doc in root.findall("ObjectDocument"):
            pol = obj_doc.find("Policy")
            if pol is None:
                continue

            pol_num  = s(pol.get("policyNumber"))
            ins      = pol.find("Insured")
            ins_name = s(ins.findtext("InsuredName")) if ins else None
            ins_type = s(ins.findtext("InsuredType")) if ins else None
            fein     = s(ins.findtext("FEIN")) if ins else None
            addr     = ins.find("Address") if ins else None
            contact  = ins.find("Contact") if ins else None

            conn.execute(
                "INSERT INTO br_policy_transaction_policy VALUES "
                "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    txn_id, pol_num,
                    s(pol.get("policyType")), s(pol.get("lineOfBusiness")),
                    s(pol.get("policyEffectiveDate")), s(pol.get("policyExpirationDate")),
                    s(pol.get("policyState")), s(pol.get("billingPlan")),
                    f(pol.get("premiumAmount")), s(pol.get("currency")),
                    ins_name, ins_type, fein,
                    s(addr.findtext("Street")) if addr else None,
                    s(addr.findtext("City")) if addr else None,
                    s(addr.findtext("State")) if addr else None,
                    s(addr.findtext("Zip")) if addr else None,
                    s(addr.findtext("Country")) if addr else None,
                    s(contact.findtext("Phone")) if contact else None,
                    s(contact.findtext("Email")) if contact else None,
                    LOAD_TS,
                )
            )

            auto_pol = pol.find("AutoPolicy")
            if auto_pol is not None:
                conn.execute(
                    "INSERT INTO br_policy_auto VALUES (?,?,?,?,?,?,?,?)",
                    (
                        txn_id, pol_num,
                        s(auto_pol.get("programCode")),
                        s(auto_pol.get("fleetIndicator")),
                        i_val(auto_pol.get("numberOfUnits")),
                        i_val(auto_pol.get("radiusOfOperation")),
                        s(auto_pol.get("primaryUse")),
                        LOAD_TS,
                    )
                )

                for veh in auto_pol.findall("Vehicle"):
                    veh_id = s(veh.get("vehicleId"))
                    conn.execute(
                        "INSERT INTO br_policy_auto_vehicle VALUES "
                        "(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            txn_id, veh_id,
                            i_val(veh.get("sequenceNumber")),
                            s(veh.get("vin")),
                            i_val(veh.get("year")),
                            s(veh.get("make")),
                            s(veh.get("model")),
                            s(veh.get("bodyType")),
                            i_val(veh.get("grossVehicleWeightRating")),
                            s(veh.get("garageState")),
                            s(veh.get("garageZip")),
                            f(veh.get("statedValue")),
                            LOAD_TS,
                        )
                    )

                    for reg in veh.findall("Registrant"):
                        conn.execute(
                            "INSERT INTO br_policy_vehicle_registrants VALUES "
                            "(?,?,?,?,?,?,?,?)",
                            (
                                txn_id, veh_id,
                                i_val(reg.get("registrantSequence")),
                                s(reg.get("registrantType")),
                                s(reg.get("registrantName")),
                                s(reg.get("registrantState")),
                                s(reg.get("licenseNumber")),
                                LOAD_TS,
                            )
                        )

                    for cov in veh.findall("ObjectCoverageInformation"):
                        conn.execute(
                            "INSERT INTO br_object_coverage_information VALUES "
                            "(?,?,?,?,?,?,?,?,?,?,?)",
                            (
                                txn_id, veh_id,
                                s(cov.get("coverageCode")),
                                s(cov.get("coverageDescription")),
                                f(cov.get("limitPerPerson")),
                                f(cov.get("limitPerOccurrence")),
                                f(cov.get("deductible")),
                                f(cov.get("premium")),
                                s(cov.get("effectiveDate")),
                                s(cov.get("expirationDate")),
                                LOAD_TS,
                            )
                        )

        loaded += 1

    conn.commit()
    print(f"✓ Bronze loaded: {loaded} XML files")

    # Bronze row counts
    for tbl in [
        "br_policy_transaction", "br_policy_transaction_policy",
        "br_policy_auto", "br_policy_auto_vehicle",
        "br_policy_vehicle_registrants", "br_object_coverage_information",
    ]:
        n = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"     {tbl}: {n:>4} rows")


# ── Stage 2 & 3: Silver views ────────────────────────────────────────────────

def create_silver_views(conn):
    conn.executescript("""
    -- ───────────────────────── STAGING (views) ───────────────────────────
    DROP VIEW IF EXISTS stg_br_policy_transaction;
    CREATE VIEW stg_br_policy_transaction AS
    SELECT
        transaction_id,
        transaction_type,
        transaction_effective_date,
        DATE(transaction_effective_date)    AS transaction_effective_dt,
        transaction_create_ts,
        source_system,
        source_file_name                    AS source_file,
        source_load_ts                      AS ingested_at
    FROM br_policy_transaction;

    DROP VIEW IF EXISTS stg_br_policy_transaction_policy;
    CREATE VIEW stg_br_policy_transaction_policy AS
    SELECT
        transaction_id,
        policy_number,
        policy_type,
        line_of_business,
        DATE(policy_effective_date)         AS policy_effective_dt,
        DATE(policy_expiration_date)        AS policy_expiration_dt,
        policy_state,
        billing_plan,
        premium_amount,
        currency,
        insured_name,
        insured_type
    FROM br_policy_transaction_policy;

    DROP VIEW IF EXISTS stg_br_policy_auto;
    CREATE VIEW stg_br_policy_auto AS
    SELECT
        transaction_id,
        policy_number,
        program_code,
        fleet_indicator,
        number_of_units,
        radius_of_operation,
        primary_use
    FROM br_policy_auto;

    DROP VIEW IF EXISTS stg_br_policy_auto_vehicle;
    CREATE VIEW stg_br_policy_auto_vehicle AS
    SELECT
        transaction_id,
        vehicle_id,
        sequence_number,
        vin,
        vehicle_year,
        make,
        model,
        UPPER(body_type)                    AS body_type,
        gross_vehicle_weight_rating,
        garage_state,
        garage_zip,
        stated_value
    FROM br_policy_auto_vehicle;

    DROP VIEW IF EXISTS stg_br_policy_vehicle_registrants;
    CREATE VIEW stg_br_policy_vehicle_registrants AS
    SELECT
        transaction_id,
        vehicle_id,
        registrant_sequence,
        UPPER(registrant_type)              AS registrant_type,
        registrant_name,
        registrant_state,
        license_number
    FROM br_policy_vehicle_registrants;

    DROP VIEW IF EXISTS stg_br_object_coverage_information;
    CREATE VIEW stg_br_object_coverage_information AS
    SELECT
        transaction_id,
        vehicle_id,
        coverage_code,
        coverage_description,
        limit_per_person,
        limit_per_occurrence,
        deductible,
        premium,
        DATE(effective_date)                AS effective_dt,
        DATE(expiration_date)               AS expiration_dt
    FROM br_object_coverage_information;

    -- ───────────────────────────── SILVER ─────────────────────────────────
    DROP VIEW IF EXISTS sl_policy;
    CREATE VIEW sl_policy AS
    SELECT
        t.transaction_id,
        p.policy_number,
        t.transaction_type,
        t.transaction_effective_dt,
        t.source_system,
        p.insured_name          AS named_insured,
        p.insured_type,
        p.policy_effective_dt,
        p.policy_expiration_dt,
        p.policy_state,
        p.line_of_business,
        p.billing_plan,
        p.premium_amount        AS total_premium,
        p.currency,
        JULIANDAY(p.policy_expiration_dt) - JULIANDAY(p.policy_effective_dt)
                                AS policy_term_days,
        t.source_file,
        t.ingested_at
    FROM stg_br_policy_transaction t
    LEFT JOIN stg_br_policy_transaction_policy p
        ON t.transaction_id = p.transaction_id;

    DROP VIEW IF EXISTS sl_vehicle;
    CREATE VIEW sl_vehicle AS
    SELECT
        v.transaction_id,
        v.vehicle_id,
        p.policy_number,
        p.insured_name          AS named_insured,
        p.policy_effective_dt,
        v.vehicle_year,
        v.make,
        v.model,
        v.vin,
        CASE v.body_type
            WHEN 'TRACTOR' THEN 'TRACTOR'
            WHEN 'TRAILER' THEN 'TRAILER'
            ELSE UPPER(v.body_type)
        END                     AS vehicle_type,
        v.gross_vehicle_weight_rating,
        v.stated_value,
        v.garage_state          AS garaging_state,
        v.garage_zip            AS garaging_zip,
        CAST(strftime('%Y', p.policy_effective_dt) AS INTEGER) - v.vehicle_year
                                AS vehicle_age_at_effective
    FROM stg_br_policy_auto_vehicle v
    LEFT JOIN stg_br_policy_auto a
        ON v.transaction_id = a.transaction_id
    LEFT JOIN stg_br_policy_transaction_policy p
        ON v.transaction_id = p.transaction_id;

    DROP VIEW IF EXISTS sl_vehicle_coverage;
    CREATE VIEW sl_vehicle_coverage AS
    SELECT
        c.transaction_id,
        c.vehicle_id,
        p.policy_number,
        c.coverage_code,
        c.coverage_description,
        c.limit_per_person,
        c.limit_per_occurrence,
        c.deductible            AS deductible_amount,
        c.premium               AS premium_amount,
        c.effective_dt,
        c.expiration_dt
    FROM stg_br_object_coverage_information c
    LEFT JOIN stg_br_policy_transaction_policy p
        ON c.transaction_id = p.transaction_id;

    DROP VIEW IF EXISTS sl_vehicle_registrant;
    CREATE VIEW sl_vehicle_registrant AS
    SELECT
        r.transaction_id,
        r.vehicle_id,
        p.policy_number,
        r.registrant_type,
        r.registrant_name,
        r.registrant_state,
        r.license_number
    FROM stg_br_policy_vehicle_registrants r
    LEFT JOIN stg_br_policy_transaction_policy p
        ON r.transaction_id = p.transaction_id;
    """)
    conn.commit()
    print("✓ Silver views created (staging + silver layers)")


# ── Stage 4: Gold tables ─────────────────────────────────────────────────────

def create_gold_tables(conn):
    conn.executescript("""
    -- ─────────────── GOLD: gl_policy_premium_summary ─────────────────────
    DROP TABLE IF EXISTS gl_policy_premium_summary;
    CREATE TABLE gl_policy_premium_summary AS
    WITH vehicle_counts AS (
        SELECT
            transaction_id,
            COUNT(DISTINCT vehicle_id)                                          AS total_vehicles,
            COUNT(DISTINCT CASE WHEN vehicle_type = 'TRACTOR' THEN vehicle_id END) AS tractor_count,
            COUNT(DISTINCT CASE WHEN vehicle_type = 'TRAILER' THEN vehicle_id END) AS trailer_count,
            COUNT(DISTINCT garaging_state)                                      AS garaging_states
        FROM sl_vehicle
        GROUP BY transaction_id
    ),
    coverage_premiums AS (
        SELECT
            transaction_id,
            ROUND(SUM(premium_amount), 2)                                       AS total_written_premium,
            ROUND(SUM(CASE WHEN coverage_code='BI'   THEN premium_amount ELSE 0 END), 2) AS bi_premium,
            ROUND(SUM(CASE WHEN coverage_code='PD'   THEN premium_amount ELSE 0 END), 2) AS pd_premium,
            ROUND(SUM(CASE WHEN coverage_code='COMP' THEN premium_amount ELSE 0 END), 2) AS comp_premium,
            ROUND(SUM(CASE WHEN coverage_code='COLL' THEN premium_amount ELSE 0 END), 2) AS coll_premium,
            COUNT(DISTINCT coverage_code)                                       AS distinct_coverages
        FROM sl_vehicle_coverage
        GROUP BY transaction_id
    )
    SELECT
        p.transaction_id,
        p.policy_number,
        p.transaction_type,
        p.named_insured,
        p.policy_state,
        p.line_of_business,
        p.policy_effective_dt,
        p.policy_expiration_dt,
        CAST(p.policy_term_days AS INTEGER)                                     AS policy_term_days,
        v.total_vehicles,
        v.tractor_count,
        v.trailer_count,
        v.garaging_states,
        c.total_written_premium,
        c.bi_premium,
        c.pd_premium,
        c.comp_premium,
        c.coll_premium,
        c.distinct_coverages,
        CASE WHEN v.total_vehicles > 0
            THEN ROUND(c.total_written_premium / v.total_vehicles, 2)
            ELSE NULL
        END                                                                     AS avg_premium_per_vehicle
    FROM sl_policy p
    LEFT JOIN vehicle_counts v  ON p.transaction_id = v.transaction_id
    LEFT JOIN coverage_premiums c ON p.transaction_id = c.transaction_id;

    -- ─────────────── GOLD: gl_fleet_risk_profile ──────────────────────────
    DROP TABLE IF EXISTS gl_fleet_risk_profile;
    CREATE TABLE gl_fleet_risk_profile AS
    WITH coverage_pivot AS (
        SELECT
            transaction_id,
            vehicle_id,
            ROUND(SUM(premium_amount), 2)                                       AS vehicle_total_premium,
            MAX(CASE WHEN coverage_code='BI'   THEN premium_amount END)         AS bi_premium,
            MAX(CASE WHEN coverage_code='BI'   THEN limit_per_occurrence END)   AS bi_limit_per_occurrence,
            MAX(CASE WHEN coverage_code='PD'   THEN premium_amount END)         AS pd_premium,
            MAX(CASE WHEN coverage_code='COMP' THEN premium_amount END)         AS comp_premium,
            MAX(CASE WHEN coverage_code='COMP' THEN deductible_amount END)      AS comp_deductible,
            MAX(CASE WHEN coverage_code='COLL' THEN premium_amount END)         AS coll_premium,
            MAX(CASE WHEN coverage_code='COLL' THEN deductible_amount END)      AS coll_deductible,
            COUNT(DISTINCT coverage_code)                                       AS coverage_count,
            MAX(CASE WHEN coverage_code IN ('COMP','COLL') THEN 1 ELSE 0 END)  AS has_physical_damage
        FROM sl_vehicle_coverage
        GROUP BY transaction_id, vehicle_id
    ),
    driver_counts AS (
        SELECT
            transaction_id,
            vehicle_id,
            COUNT(DISTINCT registrant_name)                                     AS driver_count,
            MAX(CASE WHEN registrant_type='OWNER' THEN registrant_name END)     AS primary_operator
        FROM sl_vehicle_registrant
        GROUP BY transaction_id, vehicle_id
    )
    SELECT
        v.transaction_id,
        v.vehicle_id,
        v.policy_number,
        v.named_insured,
        v.policy_effective_dt,
        v.vehicle_year,
        v.make,
        v.model,
        v.vin,
        v.vehicle_type,
        v.vehicle_age_at_effective,
        v.gross_vehicle_weight_rating,
        v.stated_value,
        v.garaging_state,
        v.garaging_zip,
        COALESCE(d.driver_count, 0)                                             AS driver_count,
        d.primary_operator,
        c.coverage_count,
        c.has_physical_damage,
        c.vehicle_total_premium,
        c.bi_premium,
        c.bi_limit_per_occurrence,
        c.pd_premium,
        c.comp_premium,
        c.comp_deductible,
        c.coll_premium,
        c.coll_deductible
    FROM sl_vehicle v
    LEFT JOIN coverage_pivot c
        ON  v.transaction_id = c.transaction_id
        AND v.vehicle_id     = c.vehicle_id
    LEFT JOIN driver_counts d
        ON  v.transaction_id = d.transaction_id
        AND v.vehicle_id     = d.vehicle_id;
    """)
    conn.commit()
    print("✓ Gold tables materialised (gl_policy_premium_summary, gl_fleet_risk_profile)")


# ── Stage 5: Report + CSV export ─────────────────────────────────────────────

def export_and_report(conn):
    def export_csv(table, label):
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        cols = [d[0] for d in conn.execute(f"SELECT * FROM {table} LIMIT 0").description]
        path = CSV_DIR / f"{table}.csv"
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(rows)
        print(f"  → Exported {len(rows):>3} rows to {path.name}")
        return rows, cols

    print("\n" + "═" * 70)
    print("  GOLD LAYER SUMMARY")
    print("═" * 70)

    # Policy Premium Summary
    print("\n── gl_policy_premium_summary ─────────────────────────────────────")
    rows, cols = export_csv("gl_policy_premium_summary", "Policy Premium Summary")
    print(f"\n  {'TXN_ID':<20} {'POLICY':<18} {'TYPE':<15} {'INSURED':<30} {'ST':<4} {'VEHICLES':>8} {'WRITTEN_PREM':>14}")
    print(f"  {'-'*20} {'-'*18} {'-'*15} {'-'*30} {'-'*4} {'-'*8} {'-'*14}")
    for r in rows:
        d = dict(zip(cols, r))
        print(f"  {d['transaction_id']:<20} {d['policy_number']:<18} "
              f"{d['transaction_type']:<15} {str(d['named_insured'])[:28]:<30} "
              f"{d['policy_state']:<4} {str(d['total_vehicles']):>8} "
              f"${str(d['total_written_premium'] or 0):>13}")

    # Fleet Risk Profile summary
    print("\n── gl_fleet_risk_profile (first 15 rows) ─────────────────────────")
    rows2, cols2 = export_csv("gl_fleet_risk_profile", "Fleet Risk Profile")
    print(f"\n  {'TXN_ID':<20} {'VEH_ID':<8} {'YEAR':>4} {'MAKE':<14} {'TYPE':<8} "
          f"{'STATE':<6} {'VEH_PREM':>10}")
    print(f"  {'-'*20} {'-'*8} {'-'*4} {'-'*14} {'-'*8} {'-'*6} {'-'*10}")
    for r in rows2[:15]:
        d = dict(zip(cols2, r))
        print(f"  {d['transaction_id']:<20} {d['vehicle_id']:<8} "
              f"{str(d['vehicle_year']):>4} {str(d['make'])[:12]:<14} "
              f"{str(d['vehicle_type'])[:7]:<8} {str(d['garaging_state']):<6} "
              f"${str(d['vehicle_total_premium'] or 0):>9}")

    # Grand totals
    totals = conn.execute("""
        SELECT
            COUNT(DISTINCT policy_number)       AS distinct_policies,
            COUNT(*)                            AS total_transactions,
            SUM(total_written_premium)          AS grand_written_premium,
            SUM(tractor_count)                  AS total_tractors,
            SUM(trailer_count)                  AS total_trailers
        FROM gl_policy_premium_summary
    """).fetchone()

    print(f"""
══ PIPELINE TOTALS ══════════════════════════════════════════════════
  Distinct policies       : {totals[0]}
  Total transactions      : {totals[1]}
  Grand written premium   : ${totals[2]:,.2f}
  Total tractors across   : {totals[3]}
  Total trailers across   : {totals[4]}
═════════════════════════════════════════════════════════════════════
""")

    # Bronze row counts summary
    print("── Bronze table row counts ───────────────────────────────────────")
    for tbl in [
        "br_policy_transaction", "br_policy_transaction_policy",
        "br_policy_auto", "br_policy_auto_vehicle",
        "br_policy_vehicle_registrants", "br_object_coverage_information",
    ]:
        n = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl:<45}: {n:>4} rows")

    print("\nCSV exports saved to:", CSV_DIR)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "═" * 70)
    print("  Insurance XML Platform — Bronze → Silver → Gold Pipeline")
    print(f"  Run timestamp: {LOAD_TS}")
    print("═" * 70 + "\n")

    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    print("── Stage 1: XML Shredder → Bronze ───────────────────────────────")
    create_schema(conn)
    shred_xml_to_bronze(conn)

    print("\n── Stage 2/3: Staging + Silver views ────────────────────────────")
    create_silver_views(conn)

    print("\n── Stage 4: Gold materialisation ────────────────────────────────")
    create_gold_tables(conn)

    print("\n── Stage 5: Export + Report ─────────────────────────────────────")
    export_and_report(conn)

    conn.close()
    print(f"\n✓ Pipeline complete. Local warehouse: {DB_PATH}")


if __name__ == "__main__":
    main()
