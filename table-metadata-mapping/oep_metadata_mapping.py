from rdflib import Graph, RDFS, RDF, URIRef
from rdflib.namespace import DCTERMS, XSD
import requests
import csv
import json
import re
from typing import Dict, List

oeo_uri = "https://archivo.dbpedia.org/download?o=http%3A//openenergy-platform.org/ontology/oeo/&f=ttl&v=2021.05.03-181314"

databus_file_id = "https://databus.dbpedia.org/denis/lod-geoss-example/api-example/2021-06-22/api-example_type=turbineData.json"


databus_file_id_regex = re.compile(r"https://databus\.dbpedia\.org/(.*?)/(.*?)/(.*?)/(.*?)/(.*)")

oeo_has_unit = "OEO_00040010"

ns_mapping = {
    "rdfs": RDFS,
    "oeo": URIRef("http://openenergy-platform.org/ontology/oeo/"),
    "rdf": RDF,
    "obo": URIRef("http://purl.obolibrary.org/obo/"), 
    "csvw": URIRef("http://www.w3.org/ns/csvw#"),
    "xsd": XSD,
    "dct": DCTERMS,
    }

def load_oeo() -> Graph:

    g = Graph()
    g.load(oeo_uri, format="turtle")
    return g

def load_csv_from_databus(file_id: str) -> str:

    res = requests.get(file_id)
    return res

def get_label_of_resource(resource_uri: str, g: Graph, lang: str="en") -> str:

    query_string = """SELECT ?label WHERE {{
        <{resource}> rdfs:label ?label .
        FILTER(LANG(?label) = "{lang}")
    }}
    """.format(resource=resource_uri, lang=lang)

    result = g.query(query_string, initNs=ns_mapping)

    if result is not None and len(result) > 0:
        for row in result:
            return str(row[0])
    else:
        return None


def load_metadata_from_moss(file_id: str) -> Graph:

    m = databus_file_id_regex.match(file_id)

    if m is None:
        raise RuntimeError("Not a valid databus identifier")

    pub, group, artifact, version, filename = m.groups()

    metadata_uri = f"https://moss.tools.dbpedia.org/data/{pub}/{group}/{artifact}/{version}/{filename}/api-demo-data.ttl"

    g = Graph()
    g.load(metadata_uri, format="turtle")
    return g

def get_columns_from_metadata(file_id: str, g: Graph) -> Dict[str, Dict[str, str]]:

    keys = ["description", "unit", "datatype", "about"]
    
    query_string = """SELECT ?label ?description ?unit ?datatype ?about WHERE {{
        <{file_id}> csvw:table/csvw:tableSchema ?tableSchema .
        ?tableSchema csvw:column ?col .
        ?col rdfs:label ?label .
        ?col oeo:OEO_00040010 ?unit .
        ?col dct:description ?description .
        ?col csvw:datatype ?datatype .
        OPTIONAL {{ ?col obo:IAO_0000136 ?about . }}
    }}
    """.format(file_id=file_id)

    result = g.query(query_string, initNs=ns_mapping)

    result_map = {}

    for row in result:
        result_as_str = list(map(str, row[1:]))
        result_map[str(row[0])] = dict(zip(keys, result_as_str))

    return result_map



if __name__ == "__main__":


    databus_file_id = "https://databus.dbpedia.org/denis/lod-geoss-example/api-example/2021-05-10/api-example_type=turbineData.json"

    # oeo = load_oeo()

    moss_metadata = load_metadata_from_moss(databus_file_id)

    print(get_columns_from_metadata(databus_file_id, moss_metadata))



