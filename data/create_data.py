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


def get_precinct_number(label: str) -> int:                                                                                                          
    """                                                                                                                                              
    Return the precinct number from a string like "1st Precinct",                                                                                    
    "5th Precinct", etc.  The result is the digits only (e.g. 1, 5).                                                                             
    """                                                                                                                                              
    match = re.search(r"(\d+)", label)
    number = int(match.group(1)) if match else None     
    extras = {"Midtown South Precinct": 14,
              "Midtown North Precinct": 18,
              "Central Park Precinct": 22
              }
    if number is None:
        number = extras.get(label)                                                                                        
    return number


def _mongo_client() -> MongoClient:
    """
    Build a MongoClient using the credentials stored in .env.
    Returns a client connected to the `nyc` database (the same DB used by
    the precinct‑ingestion code).
    """
    mongo_username = os.getenv("MONGO_USERNAME")
    mongo_password = os.getenv("MONGO_PASSWORD")
    mongo_host = os.getenv("MONGO_HOST")

    # Example URI format used elsewhere in the project:
    #   mongodb+srv://<username>:<password>@<host>
    uri = f"mongodb+srv://{mongo_username}:{mongo_password}@{mongo_host}"
    print(f"Connecting to MongoDB @ {uri}")   # optional sanity‑check

    return MongoClient(uri, server_api=ServerApi("1"))


def ingest_precint_info(path: str) -> None:
    df = (pd.read_csv(path)
            .assign(precinct_number=lambda df: 
                            df["Precinct"].apply(get_precinct_number))
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
                [["sector", "pct","geometry"]]
         .assign(precinct_number=lambda x: x["pct"].astype(int).astype(str))
         .assign(_id=lambda x: x["sector"])
         .assign(geometry=lambda x: x["geometry"].apply(lambda g: {
                                                        "coordinates": mapping(g)["coordinates"]
                                           }))
         .drop(columns=["pct", "sector"])

    )
    client = _mongo_client()
    collection = client.get_database(db_name).get_collection(collection_name)
    collection.create_index([("geometry", "2dsphere")])
    records = df.to_dict(orient="records")
    results = collection.insert_many(records)   


def ingest_public_restrooms(
    file_path: str,
    db_name: str,
    collection_name: str,
) -> None:
    df = gpd.read_file(file_path)
    df = df.drop([col for col in df.columns if ':' in  col], axis=1)
    points_df = pd.DataFrame(df.geometry.apply(mapping).tolist())
    fin_df = df.join(points_df).drop(["geometry", "longitude", "latitude"], axis=1)
    client = _mongo_client()
    collection = client.get_database(db_name).get_collection(collection_name)
    collection.create_index([("geometry", "2dsphere")])
    records = fin_df.to_dict(orient="records")
    results = collection.insert_many(records)   


def main() -> None:
    ingest_precint_info("precinct.csv")
    
    ingest_precinct_geometries(
        file_path="./NYPD_Sectors_20260507.geojson",
        db_name="nyc",
        collection_name="precincts")
    
    ingest_public_restrooms(
        file_path="./Public_Restrooms_20260508.geojson",
        db_name="nyc",
        collection_name="restrooms")
    


if __name__ == "__main__":
    main()
