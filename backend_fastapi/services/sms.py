import os
import boto3
import time
from botocore.exceptions import ClientError

AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
TOPIC_ARN = os.getenv("SNS_TOPIC_ARN", "arn:aws:sns:ap-south-1:318724430879:FARMGUARD")

sns = boto3.client("sns", region_name=AWS_REGION)

_last_alert = {}

def can_send_alert(key: str, cooldown: int = 900) -> bool:
    now = time.time()
    if key not in _last_alert or now - _last_alert[key] > cooldown:
        _last_alert[key] = now
        return True
    return False


# -----------------------------
# NEW: phone normalize (10-digit -> E.164)
# -----------------------------
def normalize_phone(phone_10: str, country: str = "NP") -> str:
    phone = (phone_10 or "").strip().replace(" ", "").replace("-", "")

    if not phone.isdigit():
        raise ValueError("Phone must contain digits only")

    if len(phone) != 10 or not phone.startswith("9"):
        raise ValueError("Phone must be 10 digits and start with 9")

    if country.upper() == "NP":
        return "+977" + phone
    if country.upper() == "IN":
        return "+91" + phone

    raise ValueError("Unsupported country (use 'NP' or 'IN')")


# -----------------------------
# NEW: subscribe farmer once (auto, no console)
# -----------------------------
def subscribe_farmer(phone_10: str, country: str = "NP") -> str:
    """
    Call this ONCE when a farmer registers (or admin adds farmer).
    Returns SubscriptionArn.
    """
    phone_e164 = normalize_phone(phone_10, country)

    try:
        resp = sns.subscribe(
            TopicArn=TOPIC_ARN,
            Protocol="sms",
            Endpoint=phone_e164,
            ReturnSubscriptionArn=True,
        )
        return resp.get("SubscriptionArn", "OK")
    except ClientError as e:
        raise RuntimeError(f"SNS subscribe failed: {e}")


# (optional but recommended) prevent duplicates
def is_subscribed(phone_10: str, country: str = "NP") -> bool:
    phone_e164 = normalize_phone(phone_10, country)
    resp = sns.list_subscriptions_by_topic(TopicArn=TOPIC_ARN)
    return any(s.get("Endpoint") == phone_e164 for s in resp.get("Subscriptions", []))


# -----------------------------
# Your existing function (unchanged)
# -----------------------------
def send_sms_alert(message: str) -> str:
    resp = sns.publish(
        TopicArn=TOPIC_ARN,
        Message=message,
        MessageAttributes={
            "AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"}
        },
    )
    return resp.get("MessageId", "OK")
