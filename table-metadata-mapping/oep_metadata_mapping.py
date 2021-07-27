from rdflib import Graph, RDFS, RDF, URIRef
from rdflib.namespace import DCTERMS, XSD
import requests
import re
from typing import Dict
import pandas as pd
from dataclasses import dataclass
from SPARQLWrapper import SPARQLWrapper, JSON

# A stable identifier for the complete oeo on archivo
oeo_uri = "https://archivo.dbpedia.org/download?o=http%3A//openenergy-platform.org/ontology/oeo/&f=ttl&v=2021.05.03-181314"

# A regex for separating databus metadata info (publisher, artifact etc) from the identifier
databus_file_id_regex = re.compile(
    r"https://databus\.dbpedia\.org/(.*?)/(.*?)/(.*?)/(.*?)/(.*)"
)

mod_endpoint = "https://mods.tools.dbpedia.org/sparql"

# A namespace mapping for easier querying
ns_mapping = {
    "rdfs": RDFS,
    "oeo": URIRef("http://openenergy-platform.org/ontology/oeo/"),
    "rdf": RDF,
    "obo": URIRef("http://purl.obolibrary.org/obo/"),
    "csvw": URIRef("http://www.w3.org/ns/csvw#"),
    "xsd": XSD,
    "dct": DCTERMS,
}


@dataclass
class ColumnInfo:
    """A simple datacass for the information of a certain column"""
    label: str
    description: str
    unit: str
    datatype: str
    about: str

def return_entry(o):
    if o == "None":
        return None
    else:
        return str(o)

def load_oeo() -> Graph:
    """loads the oeo in a rdflib graph"""
    g = Graph()
    g.load(oeo_uri, format="turtle")
    return g


def load_json(uri: str) -> Dict:
    """Loads a json file"""
    res = requests.get(uri)
    return res.json()


def get_label_of_resource(resource_uri: str, g: Graph, lang: str = "en") -> str:
    """Queries a graph g for the label of a given resource_uri. lang can be specified, default is en. Returns the first found label"""

    query_string = f"""SELECT ?label WHERE {{
        <{resource_uri}> rdfs:label ?label .
        FILTER(LANG(?label) = "{lang}")
    }}"""

    result = g.query(query_string, initNs=ns_mapping)

    if result is not None and len(result) > 0:
        for row in result:
            return str(row[0])
    else:
        return None


def load_metadata_from_moss(file_id: str) -> Graph:
    """Loads the annotated moss metdata for a given databus file_id. Returns a rdflib Graph"""

    m = databus_file_id_regex.match(file_id)

    if m is None:
        raise RuntimeError("Not a valid databus identifier")

    pub, group, artifact, version, filename = m.groups()

    metadata_uri = f"https://moss.tools.dbpedia.org/data/{pub}/{group}/{artifact}/{version}/{filename}/api-demo-data.ttl"

    g = Graph()
    g.load(metadata_uri, format="turtle")
    return g


def get_columns_from_metadata(g: Graph) -> Dict[str, ColumnInfo]:
    """Returns a dict with column_name -> column info from the metadata submitted to moss"""

    query_string = f"""SELECT ?label ?description ?unit ?datatype ?about WHERE {{
        ?fileid csvw:table/csvw:tableSchema ?tableSchema .
        OPTIONAL {{ ?tableSchema csvw:column ?col . }}
        OPTIONAL {{ ?col rdfs:label ?label . }}
        OPTIONAL {{ ?col oeo:OEO_00040010 ?unit . }}
        OPTIONAL {{ ?col dct:description ?description . }}
        OPTIONAL {{ ?col csvw:datatype ?datatype . }}
        OPTIONAL {{ ?col obo:IAO_0000136 ?about . }}
    }}
    """
    print(query_string)
    result = g.query(query_string, initNs=ns_mapping)

    result_map = {}

    for row in result:
        result_as_str = list(map(return_entry, row))
        result_map[result_as_str[0]] = ColumnInfo(
            result_as_str[0],
            result_as_str[1],
            result_as_str[2],
            result_as_str[3],
            result_as_str[4],
        )
    return result_map


def get_columns_from_databus(file_id: str) -> Dict[str, ColumnInfo]:
    """Returns a dict with column_name -> column info from the metadata in the mods endpoint"""

    query_string = f"""PREFIX dataid: <http://dataid.dbpedia.org/ns/core#>
PREFIX dct:    <http://purl.org/dc/terms/>
PREFIX dcat:   <http://www.w3.org/ns/dcat#>
PREFIX db:     <https://databus.dbpedia.org/>
PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX csvw: <http://www.w3.org/ns/csvw#>
PREFIX oeo: <http://openenergy-platform.org/ontology/oeo/>
PREFIX obo: <http://purl.obolibrary.org/obo/>

SELECT DISTINCT ?label ?description ?unit ?datatype ?about WHERE {{
  <{file_id}> csvw:table/csvw:tableSchema ?tableSchema .
  ?tableSchema csvw:column ?col .
  ?col rdfs:label ?label .
  ?col oeo:OEO_00040010 ?unit .
  ?col dct:description ?description .
  ?col csvw:datatype ?datatype .
  OPTIONAL {{ ?col obo:IAO_0000136 ?about . }}
}} """
    sparql = SPARQLWrapper(mod_endpoint)
    sparql.setQuery(query_string)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    try:
        results = results["results"]["bindings"]
    except KeyError:
        raise RuntimeError(f"No column results for the fileID {file_id}. Maybe the fileID was wrong.")

    result_map = {}
    
    for binding in results:
        col_label = binding["label"]["value"]
        result_map[col_label] = ColumnInfo(
            label=col_label,
            description=binding["description"]["value"],
            unit=binding["unit"]["value"],
            datatype=binding["datatype"]["value"],
            about=binding.get("about", {"value": None})["value"]
        )
    return result_map

def get_colname_by_info(col_info: ColumnInfo, ontgraph: Graph, lang: str = "en"):
    """Returns the new column name determined by the available info and the data in the passed ontgraph. language can be set, default is en"""

    if col_info.about is None:
        return col_info.label
    else:
        about_label = get_label_of_resource(col_info.about, ontgraph, lang=lang)

        if about_label == "None":
            return col_info.label
        else:
            return f"{about_label} ({col_info.about})"


def get_dataframe_with_mapped_columns(
    data, cols_dict: Dict[str, ColumnInfo], ontology_graph: Graph
) -> pd.DataFrame:
    """Generates a pandas DataFrame based on the DataPackage from the oep (data), the a dict of colnames -> ColumnInfo and the ontology graph"""
    df = pd.DataFrame(data=data)

    columns = df.columns.tolist()

    rename_mapping = {}

    for colname in columns:
        if colname in cols_dict:
            rename_mapping[colname] = get_colname_by_info(
                cols_dict[colname], ontology_graph
            )
    return df.rename(columns=rename_mapping)


if __name__ == "__main__":

    # Step 0.5: Load the OEO ontology from Archivo
    oeo = load_oeo()

    # Step 1: Set the databus file with the OEP data
    databus_file_id = "https://databus.dbpedia.org/denis/lod-geoss-example/api-example/2021-05-10/api-example_type=turbineData.json"

    # Step 2: Load metadata about columns from the databus
    col_info_mapping = get_columns_from_databus(file_id=databus_file_id)

    # Step 3: Load the JSON data from the Databus based on the file identifier
    data = load_json(databus_file_id)

    # Step 4: Generate the pandas dataframe based on the data from the Databus, the mapping of colnames -> colInfo and the open energy ontology
    df = get_dataframe_with_mapped_columns(
        data, col_info_mapping, oeo
    )

    # Step 5: Print out the dataframe as csv out.csv
    df.to_csv("out.csv")

    # OPTIONAL: Retrieve metadata directly from moss instead of the databus (replaces Step 2)
    # Step 2: Load the metadata annotated submitted via MOSS for the given file id
    # moss_metadata = load_metadata_from_moss(databus_file_id)

    # Step 2.5: Generate the colname -> ColumnInfo mapping based on the moss metadata
    # col_info_mapping = get_columns_from_metadata(moss_metadata)
