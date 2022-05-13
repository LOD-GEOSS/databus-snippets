import pathlib
import requests
import datetime as dt
from bs4 import BeautifulSoup

from dev_databus_api_example import (
    DataGroup,
    DataVersion,
    DatabusFile,
    deploy_to_databus,
    API_KEY,
    ACCOUNT_NAME,
)


OEP_FOLDER = pathlib.Path(__file__).parent

OEP_URL = "https://openenergy-platform.org"

GROUP = "OEP"

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
    "supply",
]


def get_tables(schema):
    schema_url = f"{OEP_URL}/dataedit/view/{schema}"
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
    meta_url = f"{OEP_URL}/api/v0/schema/{schema}/tables/{table}/meta"
    response = requests.get(meta_url)
    return response.json()


def create_databus_group():
    databus_group = DataGroup.from_yaml(OEP_FOLDER / "oep_group.yaml")
    databus_group.id = GROUP
    deploy_to_databus(API_KEY, databus_group)


def register_oep_tables():
    for schema_name in SCHEMAS:
        for table_name in get_tables(schema_name):
            metadata = get_table_meta(schema_name, table_name)

            files = [
                DatabusFile(
                    f"{OEP_URL}/api/v0/schema/{schema_name}/tables/{table_name}/rows/",
                    cvs={},
                    file_ext="json",
                )
            ]

            databus_version = DataVersion(
                account_name=ACCOUNT_NAME,
                group=GROUP,
                artifact=table_name,
                version=dt.date.today().isoformat(),
                title=metadata["title"],
                abstract=metadata["context"]["documentation"],
                description=metadata["description"],
                license=metadata["license"]["name"],
                databus_files=files,
            )

            deploy_to_databus(API_KEY, databus_version)


if __name__ == "__main__":
    create_databus_group()
    register_oep_tables()
