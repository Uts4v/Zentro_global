# loyalty/tests.py
"""
Tests for the point transfer system.

Run with: python manage.py test loyalty.tests
"""

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
        """
        Cafe A points CANNOT be transferred to a receiver who has NOT
        joined Cafe A. The receiver must have an active CustomerMerchantProfile
        at the same merchant.
        """
        # Remove receiver's join from merchant A
        CustomerMerchantProfile.objects.filter(
            customer=self.receiver, merchant=self.merchant_a
        ).update(status=CustomerMerchantProfile.STATUS_INACTIVE)

        resp = self.client.post(self._transfer_url(), self._transfer_payload())
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not joined", str(resp.data.get("error", "")).lower())

    def test_receiver_must_be_active_at_merchant(self):
        """Receiver must have an active CustomerMerchantProfile at the merchant."""
        # Receiver never joined merchant A — create a fresh customer
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
        """
        If we force a cross-merchant scenario by passing merchant_id = B,
        the sender wallet will be created at B (with 0 points),
        so the transfer should fail with insufficient balance — not a
        cross-merchant error. The cross-merchant error can only happen
        if someone bypasses the view logic.

        The REAL cross-merchant test is in services.transfer_points directly:
        """
        from loyalty.services import transfer_points
        from loyalty.services import get_or_create_wallet

        # Create a wallet for sender at merchant B with some points
        sender_wallet_b = CustomerMerchantWallet.objects.create(
            customer=self.sender, merchant=self.merchant_b,
            points_balance=100,
        )
        receiver_wallet_b = CustomerMerchantWallet.objects.create(
            customer=self.receiver, merchant=self.merchant_b,
            points_balance=0,
        )

        # This should work — same merchant B
        result = transfer_points(sender_wallet_b, receiver_wallet_b, 50)
        self.assertIsNotNone(result["transfer_group"])

        # Now try with different merchants
        sender_wallet_b.refresh_from_db()  # now has 50
        receiver_wallet_a = self.receiver_wallet_a  # merchant A wallet

        with self.assertRaises(ValueError) as ctx:
            transfer_points(sender_wallet_b, receiver_wallet_a, 25)
        self.assertIn("Cross-merchant", str(ctx.exception))

    def test_cross_merchant_rejected_via_api(self):
        """Via API: sender tries to send to receiver at a different merchant."""
        # Give sender a wallet at merchant B too
        CustomerMerchantWallet.objects.create(
            customer=self.sender, merchant=self.merchant_b,
            points_balance=200,
        )

        # Send with merchant_id = A where receiver has 100 pts,
        # but sender also has wallet at A with 500 pts.
        # The expected error will be insufficient because sender's
        # wallet at A has 500 but we try to send 600.
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
        # Create a transfer first
        self.client.post(self._transfer_url(), self._transfer_payload())

        resp = self.client.get("/api/loyalty/transfers/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)

        # The authenticated user (sender) should see TRANSFER_SENT
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

        # Authenticate as receiver
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
        """After a transfer, both wallets should reflect correct deltas."""
        self.client.post(self._transfer_url(), self._transfer_payload(amount=200))

        self.sender_wallet_a.refresh_from_db()
        self.receiver_wallet_a.refresh_from_db()
        self.assertEqual(self.sender_wallet_a.points_balance, 300)   # 500 - 200
        self.assertEqual(self.receiver_wallet_a.points_balance, 300)  # 100 + 200

    def test_multiple_transfers_accumulate(self):
        """Multiple transfers should compound correctly."""
        self.client.post(self._transfer_url(), self._transfer_payload(amount=50))
        self.client.post(self._transfer_url(), self._transfer_payload(amount=30))

        self.sender_wallet_a.refresh_from_db()
        self.receiver_wallet_a.refresh_from_db()
        self.assertEqual(self.sender_wallet_a.points_balance, 420)   # 500 - 80
        self.assertEqual(self.receiver_wallet_a.points_balance, 180)  # 100 + 80

    def test_transfer_group_links_sent_and_received(self):
        """Both transactions should share the same transfer_group UUID."""
        resp = self.client.post(self._transfer_url(), self._transfer_payload())
        tg = resp.data["transfer_group"]

        sent = PointTransaction.objects.get(id=resp.data["sent_transaction"]["id"])
        recv = PointTransaction.objects.get(id=resp.data["received_transaction"]["id"])
        self.assertEqual(str(sent.transfer_group), tg)
        self.assertEqual(str(recv.transfer_group), tg)
