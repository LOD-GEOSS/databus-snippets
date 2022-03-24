# Databus Snippets

This repository contains various examples for using the DBpedia Databus (https://databus.dbpedia.org/ and its newer version https://dev.databus.dbpedia.org/) and its ecosystem in the context of the [Open Energy Platform](https://openenergy-platform.org/).

## Folders & Files

- `databus_api_examples` contains examples of JSON-LD files required for submitting data to the Databus.
- `oep_metadata` contains an example of metadata about wind turbines (from [here](https://openenergy-platform.org/dataedit/view/supply/wind_turbine_library)) and an example how to convert the json file to JSON-LD.
- `databus_api_example.py` and `dev_databus_api_example.py` (for the new Databus version) are scripts mimicking the functionality of the [web submit form](https://databus.dbpedia.org/system/upload).



## Uploading to the DBpedia Databus

The requirement for uploading anything to the Databus is a Databus Account, you can create one at the [website](https://databus.dbpedia.org/auth/realms/databus/protocol/openid-connect/registrations?client_id=website&response_type=code&scope=openidemail&redirect_uri=https://databus.dbpedia.org&kc_locale=en) (newer version: https://dev.databus.dbpedia.org/).


### Option 1: Using the Web UI

The easiest way of deploying data to the Databus is by using the Web UI. It can be accessed [here](https://databus.dbpedia.org/system/upload) (for the new Databus version click [here](https://dev.databus.dbpedia.org/system/publish-wizard)).
It provides a straightforward UI for filling out the necessary URIs and other parameters to generate the DataID (i.e., the data to be uploaded).


### Option 2: Using the API

#### Step 1: Generating the DataID

If you want to submit content via API you need to create the DataID yourself. An example for the DataID can either be seen in the third step of Option 1 or in the example files in this repository. There are two seperate files:

  - The `group-metadata`: This is only documentation for the group, no file information is included here. An example can be seen in `databus_api_examples/group_docu.jsonld`.
  - The actual `DataID`: This tells the Databus the necessary metadata to publish on the databus. An example for this can be seen in `databus_api_examples/dataid_example.jsonld`.

The following table axplains the purpose and restrictions of the key in the JSON-LD file. It is based on the keys used in the examples in `databus_api_examples`. **NOTE**: The restrictions in this table are currently more strict then the actual live tests (e.g. a group is with underscores would work), but this may change in the future and being a bit more strict then necessary is usually better.

| Level | JSON key | Description | Restrictions |
--- | --- | --- | ---
| Group | id    | The identifier for the Group. | This will be part of the groups IRI and therefor needs to be safe for an URL. Allowed are lowercase characters  and -|
| Group | label | A human-readable name for the group.| At least 3 characters long, no further restrictions. | 
| Group | title | A name given to the group. In most cases its fine using the same as in label. | At least 3 characters long, no further restrictions. |
| Group | abstract | A short description of the group. A not too long, one line sentence about the group. | At least 25 characters long. |
| Group | comment | A short description of the group. Can be the same as abstract | At least 25 characters long. |
| Group | description | A longer and more detailed description of the purpose of the group | At least 25 characters long. |
| Artifact | id | The identifier for the Artifact. | This will be part of the groups IRI and therefor needs to be safe for an URL. Allowed are lowercase characters and -|
| Artifact | label | A human-readable name for the artifact.| At least 3 characters long, no further restrictions. | 
| Artifact | title | A name given to the artifact. In most cases its fine using the same as in label. | At least 3 characters long, no further restrictions. |
| Artifact | abstract | A short description of the artifact | A not too long, one line sentence about the group. | At least 25 characters long. |
| Artifact | comment | A short description of the artifact | Can be the same as abstract | At least 25 characters long. |
| Version | id | The identifier for the Version. | Commonly a version is identified by time (e.g. 2021-07-01) or with a semantic version (e.g. 1.2.1) | Limited to alphanumeric characters and `.-` | 
| Version | publisher | A link to a webid | Needs to be an valid WebID (check out [this](https://github.com/dbpedia/webid) for more) |
| Version | license | A URI of an license (like http://creativecommons.org/licenses/by/4.0/) | Needs to be a valid URI |
| Version | description | A longer and more detailed description of the purpose of the artifact |  At least 25 characters long. |




#### Step 2: Deploying to the Databus

For this another two steps are required:

1. Fetching a Bearer Token from the Databus (URI: https://databus.dbpedia.org/auth/realms/databus/protocol/openid-connect/token). This can be done by setting the following HTTP headers in a GET request:
    - 'client_id': 'upload-api'
    - 'username': '$USER' with user being the accountname of your account (can be seeen in the URI e.g. https://databus.dbpedia.org/denis)
    - 'grant_type': 'password' 
    - 'password': '$PASSWORD' with the password of said Databus Account

Example with curl: ```TOKEN=$(curl -s -d 'client_id=upload-api' -d 'username=XXXXXX' -d 'password=XXXXXXXXXXX' -d 'grant_type=password' https://databus.dbpedia.org/auth/realms/databus/protocol/openid-connect/token | cut -d'"' -f 4)```.

**NOTE**: A token has a lifetime of around 30 seconds.

2. Using said bearer token for deploying to the Databus. Deploy requests are HTTP PUT requests with the following header:
    - 'Authorization': 'Bearer $TOKEN' with the Token being the string returned from **Step 1**

The Target URI depends here on the type of graph you want to deploy:
    - For the group its http://databus.dbpedia.org/$USER/$GROUP
    - For the version DataID it is http://databus.dbpedia.org/$USER/$GROUP/$ARTIFACT/$VERSION

The Data is in both cases the fitting graph as JSON-LD. For testing with curl the graph can be minified with a tool like [this one](https://www.minifyjson.org/) and checked for validity with the [JSONLD playground](https://json-ld.org/playground/).

**Example with curl:**```curl -H '{Authorization: Bearer $TOKEN}' -X PUT <GROUP-OR-VERSION-URI> -d 'DATAID_JSONLD_CONTENT'```

### Option 3: Using the python3 script

An example implementation of using the API can be seen in `databus_api_example.py`. By modifying the variables below line `if __name__ == "__main__":` a DataID can easily be generated and deployed, similar to the WebUI. For the new Databus version the process is slightly different. Instead of modifying the hard-coded variables in a python script you simly modify the contents of `config.yaml` and then run `dev_databus_api_example.py`.
