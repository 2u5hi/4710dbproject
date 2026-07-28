"""Build realestate.db from scratch and populate it with synthetic data.
AI generation used for house blobs and sample data for efficiency. Opus 4.8
Run:  python seed.py

The data is hand-tuned so that every required query (a-g) returns an
"interesting" (non-empty) answer.  Only a few houses carry a photo BLOB
(the most expensive one always does, for query e).
"""

import io
import db
from PIL import Image, ImageDraw


# Photo generation:  a small, simple house illustration, PNG bytes (BLOB)

def make_house_png(wall_color, roof_color, sky_color=(135, 206, 235)):
    W, H = 320, 240
    img = Image.new("RGB", (W, H), sky_color)
    d = ImageDraw.Draw(img)

    d.rectangle([0, 180, W, H], fill=(86, 152, 72))          # grass
    d.rectangle([70, 110, 250, 200], fill=wall_color)         # wall
    d.polygon([(55, 110), (160, 45), (265, 110)], fill=roof_color)  # roof
    d.rectangle([140, 150, 180, 200], fill=(102, 61, 20))     # door
    d.ellipse([170, 172, 176, 178], fill=(240, 220, 60))      # doorknob
    d.rectangle([90, 130, 125, 160], fill=(180, 220, 240))    # window
    d.rectangle([195, 130, 230, 160], fill=(180, 220, 240))   # window
    d.ellipse([260, 25, 300, 65], fill=(255, 236, 120))       # sun

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def seed():
    conn = db.get_connection()
    db.init_schema(conn)

    # agents
    agents = [
        ("Kevin Nguyen",  "610-555-0101", "kevin@dnarealty.com"),
        ("Bob Saget",    "610-555-0102", "bob@dnarealty.com"),
        ("Phil Dunphy",    "610-555-0103", "phil@dnarealty.com"),
        ("Rick Sanchez",    "610-555-0104", "rick@dnarealty.com"),
        ("Gil Thorpe",   "610-555-0105", "gil@dnarealty.com"),
    ]
    conn.executemany(
        "INSERT INTO agents (name, phone, email) VALUES (?,?,?)", agents
    )

    # sellers
    sellers = [
        ("Frank Gallagher",   "610-555-0201"),
        ("Walter White",    "610-555-0202"),
        ("Jesse Pinkman",   "610-555-0203"),
        ("Jon Jones",    "610-555-0204"),
        ("Calvin Klein",    "610-555-0205"),
        ("Karen Black",   "610-555-0206"),
    ]
    conn.executemany("INSERT INTO sellers (name, phone) VALUES (?,?)", sellers)

    # buyers
    buyers = [
        ("Harry Potter",   "610-555-0301"),
        ("Miles Morales",    "610-555-0302"),
        ("Nina Dobrev",    "610-555-0303"),
        ("Jeff Goldblum",   "610-555-0304"),
        ("Peter Parker",   "610-555-0305"),
    ]
    conn.executemany("INSERT INTO buyers (name, phone) VALUES (?,?)", buyers)

    # photos (only a few houses; most expensive must have one)
    photo_mansion = make_house_png((225, 205, 160), (120, 40, 40))   # big/expensive
    photo_blue    = make_house_png((175, 200, 225), (60, 70, 110))
    photo_yellow  = make_house_png((240, 225, 150), (90, 110, 70))

    #properties
    #columns: address, city, district, beds, baths, pool, price, list_date,
    # photo, seller_id, agent_id
    properties = [
        # Bethlehem, in the 200k-250k  (query a hits these) - FOR SALE
        ("12 Maple St",     "Bethlehem", "Bethlehem Area", 3, 2.0, 0, 215000, "2004-03-10", None,          1, 1),
        ("48 Cedar Ave",    "Bethlehem", "Bethlehem Area", 4, 2.5, 0, 239000, "2004-05-02", photo_blue,    2, 2),
        # Bethlehem but outside the band (excluded from query a)
        ("9 Birch Ct",      "Bethlehem", "Bethlehem Area", 2, 1.0, 0, 172000, "2004-06-15", None,          3, 3),
        ("101 Summit Dr",   "Bethlehem", "Bethlehem Area", 5, 4.0, 1, 640000, "2004-01-20", photo_mansion, 4, 1),

        # Parkland district, 4+ beds, no pool (query b hits these) - FOR SALE
        ("77 Orchard Ln",   "Allentown", "Parkland",       4, 3.0, 0, 335000, "2004-04-11", None,          5, 4),
        ("5 Willow Way",    "Allentown", "Parkland",       5, 3.5, 0, 402000, "2004-02-28", photo_yellow,  6, 2),
        # Parkland but has a pool (excluded from query b)
        ("22 Pine Rd",      "Allentown", "Parkland",       4, 3.0, 1, 380000, "2004-07-01", None,          1, 5),
        # Parkland but only 3 beds (excluded from query b)
        ("3 Elm St",        "Allentown", "Parkland",       3, 2.0, 0, 260000, "2004-03-19", None,          2, 3),

        # Easton area (variety / sold homes)
        ("14 River Rd",     "Easton",    "Easton Area",    3, 2.0, 0, 245000, "2004-02-05", None,          3, 4),
        ("60 Hill St",      "Easton",    "Easton Area",    4, 2.5, 0, 298000, "2004-01-15", None,          4, 5),
        ("8 Front St",      "Easton",    "Easton Area",    3, 1.5, 0, 205000, "2003-11-10", None,          5, 1),
    ]
    conn.executemany(
        """INSERT INTO properties
           (address, city, school_district, bedrooms, bathrooms, has_pool,
            list_price, listing_date, photo, seller_id, agent_id)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        properties,
    )

    # sales (mostly in 2004; drives queries c and d)
    # A property_id here is SOLD, so it drops out of the "for sale" queries.
    # property_ids: 1..11 in insertion order above.
    # columns: property_id, buyer_id, selling_agent_id, buyer_agent_id,
    #          sale_price, sale_date
    sales = [
        # Bob (agent 2) has the highest total value in 2004.
        (9,  1, 2, 4, 241000, "2004-04-20"),   # 14 River Rd, listed 2004-02-05
        (10, 2, 2, 5, 292000, "2004-03-30"),   # 60 Hill St,  listed 2004-01-15
        # Kevin (agent 1)
        (11, 3, 1, None, 201000, "2004-01-05"),# 8 Front St,  listed 2003-11-10
        # Phil (agent 3)
        (3,  4, 3, 2, 168000, "2004-08-01"),   # 9 Birch Ct,  listed 2004-06-15
        # Rick (agent 4) - a 2003 sale, ignored by the 2004 queries
        (8,  5, 4, 1, 255000, "2003-12-15"),   # 3 Elm St
    ]
    conn.executemany(
        """INSERT INTO sales
           (property_id, buyer_id, selling_agent_id,
            buyer_agent_id, sale_price, sale_date)
           VALUES (?,?,?,?,?,?)""",
        sales,
    )

    conn.commit()

    counts = db.table_counts(conn)
    conn.close()
    print("Database built:", db.DB_PATH)
    for t, n in counts.items():
        print(f"  {t:<12} {n}")


if __name__ == "__main__":
    seed()
