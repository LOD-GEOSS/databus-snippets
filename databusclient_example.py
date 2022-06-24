from databusclient import deploy, createDataset
from typing import Dict
import os
import yaml
import json

API_KEY = os.environ["DATABUS_API_KEY"]

ACCOUNT_NAME = os.environ["DATABUS_ACCOUNT_NAME"]

DATABUS_URI_BASE = "https://energy.databus.dbpedia.org"

# this will be in the next version from the databusclient package
def create_distribution(url: str, cvs: Dict[str, str], file_format: str=None, compression: str=None) -> str:
    """Creates the the identifier-string for a distribution used as downloadURLs in the createDataset function.
    url: is the URL of the dataset
    cvs: dict of content variants identifying a certain distribution (needs to be unique for each distribution in the dataset)
    file_format: identifier for the file format (e.g. json). If set to None client tries to infer it from the path
    compression: identifier for the compression format (e.g. gzip). If set to None client tries to infer it from the path   
    """

    meta_string = "_".join([f"{key}={value}" for key, value in cvs.items()])

    # check wether to add the custom file format
    if file_format is not None: 
        meta_string += f"|{file_format}"

    # check wether to addd the custom compression string
    if compression is not None: 
        meta_string += f"|{compression}"

    return f"{url}|{meta_string}"


def create_dataset_from_yaml(yaml_path: str):

    with open(yaml_path) as yamlfile:
        data = yaml.load(yamlfile, Loader=yaml.FullLoader)

    groupid = data["group"]["id"]
    artifactid = data["dataset"]["artifact"]
    version = data["dataset"]["version"]

    version_id = f"{DATABUS_URI_BASE}/{ACCOUNT_NAME}/{groupid}/{artifactid}/{version}"

    distribs = [create_distribution(url=dmap["url"], cvs=dmap["content_variants"], file_format=dmap.get("format", None), compression=dmap.get("compression", None)) for dmap in data["dataset"]["distributions"]]

    dataset = createDataset(versionId=version_id, 
        title=data["dataset"]["title"], 
        abstract=data["dataset"]["abstract"], 
        description=data["dataset"]["description"], 
        license=data["dataset"]["license"], 
        distributions=distribs,
        group_title=data["group"].get("title", None),
        group_abstract=data["group"].get("abstract", None),
        group_description=data["group"].get("description", None))

    return dataset


if __name__ == "__main__":
    dataset = create_dataset_from_yaml("./example/new_dataset.yml")
    deploy(dataset, API_KEY)