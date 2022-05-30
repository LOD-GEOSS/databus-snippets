import os
import requests
import json
import hashlib
import yaml
from datetime import datetime
from dataclasses import dataclass, field
from typing import List

DATABUS_URI_BASE = "https://energy.databus.dbpedia.org"
DEFAULT_CONTEXT = "https://downloads.dbpedia.org/databus/context.jsonld"

post_databus_uri = "https://energy.databus.dbpedia.org/system/publish"

API_KEY = os.environ["DATABUS_API_KEY"]
ACCOUNT_NAME = os.environ["DATABUS_ACCOUNT_NAME"]


class DatabusError(Exception):
    """Raised if deployment goes wrong"""


@dataclass
class DataGroup:
    account_name: str
    id: str
    title: str
    abstract: str
    description: str
    context: str = DEFAULT_CONTEXT

    @classmethod
    def from_yaml(cls, yaml_path):
        with open(yaml_path) as yaml_file:
            data = yaml.load(yaml_file, Loader=yaml.FullLoader)
            return cls(
                account_name=ACCOUNT_NAME,
                id=data["group"],
                title=data["title"],
                abstract=data["abstract"],
                description=data["description"],
            )

    def get_target_uri(self) -> str:
        return f"{DATABUS_URI_BASE}/{self.account_name}/{self.id}"

    def to_jsonld(self) -> str:
        """Generates the json representation of group documentation"""

        group_uri = f"{DATABUS_URI_BASE}/{self.account_name}/{self.id}"
        group_data_dict = {
            "@context": self.context,
            "@graph": [
                {
                    "@id": group_uri,
                    "@type": "dataid:Group",
                    "title": self.title,
                    "abstract": self.abstract,
                    "description": self.description,
                }
            ],
        }
        return json.dumps(group_data_dict)


class DatabusFile:
    def __init__(self, uri: str, cvs: dict, file_ext: str, **kwargs):
        """Fetches the necessary information of a file URI for the deploy to the databus."""
        self.uri = uri
        self.cvs = cvs
        print(f"Fetching data from '{uri}'")
        resp = requests.get(uri, **kwargs)
        if resp.status_code > 400:
            print(f"ERROR for {uri} -> Status {str(resp.status_code)}")

        self.sha256sum = hashlib.sha256(bytes(resp.content)).hexdigest()
        self.content_length = str(len(resp.content))
        self.file_ext = file_ext
        self.id_string = "_".join([f"{k}={v}" for k, v in cvs.items()]) + "." + file_ext


@dataclass
class DataVersion:
    account_name: str
    group: str
    artifact: str
    version: str
    title: str
    abstract: str
    description: str
    license: str
    databus_files: List[DatabusFile]
    issued: datetime = field(default_factory=datetime.now)
    context: str = DEFAULT_CONTEXT

    def __post_init__(self):
        self.version_uri = f"{DATABUS_URI_BASE}/{self.account_name}/{self.group}/{self.artifact}/{self.version}"
        self.data_id_uri = f"{self.version_uri}#Dataset"
        self.artifact_uri = (
            f"{DATABUS_URI_BASE}/{self.account_name}/{self.group}/{self.artifact}"
        )
        self.group_uri = f"{DATABUS_URI_BASE}/{self.account_name}/{self.group}"
        self.timestamp = self.issued.strftime("%Y-%m-%dT%H:%M:%SZ")

    @classmethod
    def from_yaml(cls, yaml_path):
        with open(yaml_path) as yaml_file:
            data = yaml.load(yaml_file, Loader=yaml.FullLoader)
            return cls(
                account_name=ACCOUNT_NAME,
                group=data["group"],
                artifact=data["artifact"],
                version=data["version"],
                title=data["title"],
                abstract=data["abstract"],
                description=data["description"],
                license=data["license"],
                databus_files=[DatabusFile(a, b, c) for a, b, c in data["files"]],
            )

    def get_target_uri(self):
        return f"{DATABUS_URI_BASE}/{self.account_name}/{self.group}/{self.artifact}/{self.version}"

    def __dbfiles_to_dict(self):
        for dbfile in self.databus_files:
            file_dst = {
                "@id": f"{self.version_uri}#{dbfile.id_string}",
                "file": f"{self.version_uri}/{self.artifact}_{dbfile.id_string}",
                "@type": "dataid:Part",
                "formatExtension": dbfile.file_ext,
                "compression": "none",
                "downloadURL": dbfile.uri,
                "byteSize": dbfile.content_length,
                "sha256sum": dbfile.sha256sum,
            }

            for key, value in dbfile.cvs.items():
                file_dst[f"dcv:{key}"] = value

            yield file_dst

    def to_jsonld(self) -> str:
        data_id_dict = {
            "@context": self.context,
            "@graph": [
                {
                    "@type": "dataid:Dataset",
                    "@id": self.data_id_uri,
                    "hasVersion": self.version,
                    "issued": self.timestamp,
                    "title": self.title,
                    "abstract": self.abstract,
                    "description": self.description,
                    "license": self.license,
                    "distribution": list(self.__dbfiles_to_dict()),
                }
            ],
        }
        return json.dumps(data_id_dict)


def deploy_to_databus(api_key: str, databus_object):
    target = databus_object.get_target_uri()
    print(f"Deploying {target}")
    submission_data = databus_object.to_jsonld()

    resp = requests.put(
        target,
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        data=submission_data,
    )

    if resp.status_code >= 400:
        print(f"Response: Status {resp.status_code}; Text: {resp.text}")
        print(f"Problematic file:\n {submission_data}")
        raise DatabusError(f"Could not deploy '{target}'")


if __name__ == "__main__":
    databus_group = DataGroup.from_yaml("example/group.yaml")
    databus_version = DataVersion.from_yaml("example/data.yaml")

    # For the new version deployed to dev.databus.dbpedia.org
    # API KEY can be found or generated under https://dev.databus.dbpedia.org/{{user}}#settings
    deploy_to_databus(API_KEY, databus_group)
    deploy_to_databus(API_KEY, databus_version)
