#!/bin/env python
"""
Script to export data from Gerrit's postgresql table

Description:
    De data isonly available as a Postgres backup file. Load it into postgres.
    Export data from it using this script. Export is in json format, this json
    data is imported with a migration. Put the json files in migrations/data/.

Usage:
    python db_gerrit_to_json.py tablename
    Output will be tablename.json.
"""
import psycopg2
import json
import sys

credentials = {
    'dbname': 'GIS_db',
    'dbuser': 'openearth',
    'dbpass': 'openearth',
}
conn = psycopg2.connect("dbname={dbname} user={dbuser} password={dbpass}".format(**credentials))
cur = conn.cursor()

if __name__ == '__main__':
    if not len(sys.argv) == 2:
        print 'First argument should be a table name. EG: parameter.'
        exit(1)

    table_name = sys.argv[1]
    print 'Loading data from table: "{0}"'.format(table_name)
    cur.execute("SELECT row_to_json({0}) FROM {0}".format(table_name))
    records = [i[0] for i in cur]
    fname = '{0}.json'.format(table_name)

    print 'Dumping data to: "{0}"'.format(fname)
    with open(fname, 'w') as fp:
        json.dump(records, fp)
