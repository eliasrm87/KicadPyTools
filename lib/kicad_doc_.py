import os.path
import sys
from collections import defaultdict
from lib.comp_db import *

readonlyFields    = ['Reference', 'Value', 'Footprint', 'Part Number']
specialFields     = ['Reference', 'Value', 'Footprint', 'Datasheet', 'Part Number']
specialReferences = ['#PWR', '#FLG', '#GND', '#SYM']
specialValues     = ['MountingHole', 'TestPoint', 'TEST_PAD', 'SolderJumper', 'Logo', 'Fiducial']

# Objects are implemented as lists where the first element is the name and the following one is the value
class Object(list):
  def objType(self):
    self[0]

  def elementsNamed(self, objName : str):
    ojects = []
    for obj in self:
      if obj[0] == objName:
        ojects.append(obj)
    return ojects

class Property(Object):
  @classmethod
  def new(cls, propName, propVal, x, y, propId):
    return cls(['property', '"' + propName + '"', '"' + propVal + '"', ['id', propId], ['at', x, y, 0], [ 'effects', ['font', ['size', 1.27, 1.27]], 'hide']])

  def name(self):
    return self[1].strip('"')

  def value(self):
    return self[2].strip('"')

  def pid(self):
    return self.elementsNamed("id")[0][1]

  def setName(self, newName):
    self[1] = '"' + newName + '"'

  def setValue(self, newVal):
    self[2] = '"' + newVal + '"'

  def setId(self, newId):
    self.elementsNamed("id")[0][1] = newId

class Symbol(Object):
  def properties(self):
    return self.elementsNamed("property")

  def getProperty(self, propName):
    for prop in self.properties():
      if prop.name() == propName:
        return prop
    return False

  def propertiesDict(self):
    retDict = {}
    for prop in self.elementsNamed("property"):
      retDict[prop.name()] = Property(prop).value()
    return retDict

  def removeProp(self, propName):
    newId=5
    specialPropFound = []
    for prop in self.properties():
      if prop.name() in specialFields:
        # Make sure id is correct for special fields
        prop.setId(specialFields.index(prop.name()))
        # Delete duplicated special fields
        if prop.name() == propName:
          if prop.name() not in specialPropFound:
            specialPropFound.append(prop.name())
          else:
            print('WARNING: Removed duplicated', prop.name())
            self.remove(prop)
      else:
        if prop.name() == propName:
          self.remove(prop)
        else:
          prop.setId(newId)
          newId += 1

  def cleanProperties(self):
    for prop in self.properties():
      self.removeProp(prop.name())

  def addProperty(self, propName, propVal):
    # Add / Modify property
    prop = self.getProperty(propName)
    if prop != False:
      # Modify property
      if propName not in readonlyFields and len(propVal) > 0:
        print('INFO: Updating property:', propName, '=', propVal)
        prop.setValue(propVal)
    else:
      # Add property
      print('INFO: Adding property:', propName, '=', propVal)
      newId=5
      for prop in self.properties():
        newId = prop.pid()
      newId += 1
      pos = self.elementsNamed("at")[0]
      self.append(Property.new(propName, propVal, pos[1], pos[2], newId))

  def isSpecial(self):
    reference = self.getProperty('Reference').value()
    value = self.getProperty('Value').value()

    for referenceToIgnore in specialReferences:
      if reference.find(referenceToIgnore) != -1:
        return True
    for valueToIgnore in specialValues:
      if value.find(valueToIgnore) != -1:
        return True

    return False

  def addPopulateField(self, doNotPopulateMark = "DNP", populateFieldName = "Populate"):
    value = self.getProperty('Value').value()

    # Special symbols are not populated
    if self.isSpecial():
      self.addProperty(populateFieldName, 'N')
      return

    # If magic word is part of the value, the symbol is marked to not be populated
    populate = 'Y'
    if value.find(doNotPopulateMark) != -1:
      populate = 'N'
    self.addProperty(populateFieldName, populate)

class Document(Object):
  @classmethod
  def __tokenize(cls, body: str) -> list:
    "Convert a string of characters into a list of tokens."
    tokens = []
    token = ''
    inString = False
    prevChar = ''
    for c in body:
      if c == '"':
        token += c
        if inString and (prevChar != '\\'):
          inString = False
          tokens.append(token)
          token = ''
        else:
          inString = True
      elif inString:
        # If in a string, ignore character and append it to the token
        token += c
      elif (c == '(') or (c == ')'):
        # Store previous token if not empty
        if len(token) > 0:
          tokens.append(token)
        # Add parentheses as another token
        tokens.append(c)
        token = ''
      elif c.isspace():
        # Store previous token if not empty and ignore space
        if len(token) > 0:
          tokens.append(token)
          token = ''
      else:
        token += c

      prevChar = c
    return tokens

  @classmethod
  def __parseTokens(cls, tokens: list) -> (str, int, float, Object, Symbol, Property):
    "Read an expression from a sequence of tokens."
    if len(tokens) == 0:
      raise SyntaxError('unexpected EOF')
    token = tokens.pop(0)
    if token == '(':
      L = []
      while tokens[0] != ')':
        L.append(cls.__parseTokens(tokens))
      tokens.pop(0) # pop off ')'
      if L[0] == "symbol":
        return Symbol(L)
      elif L[0] == "property":
        return Property(L)
      else:
        return Object(L)
    elif token == ')':
      raise SyntaxError('unexpected )')
    else:
      "Numbers become numbers; every other token is a symbol."
      try: return int(token)
      except ValueError:
        try: return float(token)
        except ValueError:
          return str(token)

  def __serialize(self, obj : list):
    outStr = ''
    for a in obj:
      if isinstance(a, list):
        outStr += '( '
        outStr += self.__serialize(a)
        outStr += ')\n'
      else:
        if isinstance(a, str):
          outStr += a + ' '
        else:
          outStr += str(a) + ' '
    return outStr

  def readFile(self, filename):
    self.clear()
    "Read a Scheme expression from a file."
    with open(filename) as f:
      data = f.read()
      self.extend(self.__parseTokens(self.__tokenize(data)))

  def toFile(self, filename):
    with open(filename, "w") as f:
      f.write("(")
      f.write(self.__serialize(self))
      f.write(")")
      f.close()

class Schematic(Document):

  def __init__(self, doNotPopulateMark = "DNP", populateFieldName = "Populate"):
    Document.__init__(self)
    self.__doNotPopulateMark = doNotPopulateMark
    self.__populateFieldName = populateFieldName

  def symbols(self):
    return self.elementsNamed("symbol")

  def addPopulateFields(self):
    for symbol in self.symbols():
      symbol.addPopulateField(self.__doNotPopulateMark, self.__populateFieldName)

  def updateFieldsFromDB(self, compDB : CompDB, keyPropNames, cleanup = False):
    for symbol in self.symbols():
      reference = symbol.getProperty('Reference').value()
      value = symbol.getProperty('Value').value()

      if symbol.isSpecial():
        print('INFO: Ignoring special symbol', reference)
        continue

      if cleanup:
        symbol.cleanProperties()

      symbolPropsDict = symbol.propertiesDict()
      match = compDB.matchSymbol(keyPropNames, symbolPropsDict)
      # Add all fields from the DB
      if len(match) > 0:
        for propName in compDB.propNames:
          symbol.addProperty(propName, match[propName])
      else:
        print('ERROR: No match found for', symbolPropsDict['Reference'])

  def renameFields(self, oldNames, newNames):
    for symbol in self.symbols():
      for idx, oldName in enumerate(oldNames):
        propValue = symbol.getProperty(oldName)
        if propValue == False:
          continue
        propValue = propValue.value()
        symbol.removeProp(oldName)
        symbol.addProperty(newNames[idx], propValue)

