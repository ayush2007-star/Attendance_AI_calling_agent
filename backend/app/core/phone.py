import re

_E164_PHONE_REGEX = re.compile(r"^\+[1-9]\d{7,14}$")


def is_valid_phone_number(phone: str | None) -> bool:
    """
    Validate that a phone number is an E.164 compliant international number
    (starts with '+', country code, followed by 7 to 14 subscriber digits;
    total 8 to 15 digits).
    """
    if not phone or not isinstance(phone, str):
        return False
    return bool(_E164_PHONE_REGEX.fullmatch(phone.strip()))


def normalize_phone_number(phone: str | None) -> str | None:
    """
    Normalize and return stripped phone number if valid E.164, else None.
    """
    if not phone or not isinstance(phone, str):
        return None
    cleaned = phone.strip()
    if _E164_PHONE_REGEX.fullmatch(cleaned):
        return cleaned
    return None
