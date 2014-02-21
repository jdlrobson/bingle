#/usr/bin/env python
'''
Manages configuration globals across multiple modules.

Please do not edit configuration directly in this file, unless you have a
really good reason to do so. Modify config in your bingle.ini file.
'''

import ConfigParser
from optparse import OptionParser


def createDictionaryFromPropertiesList(properties):
    return dict((key.strip(), value.strip()) for key, value in (prop.split(',')
                for prop in properties.split(';') if prop.find(',') > -1))

parser = OptionParser()
parser.add_option("-c", "--config", dest="config",
                  help="Path to bingle config file", default="bingle.ini")
parser.add_option("-p", "--pretend", action="store_true", dest="pretend",
                  default=False,
                  help="Run in 'pretend' mode (currently only for handling\
                  resolved bugs)")
parser.add_option("-r", "--reconcile", action="store_true", dest="reconcile",
                  help="Attempt to reconcile bugs marked as resolved in BZ\
                  with bug cards in Mingle")
(options, args) = parser.parse_args()

config = ConfigParser.ConfigParser()
config.read(options.config)
auth = {'username': config.get('auth', 'username'),
        'password': config.get('auth', 'password')}
debug = config.getboolean('debug', 'debug')
picklePath = config.get('paths', 'picklePath')
apiBaseUrl = config.get('urls', 'mingleApiBase')
mingleUrlBase = config.get('urls', 'mingleUrlBase')
bugCard = config.get('mingle', 'bugCard')
bugIdFieldName = config.get('mingle', 'bugIdFieldName')
product = config.get('bugzilla', 'product').split(',')
component = config.get('bugzilla', 'component').split(',')
bugzillaProperties = createDictionaryFromPropertiesList(
    config.get('bugzilla', 'properties'))
mingleProperties = createDictionaryFromPropertiesList(
    config.get('mingle', 'properties'))
mapping = createDictionaryFromPropertiesList(
    config.get('mapping', 'properties'))

if options.reconcile:
    statusResolved = config.get('bingle', 'statusResolved')
    mingleStatusField = config.get('bingle', 'mingleStatusField')
    mingleResolvedStatus = config.get('bingle', 'mingleResolvedStatus')
    mingleIterationPropertyName = config.get('bingle',
                                             'mingleIterationPropertyName')
    mingleResolvedIteration = config.get('bingle', 'mingleResolvedIteration')
    mingleIgnoreResolved = [item.strip() for item in config.get(
        'bingle', 'mingleIgnoreResolved').split(',')]
