# Listings App

This app is part of the `alx_travel_app_0x00` project. It manages travel-related listings, bookings, and reviews.

## Features

- Create and manage travel listings
- Book listings
- Post reviews on listings

## Models

- `Listing`: Represents a travel listing
- `Booking`: Represents a reservation made by a user
- `Review`: Represents feedback provided for a listing

## Setup

Ensure the virtual environment is activated:

```bash
my_venv\Scripts\activate

## Chapa Integration

1. Add to .env:
   CHAPA_SECRET_KEY=...
   CHAPA_BASE_URL=https://api.chapa.co/v1
   CHAPA_CALLBACK_URL=https://<ngrok-or-domain>/api/payments/callback/
   CHAPA_RETURN_URL=https://<ngrok-or-domain>/payment/return/

2. Run:
   python manage.py migrate
   python manage.py runserver

3. Expose server for sandbox:
   ngrok http 8000

4. POST /api/payments/initiate/ with booking_id & amount (authenticated)
   -> receive checkout_url
   -> complete payment on Chapa sandbox
   -> Chapa calls /api/payments/callback/?tx_ref=...
   -> Payment status updated; confirmation email sent via Celery

5. For testing, run:
   pytest
