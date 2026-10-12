from helpers import safe_str, safe_int


def build_registrants(root, txn_id: str, source_file: str, load_ts):
    rows = []
    for doc in root.findall("ObjectDocument"):
        doc_id = safe_str(doc.get("documentId"))
        for pol in doc.findall("Policy"):
            policy_number = safe_str(pol.get("policyNumber"))
            for auto in pol.findall("AutoPolicy"):
                for veh in auto.findall("Vehicle"):
                    vehicle_id = safe_str(veh.get("vehicleId"))
                    for reg in veh.findall("Registrant"):
                        rows.append({
                            "transaction_id":      txn_id,
                            "document_id":         doc_id,
                            "policy_number":       policy_number,
                            "vehicle_id":          vehicle_id,
                            "registrant_sequence": safe_int(reg.get("registrantSequence")),
                            "registrant_type":     safe_str(reg.get("registrantType")),
                            "registrant_name":     safe_str(reg.get("registrantName")),
                            "registrant_state":    safe_str(reg.get("registrantState")),
                            "license_number":      safe_str(reg.get("licenseNumber")),
                            "source_file_name":    source_file,
                            "source_load_ts":      load_ts,
                        })
    return rows
