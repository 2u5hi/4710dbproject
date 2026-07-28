-- Database Systems Real Estate Project
-- Relational schema, implemented in SQLite.
--
-- Entity sets:  agents, sellers, buyers, properties
-- Relationship: sales  (a property is sold to a buyer, handled by agents)

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- people
-- ---------------------------------------------------------------------------
CREATE TABLE agents (
    agent_id INTEGER PRIMARY KEY,
    name     TEXT NOT NULL,
    phone    TEXT,
    email    TEXT UNIQUE
);

CREATE TABLE sellers (
    seller_id INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    phone     TEXT
);

CREATE TABLE buyers (
    buyer_id INTEGER PRIMARY KEY,
    name     TEXT NOT NULL,
    phone    TEXT
);

-- ---------------------------------------------------------------------------
-- property
-- ---------------------------------------------------------------------------
CREATE TABLE properties (
    property_id     INTEGER PRIMARY KEY,
    address         TEXT NOT NULL,
    city            TEXT NOT NULL,
    school_district TEXT,
    bedrooms        INTEGER,
    bathrooms       REAL,
    has_pool        INTEGER NOT NULL DEFAULT 0 CHECK (has_pool IN (0, 1)),
    list_price      REAL NOT NULL,
    listing_date    TEXT NOT NULL,          -- ISO 8601 'YYYY-MM-DD'
    photo           BLOB,                    -- null ok; only a few houses have images
    seller_id       INTEGER NOT NULL REFERENCES sellers(seller_id),
    agent_id        INTEGER NOT NULL REFERENCES agents(agent_id)   -- listing agent
);

-- ---------------------------------------------------------------------------
-- transaction: a property is sold at most once (property_id is UNIQUE),
-- so a property that has no matching sales row is still "for sale".
-- ---------------------------------------------------------------------------
CREATE TABLE sales (
    sale_id         INTEGER PRIMARY KEY,
    property_id     INTEGER NOT NULL UNIQUE REFERENCES properties(property_id),
    buyer_id        INTEGER NOT NULL REFERENCES buyers(buyer_id),
    selling_agent_id INTEGER NOT NULL REFERENCES agents(agent_id),
    buyer_agent_id  INTEGER REFERENCES agents(agent_id),   -- null ok
    sale_price      REAL NOT NULL,
    sale_date       TEXT NOT NULL           -- ISO 8601 'YYYY-MM-DD'
);

-- Helpful indices for the required queries.
CREATE INDEX idx_properties_city     ON properties(city);
CREATE INDEX idx_properties_district ON properties(school_district);
CREATE INDEX idx_sales_selling_agent ON sales(selling_agent_id);
CREATE INDEX idx_sales_date          ON sales(sale_date);
