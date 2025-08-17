from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Payment

@shared_task(bind=True)
def send_payment_confirmation_email(self, payment_id):
    try:
        payment = Payment.objects.select_related("user").get(pk=payment_id)
    except Payment.DoesNotExist:
        return {"error": "Payment not found"}

    user = payment.user
    subject = f"Payment Confirmation for booking {payment.booking_reference}"
    message = (
        f"Dear {user.get_full_name() or user.username},\n\n"
        f"Thank you — your payment for booking {payment.booking_reference} was successful.\n"
        f"Amount: {payment.amount} {payment.currency}\n"
        f"Transaction Ref: {payment.chapa_tx_ref}\n\n"
        "Regards,\nALX Travel"
    )

    # Send email (configure EMAIL_BACKEND in settings)
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)

    # Optionally log or update Payment
    return {"sent_to": user.email, "payment_id": payment_id}
