import os.path
import sys
from collections import defaultdict
from lib.comp_db import *

Token   = str
String  = str
Integer = int
Float   = float

# An object consists of an object name and a list of arguments
class Object():
  def __init__(self, name = "undefined", args = []):
    self.objName = name
    self.objArgs = args

  @classmethod
  def fromList(cls, elements : list):
    name = elements.pop(0)
    return cls(name, elements)

  def objargsNamed(self, objName : str):
    ojects = []
    for obj in self.objArgs:
      if isinstance(obj, Object):
        if obj.objName == objName:
          ojects.append(obj)
    return ojects

  def serialize(self, level = 1):
    result = ''
    newFragment = ''
    identation = ' ' * level * 2
    newLine = '(' + self.objName
    for a in self.objArgs:
      if callable(getattr(a, "serialize", None)):
        newFragment = a.serialize(level + 1)
      else:
        newFragment = str(a)
      # Add some identation and new lines
      if (len(newLine) + len(newFragment)) < 100:
        newLine += ' ' + newFragment
      else:
        result += newLine + '\n'
        newLine = identation + newFragment
    # Update resulting string
    result += newLine + ')'
    return result

class Property(Object):
  @classmethod
  def new(cls, propName, propVal, x, y, propId):
    return cls('property', [
      String('"' + propName + '"'),
      String('"' + propVal + '"'),
      Object('id', [propId]),
      Object('at', [x, y, 0]),
      Object('effects', [
        Object('font', [
          Object('size', [1.27, 1.27])
        ]),
        'hide'
      ])
    ])

  def name(self):
    return self.objArgs[0].strip('"')

  def value(self):
    return self.objArgs[1].strip('"')

  def pid(self):
    return self.objargsNamed('id')[0].objArgs[0]

  def setName(self, newName):
    self.objArgs[0] = '"' + newName + '"'

  def setValue(self, newVal):
    self.objArgs[1] = '"' + newVal + '"'

  def setId(self, newId):
    self.objargsNamed('id')[0].objArgs[0] = newId

class Symbol(Object):
  specialReferences = ['#PWR', '#FLG', '#GND', '#SYM']
  specialValues     = ['MountingHole', 'TestPoint', 'TEST_PAD', 'SolderJumper', 'Logo', 'Fiducial']
  readonlyFields    = ['Reference', 'Value', 'Footprint', 'Part Number']
  specialFields     = ['Reference', 'Value', 'Footprint', 'Datasheet', 'Part Number']

  def properties(self):
    props = []
    for arg in self.objArgs:
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
          self.objArgs.remove(prop)
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
        self.objArgs.remove(prop)
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
      newId=5
      for prop in self.properties():
        newId = prop.pid()
      newId += 1
      pos = self.objargsNamed("at")[0]
      self.objArgs.append(Property.new(propName, propVal, pos.objArgs[1], pos.objArgs[2], newId))

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

class Document(Object):
  @classmethod
  def __tokenize(cls, body: str) -> list:
    # Convert a string of characters into a list of tokens.
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
  def __parseTokens(cls, tokens: list) -> (Token, String, Integer, Float, Object, Symbol, Property):
    # Read an expression from a sequence of tokens.
    if len(tokens) == 0:
      raise SyntaxError('unexpected EOF')
    token = tokens.pop(0)
    if token == '(':
      L = []
      while tokens[0] != ')':
        L.append(cls.__parseTokens(tokens))
      tokens.pop(0) # pop off ')'
      if L[0] == "symbol":
        return Symbol.fromList(L)
      elif L[0] == "property":
        return Property.fromList(L)
      else:
        return Object.fromList(L)
    elif token == ')':
      raise SyntaxError('unexpected )')
    else:
      # Numbers become numbers; every other token is a Token.
      try: return Integer(token)
      except ValueError:
        try: return Float(token)
        except ValueError:
          strVal = str(token)
          if strVal[0] == '"' and strVal[-1] == '"':
            return String(strVal)
          else:
            return Token(strVal)

  def readFile(self, filename):
    # Read a Scheme expression from a file.
    with open(filename) as f:
      data = f.read()
      tokens = self.__parseTokens(self.__tokenize(data))
      self.objName = tokens.objName
      self.objArgs = tokens.objArgs

  def toFile(self, filename):
    with open(filename, "w") as f:
      f.write(self.serialize())
      f.close()

class Schematic(Document):
  def __init__(self, doNotPopulateMark = "DNP", populateFieldName = "Populate"):
    self.__doNotPopulateMark = doNotPopulateMark
    self.__populateFieldName = populateFieldName

  def symbols(self):
    result = []
    for arg in self.objArgs:
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
        propValue = symbol.getProperty(oldName)
        if propValue == False:
          continue
        propValue = propValue.value()
        symbol.removeProp(oldName)
        symbol.addProperty(newNames[idx], propValue)

