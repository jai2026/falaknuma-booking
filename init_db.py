
from database import get_connection

conn = get_connection()
cursor = conn.cursor()

# Create the rooms table
cursor.execute("""
CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price INTEGER NOT NULL CHECK(price >= 0),
    guests INTEGER NOT NULL CHECK(guests > 0),
    size TEXT NOT NULL,
    bed TEXT NOT NULL,
    image TEXT NOT NULL,
    description TEXT NOT NULL,
    total_rooms INTEGER NOT NULL DEFAULT 1
        CHECK(total_rooms >= 0)
)
""")

# Create amenities table
cursor.execute("""
CREATE TABLE IF NOT EXISTS room_amenities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    amenity_name TEXT NOT NULL,
    FOREIGN KEY (room_id)
        REFERENCES rooms(id)
        ON DELETE CASCADE
)
""")

rooms = [
    (
        1,
        "Palace Room",
        "THE CLASSIC COLLECTION",
        35000,
        2,
        "45 m²",
        "King Size Bed",
        "images/palace-room.jpg",
        "Discover timeless elegance in our Palace Room, "
        "featuring heritage-inspired interiors, "
        "beautiful furnishings and modern comfort.",
        8
    ),
    (
        2,
        "Royal Suite",
        "THE ROYAL COLLECTION",
        55000,
        3,
        "75 m²",
        "King Size Bed",
        "images/royal-suite.jpg",
        "Experience royal luxury in our Royal Suite, "
        "with spacious interiors, elegant furnishings "
        "and a relaxing atmosphere.",
        5
    ),
    (
        3,
        "Grand Royal Suite",
        "THE SIGNATURE COLLECTION",
        85000,
        4,
        "110 m²",
        "King Size Bed",
        "images/grand-royal-suite.jpg",
        "Enter a world of exceptional grandeur in "
        "our Grand Royal Suite, combining magnificent "
        "spaces with refined luxury.",
        3
    )
]

cursor.executemany("""
INSERT OR IGNORE INTO rooms (
    id, name, category, price, guests,
    size, bed, image, description, total_rooms
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", rooms)

amenities = {
    1: [
        "King Size Bed",
        "Complimentary Wi-Fi",
        "Air Conditioning",
        "Luxury Bathroom",
        "Flat Screen TV",
        "24-Hour Room Service"
    ],
    2: [
        "King Size Bed",
        "Separate Sitting Area",
        "Complimentary Wi-Fi",
        "Luxury Bathroom",
        "Smart Television",
        "24-Hour Room Service"
    ],
    3: [
        "King Size Bed",
        "Private Living Area",
        "Complimentary Wi-Fi",
        "Premium Bathroom",
        "Smart Television",
        "24-Hour Room Service"
    ]
}

for room_id, items in amenities.items():

    existing = cursor.execute(
        "SELECT COUNT(*) FROM room_amenities WHERE room_id = ?",
        (room_id,)
    ).fetchone()[0]

    if existing == 0:
        cursor.executemany(
            """
            INSERT INTO room_amenities
            (room_id, amenity_name)
            VALUES (?, ?)
            """,
            [(room_id, item) for item in items]
        )

conn.commit()
conn.close()

print("Database initialized successfully!")
print("3 room categories added to hotel.db")