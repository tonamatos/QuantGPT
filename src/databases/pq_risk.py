######################################################
##################### LIBRARIES ######################
######################################################

import os
from pathlib import Path
from urllib.parse import urljoin
import pandas as pd
import sqlite3
import time

# --- Path Setup ---
BASE_DIR = Path(__file__).resolve().parent  # This file's directory

# 1. Enter the relative path of the directory where you saved the csv files
csv_directory = BASE_DIR / 'csv_files'

# 2. Enter the relative path of the directory where you want the database stored
working_directory = BASE_DIR

# 3. Press play and have fun!

######################################################
################## EXTRACTING CSVs ###################
######################################################

algo_df = pd.read_csv(csv_directory / 'algorithms.csv')
cert_df = pd.read_csv(csv_directory / 'certificates.csv')
entity_df = pd.read_csv(csv_directory / 'entities.csv')
lir_df = pd.read_csv(csv_directory / 'lir.csv')
proto_df = pd.read_csv(csv_directory / 'protocols.csv')
risk_df = pd.read_csv(csv_directory / 'risk_assessments.csv')
vuln_df = pd.read_csv(csv_directory / 'vulnerabilities.csv')


######################################################
################## GENERATING TABLES #################
######################################################

tables = ['algorithms', 'certificates', 'entities', 'lir', 'protocols', 'risk_assessments', 'vulnerabilities']

db_path = working_directory / 'pq_risk.db'
conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

for table in tables:
    cur.execute(f'DROP TABLE IF EXISTS {table}')
    conn.commit()
    time.sleep(0.1)

# all algorithms, protocols, and certificates will be given a unique entity_id.
# this table plays the role of the master table
cur.execute('''
CREATE TABLE entities (
            entity_id INTEGER PRIMARY KEY,
            entity_type TEXT,
            entity_name TEXT
)
''')

cur.execute('''
    CREATE TABLE algorithms (
            algorithm_id INTEGER PRIMARY KEY,
            entity_id INTEGER,
            algo_name TEXT,
            algo_family TEXT,
            crypto_type TEXT,
            FOREIGN KEY (entity_id) REFERENCES entities (entity_id)
    )
''')

cur.execute('''
    CREATE TABLE certificates (
            cert_id INTEGER PRIMARY KEY,
            entity_id INTEGER,
            cert_name TEXT,
            recommended_crypto_suite TEXT,
            FOREIGN KEY (entity_id) REFERENCES entities (entity_id)
    )
''')

cur.execute('''
    CREATE TABLE protocols (
            protocol_id INTEGER PRIMARY KEY,
            entity_id INTEGER,
            protocol_name TEXT,
            cipher_suites TEXT,
            FOREIGN KEY (entity_id) REFERENCES entities (entity_id)
    )
''')

cur.execute('''
    CREATE TABLE lir (
            lir_id INTEGER PRIMARY KEY,
            likelihood INTEGER,
            impact INTEGER,
            overall_risk INTEGER
    )
''')

cur.execute('''
    CREATE TABLE vulnerabilities (
            vuln_id INTEGER PRIMARY KEY,
            vuln_type TEXT
    )
''')

cur.execute('''
    CREATE TABLE risk_assessments (
            assessment_id INTEGER PRIMARY KEY,
            entity_id INTEGER,
            vuln_id INTEGER,
            lir_id INTEGER,
            quant_stride TEXT,
            FOREIGN KEY (entity_id) REFERENCES entities (entity_id),
            FOREIGN KEY (vuln_id) REFERENCES vulnerabilities (vuln_id),
            FOREIGN KEY (lir_id) REFERENCES lir (lir_id)
    )
''')

conn.commit()

######################################################
######## WRITING CONTENTS OF CSVs TO DATABASE ########
######################################################

entity_df.to_sql('entities', conn, if_exists='append', index=False)
lir_df.to_sql('lir', conn, if_exists='append', index=False)
vuln_df.to_sql('vulnerabilities', conn, if_exists='append', index=False)
algo_df.to_sql('algorithms', conn, if_exists='append', index=False)
cert_df.to_sql('certificates', conn, if_exists='append', index=False)
proto_df.to_sql('protocols', conn, if_exists='append', index=False)
risk_df.to_sql('risk_assessments', conn, if_exists='append', index=False)

conn.commit()
conn.close()


