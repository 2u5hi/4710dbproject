import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "realestate.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def get_connection(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn):
    for table in ("sales", "properties", "buyers", "sellers", "agents"):
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()


# (a) Homes for sale in a given city within a price range.
def homes_for_sale_by_city_price(conn, city, low_price, high_price):
    return conn.execute(
        """
        SELECT p.property_id, p.address, p.city, p.list_price, p.bedrooms
        FROM   properties p
        LEFT JOIN sales s ON s.property_id = p.property_id
        WHERE  s.sale_id IS NULL                 -- still for sale
          AND  p.city = ?
          AND  p.list_price BETWEEN ? AND ?
        ORDER BY p.list_price
        """,
        (city, low_price, high_price),
    ).fetchall()


# (b) Homes for sale in a school district, 4+ bedrooms, no pool.
def homes_for_sale_by_district(conn, district, min_bedrooms=4, allow_pool=False):
    return conn.execute(
        """
        SELECT p.property_id, p.address, p.school_district,
               p.bedrooms, p.has_pool, p.list_price
        FROM   properties p
        LEFT JOIN sales s ON s.property_id = p.property_id
        WHERE  s.sale_id IS NULL
          AND  p.school_district = ?
          AND  p.bedrooms >= ?
          AND  p.has_pool = ?
        ORDER BY p.bedrooms DESC, p.list_price
        """,
        (district, min_bedrooms, 1 if allow_pool else 0),
    ).fetchall()


# (c) Agent who sold the most property (by total dollar value) in a given year.
def top_selling_agent(conn, year):
    return conn.execute(
        """
        SELECT a.agent_id, a.name,
               SUM(s.sale_price) AS total_value,
               COUNT(*)          AS num_sales
        FROM   sales s
        JOIN   agents a ON a.agent_id = s.selling_agent_id
        WHERE  strftime('%Y', s.sale_date) = ?
        GROUP BY a.agent_id, a.name
        ORDER BY total_value DESC
        LIMIT 1
        """,
        (str(year),),
    ).fetchone()


# (d) For each agent: avg selling price and avg days on market, for a year.
def agent_sales_stats(conn, year):
    return conn.execute(
        """
        SELECT a.agent_id, a.name,
               COUNT(*)                                             AS num_sales,
               ROUND(AVG(s.sale_price), 2)                          AS avg_price,
               ROUND(AVG(julianday(s.sale_date)
                         - julianday(p.listing_date)), 1)           AS avg_days_on_market
        FROM   sales s
        JOIN   properties p ON p.property_id = s.property_id
        JOIN   agents a     ON a.agent_id = s.selling_agent_id
        WHERE  strftime('%Y', s.sale_date) = ?
        GROUP BY a.agent_id, a.name
        ORDER BY avg_price DESC
        """,
        (str(year),),
    ).fetchall()


# (e) The most expensive house(s) in the database (returns rows incl. photo).
def most_expensive_houses(conn):
    return conn.execute(
        """
        SELECT property_id, address, city, list_price, photo
        FROM   properties
        WHERE  list_price = (SELECT MAX(list_price) FROM properties)
        ORDER BY property_id
        """
    ).fetchall()


# (f) Record the sale of a property that was listed as available.
def record_sale(conn, property_id, buyer_id, selling_agent_id,
                buyer_agent_id, sale_price, sale_date):
    already = conn.execute(
        "SELECT 1 FROM sales WHERE property_id = ?", (property_id,)
    ).fetchone()
    if already:
        raise ValueError("That property has already been sold.")
    cur = conn.execute(
        """
        INSERT INTO sales
            (property_id, buyer_id, selling_agent_id,
             buyer_agent_id, sale_price, sale_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (property_id, buyer_id, selling_agent_id,
         buyer_agent_id, sale_price, sale_date),
    )
    conn.commit()
    return cur.lastrowid


# (g) Add a new agent.
def add_agent(conn, name, phone, email):
    cur = conn.execute(
        "INSERT INTO agents (name, phone, email) VALUES (?, ?, ?)",
        (name, phone, email or None),
    )
    conn.commit()
    return cur.lastrowid



#   (a) city="Bethlehem", min/max price 200000/250000, status="for_sale"
#   (b) district="Parkland", min_bedrooms=4, has_pool=False, status="for_sale"
#   (e) sort results by price (desc) and open the top row to see its photo

def search_properties(conn, city=None, district=None, min_price=None,
                      max_price=None, min_bedrooms=None, has_pool=None,
                      status="for_sale"):
    clauses, params = [], []
    if city:
        clauses.append("p.city = ?"); params.append(city)
    if district:
        clauses.append("p.school_district = ?"); params.append(district)
    if min_price is not None:
        clauses.append("p.list_price >= ?"); params.append(min_price)
    if max_price is not None:
        clauses.append("p.list_price <= ?"); params.append(max_price)
    if min_bedrooms:
        clauses.append("p.bedrooms >= ?"); params.append(min_bedrooms)
    if has_pool is not None:
        clauses.append("p.has_pool = ?"); params.append(1 if has_pool else 0)
    if status == "for_sale":
        clauses.append("s.sale_id IS NULL")
    elif status == "sold":
        clauses.append("s.sale_id IS NOT NULL")

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT p.property_id, p.address, p.city, p.school_district,
               p.bedrooms, p.bathrooms, p.has_pool, p.list_price,
               p.listing_date, (p.photo IS NOT NULL) AS has_photo,
               s.sale_id, s.sale_price, s.sale_date
        FROM   properties p
        LEFT JOIN sales s ON s.property_id = p.property_id
        {where}
        ORDER BY p.list_price DESC
    """
    return conn.execute(sql, params).fetchall()


def get_property(conn, property_id):
    return conn.execute(
        """
        SELECT p.*,
               a.name  AS agent_name,
               se.name AS seller_name,
               s.sale_id, s.sale_price, s.sale_date,
               b.name  AS buyer_name
        FROM   properties p
        JOIN   agents  a  ON a.agent_id  = p.agent_id
        JOIN   sellers se ON se.seller_id = p.seller_id
        LEFT JOIN sales  s ON s.property_id = p.property_id
        LEFT JOIN buyers b ON b.buyer_id   = s.buyer_id
        WHERE  p.property_id = ?
        """,
        (property_id,),
    ).fetchone()


# Lookup helpers used to populate the GUI's dropdowns / lists


def list_cities(conn):
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT city FROM properties ORDER BY city")]


def list_districts(conn):
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT school_district FROM properties "
        "WHERE school_district IS NOT NULL ORDER BY school_district")]


def list_agents(conn):
    return conn.execute(
        "SELECT agent_id, name FROM agents ORDER BY name"
    ).fetchall()


def list_buyers(conn):
    return conn.execute(
        "SELECT buyer_id, name FROM buyers ORDER BY name"
    ).fetchall()


def list_properties_for_sale(conn):
    return conn.execute(
        """
        SELECT p.property_id, p.address, p.city, p.list_price
        FROM   properties p
        LEFT JOIN sales s ON s.property_id = p.property_id
        WHERE  s.sale_id IS NULL
        ORDER BY p.city, p.address
        """
    ).fetchall()


def table_counts(conn):
    """SELECT count(*) for each relation (a project turn-in item)."""
    counts = {}
    for t in ("agents", "sellers", "buyers", "properties", "sales"):
        counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    return counts
