from rest_framework import serializers
from .models import Listing, Booking

class ListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = '__all__'

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = '__all__'


# listings/management/commands/seed.py
from django.core.management.base import BaseCommand
from listings.models import Listing, Booking, Review
import random
from faker import Faker

class Command(BaseCommand):
    help = 'Seed the database with sample listings, bookings, and reviews'

    def handle(self, *args, **kwargs):
        fake = Faker()

        # Clear old data
        Review.objects.all().delete()
        Booking.objects.all().delete()
        Listing.objects.all().delete()

        # Create Listings
        for _ in range(10):
            listing = Listing.objects.create(
                title=fake.city(),
                description=fake.text(),
                price=round(random.uniform(50, 500), 2),
                location=fake.address()
            )

            # Create Bookings
            for _ in range(2):
                Booking.objects.create(
                    listing=listing,
                    guest_name=fake.name(),
                    guest_email=fake.email(),
                    check_in=fake.date_this_year(),
                    check_out=fake.date_this_year()
                )

            # Create Reviews
            for _ in range(3):
                Review.objects.create(
                    listing=listing,
                    reviewer_name=fake.name(),
                    comment=fake.sentence(),
                    rating=random.randint(1, 5)
                )

        self.stdout.write(self.style.SUCCESS('Database seeded successfully.'))

from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id", "booking_reference", "user", "amount", "currency",
            "chapa_tx_ref", "chapa_transaction_id", "status", "metadata",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "status", "chapa_transaction_id", "metadata", "created_at", "updated_at"]
