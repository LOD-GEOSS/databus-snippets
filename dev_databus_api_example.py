import requests
import json
import hashlib
import sys
import yaml
from datetime import datetime
from dataclasses import dataclass, field
from typing import List

DATABUS_URI_BASE = "https://energy.databus.dbpedia.org"

post_databus_uri = "https://energy.databus.dbpedia.org/system/publish"


@dataclass
class DataGroup:
    account_name: str
    id: str
    title: str
    abstract: str
    description: str
    context: str = "https://downloads.dbpedia.org/databus/context.jsonld"

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
        resp = requests.get(uri, **kwargs)
        if resp.status_code > 400:
            print(f"ERROR for {uri} -> Status {str(resp.status_code)}")

        self.sha256sum = hashlib.sha256(bytes(resp.content)).hexdigest()
        self.content_length = str(len(resp.content))
        self.file_ext = file_ext
        self.id_string = "_".join(
            [f"{k}={v}" for k, v in cvs.items()]) + "." + file_ext


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
    context: str = "https://downloads.dbpedia.org/databus/context.jsonld"

    def get_target_uri(self):

        return f"{DATABUS_URI_BASE}/{self.account_name}/{self.group}/{self.artifact}/{self.version}"

    def __dbfiles_to_dict(self):

        for dbfile in self.databus_files:
            file_dst = {
                "@id": self.version_uri + "#" + dbfile.id_string,
                "file": self.version_uri + "/" + self.artifact + "_" + dbfile.id_string,
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

    def to_jsonld(self, **kwargs) -> str:
        self.version_uri = (
            f"{DATABUS_URI_BASE}/{self.account_name}/{self.group}/{self.artifact}/{self.version}"
        )
        self.data_id_uri = self.version_uri + "#Dataset"

        self.artifact_uri = (
            f"{DATABUS_URI_BASE}/{self.account_name}/{self.group}/{self.artifact}"
        )

        self.group_uri = f"{DATABUS_URI_BASE}/{self.account_name}/{self.group}"

        self.timestamp = self.issued.strftime("%Y-%m-%dT%H:%M:%SZ")

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
                    "distribution": [d for d in self.__dbfiles_to_dict()],
                }
            ],
        }

        return json.dumps(data_id_dict)


def deploy_to_databus(user: str, passwd: str, *databus_objects):
    try:
        # Request data for bearer token
        data = {
            "client_id": "upload-api",
            "username": user,
            "password": passwd,
            "grant_type": "password",
        }

        # requesting the bearer token and saving it in a variable
        print("Accessing new token...")
        token_response = requests.post(
            "https://databus.dbpedia.org/auth/realms/databus/protocol/openid-connect/token",
            data=data,
        )
        print(f"Response: Status {token_response.status_code}")

        token = token_response.json()["access_token"]

    except Exception as e:
        print(f"Error requesting token: {str(e)}")
        sys.exit(1)

    for dbobj in databus_objects:
        # send the dataid as JSON-LD to the target
        # The Authorisation header must be set with "Bearer $TOKEN"
        # https://databus.dbpedia.org/account/group for group metadata
        # https://databus.dbpedia.org/account/group/artifact/version for Databus version
        headers = {"Authorization": "Bearer " + token}

        print(f"Deploying {dbobj.get_target_uri()}")
        response = requests.put(
            dbobj.get_target_uri(), headers=headers, data=dbobj.to_jsonld()
        )
        print(
            f"Response: Status {response.status_code}; Text: {response.text}")


def deploy_to_dev_databus(api_key: str, *databus_objects):

    for dbobj in databus_objects:
        print(f"Deploying {dbobj.get_target_uri()}")
        submission_data = dbobj.to_jsonld()

        resp = requests.put(dbobj.get_target_uri(), headers={
                            "X-API-Key": api_key, "Content-Type": "application/json"}, data=submission_data)

        if resp.status_code >= 400:
            print(f"Response: Status {resp.status_code}; Text: {resp.text}")

            print(f"Problematic file:\n {submission_data}")


def deploy_to_dev_databus_post(api_key: str, *databus_objects):

    for dbobj in databus_objects:
        print(f"Deploying {dbobj.get_target_uri()}")
        submission_data = dbobj.to_jsonld()

        resp = requests.post(post_databus_uri, headers={
                             "X-API-Key": api_key, "Content-Type": "application/json"}, data=submission_data)

        print(f"Response: Status {resp.status_code}; Text: {resp.text}")

        if resp.status_code >= 400:
            print(f"Response: Status {resp.status_code}; Text: {resp.text}")

            print(f"Problematic file:\n {submission_data}")


if __name__ == "__main__":
    
    with open('config.yaml') as file:
        groupDataId = yaml.load(file, Loader=yaml.FullLoader)

    databus_groupy = groupDataId["group_info"]
    databus_versiony = groupDataId["dataid_info"]

    databus_version = DataVersion(
        account_name=databus_groupy["account_name"],
        group=databus_versiony["group"],
        artifact=databus_versiony["artifact"],
        version=databus_versiony["version"],
        title=databus_versiony["title"],
        abstract=databus_versiony["abstract"],
        description=databus_versiony["description"],
        license=databus_versiony["license"],
        databus_files=[DatabusFile(a, b, c) for a, b, c in databus_versiony["files"]],
    )

    databus_group = DataGroup(
        account_name=databus_groupy["account_name"],
        id=databus_versiony["group"],
        title=databus_groupy["title"],
        abstract=databus_groupy["abstract"],
        description=databus_groupy["description"],
    )

    # for the current version of the databus
    # deploy_to_databus(account_name, "af30133c-9f74-4619-9b71-fff56fbc22c0", databus_group, databus_version)

    # For the new version deployed to dev.databus.dbpedia.org
    # API KEY can be found or generated under https://dev.databus.dbpedia.org/{{user}}#settings
    deploy_to_dev_databus(groupDataId["api_key"], databus_group, databus_version)

