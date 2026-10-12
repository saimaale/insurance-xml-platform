from helpers import safe_str, safe_int


def build_object_documents(root, txn_id: str, source_file: str, load_ts):
    rows = []
    for doc in root.findall("ObjectDocument"):
        rows.append({
            "transaction_id":            txn_id,
            "document_id":               safe_str(doc.get("documentId")),
            "document_type":             safe_str(doc.get("documentType")),
            "document_version":          safe_str(doc.get("documentVersion")),
            "document_effective_date":   safe_str(doc.get("documentEffectiveDate")),
            "document_expiration_date":  safe_str(doc.get("documentExpirationDate")),
            "source_file_name":          source_file,
            "source_load_ts":            load_ts,
        })
    return rows


def build_document_covered(root, txn_id: str, source_file: str, load_ts):
    rows = []
    for doc in root.findall("ObjectDocument"):
        doc_id = safe_str(doc.get("documentId"))
        for cov in doc.findall("DocumentCovered"):
            rows.append({
                "transaction_id":   txn_id,
                "document_id":      doc_id,
                "covered_sequence": safe_int(cov.get("coveredSequence")),
                "covered_type":     safe_str(cov.get("coveredType")),
                "covered_name":     safe_str(cov.get("coveredName")),
                "covered_state":    safe_str(cov.get("coveredState")),
                "interest_type":    safe_str(cov.get("interestType")),
                "source_file_name": source_file,
                "source_load_ts":   load_ts,
            })
    return rows
