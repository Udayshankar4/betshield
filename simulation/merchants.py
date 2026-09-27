"""
Fixed merchant registry for the simulation.

These represent the betting platforms (and one legitimate merchant, for
contrast) that agents transact with. IDs are hardcoded (not randomly
generated per run) so merchant identity is stable across simulation runs
and matches what gets loaded into the `merchants` table.
"""

MERCHANTS = [
    {
        "id": "b1000000-0000-0000-0000-000000000001",
        "name": "QuickWin Bets",
        "mcc_code": "7995",
        "payment_gateway_id": "PG-QW-01",
        "is_blacklisted": True,
        "app_package_name": "com.quickwinbets.app",
    },
    {
        "id": "b1000000-0000-0000-0000-000000000002",
        "name": "StarPlay Casino",
        "mcc_code": "7995",
        "payment_gateway_id": "PG-SP-02",
        "is_blacklisted": True,
        "app_package_name": "com.starplaycasino.app",
    },
    {
        "id": "b1000000-0000-0000-0000-000000000003",
        "name": "CityMart",
        "mcc_code": "5411",
        "payment_gateway_id": "PG-CM-03",
        "is_blacklisted": False,
        "app_package_name": None,
    },
]

BLACKLISTED_MERCHANTS = [m for m in MERCHANTS if m["is_blacklisted"]]
LEGIT_MERCHANTS = [m for m in MERCHANTS if not m["is_blacklisted"]]
