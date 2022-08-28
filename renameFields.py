import argparse
from lib.kicad_doc import *
from lib.csv_comp_db import *

parser = argparse.ArgumentParser()
parser.add_argument("source", type=str,
                    help="Source KiCad schematic")
parser.add_argument("destination", type=str,
                    help="Destination KiCad schematic")
parser.add_argument("oldNames", type=str,
                    help="Comma separated list of field names to be renamed")
parser.add_argument("newNames", type=str,
                    help="Comma separated list of new names for fields specified before")
args = parser.parse_args()

sch = Schematic()
sch.readFile(args.source)

oldNames = [name.strip() for name in args.oldNames.split(',')]
newNames = [name.strip() for name in args.newNames.split(',')]

sch.renameFields(oldNames, newNames)

sch.toFile(args.destination)
