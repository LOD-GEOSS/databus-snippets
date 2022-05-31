import requests
from urllib.parse import quote


MOSS_URL = "http://moss.tools.dbpedia.org/annotation-api-demo/submit"


class MossError(Exception):
    """Raised if submitting metadata to MOSS fails"""


def submit_metadata_to_moss(databus_identifier, metadata):
    # generate the URI for the request with the encoded identifier
    api_uri = f"{MOSS_URL}?id={quote(databus_identifier)}"
    response = requests.put(api_uri, headers={"Content-Type": "application/ld+json"}, json=metadata)
    if response.status_code != 200:
        raise MossError(
            f"Could not submit metadata for DI '{databus_identifier}' to MOSS. "
            f"Reason: {response.reason}"
        )
