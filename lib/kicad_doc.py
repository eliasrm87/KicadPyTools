from lib.s_expression import *
from lib.comp_db import *

class Property(SExpr):
  @classmethod
  def new(cls, propName, propVal, x, y, propId):
    return cls(SExpr('property', [
      String(propName),
      String(propVal),
      SExpr('id', [propId]),
      SExpr('at', [x, y, 0]),
      SExpr('effects', [
        SExpr('font', [
          SExpr('size', [1.27, 1.27])
        ]),
        'hide'
      ])
    ]))

  def copy(self):
    return Property(super().copy())

  def name(self):
    return self._args[0]._value.strip('"')

  def value(self):
    return self._args[1]._value.strip('"')

  def pid(self):
    return self.argsNamed('id')[0]._args[0]._value

  def setName(self, newName):
    self._args[0]._value = String(newName)

  def setValue(self, newVal):
    self._args[1]._value = String(newVal)

  def setId(self, newId):
    self.argsNamed('id')[0]._args[0]._value = newId

class Symbol(SExpr):
  specialReferences = ['#PWR', '#FLG', '#GND', '#SYM']
  specialValues     = ['MountingHole', 'TestPoint', 'TEST_PAD', 'SolderJumper', 'Logo', 'Fiducial']
  readonlyFields    = ['Reference', 'Value', 'Footprint', 'Part Number']
  specialFields     = ['Reference', 'Value', 'Footprint', 'Datasheet', 'Part Number']

  def copy(self):
    return Symbol(super().copy())

  def properties(self):
    props = []
    for arg in self._args:
      if isinstance(arg, Property):
        props.append(arg)
    return props

  def propertiesDict(self):
    retDict = {}
    for prop in self.properties():
      retDict[prop.name()] = prop
    return retDict

  def getProperty(self, propName):
    for prop in self.properties():
      if prop.name() == propName:
        return prop
    return False

  def removeProp(self, propName):
    if propName.startswith('ki_'):
      print("ERROR: cannot delete special property {}".format(propName))
      return

    found = 0
    specialPropsFound = []
    for prop in self.properties():
      name = prop.name()
      newId = prop.pid() - found
      if name not in self.specialFields:
        if name == propName:
          print("INFO: Removing", name, 'from', self.getProperty('Reference').value())
          self._args.remove(prop)
          found += 1
        else:
          prop.setId(newId)

  def cleanProperties(self):
    found = 0
    specialPropsFound = []
    for prop in self.properties():
      name = prop.name()
      newId = prop.pid() - found
      if name not in self.specialFields and not name.startswith('ki_'):
        print("INFO: Removing", name, 'from', self.getProperty('Reference').value())
        self._args.remove(prop)
        found += 1
      else:
        prop.setId(newId)

  def addProperty(self, propName, propVal):
    # Add / Modify property
    prop = self.getProperty(propName)
    if prop != False:
      # Modify property
      if propName not in self.readonlyFields and len(propVal) > 0:
        print('INFO: Updating property:', propName, '=', propVal)
        prop.setValue(propVal)
    else:
      # Add property
      print('INFO: Adding property:', propName, '=', propVal)
      # Use the last property as reference to create the new one
      # keeping the same identation all the other parameters
      newProp = self.properties()[-1].copy()
      newProp.setName(propName)
      newProp.setValue(propVal)
      newProp.setId(newProp.pid() + 1)
      # Add new property
      self._args.append(newProp)

  def isSpecial(self):
    reference = self.getProperty('Reference').value()
    value = self.getProperty('Value').value()

    for referenceToIgnore in self.specialReferences:
      if reference.find(referenceToIgnore) != -1:
        return True
    for valueToIgnore in self.specialValues:
      if value.find(valueToIgnore) != -1:
        return True

    return False

  def isPopulated(self, doNotPopulateMark = "DNP"):
    # Special symbols are not populated
    if self.isSpecial():
      return False

    value = self.getProperty('Value').value()

    # If magic word is part of the value, the symbol is marked to not be populated
    if value.find(doNotPopulateMark) != -1:
      return False

    return True

  def addPopulateField(self, doNotPopulateMark = "DNP", populateFieldName = "Populate"):
    populate = 'N'
    if self.isPopulated(doNotPopulateMark):
      populate = 'Y'

    self.addProperty(populateFieldName, populate)

class Schematic(Document):
  def __init__(self, doNotPopulateMark = "DNP", populateFieldName = "Populate"):
    self.__doNotPopulateMark = doNotPopulateMark
    self.__populateFieldName = populateFieldName

  def specialize(self, sexpr):
    if sexpr._name._value == "property":
      return Property(sexpr)

    if sexpr._name._value == "symbol":
      return Symbol(sexpr)

    return sexpr

  def symbols(self):
    result = []
    for arg in self._sexpr._args:
      if isinstance(arg, Symbol):
        result.append(arg)
    return result

  def addPopulateFields(self):
    for symbol in self.symbols():
      symbol.addPopulateField(self.__doNotPopulateMark, self.__populateFieldName)

  def updateFieldsFromDB(self, compDB : CompDB, keyPropNames):
    for symbol in self.symbols():
      reference = symbol.getProperty('Reference').value()
      value = symbol.getProperty('Value').value()

      if symbol.isSpecial():
        print('INFO: Ignoring special symbol', reference)
        continue

      symbolPropsDict = symbol.propertiesDict()
      match = compDB.matchSymbol(keyPropNames, symbolPropsDict)
      # Add all fields from the DB
      if len(match) > 0:
        for propName in compDB.propNames:
          symbol.addProperty(propName, match[propName])
      else:
        print('ERROR: No match found for', symbolPropsDict['Reference'])

  def cleanSymbolProperties(self):
    for symbol in self.symbols():
      symbol.cleanProperties()

  def renameFields(self, oldNames, newNames):
    for symbol in self.symbols():
      for idx, oldName in enumerate(oldNames):
        prop = symbol.getProperty(oldName)
        if prop == False:
          continue
        prop.setName(newNames[idx])
