from helpers import safe_str, safe_float


def build_coverages(root, txn_id: str, source_file: str, load_ts):
    rows = []
    for doc in root.findall("ObjectDocument"):
        doc_id = safe_str(doc.get("documentId"))
        for pol in doc.findall("Policy"):
            policy_number = safe_str(pol.get("policyNumber"))
            for auto in pol.findall("AutoPolicy"):
                for veh in auto.findall("Vehicle"):
                    vehicle_id = safe_str(veh.get("vehicleId"))
                    for cov in veh.findall("ObjectCoverageInformation"):
                        rows.append({
                            "transaction_id":       txn_id,
                            "document_id":          doc_id,
                            "policy_number":        policy_number,
                            "vehicle_id":           vehicle_id,
                            "coverage_code":        safe_str(cov.get("coverageCode")),
                            "coverage_description": safe_str(cov.get("coverageDescription")),
                            "limit_per_person":     safe_float(cov.get("limitPerPerson")),
                            "limit_per_occurrence": safe_float(cov.get("limitPerOccurrence")),
                            "deductible":           safe_float(cov.get("deductible")),
                            "premium":              safe_float(cov.get("premium")),
                            "effective_date":       safe_str(cov.get("effectiveDate")),
                            "expiration_date":      safe_str(cov.get("expirationDate")),
                            "source_file_name":     source_file,
                            "source_load_ts":       load_ts,
                        })
    return rows
