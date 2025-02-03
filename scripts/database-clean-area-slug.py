#!/usr/bin/env python3
"""
Area Slug Update Script

This script updates the slugs in the Area table by:
1. Removing entries that are just continent codes (e.g., 'sa', 'na', 'eu')
2. Removing continent prefixes from other slugs (e.g., 'sa_br' -> 'br')
3. Updating administrative levels based on number of underscores in slug
4. Setting parent reference for top-level areas
5. Setting parent reference for country-level areas
6. Setting parent reference for Brazilian states
7. Setting parent reference for Brazilian municipalities
"""

import os
import dotenv
import psycopg2
from tqdm import tqdm

dotenv.load_dotenv()


def connect_db():
    """Establish a connection to the PostgreSQL database."""
    db = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )
    db.autocommit = True
    return db


def main():
    """Main function to execute the slug update process."""
    db = connect_db()
    cursor = db.cursor()

    # # First, delete continent-only entries
    continent_codes = ["sa", "na", "eu", "af", "as", "oc", "an"]
    # cursor.execute(
    #     'DELETE FROM area WHERE slug = ANY(%s)',
    #     (continent_codes,)
    # )
    # print(f"Deleted {cursor.rowcount} continent entries")

    # Then, update remaining entries to remove continent prefix
    cursor.execute("SELECT id, slug FROM area")
    areas = cursor.fetchall()

    print(f"Processing {len(areas)} areas...")
    for area_id, slug in tqdm(areas):
        try:
            # Split the slug and remove the continent prefix
            parts = slug.split("_")
            if len(parts) > 1 and parts[0] in continent_codes:
                new_slug = "_".join(parts[1:])
                cursor.execute("UPDATE area SET slug = %s WHERE id = %s", (new_slug, area_id))
        except Exception as e:
            print(f"Error updating area {area_id} with slug {slug}: {str(e)}")
            continue

    # Update administrative levels based on number of underscores in slug
    cursor.execute("SELECT id, slug FROM area")
    areas = cursor.fetchall()

    print("Updating administrative levels...")
    for area_id, slug in tqdm(areas):
        underscore_count = slug.count("_")
        admin_level = underscore_count
        cursor.execute(
            "UPDATE area SET administrative_level = %s WHERE id = %s", (admin_level, area_id)
        )

    # Add parent reference for top-level areas
    world_id = "21486514-209f-416f-b73c-30f41d07e059"
    country_id = "b9bfd6a6-bc3f-460c-8a93-f695891d64d3"
    print("Setting parent reference for top-level areas...")
    cursor.execute("UPDATE area SET parent_id = %s WHERE administrative_level = 0", (world_id,))
    print("Setting parent reference for country-level areas...")
    cursor.execute("UPDATE area SET entity_id = %s WHERE administrative_level = 0", (country_id,))
    print(f"Updated {cursor.rowcount} top-level areas with world parent reference")

    # First get Brazil's ID
    cursor.execute("SELECT id FROM area WHERE slug = %s", ("br",))
    brazil_id = cursor.fetchone()[0]
    state_entity_id = "839765a7-9c7a-44bd-bb88-357cedba03f6"

    print("Setting parent reference for Brazilian states...")
    cursor.execute(
        """
        UPDATE area 
        SET parent_id = %s,
            entity_id = %s
        WHERE slug LIKE 'br_%%'
        AND slug NOT LIKE '%%\_%%\_%%'
    """,
        (brazil_id, state_entity_id),
    )

    print(f"Updated {cursor.rowcount} Brazilian state areas")

    # First, let's check what we're working with
    cursor.execute(
        """
        SELECT slug 
        FROM area 
        WHERE slug LIKE 'br\_%%\_%%' 
        LIMIT 5;
    """
    )
    print("Sample municipality slugs:", cursor.fetchall())

    cursor.execute(
        """
        SELECT slug 
        FROM area 
        WHERE slug LIKE 'br\_%%' 
        AND slug NOT LIKE 'br\_%%\_%%'
        LIMIT 5;
    """
    )
    print("Sample state slugs:", cursor.fetchall())

    # Set municipality parents and entity
    municipality_entity_id = "460cf58b-63a7-4fb7-910f-4ca8ea58c25e"  # entity ID for municipalities
    print("Setting parent reference for Brazilian municipalities...")

    cursor.execute(
        """
        UPDATE area AS municipality
        SET parent_id = state.id,
            entity_id = %s
        FROM area AS state
        WHERE municipality.slug LIKE 'br\_%%\_%%'  -- Matches municipality pattern (2 underscores)
        AND state.slug = split_part(municipality.slug, '_', 1) || '_' || split_part(municipality.slug, '_', 2)  -- Gets state slug (e.g., 'br_sp')
        AND municipality.slug NOT LIKE '%%\_%%\_%%\_%%'  -- Ensures exactly 2 underscores
    """,
        (municipality_entity_id,),
    )

    print(f"Updated {cursor.rowcount} Brazilian municipality areas")

    db.commit()
    print("All done!")


if __name__ == "__main__":
    main()
