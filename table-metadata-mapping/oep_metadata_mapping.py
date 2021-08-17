from rdflib import Graph, RDFS, RDF, URIRef
from rdflib.namespace import DCTERMS, XSD
import requests
import re
from typing import Dict
import pandas as pd
from dataclasses import dataclass
from SPARQLWrapper import SPARQLWrapper, JSON

# A stable identifier for the complete oeo on archivo


@dataclass
class ColumnInfo:
    """A simple datacass for the information of a certain column"""

    label: str
    description: str
    unit: str
    datatype: str
    about: str


def fetch_data(uri: str):
    """Loads a json file"""
    res = requests.get(uri)
    return res.json()


def load_ontology(uri: str) -> Graph:
    """loads the oeo in a rdflib graph"""
    print(f"Loading ontology from {uri}")
    g = Graph()
    g.parse(uri)
    print(f"Loading successful. Triples: {len(g)}")
    return g


class MetadataContext:
    def __init__(
        self,
        ontology_uri: str,
        metadata_endpoint: str = "https://mods.tools.dbpedia.org/sparql",
        ns_mapping: Dict[str, URIRef] = None,
    ):

        self.ontology: Graph = load_ontology(ontology_uri)
        self.metadata_endpoint = metadata_endpoint
        if ns_mapping is None:
            # A namespace mapping for easier querying
            self.ns_mapping = {
                "rdfs": RDFS,
                "oeo": URIRef("http://openenergy-platform.org/ontology/oeo/"),
                "rdf": RDF,
                "obo": URIRef("http://purl.obolibrary.org/obo/"),
                "csvw": URIRef("http://www.w3.org/ns/csvw#"),
                "xsd": XSD,
                "dct": DCTERMS,
            }
        else:
            self.ns_mapping = ns_mapping

    def __get_label_of_resource(self, resource_uri: str, lang: str = "en") -> str:
        """Queries a graph g for the label of a given resource_uri. lang can be specified, default is en. Returns the first found label"""

        query_string = f"""SELECT ?label WHERE {{
            <{resource_uri}> rdfs:label ?label .
            FILTER(LANG(?label) = "{lang}")
        }}"""

        result = self.ontology.query(query_string, initNs=self.ns_mapping)

        if result is not None and len(result) > 0:
            for row in result:
                return str(row[0])
        else:
            return None

    def __get_column_name_from_ontology(self, col_info: ColumnInfo, lang="en"):
        """Returns the new column name determined by the ColumnInfo object and the data in the passed ontgraph. language can be set, default is en"""

        if col_info.about is None:
            return col_info.label
        else:
            about_label = self.__get_label_of_resource(col_info.about, lang=lang)

            if about_label == "None":
                return col_info.label
            else:
                return f"{about_label} ({col_info.about})"

    def gen_dataframe(
        self, file_id, lang="en", column_infos: Dict[str, ColumnInfo] = None
    ) -> pd.DataFrame:
        """Generates a pandas DataFrame based on the DataPackage from the oep (data), the a dict of colnames -> ColumnInfo and the ontology graph"""

        data = fetch_data(file_id)

        df = pd.DataFrame(data=data)

        columns = df.columns.tolist()

        rename_mapping = {}

        if column_infos is None:
            cols_dict = self.get_columns_from_databus(file_id)
        else:
            cols_dict = column_infos

        for colname in columns:
            if colname in cols_dict:
                rename_mapping[colname] = self.__get_column_name_from_ontology(
                    cols_dict[colname], lang=lang
                )
        return df.rename(columns=rename_mapping)

    def get_columns_from_databus(self, file_id: str) -> Dict[str, ColumnInfo]:
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
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT DISTINCT ?label ?description ?unit ?datatype ?about WHERE {{
  ?dfi csvw:table/csvw:tableSchema ?tableSchema .
  ?tableSchema csvw:column ?col .
  ?col rdfs:label ?label .
  ?col oeo:OEO_00040010 ?unit .
  ?col dct:description ?description .
  ?col csvw:datatype ?datatype .
  OPTIONAL {{ ?col obo:IAO_0000136 ?about . }}
  ?activity a <http://mods.tools.dbpedia.org/ns/demo#ApiDemoMod>; 
       prov:used <https://databus.dbpedia.org/denis/lod-geoss-example/api-example/2021-06-22/api-example_type=turbineData.json> .
}}  """
        sparql = SPARQLWrapper(self.metadata_endpoint)
        sparql.setQuery(query_string)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        try:
            results = results["results"]["bindings"]
        except KeyError:
            raise RuntimeError(
                f"No column results for the fileID {file_id}. Maybe the fileID was wrong."
            )

        result_map = {}

        for binding in results:
            col_label = binding["label"]["value"]
            result_map[col_label] = ColumnInfo(
                label=col_label,
                description=binding["description"]["value"],
                unit=binding["unit"]["value"],
                datatype=binding["datatype"]["value"],
                about=binding.get("about", {"value": None})["value"],
            )
        return result_map


def usage_example():
    # generate the metadata context
    meta_context = MetadataContext(
        "https://archivo.dbpedia.org/download?o=http%3A//openenergy-platform.org/ontology/oeo/&f=ttl&v=2021.05.03-181314"
    )

    # Step 1: Set the databus file with the OEP data
    databus_file_id = "https://databus.dbpedia.org/denis/lod-geoss-example/api-example/2021-06-22/api-example_type=turbineData.json"

    df = meta_context.gen_dataframe(databus_file_id)

    df.to_csv("out.csv")


if __name__ == "__main__":
    usage_example()
