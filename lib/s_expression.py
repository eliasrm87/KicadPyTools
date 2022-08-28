import os.path
import sys
from io import StringIO
from collections import defaultdict
from lib.comp_db import *

DEBUG = False

def String(s : str):
  return '"' + s + '"'

class Token():
  _leading = ' '
  _value = ''

  def parseValue(self, value):
    if isinstance(value, int) or isinstance(value, float):
      return value

    try: return int(value)
    except ValueError:
      try: return float(value)
      except ValueError:
        return str(value)

  def __init__(self, value, leading = ' '):
    self._leading = leading
    self._value = self.parseValue(value)

  def copy(self):
    return Token(self._value, self._leading)

  def setValue(self, value : str):
    self._value = self.parseValue(value)

  def serialize(self):
    if DEBUG:
      print('Token::serialize')
    result = self._leading

    if DEBUG and (self._value != '(') and (self._value != ')'):
      result += '<Token:' + type(self._value).__name__ + '>'

    result += str(self._value)

    return result

  def __repr__(self):
    return self.serialize()

# An object consists of an object name and a list of arguments
class SExpr():
  _start = Token('(')
  _name = Token('')
  _args = []
  _end = Token(')')
  _value = None # Trick to make SExpr "compatible" with Token

  def __init__(self, name, args = [], start = Token('('), end = Token(')')):
    if isinstance(name, SExpr):
      self._start = name._start
      self._name = name._name
      self._args = name._args
      self._end = name._end
      return

    if isinstance(start, Token):
      self._start = start
    else:
      self._start = Token(start)

    if isinstance(name, Token):
      self._name = name
    else:
      self._name = Token(name)

    self._args = []
    for arg in args:
      if isinstance(arg, Token) or isinstance(arg, SExpr):
        self._args.append(arg)
      else:
        self._args.append(Token(arg))

    if isinstance(end, Token):
      self._end = end
    else:
      self._end = Token(end)

  def copy(self):
    newArgs = []
    for arg in self._args:
      newArgs.append(arg.copy())

    return SExpr(self._name.copy(),
                 newArgs,
                 self._start.copy(),
                 self._end.copy())

  @classmethod
  def fromTokenListRec(cls, tokens : list):
    # Read an expression from a sequence of tokens.
    if len(tokens) == 0:
      raise SyntaxError('unexpected EOF')
    token = tokens.pop(0)
    if token._value == ')':
      raise SyntaxError('unexpected )')
    elif token._value == '(':
      # Create new expression with the start and the name
      sexpr = cls(tokens.pop(0), [], token)
      while tokens[0]._value != ')':
        sexpr._args.append(cls.fromTokenListRec(tokens))
      sexpr._end = tokens.pop(0) # pop off ')'
      return sexpr
    else:
      return token

  @classmethod
  def fromTokenList(cls, tokens : list, doc):
    # Read an expression from a sequence of tokens.
    token = tokens.pop(0)
    if token._value != '(':
      raise SyntaxError('unexpected ' + token._value)
    stack = [doc.specialize(cls(tokens.pop(0), [], token))]

    args = [token]
    while len(tokens) > 0:
      token = tokens.pop(0)
      if token._value == '(':
        # Create new expression with the start and the name
        stack.append(doc.specialize(cls(tokens.pop(0), [], token)))
        args.append(token)
      elif token._value == ')':
        sexpr = stack.pop()
        sexpr._end = token
        token = args.pop()
        while token._value != '(':
          sexpr._args.insert(0, token)
          token = args.pop()
        if len(stack) == 0:
          return sexpr
        args.append(sexpr)
      else:
        args.append(token)

    raise SyntaxError('unexpected EOF')

  @classmethod
  def fromStream(cls, stream, doc):
    # Convert a stream of characters into a sequence of tokens
    # and then parses it into an s-expression
    tokens = []
    inString = False
    prevChar = ''
    leading = ''
    value = ''
    c = stream.read(1)
    while len(c) == 1:
      if c == '"':
        value += c
        if inString and (prevChar != '\\'):
          inString = False
          tokens.append(Token(value, leading))
          leading = ''
          value = ''
        else:
          inString = True
      elif inString:
        # If in a string, ignore character and append it to the token
        value += c
      elif (c == '(') or (c == ')'):
        # Store previous token if not empty
        if len(value) > 0:
          tokens.append(Token(value, leading))
          leading = ''
        # Add parentheses as another token
        value = c
        tokens.append(Token(value, leading))
        leading = ''
        value = ''
      elif c.isspace():
        # Store previous token if not empty
        if len(value) > 0:
          tokens.append(Token(value, leading))
          leading = ''
          value = ''
        leading += c
      else:
        value += c
      prevChar = c
      c = stream.read(1)
    return SExpr.fromTokenList(tokens, doc)

  @classmethod
  def fromString(cls, string : str):
    # Convert a string of characters into an s-expression
    return cls.fromStream(StringIO(string))

  def argsNamed(self, name : str):
    args = []
    for arg in self._args:
      if isinstance(arg, SExpr):
        if arg._name._value == name:
          args.append(arg)
    return args

  def serialize(self):
    if DEBUG:
      print('SExpr::serialize')
    result = ''
    if DEBUG:
      result += '<SExpr>'
    result += self._start.serialize() + self._name.serialize()

    for sexpr in self._args:
      result += sexpr.serialize()
    result += self._end.serialize()
    return result

  def __repr__(self):
    return self.serialize()

class Document():
  _sexpr = None

  def readFile(self, filename):
    # Read a Scheme expression from a file.
    with open(filename) as f:
      self._sexpr = SExpr.fromStream(f, self)

  def toFile(self, filename):
    with open(filename, "w") as f:
      f.write(self._sexpr.serialize())
      f.write('\n')
      f.close()

  def specialize(self, sexpr):
    return sexpr

  def __repr__(self):
    return self._sexpr.serialize()
