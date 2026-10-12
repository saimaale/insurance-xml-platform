from helpers import safe_str, safe_float


def build_policy(root, txn_id: str, source_file: str, load_ts):
    rows = []
    for doc in root.findall("ObjectDocument"):
        doc_id = safe_str(doc.get("documentId"))
        for pol in doc.findall("Policy"):
            insured = pol.find("Insured")
            rows.append({
                "transaction_id":           txn_id,
                "document_id":              doc_id,
                "policy_number":            safe_str(pol.get("policyNumber")),
                "policy_type":              safe_str(pol.get("policyType")),
                "line_of_business":         safe_str(pol.get("lineOfBusiness")),
                "policy_effective_date":    safe_str(pol.get("policyEffectiveDate")),
                "policy_expiration_date":   safe_str(pol.get("policyExpirationDate")),
                "policy_state":             safe_str(pol.get("policyState")),
                "billing_plan":             safe_str(pol.get("billingPlan")),
                "premium_amount":           safe_float(pol.get("premiumAmount")),
                "currency":                 safe_str(pol.get("currency")),
                "insured_name":             safe_str(insured.findtext("InsuredName")) if insured is not None else None,
                "insured_type":             safe_str(insured.findtext("InsuredType")) if insured is not None else None,
                "source_file_name":         source_file,
                "source_load_ts":           load_ts,
            })
    return rows
