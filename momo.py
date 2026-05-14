"""
MTN MoMo Collections API client.
Docs: https://momodeveloper.mtn.com/docs/services/collection
"""
import uuid
import requests
from config import MOMO_BASE_URL, MOMO_SUBSCRIPTION_KEY, MOMO_API_USER, MOMO_API_KEY, MOMO_ENV


def _auth_header():
    import base64
    creds = f"{MOMO_API_USER}:{MOMO_API_KEY}"
    token = base64.b64encode(creds.encode()).decode()
    return f"Basic {token}"


def get_access_token():
    url = f"{MOMO_BASE_URL}/collection/token/"
    headers = {
        "Authorization": _auth_header(),
        "Ocp-Apim-Subscription-Key": MOMO_SUBSCRIPTION_KEY,
    }
    resp = requests.post(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()["access_token"]


def request_to_pay(phone: str, amount: str, currency: str, item_name: str, reference_id: str = None) -> str:
    """
    Initiate a MoMo payment request. Returns the reference_id (UUID).
    The fan approves the prompt on their phone.
    """
    if not reference_id:
        reference_id = str(uuid.uuid4())

    token = get_access_token()
    url = f"{MOMO_BASE_URL}/collection/v1_0/requesttopay"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Reference-Id": reference_id,
        "X-Target-Environment": MOMO_ENV,
        "Ocp-Apim-Subscription-Key": MOMO_SUBSCRIPTION_KEY,
        "Content-Type": "application/json",
    }
    body = {
        "amount": str(amount),
        "currency": currency,
        "externalId": reference_id,
        "payer": {
            "partyIdType": "MSISDN",
            "partyId": phone,
        },
        "payerMessage": f"ZYNARA – {item_name}",
        "payeeNote": f"Payment for {item_name}",
    }
    resp = requests.post(url, json=body, headers=headers, timeout=15)
    if resp.status_code not in (200, 202):
        raise RuntimeError(f"MoMo request failed: {resp.status_code} {resp.text}")
    return reference_id


def get_payment_status(reference_id: str) -> dict:
    """
    Poll the status of a payment. Returns dict with 'status' and optional 'reason'.
    Possible statuses: PENDING, SUCCESSFUL, FAILED
    """
    token = get_access_token()
    url = f"{MOMO_BASE_URL}/collection/v1_0/requesttopay/{reference_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Target-Environment": MOMO_ENV,
        "Ocp-Apim-Subscription-Key": MOMO_SUBSCRIPTION_KEY,
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()
