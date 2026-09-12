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
# Each list covers genuinely distinct sub-scopes of work within the category (not
# synonym-swapped phrasings of one scope) — verified against all-MiniLM-L6-v2 that
# distinct sub-scopes embed far enough apart to stay under scoring.py's 0.85
# duplicate-similarity threshold; synonym-swapped single-scope phrasing does not
# (see task-3-report.md for the measurements).
WORK_TEMPLATES = {
    "Drinking Water": [
        "Installation of a new drinking water supply pipeline in {place}",
        "Repair and augmentation of the overhead water tank at {place}",
        "Installation of hand pumps and bore wells near {place}",
        "Provision of household water connections in {place}",
        "Construction of an underground water storage sump at {place}",
        "Replacement of corroded water supply pipes along {place}",
        "Installation of water purification units at {place}",
        "Repair of the water distribution network serving {place}",
    ],
    "Road Construction": [
        "Construction of a new concrete road connecting {place}",
        "Widening and resurfacing of the approach road near {place}",
        "Construction of a culvert and drainage channel at {place}",
        "Repair of potholes and patchwork on the road at {place}",
        "Construction of a footpath and pedestrian crossing near {place}",
        "Installation of road safety signage and speed breakers at {place}",
        "Construction of a retaining wall along the road at {place}",
        "Widening of the bridge approach road near {place}",
    ],
    "School Infrastructure": [
        "Construction of additional classrooms at the school in {place}",
        "Renovation of the toilet block and boundary wall at the school near {place}",
        "Provision of furniture and a computer lab for the school in {place}",
        "Construction of a school playground and boundary fencing at {place}",
        "Repair of the school roof and flooring near {place}",
        "Installation of drinking water and handwash facilities at the school in {place}",
        "Construction of a library room at the school near {place}",
        "Provision of solar power backup for the school at {place}",
    ],
    "Community Hall": [
        "Construction of a new community hall at {place}",
        "Renovation and extension of the existing community hall near {place}",
        "Construction of a marriage and function hall for residents of {place}",
        "Repair of the roof and flooring of the community hall at {place}",
        "Provision of furniture and seating for the community hall in {place}",
        "Construction of a stage and public address facility at the community hall near {place}",
        "Installation of backup power for the community hall at {place}",
        "Construction of a boundary wall around the community hall in {place}",
    ],
    "Street Lighting": [
        "Installation of solar street lights along {place}",
        "Replacement of old streetlights with LED fixtures near {place}",
        "Provision of high-mast lighting at the junction near {place}",
        "Installation of streetlights on the internal roads of {place}",
        "Repair and maintenance of the existing streetlight network at {place}",
        "Installation of decorative lighting at the public square near {place}",
        "Provision of solar lighting for the park at {place}",
        "Extension of the streetlight line to cover {place}",
    ],
    "Health Facility": [
        "Upgradation of the primary health centre at {place}",
        "Construction of a new sub-health centre building near {place}",
        "Provision of additional beds and OPD facilities at the health centre in {place}",
        "Installation of solar backup power at the health facility in {place}",
        "Construction of a boundary wall and drainage around the health centre at {place}",
        "Renovation of staff quarters attached to the health centre in {place}",
        "Procurement of diagnostic equipment for the health centre at {place}",
        "Construction of an ambulance parking bay at the health centre near {place}",
    ],
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
    place = f"{fake.street_name()}, {district}"
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
    description = random.choice(WORK_TEMPLATES[category]).format(place=place)

    return {
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
