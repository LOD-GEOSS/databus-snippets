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

The base for any usage is the ID of a file on the [Databus](https://databus.dbpedia.org/), like https://databus.dbpedia.org/denis/lod-geoss-example/api-example/2021-06-22/api-example_type=turbineData.json. The general usage can then be done in a few steps:

#### Step 0.5: Load the Open Energy Ontology as a Graph Object

For this the script contains the simple function `oeo = load_oeo()`.

#### Step 1: Load the Metadata about the columns from the Databus (Mods)

This can be done with the function `col_info_mapping = get_columns_from_databus(file_id)` which returns a dictionary with column-label (same as column name in the table) -> ColumnInfo (dataclass containing metadata, like description, unit, about etc.). 

#### Step 2: Load the actual data as JSON from the Databus

This can easily be done by just accessing the FileID, the function `load_json(file_id)` directly parses it into Python JSON representation.

#### Step 3: Generate a pandas Dataframe based on the Data, the Columns and the OEO

For this the function `get_dataframe_with_mapped_columns(data, col_info_mapping, oeo, lang)` can be used. Currently the Column name gets transformed to the `rdfs:label` of the class listed in about (see ColumnInfo) in the language passed as `lang` and the resource identifier of the class.
