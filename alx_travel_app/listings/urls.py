from django.urls import path
from .views import ListingView
from rest_framework.routers import DefaultRouter
from .views import ListingViewSet, BookingViewSet

router = DefaultRouter()
router.register(r'listings', ListingViewSet)
router.register(r'bookings', BookingViewSet)

urlpatterns = router.urls

urlpatterns = [
    path('listings/', ListingView.as_view(), name='listings-view'),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, chapa_callback

router = DefaultRouter()
router.register(r"payments", PaymentViewSet, basename="payment")

urlpatterns = [
    path("", include(router.urls)),
    path("payments/callback/", chapa_callback, name="chapa-callback"),
]
