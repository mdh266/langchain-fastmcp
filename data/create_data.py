import geopandas as gpd
import re 

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


def precinct_data():
    # Read the GeoJSON file and select only the relevant columns
    df = gpd.read_file("NYPD_Sectors_20260507.geojson")[
        ["pct", "sector", "geometry"]
    ]
    
    # Save the DataFrame to a Parquet file
    df.to_parquet("NYPD_Sectors_20260507.parquet")


