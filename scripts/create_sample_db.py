"""
Sample database seed script.

Creates a realistic e-commerce SQLite database with six related tables
and approximately 1,000 rows of deterministic sample data.  Intended to
be run once during initial setup.

Usage:
    python scripts/create_sample_db.py
"""

import os
import random
import sqlite3
from datetime import datetime, timedelta

# -- Configuration ------------------------------------------------------------

DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "sample.db")

# Fixed seed for reproducibility.
random.seed(42)


# -- Schema -------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE customers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    email       TEXT UNIQUE NOT NULL,
    city        TEXT,
    country     TEXT DEFAULT 'USA',
    joined_date TEXT NOT NULL
);

CREATE TABLE products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    category_id INTEGER NOT NULL,
    price       REAL NOT NULL,
    stock       INTEGER DEFAULT 0,
    description TEXT,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    total       REAL NOT NULL,
    status      TEXT DEFAULT 'completed',
    order_date  TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE order_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id   INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity   INTEGER NOT NULL DEFAULT 1,
    price      REAL NOT NULL,
    FOREIGN KEY (order_id)   REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE reviews (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    rating      INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment     TEXT,
    review_date TEXT NOT NULL,
    FOREIGN KEY (product_id)  REFERENCES products(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);
"""


# -- Seed data ----------------------------------------------------------------

_CATEGORIES = [
    ("Electronics",      "Gadgets, devices, and accessories"),
    ("Books",            "Physical and digital books"),
    ("Clothing",         "Apparel and fashion items"),
    ("Home & Kitchen",   "Household and kitchen products"),
    ("Sports",           "Sports equipment and gear"),
    ("Toys",             "Toys and games for all ages"),
    ("Beauty",           "Skincare, makeup, and personal care"),
    ("Food & Beverages", "Snacks, drinks, and groceries"),
    ("Office Supplies",  "Stationery and office products"),
    ("Music",            "Instruments and music accessories"),
]

_FIRST_NAMES = [
    "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry",
    "Ivy", "Jack", "Karen", "Leo", "Mia", "Noah", "Olivia", "Pete",
    "Quinn", "Rachel", "Sam", "Tina", "Uma", "Victor", "Wendy", "Xander",
    "Yara", "Zane", "Aisha", "Brian", "Chloe", "Derek", "Elena", "Finn",
    "Gina", "Hugo", "Iris", "Jay", "Kira", "Liam", "Maya", "Nate",
    "Opal", "Paul", "Rosa", "Sean", "Tara", "Uri", "Vera", "Will",
    "Xena", "Yuri",
]

_LAST_NAMES = [
    "Johnson", "Smith", "Williams", "Brown", "Davis", "Miller", "Wilson",
    "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris",
    "Martin", "Thompson", "Garcia", "Martinez", "Robinson", "Clark",
]

_CITIES = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
    "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose",
    "Austin", "Seattle", "Denver", "Boston", "Portland", "Atlanta",
    "Miami", "Nashville",
]

# Product catalogue keyed by category_id (1-indexed).
_PRODUCTS_BY_CATEGORY: dict[int, list[tuple[str, float, int, str]]] = {
    1: [
        ("Wireless Headphones", 79.99, 150, "Premium Bluetooth headphones with noise cancellation"),
        ("USB-C Hub", 34.99, 200, "7-in-1 USB-C adapter for laptops"),
        ("Portable Charger", 29.99, 300, "10000mAh power bank"),
        ("Mechanical Keyboard", 89.99, 100, "RGB mechanical keyboard with Cherry switches"),
        ("Webcam HD", 49.99, 120, "1080p webcam with built-in microphone"),
        ("Wireless Mouse", 24.99, 250, "Ergonomic wireless mouse"),
        ("Monitor Stand", 39.99, 80, "Adjustable aluminum monitor stand"),
        ("Smart Watch", 149.99, 90, "Fitness tracker with heart rate monitor"),
        ("Bluetooth Speaker", 59.99, 110, "Waterproof portable speaker"),
        ("Laptop Stand", 44.99, 95, "Foldable aluminum laptop stand"),
    ],
    2: [
        ("Python Programming", 39.99, 200, "Complete guide to Python"),
        ("Data Science Handbook", 44.99, 150, "Practical data science with Python"),
        ("Machine Learning Basics", 49.99, 120, "Introduction to ML algorithms"),
        ("SQL Mastery", 34.99, 180, "Advanced SQL techniques"),
        ("Web Development", 29.99, 160, "Full-stack web development guide"),
        ("AI for Beginners", 24.99, 200, "Getting started with artificial intelligence"),
        ("Clean Code", 32.99, 170, "Writing maintainable code"),
        ("System Design", 42.99, 130, "Large-scale system design principles"),
        ("The Art of Problem Solving", 27.99, 140, "Critical thinking techniques"),
        ("Digital Marketing Guide", 22.99, 190, "Modern marketing strategies"),
    ],
    3: [
        ("Cotton T-Shirt", 19.99, 500, "100% organic cotton t-shirt"),
        ("Denim Jeans", 49.99, 300, "Classic fit denim jeans"),
        ("Running Shoes", 89.99, 200, "Lightweight running shoes"),
        ("Winter Jacket", 129.99, 100, "Waterproof insulated jacket"),
        ("Baseball Cap", 14.99, 400, "Adjustable cotton cap"),
        ("Wool Sweater", 59.99, 150, "Merino wool pullover"),
        ("Cargo Shorts", 34.99, 250, "Multi-pocket cargo shorts"),
        ("Silk Scarf", 24.99, 180, "Elegant silk scarf"),
        ("Sneakers", 69.99, 220, "Casual everyday sneakers"),
        ("Formal Shirt", 44.99, 160, "Slim fit formal shirt"),
    ],
    4: [
        ("Coffee Maker", 69.99, 80, "12-cup programmable coffee maker"),
        ("Cutting Board Set", 24.99, 200, "Bamboo cutting board set"),
        ("Stainless Pot Set", 89.99, 60, "5-piece stainless steel cookware"),
        ("Blender", 44.99, 120, "High-speed countertop blender"),
        ("Toaster", 29.99, 150, "4-slice stainless steel toaster"),
        ("Kitchen Scale", 19.99, 180, "Digital food scale"),
        ("Storage Containers", 22.99, 250, "10-piece food storage set"),
        ("Wine Glasses Set", 34.99, 100, "Set of 6 crystal wine glasses"),
        ("Cast Iron Skillet", 39.99, 90, "Pre-seasoned 12-inch skillet"),
        ("French Press", 27.99, 140, "Stainless steel French press"),
    ],
    5: [
        ("Yoga Mat", 29.99, 200, "Non-slip exercise mat"),
        ("Resistance Bands", 14.99, 300, "Set of 5 resistance bands"),
        ("Water Bottle", 12.99, 500, "32oz insulated water bottle"),
        ("Dumbbells Set", 79.99, 80, "Adjustable dumbbell set"),
        ("Jump Rope", 9.99, 400, "Speed jump rope"),
        ("Tennis Racket", 59.99, 100, "Lightweight graphite racket"),
        ("Soccer Ball", 24.99, 150, "Official size soccer ball"),
        ("Gym Bag", 34.99, 200, "Large capacity sport duffel bag"),
        ("Foam Roller", 19.99, 180, "High-density foam roller"),
        ("Boxing Gloves", 39.99, 120, "Training boxing gloves"),
    ],
    6: [
        ("Building Blocks Set", 29.99, 200, "500-piece building block set"),
        ("Board Game Collection", 24.99, 150, "Classic board game collection"),
        ("RC Car", 44.99, 100, "Remote control racing car"),
        ("Puzzle Set", 14.99, 250, "1000-piece jigsaw puzzle"),
        ("Play Dough Kit", 12.99, 300, "24-color play dough set"),
        ("Action Figure Set", 19.99, 200, "Set of 6 action figures"),
        ("Card Game Pack", 9.99, 350, "Family card game pack"),
        ("Stuffed Animal", 16.99, 250, "Large plush teddy bear"),
        ("Science Kit", 34.99, 120, "Kids chemistry experiment set"),
        ("Drone Mini", 49.99, 80, "Beginner-friendly mini drone"),
    ],
    7: [
        ("Moisturizer", 22.99, 200, "Daily hydrating face moisturizer"),
        ("Sunscreen SPF50", 14.99, 300, "Broad spectrum sunscreen"),
        ("Lip Balm Set", 9.99, 400, "Set of 4 organic lip balms"),
        ("Face Wash", 12.99, 250, "Gentle foaming face cleanser"),
        ("Hair Oil", 18.99, 180, "Argan hair treatment oil"),
        ("Hand Cream", 8.99, 350, "Shea butter hand cream"),
        ("Eye Cream", 29.99, 150, "Anti-aging eye cream"),
        ("Perfume", 59.99, 100, "Eau de parfum 50ml"),
        ("Shampoo", 11.99, 280, "Sulfate-free shampoo"),
        ("Face Mask Set", 16.99, 200, "10-pack sheet face masks"),
    ],
    8: [
        ("Coffee Beans", 16.99, 300, "Premium Arabica whole beans"),
        ("Green Tea Pack", 12.99, 250, "100 organic green tea bags"),
        ("Dark Chocolate Box", 19.99, 200, "Assorted dark chocolate box"),
        ("Trail Mix", 9.99, 400, "Mixed nuts and dried fruits"),
        ("Olive Oil", 14.99, 180, "Extra virgin olive oil 500ml"),
        ("Honey Jar", 11.99, 220, "Raw organic wildflower honey"),
        ("Protein Bars", 24.99, 300, "12-pack protein bars"),
        ("Hot Sauce Set", 18.99, 150, "Artisan hot sauce collection"),
        ("Granola", 8.99, 350, "Organic crunchy granola"),
        ("Sparkling Water", 6.99, 500, "12-pack sparkling water"),
    ],
    9: [
        ("Notebook Set", 12.99, 300, "3-pack lined notebooks"),
        ("Pen Set", 8.99, 400, "10-pack ballpoint pens"),
        ("Desk Organizer", 24.99, 150, "Bamboo desk organizer"),
        ("Sticky Notes", 6.99, 500, "12-pack colored sticky notes"),
        ("Paper Clips", 3.99, 600, "200 assorted paper clips"),
        ("Stapler", 9.99, 250, "Heavy-duty desktop stapler"),
        ("Whiteboard", 29.99, 100, "24x36 inch magnetic whiteboard"),
        ("File Folders", 7.99, 350, "25-pack manila file folders"),
        ("Desk Lamp", 34.99, 120, "LED adjustable desk lamp"),
        ("Calendar Planner", 14.99, 200, "2024 daily planner"),
    ],
    10: [
        ("Guitar Strings", 9.99, 300, "Set of 6 acoustic guitar strings"),
        ("Drum Sticks", 7.99, 250, "Pair of maple drum sticks"),
        ("Guitar Pick Set", 4.99, 500, "12-pack assorted guitar picks"),
        ("Ukulele", 49.99, 80, "Soprano ukulele for beginners"),
        ("Music Stand", 19.99, 150, "Foldable sheet music stand"),
        ("Capo", 8.99, 300, "Universal guitar capo"),
        ("Metronome", 14.99, 200, "Digital clip-on metronome"),
        ("Harmonica", 12.99, 180, "Key of C diatonic harmonica"),
        ("Tuner", 11.99, 250, "Clip-on chromatic tuner"),
        ("Piano Keyboard Cover", 16.99, 120, "Dust cover for 88-key piano"),
    ],
}

_REVIEW_COMMENTS: dict[int, list[str]] = {
    5: ["Excellent product!", "Love it!", "Highly recommend!", "Best purchase ever!", "Amazing quality!"],
    4: ["Very good product.", "Happy with my purchase.", "Good value for money.", "Would buy again."],
    3: ["It's okay.", "Average product.", "Does the job.", "Expected better quality."],
    2: ["Not great.", "Disappointing.", "Below expectations.", "Wouldn't recommend."],
    1: ["Terrible quality.", "Waste of money.", "Very disappointed.", "Broke after a week."],
}

_ORDER_STATUSES = [
    "completed", "completed", "completed", "completed",
    "shipped", "processing", "cancelled",
]


# -- Helpers ------------------------------------------------------------------


def _random_date(start: datetime, range_days: int) -> str:
    """Return a random date string within *range_days* of *start*."""
    return (start + timedelta(days=random.randint(0, range_days))).strftime("%Y-%m-%d")


# -- Main builder -------------------------------------------------------------


def create_database() -> None:
    """Create and populate the sample database at ``DB_PATH``."""
    os.makedirs(DB_DIR, exist_ok=True)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # -- Schema
    cursor.executescript(_SCHEMA_SQL)

    # -- Categories
    cursor.executemany(
        "INSERT INTO categories (name, description) VALUES (?, ?)",
        _CATEGORIES,
    )

    # -- Customers
    customers: list[tuple[str, str, str, str, str]] = []
    for first in _FIRST_NAMES:
        last = random.choice(_LAST_NAMES)
        email = f"{first.lower()}.{last.lower()}@email.com"
        city = random.choice(_CITIES)
        joined = _random_date(datetime(2022, 1, 1), 1000)
        customers.append((f"{first} {last}", email, city, "USA", joined))

    cursor.executemany(
        "INSERT INTO customers (name, email, city, country, joined_date) "
        "VALUES (?, ?, ?, ?, ?)",
        customers,
    )

    # -- Products
    products: list[tuple[str, int, float, int, str]] = []
    for cat_id, items in _PRODUCTS_BY_CATEGORY.items():
        for name, price, stock, desc in items:
            products.append((name, cat_id, price, stock, desc))

    cursor.executemany(
        "INSERT INTO products (name, category_id, price, stock, description) "
        "VALUES (?, ?, ?, ?, ?)",
        products,
    )

    # -- Orders and order items
    orders_data: list[tuple[int, float, str, str]] = []
    order_items_data: list[tuple[int, int, int, float]] = []
    order_id = 1

    for _ in range(200):
        customer_id = random.randint(1, len(customers))
        order_date = _random_date(datetime(2023, 6, 1), 500)
        status = random.choice(_ORDER_STATUSES)

        num_items = random.randint(1, 5)
        order_total = 0.0

        for _ in range(num_items):
            product_id = random.randint(1, len(products))
            quantity = random.randint(1, 3)
            unit_price = products[product_id - 1][2]
            line_total = round(unit_price * quantity, 2)
            order_total += line_total
            order_items_data.append((order_id, product_id, quantity, unit_price))

        orders_data.append((customer_id, round(order_total, 2), status, order_date))
        order_id += 1

    cursor.executemany(
        "INSERT INTO orders (customer_id, total, status, order_date) "
        "VALUES (?, ?, ?, ?)",
        orders_data,
    )
    cursor.executemany(
        "INSERT INTO order_items (order_id, product_id, quantity, price) "
        "VALUES (?, ?, ?, ?)",
        order_items_data,
    )

    # -- Reviews
    reviews_data: list[tuple[int, int, int, str, str]] = []
    for _ in range(150):
        product_id = random.randint(1, len(products))
        customer_id = random.randint(1, len(customers))
        rating = random.choices([1, 2, 3, 4, 5], weights=[5, 10, 20, 35, 30])[0]
        comment = random.choice(_REVIEW_COMMENTS[rating])
        review_date = _random_date(datetime(2023, 8, 1), 500)
        reviews_data.append((product_id, customer_id, rating, comment, review_date))

    cursor.executemany(
        "INSERT INTO reviews (product_id, customer_id, rating, comment, review_date) "
        "VALUES (?, ?, ?, ?, ?)",
        reviews_data,
    )

    conn.commit()
    conn.close()

    # -- Summary
    print(f"Sample database created at: {DB_PATH}")
    print(f"  Categories:  {len(_CATEGORIES)}")
    print(f"  Customers:   {len(customers)}")
    print(f"  Products:    {len(products)}")
    print(f"  Orders:      {len(orders_data)}")
    print(f"  Order items: {len(order_items_data)}")
    print(f"  Reviews:     {len(reviews_data)}")


if __name__ == "__main__":
    create_database()
