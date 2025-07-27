from django.urls import path
from .views import ListingView

urlpatterns = [
    path('listings/', ListingView.as_view(), name='listings-view'),
]
