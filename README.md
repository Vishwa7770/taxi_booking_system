# 🚕 TaxiApp – Django Taxi Booking Platform

A **production-ready** Django taxi booking application with real-time WebSocket tracking, REST API, Stripe payment integration, and full rider/driver/admin dashboards.

---

## 📦 Features

| Role   | Features |
|--------|----------|
| Rider  | Signup/Login · Request ride · Fare estimate · Live driver tracking · Ride history · Rate driver |
| Driver | Signup/Login · Add vehicle · Go online/offline · Accept rides · Share live GPS · View earnings · Rate rider |
| Admin  | Manage users/rides/payments · Analytics dashboard · Django Admin panel |

---

## 🛠 Tech Stack

- **Backend**: Django 4.2 + Django REST Framework
- **Real-time**: Django Channels + WebSockets (InMemoryChannelLayer by default, Redis for prod)
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Frontend**: Bootstrap 5 + Leaflet.js (no API key needed)
- **Payments**: Stripe integration (placeholder, add keys in .env)
- **Auth**: Session auth (HTML) + JWT (API)

---

## 🚀 Quick Start

### 1. Clone / Unzip the project
```bash
cd taxi_project
```

### 2. Create virtual environment
```bash
python -m venv env
source env/bin/activate      # Windows: env\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env and fill in your values (defaults work for dev)
```

### 5. Apply database migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create a superuser (admin)
```bash
python manage.py createsuperuser
```

### 7. Load sample data (optional)
```bash
python manage.py seed_data
# Creates riders: alice_rider, bob_rider, carol_rider  (password: password123)
# Creates drivers: david_driver, emma_driver           (password: password123)
```

### 8. Run the development server
```bash
python manage.py runserver
```

Open: http://127.0.0.1:8000

---

## 🌐 URLs

| URL | Description |
|-----|-------------|
| `/` | Landing page |
| `/signup/` | Register as rider or driver |
| `/login/` | Login |
| `/dashboard/` | Redirects to rider or driver dashboard |
| `/rider/` | Rider dashboard with map + booking |
| `/driver/` | Driver dashboard with pending rides |
| `/history/` | Ride history |
| `/rides/<pk>/` | Ride detail + live tracking + rating |
| `/admin/` | Django admin panel |
| `/api/` | DRF browsable API |
| `/api/auth/token/` | JWT token endpoint |

---

## 📡 WebSocket Endpoints

| Endpoint | Purpose |
|----------|---------|
| `ws://host/ws/location/<ride_id>/` | Driver pushes GPS; rider receives live updates |
| `ws://host/ws/notifications/<user_id>/` | Ride status push notifications |
| `ws://host/ws/drivers/nearby/` | Rider sees all online drivers on map |

---

## 🔑 REST API Endpoints (JWT Auth)

```
POST   /api/auth/register/          Register rider or driver
POST   /api/auth/token/             Obtain JWT token
GET    /api/auth/me/                Current user profile

GET    /api/rides/                  List rides
POST   /api/rides/                  Create ride (riders only)
GET    /api/rides/fare-estimate/    Fare estimation
POST   /api/rides/<id>/accept/      Accept ride (drivers)
POST   /api/rides/<id>/start/       Start ride (drivers)
POST   /api/rides/<id>/complete/    Complete ride (drivers)
POST   /api/rides/<id>/cancel/      Cancel ride

GET    /api/vehicles/               List vehicles
POST   /api/vehicles/               Add vehicle (drivers)
POST   /api/vehicles/<id>/toggle-online/   Go online/offline
POST   /api/vehicles/<id>/update-location/ Update GPS

POST   /api/payments/<id>/pay-stripe/  Pay with Stripe

POST   /api/ratings/               Leave a rating
GET    /api/analytics/             Admin analytics summary
```

---

## 🗃️ Project Structure

```
taxi_project/
├── taxi_project/
│   ├── settings.py          # All settings
│   ├── urls.py              # Root URL conf
│   ├── asgi.py              # ASGI + WebSocket routing
│   └── wsgi.py
├── taxiapp/
│   ├── models.py            # User, Vehicle, Ride, Payment, Rating
│   ├── serializers.py       # DRF serializers
│   ├── views.py             # All views (API + HTML)
│   ├── urls.py              # App URL patterns
│   ├── consumers.py         # WebSocket consumers
│   ├── routing.py           # WebSocket URL routing
│   ├── admin.py             # Admin configuration
│   ├── utils.py             # Fare calculation helpers
│   ├── context_processors.py
│   ├── templates/taxiapp/
│   │   ├── base.html
│   │   ├── home.html
│   │   ├── login.html
│   │   ├── signup.html
│   │   ├── rider_dashboard.html
│   │   ├── driver_dashboard.html
│   │   ├── ride_history.html
│   │   └── ride_detail.html
│   └── management/commands/
│       └── seed_data.py     # Sample data seeder
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⚙️ Production Notes

- Switch `CHANNEL_LAYERS` in `settings.py` to `RedisChannelLayer` (uncomment the lines).
- Set `DEBUG=False` and configure `ALLOWED_HOSTS` in `.env`.
- Run with Daphne: `daphne -p 8000 taxi_project.asgi:application`
- Add real Stripe keys to `.env` for payments.
- Use PostgreSQL: set `DATABASE_URL=postgres://user:pass@host/db` in `.env`.
- Run `python manage.py collectstatic` before serving static files.

---

## 🔐 Sample Credentials (after `seed_data`)

| Username | Password | Role |
|----------|----------|------|
| alice_rider | password123 | Rider |
| david_driver | password123 | Driver |
| *(your superuser)* | *(set during createsuperuser)* | Admin |
