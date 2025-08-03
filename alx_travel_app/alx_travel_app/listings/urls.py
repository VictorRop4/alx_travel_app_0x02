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
