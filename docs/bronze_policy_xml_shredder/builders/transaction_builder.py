from helpers import safe_str


def build_policy_transaction(root, source_file: str, load_ts):
    return {
        "transaction_id":             safe_str(root.get("transactionId")),
        "transaction_type":           safe_str(root.get("transactionType")),
        "transaction_effective_date": safe_str(root.get("transactionEffectiveDate")),
        "transaction_create_ts":      safe_str(root.get("transactionCreateTs")),
        "source_system":              safe_str(root.get("sourceSystem")),
        "source_file_name":           source_file,
        "source_load_ts":             load_ts,
    }
