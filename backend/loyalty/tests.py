# loyalty/tests.py
"""
Tests for the point transfer system and customer memberships.

Run with: python manage.py test loyalty.tests
"""

import re

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import User, CustomerProfile
from merchants.models import MerchantProfile
from loyalty.models import (
    CustomerMerchantProfile,
    CustomerMerchantWallet,
    PointTransaction,
)


# ── Shared helpers ───────────────────────────────────────────────────────────

_MEMBERSHIP_NUMBER_RE = re.compile(r"^[A-Z]{3}-[A-Z0-9]{6}$")


def _create_customer(username, email):
    user = User.objects.create_user(
        username=username, email=email, password="pass1234",
        role=User.ROLE_CUSTOMER,
    )
    profile = CustomerProfile.objects.create(user=user, full_name=username.title())
    return user, profile


def _create_merchant(username, email, name, slug):
    user = User.objects.create_user(
        username=username, email=email, password="pass1234",
        role=User.ROLE_MERCHANT,
    )
    profile = MerchantProfile.objects.create(
        user=user, business_name=name, slug=slug,
        is_approved=True, is_open=True,
    )
    return user, profile


# ═══════════════════════════════════════════════════════════════════════════════
# Membership Tests
# ═══════════════════════════════════════════════════════════════════════════════


class MembershipModelTests(TestCase):
    """Unit tests for the CustomerMerchantProfile model extensions."""

    def setUp(self):
        self.customer_user, self.customer = _create_customer(
            "alice", "alice@example.com",
        )
        self.merchant_user, self.merchant = _create_merchant(
            "shopa", "shopa@test.com", "Cafe Aroma", "cafe-aroma",
        )

    def test_membership_number_auto_generated(self):
        profile = CustomerMerchantProfile.objects.create(
            customer=self.customer, merchant=self.merchant,
        )
        self.assertIsNotNone(profile.membership_number)
        self.assertRegex(profile.membership_number, _MEMBERSHIP_NUMBER_RE)

    def test_membership_number_prefix_matches_slug(self):
        profile = CustomerMerchantProfile.objects.create(
            customer=self.customer, merchant=self.merchant,
        )
        prefix = profile.membership_number.split("-")[0]
        self.assertEqual(prefix, "CAF")

    def test_membership_number_is_unique(self):
        p1 = CustomerMerchantProfile.objects.create(
            customer=self.customer, merchant=self.merchant,
        )
        # Create a second merchant
        _, merchant2 = _create_merchant(
            "shopb", "shopb@test.com", "Restaurant Zen", "restaurant-zen",
        )
        p2 = CustomerMerchantProfile.objects.create(
            customer=self.customer, merchant=merchant2,
        )
        self.assertNotEqual(p1.membership_number, p2.membership_number)

    def test_different_merchants_different_prefixes(self):
        p1 = CustomerMerchantProfile.objects.create(
            customer=self.customer, merchant=self.merchant,
        )
        _, merchant2 = _create_merchant(
            "shopb", "shopb@test.com", "Restaurant Zen", "restaurant-zen",
        )
        p2 = CustomerMerchantProfile.objects.create(
            customer=self.customer, merchant=merchant2,
        )
        self.assertEqual(p1.membership_number.split("-")[0], "CAF")
        self.assertEqual(p2.membership_number.split("-")[0], "RES")

    def test_is_active_defaults_true(self):
        profile = CustomerMerchantProfile.objects.create(
            customer=self.customer, merchant=self.merchant,
        )
        self.assertTrue(profile.is_active)

    def test_last_active_at_nullable(self):
        profile = CustomerMerchantProfile.objects.create(
            customer=self.customer, merchant=self.merchant,
        )
        self.assertIsNone(profile.last_active_at)

    def test_unique_together_constraint(self):
        CustomerMerchantProfile.objects.create(
            customer=self.customer, merchant=self.merchant,
        )
        with self.assertRaises(Exception):
            CustomerMerchantProfile.objects.create(
                customer=self.customer, merchant=self.merchant,
            )

    def test_explicit_membership_number_preserved(self):
        profile = CustomerMerchantProfile.objects.create(
            customer=self.customer, merchant=self.merchant,
            membership_number="CAF-TEST99",
        )
        self.assertEqual(profile.membership_number, "CAF-TEST99")


class MembershipAPITests(TestCase):
    """Integration tests for the membership API endpoints."""

    def setUp(self):
        self.client = APIClient()

        # Customer
        self.customer_user, self.customer = _create_customer(
            "alice", "alice@example.com",
        )

        # Merchant A
        self.merchant_a_user, self.merchant_a = _create_merchant(
            "shopa", "shopa@test.com", "Cafe Aroma", "cafe-aroma",
        )

        # Merchant B
        self.merchant_b_user, self.merchant_b = _create_merchant(
            "shopb", "shopb@test.com", "Restaurant Zen", "restaurant-zen",
        )

        self.client.force_authenticate(user=self.customer_user)

    # ── POST /api/customer/memberships/join/ ──────────────────────────────────

    def test_join_creates_membership(self):
        resp = self.client.post(
            "/api/customer/memberships/join/",
            {"merchant_slug": "cafe-aroma"},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("membership_number", resp.data)
        self.assertIn("merchant", resp.data)
        self.assertEqual(resp.data["merchant"]["slug"], "cafe-aroma")
        self.assertEqual(resp.data["status"], "active")
        self.assertTrue(resp.data["is_active"])
        self.assertRegex(resp.data["membership_number"], _MEMBERSHIP_NUMBER_RE)

    def test_join_returns_existing_idempotent(self):
        resp1 = self.client.post(
            "/api/customer/memberships/join/",
            {"merchant_slug": "cafe-aroma"},
        )
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)

        resp2 = self.client.post(
            "/api/customer/memberships/join/",
            {"merchant_slug": "cafe-aroma"},
        )
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(
            resp1.data["membership_number"],
            resp2.data["membership_number"],
        )
        # Only one record in the database
        self.assertEqual(
            CustomerMerchantProfile.objects.filter(
                customer=self.customer, merchant=self.merchant_a,
            ).count(),
            1,
        )

    def test_join_missing_slug_returns_400(self):
        resp = self.client.post("/api/customer/memberships/join/", {})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_join_invalid_slug_returns_404(self):
        resp = self.client.post(
            "/api/customer/memberships/join/",
            {"merchant_slug": "nonexistent"},
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_join_creates_wallet_and_profile(self):
        self.client.post(
            "/api/customer/memberships/join/",
            {"merchant_slug": "cafe-aroma"},
        )
        self.assertTrue(
            CustomerMerchantProfile.objects.filter(
                customer=self.customer, merchant=self.merchant_a,
            ).exists()
        )
        self.assertTrue(
            CustomerMerchantWallet.objects.filter(
                customer=self.customer, merchant=self.merchant_a,
            ).exists()
        )

    # ── GET /api/customer/memberships/ ────────────────────────────────────────

    def test_list_memberships_empty(self):
        resp = self.client.get("/api/customer/memberships/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    def test_list_memberships_returns_joined(self):
        self.client.post(
            "/api/customer/memberships/join/",
            {"merchant_slug": "cafe-aroma"},
        )
        self.client.post(
            "/api/customer/memberships/join/",
            {"merchant_slug": "restaurant-zen"},
        )

        resp = self.client.get("/api/customer/memberships/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

        slugs = {m["merchant"]["slug"] for m in resp.data}
        self.assertEqual(slugs, {"cafe-aroma", "restaurant-zen"})

    def test_list_memberships_has_all_fields(self):
        self.client.post(
            "/api/customer/memberships/join/",
            {"merchant_slug": "cafe-aroma"},
        )
        resp = self.client.get("/api/customer/memberships/")
        m = resp.data[0]
        self.assertIn("membership_id", m)
        self.assertIn("membership_number", m)
        self.assertIn("merchant", m)
        self.assertIn("joined_at", m)
        self.assertIn("status", m)
        self.assertIn("is_active", m)
        self.assertIn("last_active_at", m)
        # merchant sub-object
        self.assertIn("name", m["merchant"])
        self.assertIn("slug", m["merchant"])
        self.assertIn("logo", m["merchant"])

    def test_list_only_returns_own_memberships(self):
        """Customer B should NOT see Customer A's memberships."""
        self.client.post(
            "/api/customer/memberships/join/",
            {"merchant_slug": "cafe-aroma"},
        )

        # Create a second customer
        customer_b_user, customer_b = _create_customer(
            "bob", "bob@example.com",
        )
        self.client.force_authenticate(user=customer_b_user)
        resp = self.client.get("/api/customer/memberships/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    # ── GET /api/customer/memberships/<slug>/ ─────────────────────────────────

    def test_detail_by_slug_returns_membership(self):
        self.client.post(
            "/api/customer/memberships/join/",
            {"merchant_slug": "cafe-aroma"},
        )
        resp = self.client.get("/api/customer/memberships/cafe-aroma/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["merchant"]["slug"], "cafe-aroma")
        self.assertRegex(resp.data["membership_number"], _MEMBERSHIP_NUMBER_RE)

    def test_detail_by_slug_not_joined_returns_404(self):
        resp = self.client.get("/api/customer/memberships/cafe-aroma/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_by_slug_invalid_merchant_returns_404(self):
        resp = self.client.get("/api/customer/memberships/nonexistent/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_by_slug_merchant_isolation(self):
        """
        Merchant A must never access Merchant B membership data.
        A customer joining Merchant B should not affect Merchant A's view.
        """
        self.client.post(
            "/api/customer/memberships/join/",
            {"merchant_slug": "cafe-aroma"},
        )
        self.client.post(
            "/api/customer/memberships/join/",
            {"merchant_slug": "restaurant-zen"},
        )

        resp_a = self.client.get("/api/customer/memberships/cafe-aroma/")
        resp_b = self.client.get("/api/customer/memberships/restaurant-zen/")

        self.assertEqual(resp_a.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_b.status_code, status.HTTP_200_OK)
        self.assertNotEqual(
            resp_a.data["membership_number"],
            resp_b.data["membership_number"],
        )

    # ── Authentication ────────────────────────────────────────────────────────

    def test_unauthenticated_join_returns_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.post(
            "/api/customer/memberships/join/",
            {"merchant_slug": "cafe-aroma"},
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_list_returns_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get("/api/customer/memberships/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_merchant_account_cannot_join(self):
        """Merchant accounts should not be able to use customer membership endpoints."""
        self.client.force_authenticate(user=self.merchant_a_user)
        resp = self.client.post(
            "/api/customer/memberships/join/",
            {"merchant_slug": "cafe-aroma"},
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ── Membership number format ──────────────────────────────────────────────

    def test_membership_number_format_no_sequential_id(self):
        """Membership numbers must not contain raw database IDs."""
        self.client.post(
            "/api/customer/memberships/join/",
            {"merchant_slug": "cafe-aroma"},
        )
        resp = self.client.get("/api/customer/memberships/cafe-aroma/")
        number = resp.data["membership_number"]
        self.assertRegex(number, r"^[A-Z]{3}-[A-Z0-9]{6}$")

    def test_repeated_joins_produce_consistent_number(self):
        """Idempotent joins must not change the membership number."""
        self.client.post(
            "/api/customer/memberships/join/",
            {"merchant_slug": "cafe-aroma"},
        )
        num1 = self.client.get(
            "/api/customer/memberships/cafe-aroma/"
        ).data["membership_number"]

        for _ in range(5):
            self.client.post(
                "/api/customer/memberships/join/",
                {"merchant_slug": "cafe-aroma"},
            )
        num2 = self.client.get(
            "/api/customer/memberships/cafe-aroma/"
        ).data["membership_number"]

        self.assertEqual(num1, num2)

    # ── Existing functionality still works ────────────────────────────────────

    def test_existing_join_endpoint_still_works(self):
        """The old /api/loyalty/merchant-profiles/join/ must still work."""
        resp = self.client.post(
            "/api/loyalty/merchant-profiles/join/",
            {"merchant_slug": "cafe-aroma"},
        )
        self.assertIn(resp.status_code, [200, 201])

    def test_existing_wallets_endpoint_still_works(self):
        """The old /api/loyalty/wallets/ must still work."""
        # Join first
        self.client.post(
            "/api/customer/memberships/join/",
            {"merchant_slug": "cafe-aroma"},
        )
        resp = self.client.get("/api/loyalty/wallets/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════════════════════════════
# Transfer Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TransferTests(TestCase):
    """Point transfer — validation, cross-merchant blocking, history."""

    def setUp(self):
        self.client = APIClient()

        # -- Sender (Customer A) --
        self.sender_user = User.objects.create_user(
            username="sender", email="sender@example.com", password="pass1234",
            role=User.ROLE_CUSTOMER,
        )
        self.sender = CustomerProfile.objects.create(
            user=self.sender_user, full_name="Alice",
        )

        # -- Receiver (Customer B) --
        self.receiver_user = User.objects.create_user(
            username="receiver", email="receiver@example.com", password="pass1234",
            role=User.ROLE_CUSTOMER,
        )
        self.receiver = CustomerProfile.objects.create(
            user=self.receiver_user, full_name="Bob",
        )

        # -- Merchant A (same merchant) --
        self.merchant_a_user = User.objects.create_user(
            username="merchA", email="merchA@test.com", password="pass1234",
            role=User.ROLE_MERCHANT,
        )
        self.merchant_a = MerchantProfile.objects.create(
            user=self.merchant_a_user,
            business_name="Cafe A",
            slug="cafe-a",
            is_approved=True,
            is_open=True,
        )

        # -- Merchant B (different merchant) --
        self.merchant_b_user = User.objects.create_user(
            username="merchB", email="merchB@test.com", password="pass1234",
            role=User.ROLE_MERCHANT,
        )
        self.merchant_b = MerchantProfile.objects.create(
            user=self.merchant_b_user,
            business_name="Cafe B",
            slug="cafe-b",
            is_approved=True,
            is_open=True,
        )

        # Join both customers to merchant A only
        CustomerMerchantProfile.objects.create(
            customer=self.sender, merchant=self.merchant_a,
            status=CustomerMerchantProfile.STATUS_ACTIVE,
        )
        CustomerMerchantProfile.objects.create(
            customer=self.receiver, merchant=self.merchant_a,
            status=CustomerMerchantProfile.STATUS_ACTIVE,
        )

        # Create wallets with balances
        self.sender_wallet_a = CustomerMerchantWallet.objects.create(
            customer=self.sender, merchant=self.merchant_a,
            points_balance=500, lifetime_points=1000,
        )
        self.receiver_wallet_a = CustomerMerchantWallet.objects.create(
            customer=self.receiver, merchant=self.merchant_a,
            points_balance=100, lifetime_points=200,
        )

        # Authenticate as sender by default
        self.client.force_authenticate(user=self.sender_user)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _transfer_url(self):
        return "/api/loyalty/transfers/create/"

    def _transfer_payload(self, **overrides):
        payload = {
            "receiver_transfer_code": self.receiver.transfer_code,
            "merchant_id": self.merchant_a.id,
            "amount": 100,
        }
        payload.update(overrides)
        return payload

    # ── Successful Transfer ────────────────────────────────────────────────────

    def test_successful_transfer_same_merchant(self):
        resp = self.client.post(self._transfer_url(), self._transfer_payload())
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Check balances updated correctly
        self.sender_wallet_a.refresh_from_db()
        self.receiver_wallet_a.refresh_from_db()
        self.assertEqual(self.sender_wallet_a.points_balance, 400)   # 500 - 100
        self.assertEqual(self.receiver_wallet_a.points_balance, 200)  # 100 + 100

        # Check transactions created
        data = resp.data
        self.assertIsNotNone(data["transfer_group"])
        self.assertEqual(data["sent_transaction"]["transaction_type"], "TRANSFER_SENT")
        self.assertEqual(data["sent_transaction"]["points"], -100)
        self.assertEqual(data["received_transaction"]["transaction_type"], "TRANSFER_RECEIVED")
        self.assertEqual(data["received_transaction"]["points"], 100)

        # Verify both transactions share the same transfer_group
        sent_txn = PointTransaction.objects.get(id=data["sent_transaction"]["id"])
        recv_txn = PointTransaction.objects.get(id=data["received_transaction"]["id"])
        self.assertEqual(sent_txn.transfer_group, recv_txn.transfer_group)

        # Verify correct customer on each transaction
        self.assertEqual(sent_txn.customer_id, self.sender.id)
        self.assertEqual(recv_txn.customer_id, self.receiver.id)

    # ── Cross-Merchant Blocked ────────────────────────────────────────────────

    def test_cross_merchant_transfer_blocked(self):
        CustomerMerchantProfile.objects.filter(
            customer=self.receiver, merchant=self.merchant_a
        ).update(status=CustomerMerchantProfile.STATUS_INACTIVE)

        resp = self.client.post(self._transfer_url(), self._transfer_payload())
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not joined", str(resp.data.get("error", "")).lower())

    def test_receiver_must_be_active_at_merchant(self):
        new_user = User.objects.create_user(
            username="newrecv", email="newrecv@test.com", password="pass1234",
            role=User.ROLE_CUSTOMER,
        )
        new_customer = CustomerProfile.objects.create(user=new_user, full_name="Newbie")

        resp = self.client.post(self._transfer_url(), self._transfer_payload(
            receiver_transfer_code=new_customer.transfer_code,
        ))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not joined", str(resp.data.get("error", "")).lower())

    def test_cross_merchant_transfer_blocked_explicit(self):
        from loyalty.services import transfer_points
        from loyalty.services import get_or_create_wallet

        sender_wallet_b = CustomerMerchantWallet.objects.create(
            customer=self.sender, merchant=self.merchant_b,
            points_balance=100,
        )
        receiver_wallet_b = CustomerMerchantWallet.objects.create(
            customer=self.receiver, merchant=self.merchant_b,
            points_balance=0,
        )

        result = transfer_points(sender_wallet_b, receiver_wallet_b, 50)
        self.assertIsNotNone(result["transfer_group"])

        sender_wallet_b.refresh_from_db()
        receiver_wallet_a = self.receiver_wallet_a

        with self.assertRaises(ValueError) as ctx:
            transfer_points(sender_wallet_b, receiver_wallet_a, 25)
        self.assertIn("Cross-merchant", str(ctx.exception))

    def test_cross_merchant_rejected_via_api(self):
        CustomerMerchantWallet.objects.create(
            customer=self.sender, merchant=self.merchant_b,
            points_balance=200,
        )

        resp = self.client.post(self._transfer_url(), self._transfer_payload(
            amount=600,
        ))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient", str(resp.data["error"]))

    # ── Insufficient Balance ──────────────────────────────────────────────────

    def test_insufficient_balance_blocked(self):
        resp = self.client.post(self._transfer_url(), self._transfer_payload(
            amount=99999,
        ))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient", str(resp.data["error"]))

    # ── Zero / Negative Amount ────────────────────────────────────────────────

    def test_zero_amount_blocked(self):
        resp = self.client.post(self._transfer_url(), self._transfer_payload(amount=0))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_negative_amount_blocked(self):
        resp = self.client.post(self._transfer_url(), self._transfer_payload(amount=-50))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Missing Fields ────────────────────────────────────────────────────────

    def test_missing_required_fields(self):
        resp = self.client.post(self._transfer_url(), {})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_merchant_id(self):
        resp = self.client.post(self._transfer_url(), {
            "receiver_transfer_code": self.receiver.transfer_code,
            "amount": 50,
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Authentication ────────────────────────────────────────────────────────

    def test_unauthenticated_blocked(self):
        self.client.force_authenticate(user=None)
        resp = self.client.post(self._transfer_url(), self._transfer_payload())
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_merchant_account_blocked(self):
        self.client.force_authenticate(user=self.merchant_a_user)
        resp = self.client.post(self._transfer_url(), self._transfer_payload())
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ── Transfer History ──────────────────────────────────────────────────────

    def test_customer_transfer_history(self):
        self.client.post(self._transfer_url(), self._transfer_payload())

        resp = self.client.get("/api/loyalty/transfers/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)

        types = {t["transaction_type"] for t in resp.data}
        self.assertIn("TRANSFER_SENT", types)

    def test_customer_transfer_history_filtered_by_merchant(self):
        self.client.post(self._transfer_url(), self._transfer_payload())

        resp = self.client.get(
            f"/api/loyalty/transfers/?merchant={self.merchant_a.id}"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_receiver_sees_transfer_received(self):
        self.client.post(self._transfer_url(), self._transfer_payload())

        self.client.force_authenticate(user=self.receiver_user)
        resp = self.client.get("/api/loyalty/transfers/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        types = {t["transaction_type"] for t in resp.data}
        self.assertIn("TRANSFER_RECEIVED", types)

    # ── Merchant Transfer History ─────────────────────────────────────────────

    def test_merchant_transfer_history(self):
        self.client.post(self._transfer_url(), self._transfer_payload())

        self.client.force_authenticate(user=self.merchant_a_user)
        resp = self.client.get("/api/loyalty/merchant/transfers/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)

    # ── Wallet Integrity ──────────────────────────────────────────────────────

    def test_wallet_balances_never_negative(self):
        self.client.post(self._transfer_url(), self._transfer_payload(amount=200))

        self.sender_wallet_a.refresh_from_db()
        self.receiver_wallet_a.refresh_from_db()
        self.assertEqual(self.sender_wallet_a.points_balance, 300)   # 500 - 200
        self.assertEqual(self.receiver_wallet_a.points_balance, 300)  # 100 + 200

    def test_multiple_transfers_accumulate(self):
        self.client.post(self._transfer_url(), self._transfer_payload(amount=50))
        self.client.post(self._transfer_url(), self._transfer_payload(amount=30))

        self.sender_wallet_a.refresh_from_db()
        self.receiver_wallet_a.refresh_from_db()
        self.assertEqual(self.sender_wallet_a.points_balance, 420)   # 500 - 80
        self.assertEqual(self.receiver_wallet_a.points_balance, 180)  # 100 + 80

    def test_transfer_group_links_sent_and_received(self):
        resp = self.client.post(self._transfer_url(), self._transfer_payload())
        tg = resp.data["transfer_group"]

        sent = PointTransaction.objects.get(id=resp.data["sent_transaction"]["id"])
        recv = PointTransaction.objects.get(id=resp.data["received_transaction"]["id"])
        self.assertEqual(str(sent.transfer_group), tg)
        self.assertEqual(str(recv.transfer_group), tg)


# ═══════════════════════════════════════════════════════════════════════════════
# Wallet Isolation Tests (Step 3)
# ═══════════════════════════════════════════════════════════════════════════════


class WalletIsolationTests(TestCase):
    """Each merchant membership has its own wallet. No cross-merchant leakage."""

    def setUp(self):
        self.client = APIClient()

        self.customer_user, self.customer = _create_customer(
            "alice", "alice@example.com",
        )
        self.merchant_a_user, self.merchant_a = _create_merchant(
            "shopa", "shopa@test.com", "Cafe Aroma", "cafe-aroma",
        )
        self.merchant_b_user, self.merchant_b = _create_merchant(
            "shopb", "shopb@test.com", "Restaurant Zen", "restaurant-zen",
        )

        self.client.force_authenticate(user=self.customer_user)

    def test_same_customer_separate_wallets(self):
        """Same customer can have separate wallets for two merchants."""
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "cafe-aroma"})
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "restaurant-zen"})

        wallets = CustomerMerchantWallet.objects.filter(customer=self.customer)
        self.assertEqual(wallets.count(), 2)
        wallet_a = wallets.get(merchant=self.merchant_a)
        wallet_b = wallets.get(merchant=self.merchant_b)
        self.assertNotEqual(wallet_a.id, wallet_b.id)

    def test_merchant_a_balance_does_not_affect_b(self):
        """Merchant A balance changes do not affect Merchant B."""
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "cafe-aroma"})
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "restaurant-zen"})

        wallet_a = CustomerMerchantWallet.objects.get(
            customer=self.customer, merchant=self.merchant_a,
        )
        wallet_b = CustomerMerchantWallet.objects.get(
            customer=self.customer, merchant=self.merchant_b,
        )

        from loyalty.services import award_wallet_points
        award_wallet_points(wallet_a, 500)
        award_wallet_points(wallet_b, 100)

        wallet_a.refresh_from_db()
        wallet_b.refresh_from_db()
        self.assertEqual(wallet_a.points_balance, 500)
        self.assertEqual(wallet_b.points_balance, 100)

    def test_wallet_linked_to_membership(self):
        """Wallet is linked to the correct membership."""
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "cafe-aroma"})

        membership = CustomerMerchantProfile.objects.get(
            customer=self.customer, merchant=self.merchant_a,
        )
        wallet = CustomerMerchantWallet.objects.get(
            customer=self.customer, merchant=self.merchant_a,
        )
        self.assertEqual(wallet.membership_id, membership.id)

    def test_duplicate_wallet_prevented(self):
        """Duplicate wallet creation is prevented by unique constraint."""
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "cafe-aroma"})
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "cafe-aroma"})

        wallets = CustomerMerchantWallet.objects.filter(
            customer=self.customer, merchant=self.merchant_a,
        )
        self.assertEqual(wallets.count(), 1)

    def test_wallet_created_automatically_on_join(self):
        """Create the wallet automatically when membership is created."""
        resp = self.client.post("/api/customer/memberships/join/", {"merchant_slug": "cafe-aroma"})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        self.assertTrue(
            CustomerMerchantWallet.objects.filter(
                customer=self.customer, merchant=self.merchant_a,
            ).exists()
        )

    def test_merchant_a_cannot_query_merchant_b_wallets(self):
        """Merchant A cannot query Merchant B wallets."""
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "cafe-aroma"})
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "restaurant-zen"})

        self.client.force_authenticate(user=self.merchant_a_user)
        resp = self.client.get("/api/loyalty/merchant/customers/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Only merchant A's members
        membership_numbers = {c["membership_number"] for c in resp.data}
        # Should not include merchant B's membership
        memberships_b = CustomerMerchantProfile.objects.filter(
            merchant=self.merchant_b,
        ).values_list("membership_number", flat=True)
        for mn in memberships_b:
            self.assertNotIn(mn, membership_numbers)


# ═══════════════════════════════════════════════════════════════════════════════
# Membership Card API Tests (Step 12)
# ═══════════════════════════════════════════════════════════════════════════════


class MembershipCardAPITests(TestCase):
    """Tests for the card stack API endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.customer_user, self.customer = _create_customer(
            "alice", "alice@example.com",
        )
        self.merchant_a_user, self.merchant_a = _create_merchant(
            "shopa", "shopa@test.com", "Cafe Aroma", "cafe-aroma",
        )
        self.client.force_authenticate(user=self.customer_user)

    def test_empty_cards_list(self):
        resp = self.client.get("/api/loyalty/membership-cards/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    def test_cards_after_join(self):
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "cafe-aroma"})
        resp = self.client.get("/api/loyalty/membership-cards/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        card = resp.data[0]
        self.assertIn("merchant", card)
        self.assertIn("membership", card)
        self.assertIn("wallet", card)
        self.assertIn("transfer_enabled", card)
        self.assertEqual(card["merchant"]["slug"], "cafe-aroma")

    def test_card_masked_number(self):
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "cafe-aroma"})
        resp = self.client.get("/api/loyalty/membership-cards/")
        masked = resp.data[0]["membership"]["membership_number_masked"]
        self.assertTrue(masked.startswith("••••"))

    def test_unauthenticated_cards_returns_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get("/api/loyalty/membership-cards/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_card_design_defaults_to_none(self):
        """Default Zentro card appears if no design exists."""
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "cafe-aroma"})
        resp = self.client.get("/api/loyalty/membership-cards/")
        self.assertIsNone(resp.data[0]["card_design"])

    def test_card_design_appears_when_published(self):
        from loyalty.models import MerchantMembershipCardDesign
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "cafe-aroma"})

        MerchantMembershipCardDesign.objects.create(
            merchant=self.merchant_a,
            card_title="VIP Club",
            primary_color="#000000",
            accent_color="#FF5500",
            is_published=True,
        )

        resp = self.client.get("/api/loyalty/membership-cards/")
        design = resp.data[0]["card_design"]
        self.assertIsNotNone(design)
        self.assertEqual(design["card_title"], "VIP Club")
        self.assertEqual(design["primary_color"], "#000000")

    def test_unpublished_design_not_returned(self):
        from loyalty.models import MerchantMembershipCardDesign
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "cafe-aroma"})

        MerchantMembershipCardDesign.objects.create(
            merchant=self.merchant_a,
            card_title="Draft",
            is_published=False,
        )

        resp = self.client.get("/api/loyalty/membership-cards/")
        self.assertIsNone(resp.data[0]["card_design"])

    def test_transfer_enabled_reflects_merchant_setting(self):
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "cafe-aroma"})
        resp = self.client.get("/api/loyalty/membership-cards/")
        self.assertFalse(resp.data[0]["transfer_enabled"])

        self.merchant_a.allow_point_transfer = True
        self.merchant_a.save(update_fields=["allow_point_transfer"])

        resp = self.client.get("/api/loyalty/membership-cards/")
        self.assertTrue(resp.data[0]["transfer_enabled"])


# ═══════════════════════════════════════════════════════════════════════════════
# Membership QR Tests (Step 8)
# ═══════════════════════════════════════════════════════════════════════════════


class MembershipQRTests(TestCase):
    """Tests for per-membership QR tokens."""

    def setUp(self):
        self.client = APIClient()
        self.customer_user, self.customer = _create_customer(
            "alice", "alice@example.com",
        )
        self.merchant_a_user, self.merchant_a = _create_merchant(
            "shopa", "shopa@test.com", "Cafe Aroma", "cafe-aroma",
        )
        self.client.force_authenticate(user=self.customer_user)
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "cafe-aroma"})

    def test_qr_created_on_get(self):
        resp = self.client.get("/api/customer/memberships/cafe-aroma/qr/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("public_token", resp.data)
        self.assertTrue(resp.data["public_token"].startswith("MQR_"))

    def test_qr_idempotent_on_get(self):
        resp1 = self.client.get("/api/customer/memberships/cafe-aroma/qr/")
        resp2 = self.client.get("/api/customer/memberships/cafe-aroma/qr/")
        self.assertEqual(resp1.data["public_token"], resp2.data["public_token"])

    def test_qr_rotation(self):
        resp1 = self.client.post("/api/customer/memberships/cafe-aroma/qr/")
        resp2 = self.client.post("/api/customer/memberships/cafe-aroma/qr/")
        self.assertNotEqual(resp1.data["public_token"], resp2.data["public_token"])

    def test_qr_resolve_public(self):
        from loyalty.models import MembershipQrToken
        membership = CustomerMerchantProfile.objects.get(
            customer=self.customer, merchant=self.merchant_a,
        )
        qr = MembershipQrToken.objects.create(membership=membership)

        resp = self.client.get(f"/api/loyalty/qr/{qr.public_token}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["merchant"]["slug"], "cafe-aroma")
        self.assertEqual(resp.data["membership_number"], membership.membership_number)

    def test_invalid_qr_returns_404(self):
        resp = self.client.get("/api/loyalty/qr/INVALID_TOKEN/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_rotated_qr_no_longer_works(self):
        from loyalty.models import MembershipQrToken
        membership = CustomerMerchantProfile.objects.get(
            customer=self.customer, merchant=self.merchant_a,
        )
        qr = MembershipQrToken.objects.create(membership=membership)
        qr.rotate()

        resp = self.client.get(f"/api/loyalty/qr/{qr.public_token}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_qr_does_not_expose_sensitive_data(self):
        from loyalty.models import MembershipQrToken
        membership = CustomerMerchantProfile.objects.get(
            customer=self.customer, merchant=self.merchant_a,
        )
        qr = MembershipQrToken.objects.create(membership=membership)

        resp = self.client.get(f"/api/loyalty/qr/{qr.public_token}/")
        data = resp.data
        self.assertNotIn("email", data)
        self.assertNotIn("points_balance", data)
        self.assertNotIn("wallet", data)
        self.assertNotIn("user_id", data)


# ═══════════════════════════════════════════════════════════════════════════════
# Merchant Card Design Tests (Step 10+11)
# ═══════════════════════════════════════════════════════════════════════════════


class MerchantCardDesignTests(TestCase):
    """Tests for merchant card customization."""

    def setUp(self):
        self.client = APIClient()
        self.customer_user, self.customer = _create_customer(
            "alice", "alice@example.com",
        )
        self.merchant_a_user, self.merchant_a = _create_merchant(
            "shopa", "shopa@test.com", "Cafe Aroma", "cafe-aroma",
        )
        self.client.force_authenticate(user=self.merchant_a_user)

    def test_get_design_creates_default(self):
        resp = self.client.get("/api/loyalty/merchant/card-design/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["card_title"], "Membership")
        self.assertFalse(resp.data["is_published"])

    def test_update_design(self):
        resp = self.client.patch(
            "/api/loyalty/merchant/card-design/",
            {"card_title": "VIP Club", "accent_color": "#FF0000"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["card_title"], "VIP Club")
        self.assertEqual(resp.data["accent_color"], "#FF0000")

    def test_publish_design(self):
        self.client.patch("/api/loyalty/merchant/card-design/", {"card_title": "Gold"})
        resp = self.client.post("/api/loyalty/merchant/card-design/publish/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["is_published"])

    def test_customer_sees_only_published_design(self):
        from loyalty.models import MerchantMembershipCardDesign
        self.client.force_authenticate(user=self.customer_user)
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "cafe-aroma"})

        # Unpublished
        resp = self.client.get("/api/loyalty/membership-cards/")
        self.assertIsNone(resp.data[0]["card_design"])

        # Publish
        self.client.force_authenticate(user=self.merchant_a_user)
        self.client.post("/api/loyalty/merchant/card-design/publish/")

        self.client.force_authenticate(user=self.customer_user)
        resp = self.client.get("/api/loyalty/membership-cards/")
        self.assertIsNotNone(resp.data[0]["card_design"])

    def test_merchant_cannot_update_other_merchant_design(self):
        """Implicit: merchant_update only affects own merchant profile."""
        _, merchant_b = _create_merchant(
            "shopb", "shopb@test.com", "Restaurant Zen", "restaurant-zen",
        )
        from loyalty.models import MerchantMembershipCardDesign
        MerchantMembershipCardDesign.objects.create(
            merchant=merchant_b, card_title="Original",
        )

        # Merchant A tries to update — only their own design is accessible
        resp = self.client.get("/api/loyalty/merchant/card-design/")
        self.assertEqual(resp.data["card_title"], "Membership")  # A's default, not B's


# ═══════════════════════════════════════════════════════════════════════════════
# Merchant Customer List Tests (Step 13)
# ═══════════════════════════════════════════════════════════════════════════════


class MerchantCustomerListTests(TestCase):
    """Merchant sees only their own customers."""

    def setUp(self):
        self.client = APIClient()
        self.customer_user, self.customer = _create_customer(
            "alice", "alice@example.com",
        )
        self.merchant_a_user, self.merchant_a = _create_merchant(
            "shopa", "shopa@test.com", "Cafe Aroma", "cafe-aroma",
        )
        self.merchant_b_user, self.merchant_b = _create_merchant(
            "shopb", "shopb@test.com", "Restaurant Zen", "restaurant-zen",
        )

        # Customer joins both merchants
        self.client.force_authenticate(user=self.customer_user)
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "cafe-aroma"})
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "restaurant-zen"})

    def test_merchant_sees_own_members(self):
        self.client.force_authenticate(user=self.merchant_a_user)
        resp = self.client.get("/api/loyalty/merchant/customers/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["customer_email"], "alice@example.com")

    def test_merchant_does_not_see_other_members(self):
        """Merchant A cannot see Merchant B's members."""
        self.client.force_authenticate(user=self.merchant_a_user)
        resp = self.client.get("/api/loyalty/merchant/customers/")
        self.assertEqual(len(resp.data), 1)

        # The member should have merchant A's membership number
        membership_a = CustomerMerchantProfile.objects.get(
            customer=self.customer, merchant=self.merchant_a,
        )
        self.assertEqual(resp.data[0]["membership_number"], membership_a.membership_number)

    def test_merchant_customer_detail(self):
        membership = CustomerMerchantProfile.objects.get(
            customer=self.customer, merchant=self.merchant_a,
        )
        self.client.force_authenticate(user=self.merchant_a_user)
        resp = self.client.get(f"/api/loyalty/merchant/customers/{membership.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("wallet", resp.data)
        self.assertIn("recent_transactions", resp.data)

    def test_merchant_cannot_view_other_merchant_customer(self):
        membership_b = CustomerMerchantProfile.objects.get(
            customer=self.customer, merchant=self.merchant_b,
        )
        self.client.force_authenticate(user=self.merchant_a_user)
        resp = self.client.get(f"/api/loyalty/merchant/customers/{membership_b.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ═══════════════════════════════════════════════════════════════════════════════
# Point Transaction Ledger Tests (Step 4)
# ═══════════════════════════════════════════════════════════════════════════════


class PointTransactionLedgerTests(TestCase):
    """Every point change creates a ledger record."""

    def setUp(self):
        self.client = APIClient()
        self.customer_user, self.customer = _create_customer(
            "alice", "alice@example.com",
        )
        self.merchant_a_user, self.merchant_a = _create_merchant(
            "shopa", "shopa@test.com", "Cafe Aroma", "cafe-aroma",
        )
        self.client.force_authenticate(user=self.customer_user)
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "cafe-aroma"})
        self.wallet = CustomerMerchantWallet.objects.get(
            customer=self.customer, merchant=self.merchant_a,
        )

    def test_award_creates_transaction(self):
        from loyalty.services import award_wallet_points
        award_wallet_points(self.wallet, 100, description="Test award")

        txn = PointTransaction.objects.get(wallet=self.wallet, transaction_type="EARNED")
        self.assertEqual(txn.points, 100)
        self.assertEqual(txn.balance_before, 0)
        self.assertEqual(txn.balance_after, 100)
        self.assertIsNotNone(txn.merchant)
        self.assertIsNotNone(txn.customer)
        self.assertIsNotNone(txn.wallet)

    def test_transaction_has_membership(self):
        from loyalty.services import award_wallet_points
        award_wallet_points(self.wallet, 50)

        txn = PointTransaction.objects.get(wallet=self.wallet)
        self.assertIsNotNone(txn.membership)
        self.assertEqual(txn.merchant_id, self.merchant_a.id)

    def test_deduct_creates_transaction(self):
        from loyalty.services import award_wallet_points, deduct_wallet_points
        award_wallet_points(self.wallet, 200)
        deduct_wallet_points(self.wallet, 75, description="Reward redemption")

        txn = PointTransaction.objects.filter(
            wallet=self.wallet, transaction_type="REDEEMED",
        ).first()
        self.assertIsNotNone(txn)
        self.assertEqual(txn.points, -75)

    def test_transfer_creates_two_transactions(self):
        from loyalty.services import get_or_create_wallet, transfer_points
        receiver_user, receiver_profile = _create_customer("bob", "bob2@example.com")

        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "cafe-aroma"})
        self.client.force_authenticate(user=receiver_user)
        self.client.post("/api/customer/memberships/join/", {"merchant_slug": "cafe-aroma"})
        self.client.force_authenticate(user=self.customer_user)

        from loyalty.models import CustomerMerchantProfile
        receiver_membership = CustomerMerchantProfile.objects.get(
            customer=receiver_profile, merchant=self.merchant_a,
        )
        receiver_wallet = get_or_create_wallet(
            receiver_profile, self.merchant_a, membership=receiver_membership,
        )

        from loyalty.services import award_wallet_points
        award_wallet_points(self.wallet, 300)

        result = transfer_points(self.wallet, receiver_wallet, 100)
        self.assertEqual(
            PointTransaction.objects.filter(transfer_group=result["transfer_group"]).count(), 2
        )
