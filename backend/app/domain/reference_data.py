"""Static seed data for public reference/reference-adjacent endpoints.

These lists back the read-only `/v1/reference/*`, `/v1/context`, and
`/v1/plans` endpoints. There is no admin CRUD for this content yet — it is a
deliberately small, real seed list (not exhaustive) and can be moved to a
DynamoDB-backed admin-managed table later without changing the API shape.
"""
from __future__ import annotations

COUNTRIES = [
    {"code": "IN", "name": "India"},
    {"code": "CA", "name": "Canada"},
    {"code": "US", "name": "United States"},
    {"code": "GB", "name": "United Kingdom"},
    {"code": "AU", "name": "Australia"},
]

# Keyed by country code; a handful of representative regions per country.
REGIONS_BY_COUNTRY: dict[str, list[dict[str, str]]] = {
    "IN": [
        {"code": "PB", "name": "Punjab"},
        {"code": "HR", "name": "Haryana"},
        {"code": "DL", "name": "Delhi"},
        {"code": "CH", "name": "Chandigarh"},
    ],
    "CA": [
        {"code": "ON", "name": "Ontario"},
        {"code": "BC", "name": "British Columbia"},
        {"code": "AB", "name": "Alberta"},
    ],
    "US": [
        {"code": "CA", "name": "California"},
        {"code": "NY", "name": "New York"},
        {"code": "TX", "name": "Texas"},
    ],
    "GB": [
        {"code": "ENG", "name": "England"},
        {"code": "SCT", "name": "Scotland"},
    ],
    "AU": [
        {"code": "NSW", "name": "New South Wales"},
        {"code": "VIC", "name": "Victoria"},
    ],
}

LANGUAGES = [
    {"code": "pa", "name": "Punjabi"},
    {"code": "en", "name": "English"},
    {"code": "hi", "name": "Hindi"},
    {"code": "ur", "name": "Urdu"},
]

COMMUNITIES = [
    {"id": "jatt-sikh", "label": "Jatt Sikh"},
    {"id": "khatri-sikh", "label": "Khatri Sikh"},
    {"id": "ramgarhia-sikh", "label": "Ramgarhia Sikh"},
    {"id": "arora", "label": "Arora"},
    {"id": "other", "label": "Other / prefer not to say"},
]

RELIGIOUS_PRACTICES = [
    {"id": "amritdhari", "label": "Amritdhari"},
    {"id": "keshdhari", "label": "Keshdhari"},
    {"id": "sehajdhari", "label": "Sehajdhari"},
    {"id": "non-practicing", "label": "Non-practicing"},
    {"id": "prefer-not-to-say", "label": "Prefer not to say"},
]

EDUCATION_LEVELS = [
    {"id": "high-school", "label": "High school"},
    {"id": "bachelors", "label": "Bachelor's degree"},
    {"id": "masters", "label": "Master's degree"},
    {"id": "doctorate", "label": "Doctorate"},
    {"id": "trade-certification", "label": "Trade certification"},
]

OCCUPATION_CATEGORIES = [
    {"id": "engineering-it", "label": "Engineering / IT"},
    {"id": "medicine-healthcare", "label": "Medicine / Healthcare"},
    {"id": "business-finance", "label": "Business / Finance"},
    {"id": "education", "label": "Education"},
    {"id": "trades-services", "label": "Trades / Services"},
    {"id": "other", "label": "Other"},
]

INTERESTS = [
    {"id": "cooking", "label": "Cooking"},
    {"id": "travel", "label": "Travel"},
    {"id": "sports", "label": "Sports"},
    {"id": "music", "label": "Music"},
    {"id": "reading", "label": "Reading"},
    {"id": "volunteering", "label": "Volunteering"},
]

# Catalog §11: available verification checks. `countries` empty means
# "available everywhere"; a handful of representative check types, not an
# exhaustive/authoritative provider catalog.
VERIFICATION_CHECKS = [
    {"id": "government_id", "label": "Government-issued ID", "countries": []},
    {"id": "selfie_liveness", "label": "Selfie liveness match", "countries": []},
    {"id": "phone", "label": "Phone number verification", "countries": []},
    {"id": "education_document", "label": "Education document review", "countries": []},
]

PLANS = [
    {
        "id": "free",
        "name": "Free",
        "price_cents": 0,
        "currency": "USD",
        "interval": "month",
    },
    {
        "id": "premium-monthly",
        "name": "Premium (monthly)",
        "price_cents": 1999,
        "currency": "USD",
        "interval": "month",
    },
    {
        "id": "premium-annual",
        "name": "Premium (annual)",
        "price_cents": 14999,
        "currency": "USD",
        "interval": "year",
    },
]
