from helpers import safe_str, safe_int, safe_float


def build_vehicles(root, txn_id: str, source_file: str, load_ts):
    rows = []
    for doc in root.findall("ObjectDocument"):
        doc_id = safe_str(doc.get("documentId"))
        for pol in doc.findall("Policy"):
            policy_number = safe_str(pol.get("policyNumber"))
            for auto in pol.findall("AutoPolicy"):
                for veh in auto.findall("Vehicle"):
                    rows.append({
                        "transaction_id":              txn_id,
                        "document_id":                 doc_id,
                        "policy_number":               policy_number,
                        "vehicle_id":                  safe_str(veh.get("vehicleId")),
                        "sequence_number":             safe_int(veh.get("sequenceNumber")),
                        "vin":                         safe_str(veh.get("vin")),
                        "year":                        safe_int(veh.get("year")),
                        "make":                        safe_str(veh.get("make")),
                        "model":                       safe_str(veh.get("model")),
                        "body_type":                   safe_str(veh.get("bodyType")),
                        "gross_vehicle_weight_rating": safe_int(veh.get("grossVehicleWeightRating")),
                        "garage_state":                safe_str(veh.get("garageState")),
                        "garage_zip":                  safe_str(veh.get("garageZip")),
                        "stated_value":                safe_float(veh.get("statedValue")),
                        "source_file_name":            source_file,
                        "source_load_ts":              load_ts,
                    })
    return rows
