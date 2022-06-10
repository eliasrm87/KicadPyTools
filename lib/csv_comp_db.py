from lib.comp_db import *
import csv

# CSV file containing a list of symbols Part Numbers and other fields to be included
# in the schematic for BoM generation

class CsvCompDB(CompDB):
  def __init__(self, filename):
    CompDB.__init__(self)
    with open(filename, newline='') as csvfile:
      csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')
      self.propNames = next(csvreader)
      for row in csvreader:
        i = 0;
        dictRow = {}
        for cell in row:
          dictRow[self.propNames[i]] = cell
          i += 1
        self.symbols.append(dictRow)
