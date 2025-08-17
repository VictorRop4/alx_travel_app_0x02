# listings/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
# listings/views.py
from rest_framework import viewsets
from .models import Listing, Booking
from .serializers import ListingSerializer, BookingSerializer

class ListingViewSet(viewsets.ModelViewSet):
    """
    A viewset that provides the standard CRUD actions for the Listing model.
    """
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer


class BookingViewSet(viewsets.ModelViewSet):
    """
    A viewset that provides the standard CRUD actions for the Booking model.
    """
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer


class ListingView(APIView):
    def get(self, request):
        data = {
            "message": "Listing endpoint working correctly."
        }
        return Response(data, status=status.HTTP_200_OK)


import uuid
import requests
from django.conf import settings
from django.shortcuts import redirect
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .models import Payment, Booking  # Booking model assumed to exist
from .serializers import PaymentSerializer
from .tasks import send_payment_confirmation_email  # Celery task (below)


class PaymentViewSet(viewsets.GenericViewSet):
    """
    Payment endpoints: initiate and verify (also callback handler).
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="initiate", permission_classes=[IsAuthenticated])
    def initiate(self, request):
        """
        Initiate a Chapa payment.
        Expected payload: { "booking_id": 123, "amount": "120.00", "currency": "ETB" }
        """
        # 1. Input validation
        booking_id = request.data.get("booking_id")
        amount = request.data.get("amount")
        currency = request.data.get("currency", "ETB")

        if not booking_id or not amount:
            return Response({"detail": "booking_id and amount are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            booking = Booking.objects.get(pk=booking_id)
        except Booking.DoesNotExist:
            return Response({"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        # 2. Create a unique tx_ref (merchant reference) — save Payment with status "pending"
        tx_ref = f"{request.user.id}-{booking_id}-{uuid.uuid4().hex[:12]}"

        payment = Payment.objects.create(
            booking_reference=str(booking_id),
            user=request.user,
            amount=amount,
            currency=currency,
            chapa_tx_ref=tx_ref,
            status="pending",
        )

        # 3. Prepare payload for Chapa initialize
        payload = {
            "amount": float(amount),
            "currency": currency,
            "tx_ref": tx_ref,
            "first_name": request.user.first_name or request.user.username,
            "last_name": request.user.last_name or "",
            "email": request.user.email,
            "callback_url": settings.CHAPA_CALLBACK_URL,  # Chapa will call with tx_ref
            "return_url": settings.CHAPA_RETURN_URL,      # user returns here after payment
            # Optional: "customization": {"title": "ALX Travel", "description": "Booking payment"}
        }

        headers = {
            "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
            "Content-Type": "application/json",
        }

        # 4. Call Chapa initialize endpoint
        init_url = f"{settings.CHAPA_BASE_URL.rstrip('/')}/transaction/initialize"
        try:
            resp = requests.post(init_url, json=payload, headers=headers, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as exc:
            # update Payment metadata and status
            payment.metadata = {"error": str(exc)}
            payment.status = "failed"
            payment.save(update_fields=["metadata", "status", "updated_at"])
            return Response({"detail": "Failed to initialize payment.", "error": str(exc)},
                            status=status.HTTP_502_BAD_GATEWAY)

        data = resp.json()
        # Typically Chapa returns an object with authorization_url (or data.authorization_url)
        # store raw response for audit:
        payment.metadata = data
        payment.save(update_fields=["metadata", "updated_at"])

        # Extract redirect url for the user
        # Chapa docs: response.data.checkout_url or data['data']['checkout_url'] sometimes
        # We'll attempt to look for common keys:
        checkout_url = None
        if isinstance(data, dict):
            if "data" in data and isinstance(data["data"], dict):
                checkout_url = data["data"].get("checkout_url") or data["data"].get("authorization_url") or data["data"].get("url")
            checkout_url = checkout_url or data.get("checkout_url") or data.get("authorization_url") or data.get("url")

        if not checkout_url:
            # If not found, treat as failure
            payment.status = "failed"
            payment.save(update_fields=["status"])
            return Response({"detail": "Payment initialized but no checkout URL returned.", "response": data},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Respond with the checkout/redirect URL for the frontend to redirect the user
        return Response({"checkout_url": checkout_url, "payment_id": payment.id, "chapa_tx_ref": tx_ref}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="verify", permission_classes=[AllowAny])
    def verify(self, request):
        """
        Explicit verify endpoint: Provide tx_ref as query param ?tx_ref=...
        """
        tx_ref = request.query_params.get("tx_ref")
        if not tx_ref:
            return Response({"detail": "tx_ref query parameter required."}, status=status.HTTP_400_BAD_REQUEST)
        return verify_chapa_transaction(tx_ref)


# Helper: centralize verification logic (callable from callback view)
def verify_chapa_transaction(tx_ref):
    """
    Verify tx_ref with Chapa and update Payment model. Returns DRF Response.
    """
    try:
        payment = Payment.objects.get(chapa_tx_ref=tx_ref)
    except Payment.DoesNotExist:
        return Response({"detail": "Payment record not found for the provided tx_ref."}, status=status.HTTP_404_NOT_FOUND)

    verify_url = f"{settings.CHAPA_BASE_URL.rstrip('/')}/transaction/verify/{tx_ref}"
    headers = {"Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"}

    try:
        resp = requests.get(verify_url, headers=headers, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        payment.metadata = {"verify_error": str(exc)}
        payment.save(update_fields=["metadata", "updated_at"])
        return Response({"detail": "Failed to verify with Chapa.", "error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

    data = resp.json()
    payment.metadata = data

    # Chapa returns something like data['status'] or data['data']['status']
    status_value = None
    if isinstance(data, dict):
        if "data" in data and isinstance(data["data"], dict):
            status_value = data["data"].get("status") or data.get("status")
            chapa_tx_id = data["data"].get("id") or data.get("id")
        else:
            status_value = data.get("status")
            chapa_tx_id = data.get("id")
    else:
        chapa_tx_id = None

    # Normalize to our Payment.status choices
    if status_value and str(status_value).lower() in ("success", "completed", "paid"):
        payment.status = "completed"
    elif status_value and str(status_value).lower() in ("failed", "declined"):
        payment.status = "failed"
    else:
        # Keep pending otherwise; but for safety, set to pending if unknown
        payment.status = payment.status or "pending"

    if chapa_tx_id:
        payment.chapa_transaction_id = str(chapa_tx_id)

    payment.save(update_fields=["status", "chapa_transaction_id", "metadata", "updated_at"])

    # If completed, launch async tasks like email confirmation
    if payment.status == "completed":
        # use Celery task (non-blocking)
        send_payment_confirmation_email.delay(payment.id)

    return Response({"detail": "Verification done.", "payment_status": payment.status, "metadata": payment.metadata}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
def chapa_callback(request):
    """
    Chapa will call this endpoint after payment attempt.
    Chapa typically includes a tx_ref query parameter (or reference).
    We call our verify helper and then redirect user to return page.
    """
    tx_ref = request.GET.get("tx_ref") or request.GET.get("reference") or request.GET.get("tx_ref", None)
    if not tx_ref:
        return Response({"detail": "tx_ref is required in callback."}, status=status.HTTP_400_BAD_REQUEST)

    # call same verification function
    resp = verify_chapa_transaction(tx_ref)
    # After verification, redirect to a frontend success/failure page (you may customize)
    # If you need to return JSON to Chapa, return resp; otherwise redirect user to CHAPA_RETURN_URL
    return redirect(settings.CHAPA_RETURN_URL + f"?tx_ref={tx_ref}&status={resp.data.get('payment_status') if isinstance(resp, Response) else ''}")
