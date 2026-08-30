import os
import random
from datetime import date, timedelta
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from faker import Faker

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
fake = Faker("en_IN")
random.seed(42)

STATES_DISTRICTS = {
    "Maharashtra": ["Pune", "Nagpur", "Nashik"],
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Varanasi"],
    "Tamil Nadu": ["Chennai", "Madurai", "Coimbatore"],
    "Karnataka": ["Bengaluru Urban", "Mysuru", "Belagavi"],
    "West Bengal": ["Kolkata", "Howrah", "Darjeeling"],
}
CATEGORIES = ["Drinking Water", "Road Construction", "School Infrastructure",
              "Community Hall", "Street Lighting", "Health Facility"]
AGENCIES = [f"Agency {c}" for c in "ABCDEFGH"]
WORK_TEMPLATES = {
    "Drinking Water": "Installation of drinking water supply system in {place}",
    "Road Construction": "Construction/repair of road connecting {place}",
    "School Infrastructure": "Construction of additional classroom at {place} school",
    "Community Hall": "Construction of community hall at {place}",
    "Street Lighting": "Installation of solar street lights in {place}",
    "Health Facility": "Upgradation of primary health centre at {place}",
}
BASE_COST = {
    "Drinking Water": 800000, "Road Construction": 1500000,
    "School Infrastructure": 600000, "Community Hall": 900000,
    "Street Lighting": 300000, "Health Facility": 1200000,
}


def make_project(force_anomaly=None):
    state = random.choice(list(STATES_DISTRICTS))
    district = random.choice(STATES_DISTRICTS[state])
    category = random.choice(CATEGORIES)
    place = f"{fake.city_suffix()} {district}"
    base = BASE_COST[category]
    agency = random.choice(AGENCIES)

    sanctioned = base * random.uniform(0.85, 1.15)
    start = date(2022, 1, 1) + timedelta(days=random.randint(0, 700))
    expected_completion = start + timedelta(days=random.randint(90, 365))
    actual_delay = random.randint(-10, 30)
    expenditure = sanctioned * random.uniform(0.7, 1.0)

    if force_anomaly == "cost":
        sanctioned = base * random.uniform(2.2, 3.0)
    elif force_anomaly == "delay":
        actual_delay = random.randint(120, 400)
    elif force_anomaly == "agency":
        agency = "Agency X"
        actual_delay = random.randint(150, 300)

    actual_completion = expected_completion + timedelta(days=actual_delay)
    description = WORK_TEMPLATES[category].format(place=place)

    return {
        "work_name": description[:60],
        "description": description,
        "mp_name": fake.name(),
        "constituency": f"{district} constituency",
        "state": state,
        "district": district,
        "category": category,
        "implementing_agency": agency,
        "recommended_amount": round(sanctioned, 2),
        "sanctioned_amount": round(sanctioned, 2),
        "expenditure": round(expenditure, 2),
        "work_status": "completed",
        "start_date": start,
        "expected_completion": expected_completion,
        "actual_completion": actual_completion,
        "source": "synthetic",
    }


def make_duplicate_pair():
    p1 = make_project()
    p2 = dict(p1)
    p2["work_name"] = (p1["work_name"] + " Phase 2")[:60]
    p2["description"] = p1["description"] + ", phase 2 continuation"
    return [p1, p2]


def build_dataset(n=1500):
    n_cost = int(n * 0.03)
    n_delay = int(n * 0.05)
    n_agency = int(n * 0.04)
    n_normal = n - n_cost - n_delay - n_agency - 10

    rows = [make_project() for _ in range(n_normal)]
    rows += [make_project(force_anomaly="cost") for _ in range(n_cost)]
    rows += [make_project(force_anomaly="delay") for _ in range(n_delay)]
    rows += [make_project(force_anomaly="agency") for _ in range(n_agency)]
    for _ in range(5):
        rows.extend(make_duplicate_pair())

    random.shuffle(rows)
    return rows


def insert_rows(rows):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cols = list(rows[0].keys())
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f"INSERT INTO projects ({', '.join(cols)}) VALUES ({placeholders})"
    for row in rows:
        cur.execute(sql, [row[c] for c in cols])
    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    dataset = build_dataset()
    insert_rows(dataset)
    print(f"Inserted {len(dataset)} synthetic projects.")
