# listings/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class ListingView(APIView):
    def get(self, request):
        data = {
            "message": "Listing endpoint working correctly."
        }
        return Response(data, status=status.HTTP_200_OK)
