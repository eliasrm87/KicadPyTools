import argparse
from lib.kicad_doc import *
from lib.csv_comp_db import *

parser = argparse.ArgumentParser()
parser.add_argument("--doNotPopulateMark", type=str, default='DNP',
                    help="Magic word used in the value field to specify if a component is not populated on the PCB, default is 'DNP'")
parser.add_argument("csvDB", type=str,
                    help="CSV file containing the database of known components")
parser.add_argument("source", type=str,
                    help="Source KiCad schematic")
parser.add_argument("destination", type=str,
                    help="Destination KiCad schematic")
parser.add_argument("keyFields", nargs='+', type=str,
                    help="Comma separated list of fields to be used for matching against the DB")
args = parser.parse_args()

compDB   = CsvCompDB(args.csvDB)
sch      = Schematic(args.doNotPopulateMark)

sch.readFile(args.source)

keyFields = []
for keys in args.keyFields:
  keyFields.append([key.strip() for key in keys.split(',')])

sch.cleanSymbolProperties()
sch.updateFieldsFromDB(compDB, keyFields)
sch.addPopulateAttrs()
sch.addInBomAttrs()

sch.toFile(args.destination)
