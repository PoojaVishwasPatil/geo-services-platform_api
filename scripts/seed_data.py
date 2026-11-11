import asyncio
import os
import random
import sys
import uuid

# Ensure the project root is in sys.path whether executed from root or backend/
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (ROOT_DIR, BACKEND_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from typing import List, Dict, Any
from sqlalchemy import select, func
from geoalchemy2.elements import WKTElement

from backend.app.database import AsyncSessionLocal, init_db, engine
from backend.app.models.service import Service, ServiceCategory
from backend.app.models.user import AdminUser
from backend.app.core.security import get_password_hash
from backend.app.config import settings
from backend.app.core.logging import logger

# Target Locations: Nashik & Mumbai (Maharashtra, India)
ANCHORS = [
    {
        "city": "Nashik",
        "lat": 19.9975,
        "lng": 73.7898,
        "areas": [
            "College Road", "Gangapur Road", "Cidco", "Mahatma Nagar",
            "Indira Nagar", "Panchavati", "Govind Nagar", "Dwarka Circle",
            "Satpur MIDC", "Nashik Road"
        ]
    },
    {
        "city": "Mumbai",
        "lat": 19.0760,
        "lng": 72.8777,
        "areas": [
            "Bandra West", "Andheri East", "Powai", "Dadar",
            "Colaba", "Juhu", "Lower Parel", "Goregaon",
            "Worli", "Vile Parle"
        ]
    }
]

SAMPLE_NAMES = {
    ServiceCategory.HOSPITALS: [
        "Sahyadri Super Speciality Hospital", "Ashoka Medicover Hospital", "Wockhardt Hospital",
        "Apollo Hospitals", "Lilavati Hospital & Research", "Kokilaben Dhirubhai Ambani Hospital",
        "Nanavati Max Super Speciality", "Hinduja Hospital", "Fortis Healthcare Center", "Six Sigma Hospital"
    ],
    ServiceCategory.ATMS: [
        "State Bank of India 24/7 e-Corner", "HDFC Bank ATM Hub", "ICICI Bank Express ATM",
        "Axis Bank 24hr ATM", "Kotak Mahindra Bank ATM", "Bank of Baroda e-Lobby",
        "Punjab National Bank ATM", "Union Bank of India ATM", "Canara Bank ATM", "IDBI Bank ATM"
    ],
    ServiceCategory.SHOPS: [
        "D-Mart Supermarket & Hypermarket", "Reliance Smart Bazaar", "Nature's Basket Organic Mart",
        "Croma Electronics & Appliances", "Vijay Sales Mega Store", "Crossword Bookstore & Cafe",
        "Westside Lifestyle Store", "Zudio Fashion Outlet", "Fabindia Handcrafted Goods", "Decathlon Sports Store"
    ],
    ServiceCategory.RESTAURANTS: [
        "Barbeque Nation Buffet & Grill", "Mainland China Fine Dining", "Shree Krishna Veg Thali",
        "Copper Chimney North Indian", "Saffron Multicuisine Restaurant", "Sigree Global Grill",
        "Punjab Grill Gourmet", "Mahesh Lunch Home Seafood", "Cafe Mondegar & Bistro", "The Belgian Waffle Co."
    ],
    ServiceCategory.PHARMACIES: [
        "Apollo 24/7 Day & Night Pharmacy", "Wellness Forever Chemist", "MedPlus Health & Wellness",
        "Noble Chemists & Druggists", "Frank Ross Pharmacy", "LifeCare Chemist Hub",
        "Sanjivani Medical Store", "Reliance Netmeds Pharmacy", "Fortis Health Chemist", "Metro Care Chemist"
    ],
    ServiceCategory.OTHERS: [
        "SpeedX Multi-Brand Auto Repair", "Cult.fit Fitness & Yoga Center", "Gold's Gym Health Club",
        "Paws & Claws Pet Care Clinic", "Blue Dart Express Courier Hub", "WeWork Premium Coworking",
        "CleanWash Express Laundromat", "Kaya Skin Clinic & Spa", "Rotary Community Center", "City Central Public Library"
    ]
}


def generate_cluster_point(base_lat: float, base_lng: float, max_offset_km: float = 6.0):
    # 1 deg lat is approx 111 km. 1 deg lon is approx 111 km * cos(lat)
    lat_offset = (random.uniform(-max_offset_km, max_offset_km)) / 111.0
    lng_offset = (random.uniform(-max_offset_km, max_offset_km)) / (111.0 * random.choice([0.85, 0.95, 1.0]))
    return round(base_lat + lat_offset, 6), round(base_lng + lng_offset, 6)


async def seed():
    logger.info("Initializing database schema for seeding...")
    await init_db()

    from backend.app.database import engine, AsyncSessionLocal
    from backend.app.services.cache_service import cache_service
    from sqlalchemy import delete

    async with AsyncSessionLocal() as session:
        # 1. Ensure Default Admin exists
        stmt = select(AdminUser).where(AdminUser.username == settings.ADMIN_DEFAULT_USERNAME)
        existing_admin = (await session.execute(stmt)).scalar_one_or_none()
        if not existing_admin:
            admin = AdminUser(
                username=settings.ADMIN_DEFAULT_USERNAME,
                email=settings.ADMIN_DEFAULT_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_DEFAULT_PASSWORD),
                is_active=True
            )
            session.add(admin)
            logger.info(f"Created default admin user: {settings.ADMIN_DEFAULT_USERNAME}")
        else:
            logger.info("Admin user already present.")

        # 2. Reset services to strictly contain only Nashik & Mumbai Indian locations
        logger.info("Purging old benchmark records to ensure 100% Nashik & Mumbai Indian dataset...")
        await session.execute(delete(Service))
        await session.commit()

        logger.info(f"Generating realistic Indian service dataset across {len(ANCHORS)} urban centers (Nashik & Mumbai)...")
        services_to_add: List[Service] = []

        for anchor in ANCHORS:
            city_name = anchor["city"]
            base_lat = anchor["lat"]
            base_lng = anchor["lng"]
            areas = anchor["areas"]

            for category, names in SAMPLE_NAMES.items():
                for name in names:
                    lat, lng = generate_cluster_point(base_lat, base_lng, max_offset_km=7.0)
                    rating = round(random.uniform(3.5, 4.9), 1)
                    phone = f"+91-{random.choice([98, 97, 96, 95, 93, 88, 87])}{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
                    area_name = random.choice(areas)

                    point_geom = WKTElement(f"POINT({lng} {lat})", srid=4326)

                    svc = Service(
                        name=f"{name} ({city_name})",
                        category=category.value,
                        latitude=lat,
                        longitude=lng,
                        location=point_geom,
                        address=f"{random.randint(10, 450)}, {area_name}, {city_name}, Maharashtra, India",
                        rating=rating,
                        contact_phone=phone,
                        metadata_json={
                            "city": city_name,
                            "area": area_name,
                            "state": "Maharashtra",
                            "country": "India",
                            "wheelchair_accessible": random.choice([True, False]),
                            "open_24_7": random.choice([True, False]) if category in [ServiceCategory.ATMS, ServiceCategory.HOSPITALS, ServiceCategory.PHARMACIES] else False,
                            "verified": True
                        },
                        is_active=True
                    )
                    services_to_add.append(svc)

        session.add_all(services_to_add)
        await session.commit()
        await cache_service.invalidate_service_caches()
        logger.info(f"Successfully seeded {len(services_to_add)} realistic Indian service locations (Nashik & Mumbai)!")

    # Gracefully close connections to prevent Windows asyncio transport warning
    await engine.dispose()
    await cache_service.close()


if __name__ == "__main__":
    asyncio.run(seed())

