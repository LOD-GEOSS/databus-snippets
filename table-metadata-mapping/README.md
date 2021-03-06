# Generating a pandas DataFrame/a csv with labels from the OEO

A simple python script for generating a pandas DataFrame / a CSV file with column names derived from the OEO, using the Databus and DBpedia Archivo.

## Setup

Requirements: python 3.9

Start in this directory and run:
```
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

## Usage

The base for any usage is the ID of a file on the [Databus](https://databus.dbpedia.org/), like https://databus.dbpedia.org/denis/lod-geoss-example/api-example/2021-06-22/api-example_type=turbineData.json. The general usage can then be done in two steps:

#### Step 1: Generate the MetadataContext

Initiate an object of the class with `metadata_context = MetadataContext(ontology_uri)`. This will provide the functionality for combining the Databus with mods and the given ontology.
Paramters:

- `ontology_uri`: The URI of the onology. Note that the FULL RDF content needs to be available from there.
- `metadata_endpoint`: SPARQL endpoint where the metadata (in context with the Databus Identifier) is stored. Defaul is the mods metadata endpoint.

**Example:** Load the context with the OEO from Archivo: 
```
metadata_context = MetadataContext("https://archivo.dbpedia.org/download?o=http%3A//openenergy-platform.org/ontology/oeo/&f=ttl&v=2021.05.03-181314")
```

#### Step 2: Generate a pandas dataframe of a file on the Databus 

A dataframe of a certain file on the Databus can be generated by calling `df = metadata_context.gen_dataframe(file_id)`. Currently the mapping behavior is hardcoded to rreplace column titles with the label of the class the column is about with the classes `rdfs:label`.
Parameters:

- `file_id`: an URI of a file on the Databus (see above).
- `column_infos` *(Optional)*: If the metadata of the columns need to be used multiple times (e.g. for different versions of the same file) they can first be generated by calling `column_infos = metadata_context.get_columns_from_databus(file_id)` and passed by calling `df = metadata_context.gen_dataframe(file_id, column_infos=column_infos)`. 
- `lang` *(Optional)*: Use a language constraint on the values returned from the ontology. Default is `"en"`.

**Example:** Generate a dataframe of the turbine data deployed to the Databus: 
```
turbine_df = metadata_context.gen_dataframe("https://databus.dbpedia.org/denis/lod-geoss-example/api-example/2021-05-10/api-example_type=turbineData.json")
```
