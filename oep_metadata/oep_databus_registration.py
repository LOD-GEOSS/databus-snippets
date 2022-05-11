
import requests
from bs4 import BeautifulSoup


OEP_URL = "https://openenergy-platform.org"

SCHEMAS = [
    "boundaries",
    "climate",
    "demand",
    "economy",
    "environment",
    "grid",
    "model_draft",
    "openstreetmap",
    "policy",
    "reference",
    "scenario",
    "society",
    "supply"
]


def get_tables(schema):
    schema_url = f'https://openenergy-platform.org/dataedit/view/{schema}'
    html = requests.get(schema_url).content
    soup = BeautifulSoup(html, features="html.parser")
    table = soup.find(id="tables")
    rows = table.find_all("tr")
    for row in rows:
        if "onclick" not in row.attrs:
            continue
        raw_url = row.attrs["onclick"].split("'")[1]
        yield raw_url.split("/")[-1]


def get_table_meta(schema, table):
    meta_url = f"https://openenergy-platform.org/api/v0/schema/{schema}/tables/{table}/meta"
    response = requests.get(meta_url)
    return response.json()


if __name__ == "__main__":
    for s in SCHEMAS:
        for t in get_tables(s):
            metadata = get_table_meta(s, t)
            print(metadata)
