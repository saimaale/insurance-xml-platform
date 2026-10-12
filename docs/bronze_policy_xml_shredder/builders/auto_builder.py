from helpers import safe_str, safe_int


def build_auto_policy(root, txn_id: str, source_file: str, load_ts):
    rows = []
    for doc in root.findall("ObjectDocument"):
        doc_id = safe_str(doc.get("documentId"))
        for pol in doc.findall("Policy"):
            policy_number = safe_str(pol.get("policyNumber"))
            for auto in pol.findall("AutoPolicy"):
                rows.append({
                    "transaction_id":       txn_id,
                    "document_id":          doc_id,
                    "policy_number":        policy_number,
                    "program_code":         safe_str(auto.get("programCode")),
                    "fleet_indicator":      safe_str(auto.get("fleetIndicator")),
                    "number_of_units":      safe_int(auto.get("numberOfUnits")),
                    "radius_of_operation":  safe_int(auto.get("radiusOfOperation")),
                    "primary_use":          safe_str(auto.get("primaryUse")),
                    "source_file_name":     source_file,
                    "source_load_ts":       load_ts,
                })
    return rows
