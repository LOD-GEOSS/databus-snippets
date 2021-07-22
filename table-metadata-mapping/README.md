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

Modify the variables below the `if __name__ == "__main__":` for your needs and run:
```
python oep_metadata_mapping.py
```