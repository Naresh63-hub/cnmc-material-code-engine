from src.persistence.database import engine
from sqlalchemy import text

with engine.connect() as connection:
    connection.execute(
        text("""
            UPDATE cnmc_registry
            SET canonical_description = :description
            WHERE cnmc_code = :cnmc_code
        """),
        {
            "description": "Flange Weld Neck Raised Face 150# ASTM A105 6IN ASME B16.5",
            "cnmc_code": "CNMC-000001",
        },
    )
    connection.commit()

print("CNMC-000001 canonical description updated.")