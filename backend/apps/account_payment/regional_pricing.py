# -*- coding: utf-8 -*-
"""Region-aware pricing: map a card's country to a pricing region and pick the
matching Stripe price.

Data Basis sells the same products (BD Pro, Chatbot) at different prices by
region: Brazilian cards in BRL, Spanish-speaking Latin America and the wider
world in USD at region-specific tiers. Each Stripe price carries a ``region``
metadata tag (``br``, ``latam`` or ``intl``); its product carries a ``code`` tag
(``bd_pro``, ``chatbot``) and its recurring block carries the interval
(``month``, ``year``).

The checkout page decides which price to *show*; this module is the server-side
guardrail that decides which price to *charge*, from the country of the card the
customer actually used. It exists so that switching to a cheaper regional
storefront (e.g. a US customer checking out on the Brazilian domain) does not
change what they pay.

The functions here are pure: they take Price-like objects and strings and never
touch the database or the Stripe API. The webhook glue that reads the card
country and loads prices lives in ``webhooks.py``.
"""

from __future__ import annotations

DEFAULT_REGION = "intl"

# Spanish-speaking Latin America, as ISO 3166-1 alpha-2 codes. Brazil is its own
# region (``br``); every country not listed here bills at the international
# (``intl``) tier.
_LATAM_COUNTRIES = frozenset(
    {
        "AR",  # Argentina
        "BO",  # Bolivia
        "CL",  # Chile
        "CO",  # Colombia
        "CR",  # Costa Rica
        "CU",  # Cuba
        "DO",  # Dominican Republic
        "EC",  # Ecuador
        "GT",  # Guatemala
        "HN",  # Honduras
        "MX",  # Mexico
        "NI",  # Nicaragua
        "PA",  # Panama
        "PE",  # Peru
        "PY",  # Paraguay
        "SV",  # El Salvador
        "UY",  # Uruguay
        "VE",  # Venezuela
    }
)


def country_to_region(country: str | None) -> str:
    """Map an ISO 3166-1 alpha-2 country code to a pricing region.

    Args:
        country: Two-letter country code from the payment card
            (case-insensitive), or ``None``/empty when unknown.

    Returns:
        ``"br"`` for Brazil, ``"latam"`` for Spanish-speaking Latin America, and
        ``"intl"`` for everywhere else or when the country is unknown.
    """
    if not country:
        return DEFAULT_REGION
    code = country.strip().upper()
    if code == "BR":
        return "br"
    if code in _LATAM_COUNTRIES:
        return "latam"
    return DEFAULT_REGION


def _price_region(price) -> str:
    return (getattr(price, "metadata", None) or {}).get("region", "")


def _price_code(price) -> str:
    product = getattr(price, "product", None)
    if product is None:
        return ""
    return (getattr(product, "metadata", None) or {}).get("code", "")


def _price_interval(price) -> str:
    return (getattr(price, "recurring", None) or {}).get("interval", "")


def resolve_regional_price_id(prices, original_price_id: str, region: str) -> str:
    """Pick the Stripe price id to charge, given the customer's region.

    Given the price the customer checked out with and their card's region, return
    the id of the equivalent price (same product ``code`` and billing interval)
    tagged for that region. Falls back to ``original_price_id`` whenever a
    confident swap cannot be made: the original price is not in ``prices``, it
    already matches the region, it lacks a code or interval, or no active sibling
    price for the region exists.

    The function never raises and never returns an id that is not present in
    ``prices``. This conservatism is deliberate — a wrong or missing regional
    price must never block a subscription from being created.

    Args:
        prices: Iterable of dj-stripe ``Price``-like objects. Each needs ``.id``,
            ``.metadata`` (with ``region``), ``.recurring`` (with ``interval``),
            ``.product.metadata`` (with ``code``), and ``.active``.
        original_price_id: The Stripe price id encoded in the checkout.
        region: Target region from the card country (``br``/``latam``/``intl``).

    Returns:
        The Stripe price id to charge — either a region-matched sibling or, when
        no confident match exists, ``original_price_id`` unchanged.
    """
    prices = list(prices)

    original = next((p for p in prices if p.id == original_price_id), None)
    if original is None:
        return original_price_id
    if _price_region(original) == region:
        return original_price_id

    code = _price_code(original)
    interval = _price_interval(original)
    if not code or not interval:
        return original_price_id

    for candidate in prices:
        if (
            candidate.id != original_price_id
            and getattr(candidate, "active", True)
            and _price_code(candidate) == code
            and _price_interval(candidate) == interval
            and _price_region(candidate) == region
        ):
            return candidate.id

    return original_price_id
