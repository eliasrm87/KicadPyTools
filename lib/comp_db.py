import os.path
import sys
from collections import defaultdict

# List of symbols Part Numbers and other fields to be included
# in the schematic for BoM generation

class CompDB():
  def __init__(self):
    self.propNames = []
    self.symbols = []

  def matchSymbol(self, keyColumnNames, symbolPropsDict : dict):
    for columnNames in keyColumnNames:
      for row in self.symbols:
        i = 0
        for colName in columnNames:
          if colName in symbolPropsDict:
            if len(row[colName]) > 0 and symbolPropsDict[colName].value().find(row[colName]) != -1:
              i += 1
          if i == len(columnNames):
            print('INFO:', symbolPropsDict['Reference'], 'Matched by (', ', '.join(columnNames), ')', end=' ')
            for column in columnNames:
              print(symbolPropsDict[column], end=' ')
            print('')
            return row
    return []
