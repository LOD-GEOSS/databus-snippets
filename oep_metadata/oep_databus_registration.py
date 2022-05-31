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
    DatabusError
)
from moss import submit_metadata_to_moss


class MetadataError(Exception):
    """Raised if metadata is invalid"""


OEP_FOLDER = pathlib.Path(__file__).parent

OEP_URL = "https://openenergy-platform.org"

GROUP = "OEP"
GROUP_YAML = OEP_FOLDER / "oep_group.yaml"

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
    databus_group = DataGroup.from_yaml(GROUP_YAML)
    databus_group.id = GROUP
    deploy_to_databus(API_KEY, databus_group)


def register_oep_table(schema_name, table_name):
    metadata = get_table_meta(schema_name, table_name)

    if len(metadata) == 0:
        raise MetadataError(f"Metadata for table '{schema_name}.{table_name}' is empty.")
    abstract = metadata.get("context", {}).get("documentation", "")
    if not abstract:
        raise MetadataError(f"Abstract for table '{schema_name}.{table_name}' is empty.")
    try:
        license_ = metadata["licenses"][0]["path"]
    except (IndexError, KeyError) as e:
        raise MetadataError(f"No license found for for table '{schema_name}.{table_name}'.") from e

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
        abstract=abstract,
        description=metadata.get("description", ""),
        license=license_,
        databus_files=files,
    )

    deploy_to_databus(API_KEY, databus_version)

    # Get file identifier:
    databus_identifier = f"{databus_version.version_uri}/{databus_version.artifact}_{files[0].id_string}"
    submit_metadata_to_moss(databus_identifier, metadata)


def register_oep_tables():
    for schema_name in SCHEMAS:
        for table_name in get_tables(schema_name):
            try:
                register_oep_table(schema_name, table_name)
            except (DatabusError, MetadataError) as e:
                print(f"{e}\nSkipping registration for table '{schema_name}.{table_name}'")


if __name__ == "__main__":
    create_databus_group()
    register_oep_tables()
