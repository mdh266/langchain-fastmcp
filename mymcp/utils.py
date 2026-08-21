import os
from pymongo import MongoClient
from pymongo.server_api import ServerApi


def get_mongo_client() -> MongoClient:
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
    # print(f"Connecting to MongoDB @ {uri}")   # optional sanity‑check

    return MongoClient(uri, server_api=ServerApi("1"))

