import argparse
import redis
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import geopandas as gpd
import pandas as pd
import os
import re
import json
from shapely.geometry import mapping
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
from utils import get_mongo_client


def get_precinct_number(label: str) -> int:
    """
    Return the precinct number from a string like "1st Precinct",
    "5th Precinct", etc.  The result is the digits only (e.g. 1, 5).
    """
    match = re.search(r"(\d+)", label)
    number = int(match.group(1)) if match else None
    extras = {"Midtown South Precinct": 14,
              "Midtown North Precinct": 18,
              "Central Park Precinct": 22}
    if number is None:
        number = extras.get(label)
    return number


def ingest_precint_info(path: str) -> None:
    df = (pd.read_csv(path)
            .assign(precinct_number=lambda df: df["Precinct"].apply(get_precinct_number))
            .drop(columns=["Precinct"]))

    precinct_dict = (df.groupby("precinct_number")
                    .apply(lambda x: x.to_dict(orient="records")[0])
                    .to_dict())

    r = redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=11170,
        decode_responses=True,
        username=os.getenv("REDIS_USERNAME"),
        password=os.getenv("REDIS_PASSWORD")
    )

    for precinct_number, precinct_info in precinct_dict.items():
        r.set(f"{precinct_number}", json.dumps(precinct_info, ensure_ascii=False))


def ingest_precinct_geometries(
        file_path: str,
        db_name: str,
        collection_name: str
    ) -> None:
    df = (gpd.read_file(file_path)
                [["sector", "pct", "geometry"]]
         .assign(precinct_number=lambda x: x["pct"].astype(int).astype(str))
         .assign(_id=lambda x: x["sector"])
         .assign(geom=lambda x: x["geometry"].apply(lambda g: {
                                                                "type": mapping(g)["type"],
                                                                "coordinates": mapping(g)["coordinates"]
                                           }))
         .drop(columns=["pct", "sector", "geometry"]))

    client = get_mongo_client()
    collection = client.get_database(db_name).get_collection(collection_name)
    collection.create_index([("geom", "2dsphere")])
    records = df.to_dict(orient="records")
    collection.insert_many(records)


def ingest_public_restrooms(
    file_path: str,
    db_name: str,
    collection_name: str,
) -> None:
    # Load the GeoJSON, clean up unnecessary columns, and construct a proper
    # GeoJSON geometry object under the ``geom`` field (type + coordinates).
    df = gpd.read_file(file_path)
    df = df.drop([col for col in df.columns if ':' in col], axis=1)
    # Convert Shapely geometry to a dict with required keys.
    df['geom'] = df.geometry.apply(lambda g: {
        "type": mapping(g)["type"],
        "coordinates": mapping(g)["coordinates"]
    })
    # Remove the original geometry column and any legacy coordinate columns.
    fin_df = df.drop(["geometry", "longitude", "latitude"], axis=1, errors='ignore')
    client = get_mongo_client()
    collection = client.get_database(db_name).get_collection(collection_name)
    collection.create_index([("geom", "2dsphere")])
    records = fin_df.to_dict(orient="records")
    collection.insert_many(records)



def main() -> None:
    # Resolve a sensible default data directory based on the script location.
    # This points to the repository's top‑level "data" folder, which works whether
    # the script is invoked from the project root or from the ``mymcp`` package.
    script_dir = os.path.abspath(os.path.dirname(__file__))
    default_data_dir = os.path.abspath(os.path.join(script_dir, "..", "data"))

    parser = argparse.ArgumentParser(description="Ingest data files into MongoDB.")
    parser.add_argument(
        "--data",
        type=str,
        default=default_data_dir,
        help="Directory containing data files (CSV, GeoJSON)."
    )
    args = parser.parse_args()
    data_dir = args.data


    ingest_precint_info(os.path.join(data_dir, "precinct.csv"))

    ingest_precinct_geometries(
        file_path=os.path.join(data_dir, "NYPD_Sectors_20260507.geojson"),
        db_name="nyc",
        collection_name="precincts"
    )

    ingest_public_restrooms(
        file_path=os.path.join(data_dir, "Public_Restrooms_20260508.geojson"),
        db_name="nyc",
        collection_name="restrooms"
    )


if __name__ == "__main__":
    main()
