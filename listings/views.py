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
