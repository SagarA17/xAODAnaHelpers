#!/usr/bin/env python
# -*- coding: utf-8 -*-,
from __future__ import absolute_import
from __future__ import print_function
import logging
logger = logging.getLogger("xAH.utils")

import json
import os
import random
import re
import ROOT

class NameGenerator(object):
  adjectives = None
  animals = None
  def __init__(self):
    from PathResolver import PathResolver
    if self.__class__.adjectives is None:
      self.__class__.adjectives = open(PathResolver.FindCalibFile("xAODAnaHelpers/xAH_adjectives")).read().splitlines()
    if self.__class__.animals is None:
      self.__class__.animals = open(PathResolver.FindCalibFile("xAODAnaHelpers/xAH_animals")).read().splitlines()
  def __repr__(self):
    return "{0:s}{1:s}".format(random.choice(self.__class__.adjectives).capitalize(), random.choice(self.__class__.animals).capitalize())

  def __str__(self):
    return self.__repr__()

def is_release21():
  return True

## Find ASG analysis type (e.g. Base, Top) from a given list.  Return first option, or else None
def findFrameworkTypeFromList(ASG_framework_list):
  ASG_framework_types = [ ASGtype for ASGtype in ASG_framework_list if int( os.environ.get('Analysis'+ASGtype+'_SET_UP', 0) ) ]

  if len(ASG_framework_types) == 0:
    return None
  else:
    return ASG_framework_types[0]

class ColoredFormatter(logging.Formatter):
  RESET_SEQ = "\033[0m"
  COLOR_SEQ = "\033[1;%dm"
  BOLD_SEQ = "\033[1m"
  BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)
  #The background is set with 40 plus the number of the color, and the foreground with 30
  #These are the sequences need to get colored ouput
  COLORS = {
    'WARNING': YELLOW,
    'INFO': WHITE,
    'DEBUG': BLUE,
    'CRITICAL': YELLOW,
    'ERROR': RED
  }

  def __init__(self, msg=None, use_color = True):
    if msg is None:
      msg = "[$BOLD%(asctime)s$RESET][%(levelname)-18s]  %(message)s ($BOLD%(filename)s$RESET:%(lineno)d)"
    msg = msg.replace("$RESET", self.RESET_SEQ).replace("$BOLD", self.BOLD_SEQ)
    logging.Formatter.__init__(self, msg)
    self.use_color = use_color

  def format(self, record):
    levelname = record.levelname
    if self.use_color and levelname in self.COLORS:
      levelname_color = self.COLOR_SEQ % (30 + self.COLORS[levelname]) + levelname + self.RESET_SEQ
      record.levelname = levelname_color
    return logging.Formatter.format(self, record)

# Custom logger class with multiple destinations
class ColoredLogger(logging.Logger):
  def __init__(self, name):
    logging.Logger.__init__(self, name, logging.DEBUG)
    color_formatter = ColoredFormatter()
    if '.' in name: return
    console = logging.StreamHandler()
    console.setFormatter(color_formatter)
    self.addHandler(console)
    return


# Regular expression for comments
comment_re = re.compile('(^)?[^\S\n]*/(?:\*(.*?)\*/[^\S\n]*|/[^\n]*)($)?',
                        re.DOTALL | re.MULTILINE)

# http://www.lifl.fr/~damien.riquet/parse-a-json-file-with-comments.html
def parse_json(filename):
  """ Parse a JSON file
      First remove comments and then use the json module package
      Comments look like :
          // ...
      or
          /*
          ...
          */
  """
  with open(filename) as f:
    content = ''.join(f.readlines())
    ## Looking for comments
    match = comment_re.search(content)
    while match:
      # single line comment
      content = content[:match.start()] + content[match.end():]
      match = comment_re.search(content)
    #print(content)
    # Return json file
    return json.loads(content)

# this registers the provided dictionary of cli-options on an argparse.ArgumentParser object
def register_on_parser(cli_options, parser):
    for optName, optConfig in cli_options.items():
        # no flags specified? that's fine, use '--{optName}' as default
        flags = optConfig.pop("flags", ["--{0:s}".format(optName)])
        parser.add_argument(*flags, **optConfig)

def update_clioption_defaults(argdict, newvalues):
  """Update the default fields of an argument definition dictionary from cli-options.

  Keyword arguments:
  argdict -- reference to the argument definitions
  newvalues -- dictionary with the argument name as key and new default value as value
  """

  for key,value in newvalues.items():
    if key in argdict: argdict[key]['default']=value

# helper function to deal with type madness in vector(...)
def _find_element_type(iterable, element_type):
  supported = (int, float)

  if element_type is None:
    try:
      element_type = type(iterable[0])
    except IndexError: 
      # for empty iterables, c++ still needs a type, 
      raise ValueError(
          '`vector` cannot determine the element type of an empty input iterable.'
          ' Please specify the expected type using the element_type argument.')
    
    if element_type not in supported:
      raise NotImplementedError(
          '`vector` recieved iterable with elements of '
          + 'unsupported type "{}". '.format(element_type.__name__)
          + 'The following types are supported: "'
          + '", "'.join([s.__name__ for s in supported])
          + '"')
  else:
    if element_type not in supported:
      raise NotImplementedError(
        'The specified element_type ("{}")'.format(element_type.__name__)
        + ' is not supported. The following types are supported: "'
        + '", "'.join([s.__name__ for s in supported])
        + '"')
    
    if iterable and not isinstance(iterable[0], element_type):
      raise ValueError(
          'The specified element_type ("{}") '.format(element_type.__name__)
          + 'does not match the types of the iterable elements.')


  if not all(isinstance(e, element_type) for e in iterable):
    raise TypeError(
        '`vector` needs a single element type, '
        'iterable {} has more than one type of element'.format(iterable))

  return element_type

def vector(iterable, element_type = None):
  """
  Convert a list or tuple of ints or floats into a c++ std::vector.


  Input elements need to have a single shared type.
  >>> my_vector = vector([0.8, 2.3, -0.7]) # a vector of floats

  Inputs may be empty (specify element_type to avoid type mismatches).
  >>> my_vector = vector([], element_type = float) # an empty vector of floats
  
  Arguments:
     - iterable : a list or tuple of numbers, to be converted into a vector
     - element_type : type of the vector elements. With non-empty
                      iterables, the element type is deduced, so 
                      this argument is optional. On empty iterables,
                      you need to specify it.
  Returns:
    A new vector containing the elements of the input iterable.
  
  Raises an exception if the element types are not matching, or not supported.
  """
  
  element_type = _find_element_type(iterable, element_type)
  vector = ROOT.std.vector(element_type.__name__)()
  for element in iterable:
    vector.push_back(element)
  return vector
