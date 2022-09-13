
import os
import pathlib
import requests
import datetime as dt
from bs4 import BeautifulSoup

import databusclient
from databusclient_example import create_distribution  # in future from databusclient
from moss import submit_metadata_to_moss


class MetadataError(Exception):
    """Raised if metadata is invalid"""


API_KEY = os.environ["DATABUS_API_KEY"]
ACCOUNT_NAME = os.environ["DATABUS_ACCOUNT_NAME"]


OEP_FOLDER = pathlib.Path(__file__).parent

OEP_URL = "https://openenergy-platform.org"
DATABUS_URI_BASE = "https://energy.databus.dbpedia.org"

GROUP = "OEP"
GROUP_TITLE = "OEP Group"
GROUP_ABSTRACT = "OEP Group holds databus releases of OEP tables"
GROUP_DESCRIPTION = (
    "Tables in the OEP group have been released automatically to databaus "
    "via script oep_databus_registration.py from https://github.com/LOD-GEOSS/databus-snippets "
    "additionally related metadata has been released to MOSS (https://moss.tools.dbpedia.org)."
)

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
    metadata = response.json()

    if len(metadata) == 0:
        raise MetadataError(f"Metadata for table '{schema}.{table}' is empty.")

    abstract = metadata.get("context", {}).get("documentation", "")
    if not abstract:
        raise MetadataError(f"Abstract for table '{schema}.{table}' is empty.")

    try:
        license_ = metadata["licenses"][0]["path"]
    except (IndexError, KeyError):
        license_ = None
    if not license_:
        raise MetadataError(f"No license found for for table '{schema}.{table}'.")

    return metadata


def register_oep_table(schema_name, table_name):
    metadata = get_table_meta(schema_name, table_name)
    abstract = metadata["context"]["documentation"]
    license_ = metadata["licenses"][0]["path"]

    distributions = [
        create_distribution(
            url=f"{OEP_URL}/api/v0/schema/{schema_name}/tables/{table_name}/rows/",
            cvs={},
            file_format="json"
        )
    ]

    version_id = f"{DATABUS_URI_BASE}/{ACCOUNT_NAME}/{GROUP}/{table_name}/{dt.date.today().isoformat()}"
    dataset = databusclient.createDataset(
        version_id,
        title=metadata["title"],
        abstract=abstract,
        description=metadata.get("description", ""),
        license=license_,
        distributions=distributions,
        group_title=GROUP_TITLE,
        group_abstract=GROUP_ABSTRACT,
        group_description=GROUP_DESCRIPTION
    )

    databusclient.deploy(dataset, API_KEY)

    # Get file identifier:
    databus_identifier = f"{version_id}/{table_name}_.json"
    submit_metadata_to_moss(databus_identifier, metadata)


def register_oep_tables():
    for schema_name in SCHEMAS:
        for table_name in get_tables(schema_name):
            try:
                register_oep_table(schema_name, table_name)
            except MetadataError as e:
                print(f"{e}\nSkipping registration for table '{schema_name}.{table_name}'")


if __name__ == "__main__":
    register_oep_tables()
