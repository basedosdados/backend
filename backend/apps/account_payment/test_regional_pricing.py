# -*- coding: utf-8 -*-
"""Tests for region-aware pricing.

The decision logic lives in pure functions (``country_to_region`` and
``resolve_regional_price_id``) and is tested directly with stub prices — no
database, no Stripe. The webhook glue (``_regional_price_id``, ``_card_country``)
is tested with mocks for the Stripe API and the price queryset.
"""

from types import SimpleNamespace
from unittest.mock import patch

from backend.apps.account_payment.regional_pricing import (
    country_to_region,
    resolve_regional_price_id,
)
from backend.apps.account_payment.webhooks import (
    _card_country,
    _regional_price_id,
)


def _price(price_id, region, code, interval, active=True):
    """Build a dj-stripe ``Price``-like stub."""
    return SimpleNamespace(
        id=price_id,
        active=active,
        metadata={"region": region},
        recurring={"interval": interval},
        product=SimpleNamespace(metadata={"code": code}),
    )


# A realistic catalogue: BD Pro and Chatbot, monthly and yearly, in three regions.
CATALOGUE = [
    _price("price_br_pro_m", "br", "bd_pro", "month"),
    _price("price_latam_pro_m", "latam", "bd_pro", "month"),
    _price("price_intl_pro_m", "intl", "bd_pro", "month"),
    _price("price_br_pro_y", "br", "bd_pro", "year"),
    _price("price_intl_pro_y", "intl", "bd_pro", "year"),
    _price("price_br_cb_m", "br", "chatbot", "month"),
    _price("price_intl_cb_m", "intl", "chatbot", "month"),
]


# ---------------------------------------------------------------------------
# country_to_region
# ---------------------------------------------------------------------------


class TestCountryToRegion:
    def test_brazil_is_br(self):
        assert country_to_region("BR") == "br"

    def test_is_case_insensitive(self):
        assert country_to_region("br") == "br"
        assert country_to_region("mx") == "latam"

    def test_whitespace_is_trimmed(self):
        assert country_to_region("  BR  ") == "br"

    def test_spanish_latam_is_latam(self):
        for code in ("AR", "MX", "CO", "CL", "PE", "UY", "VE", "DO"):
            assert country_to_region(code) == "latam", code

    def test_rest_of_world_is_intl(self):
        for code in ("US", "GB", "PT", "DE", "JP", "AU", "ZZ"):
            assert country_to_region(code) == "intl", code

    def test_unknown_country_is_intl(self):
        assert country_to_region(None) == "intl"
        assert country_to_region("") == "intl"


# ---------------------------------------------------------------------------
# resolve_regional_price_id
# ---------------------------------------------------------------------------


class TestResolveRegionalPriceId:
    def test_swaps_br_to_intl_same_product_and_interval(self):
        # A US card checking out the Brazilian monthly BD Pro price gets the
        # international monthly BD Pro price.
        assert resolve_regional_price_id(CATALOGUE, "price_br_pro_m", "intl") == "price_intl_pro_m"

    def test_swaps_br_to_latam(self):
        assert (
            resolve_regional_price_id(CATALOGUE, "price_br_pro_m", "latam") == "price_latam_pro_m"
        )

    def test_no_swap_when_region_already_matches(self):
        assert (
            resolve_regional_price_id(CATALOGUE, "price_intl_pro_m", "intl") == "price_intl_pro_m"
        )

    def test_keeps_original_when_no_sibling_for_region(self):
        # Chatbot has no latam price in the catalogue.
        assert resolve_regional_price_id(CATALOGUE, "price_br_cb_m", "latam") == "price_br_cb_m"

    def test_keeps_original_when_not_in_catalogue(self):
        assert resolve_regional_price_id(CATALOGUE, "price_unknown", "intl") == "price_unknown"

    def test_interval_must_match(self):
        # Yearly original must not be swapped for a monthly sibling.
        catalogue = [
            _price("price_br_pro_y", "br", "bd_pro", "year"),
            _price("price_intl_pro_m", "intl", "bd_pro", "month"),
        ]
        assert resolve_regional_price_id(catalogue, "price_br_pro_y", "intl") == "price_br_pro_y"

    def test_product_code_must_match(self):
        # A chatbot original must not be swapped for a bd_pro sibling.
        catalogue = [
            _price("price_br_cb_m", "br", "chatbot", "month"),
            _price("price_intl_pro_m", "intl", "bd_pro", "month"),
        ]
        assert resolve_regional_price_id(catalogue, "price_br_cb_m", "intl") == "price_br_cb_m"

    def test_inactive_sibling_is_ignored(self):
        catalogue = [
            _price("price_br_pro_m", "br", "bd_pro", "month"),
            _price("price_intl_pro_m", "intl", "bd_pro", "month", active=False),
        ]
        assert resolve_regional_price_id(catalogue, "price_br_pro_m", "intl") == "price_br_pro_m"

    def test_untagged_original_still_swaps_to_region(self):
        # A price with no region tag ("") differs from the target region, so a
        # tagged sibling is still substituted.
        catalogue = [
            _price("price_legacy_pro_m", "", "bd_pro", "month"),
            _price("price_intl_pro_m", "intl", "bd_pro", "month"),
        ]
        assert (
            resolve_regional_price_id(catalogue, "price_legacy_pro_m", "intl") == "price_intl_pro_m"
        )


# ---------------------------------------------------------------------------
# _card_country
# ---------------------------------------------------------------------------


class TestCardCountry:
    @patch("backend.apps.account_payment.webhooks.StripePaymentMethod")
    def test_reads_card_country(self, pm_cls):
        pm_cls.retrieve.return_value = {"card": {"country": "US"}}
        assert _card_country("pm_123") == "US"
        pm_cls.retrieve.assert_called_once_with("pm_123")

    @patch("backend.apps.account_payment.webhooks.StripePaymentMethod")
    def test_returns_none_without_card(self, pm_cls):
        pm_cls.retrieve.return_value = {"card": None}
        assert _card_country("pm_123") is None

    @patch("backend.apps.account_payment.webhooks.StripePaymentMethod")
    def test_returns_none_when_card_missing(self, pm_cls):
        pm_cls.retrieve.return_value = {}
        assert _card_country("pm_123") is None


# ---------------------------------------------------------------------------
# _regional_price_id (webhook glue)
# ---------------------------------------------------------------------------


class TestRegionalPriceIdGlue:
    def test_no_payment_method_keeps_original(self):
        assert _regional_price_id("price_br_pro_m", None, "[ctx] ") == "price_br_pro_m"

    @patch("backend.apps.account_payment.webhooks._card_country")
    def test_stripe_error_keeps_original(self, card_country):
        card_country.side_effect = RuntimeError("stripe down")
        assert _regional_price_id("price_br_pro_m", "pm_123", "[ctx] ") == "price_br_pro_m"

    @patch("backend.apps.account_payment.webhooks.DJStripePrice")
    @patch("backend.apps.account_payment.webhooks._card_country")
    def test_us_card_swaps_to_intl(self, card_country, price_model):
        card_country.return_value = "US"
        price_model.objects.all.return_value = CATALOGUE
        assert _regional_price_id("price_br_pro_m", "pm_123", "[ctx] ") == "price_intl_pro_m"

    @patch("backend.apps.account_payment.webhooks.DJStripePrice")
    @patch("backend.apps.account_payment.webhooks._card_country")
    def test_br_card_keeps_brl_price(self, card_country, price_model):
        card_country.return_value = "BR"
        price_model.objects.all.return_value = CATALOGUE
        assert _regional_price_id("price_br_pro_m", "pm_123", "[ctx] ") == "price_br_pro_m"

    @patch("backend.apps.account_payment.webhooks.DJStripePrice")
    @patch("backend.apps.account_payment.webhooks._card_country")
    def test_unknown_card_country_bills_intl(self, card_country, price_model):
        # Stripe returned no country -> intl tier, arbitrage-safe default.
        card_country.return_value = None
        price_model.objects.all.return_value = CATALOGUE
        assert _regional_price_id("price_br_pro_m", "pm_123", "[ctx] ") == "price_intl_pro_m"
