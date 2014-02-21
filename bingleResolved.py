#!/usr/bin/env python

import ConfigParser
import re
import json
import requests
import sys
from optparse import OptionParser

from lib.bingle import Bingle
from lib.mingle import Mingle
from bingle import createDictionaryFromPropertiesList


def getBzSearchParams():
    bzSearchParams = {
        'product': product,
        'component': component,
        'status': [statusResolved]
    }
    if fromTime:
        bzSearchParams['last_change_time'] = fromTime
    bingle.info(bzSearchParams)
    return bzSearchParams


def fetchBugsResolved(bzSearchParams):
    bugzillaPayload = {
        'method': 'Bug.search',
        'params': json.dumps([bzSearchParams])
    }
    bugs = bingle.getBugEntries(bugzillaPayload)
    bingle.info('Number of bugs: %s' % len(bugs))
    return bugs


def reconcileMingle(bugs, pretend=True):
    counter = 0
    cardsToUpdate = []
    for bug in bugs:
        # see if there's a mingle card matching this bug
        if len(bugIdFieldName) > 0:
            foundBug = mingle.findCardNumByBugId(
                bugCard, bug.get('id'), bugIdFieldName)
        else:
            foundBug = mingle.findCardNumByBugName(
                bugCard, bug.get('id'), bug.get('summary'))
        bingle.info(mingle.dumpRequest())
        if len(foundBug) < 1:
            # eh... we probably want to do something else here
            continue
        cardId = foundBug[0]['Number']
        # figure out the card's status
        status = mingle.getCardById(cardId).getStatus(mingleStatusField)
        if status not in mingleIgnoreResolved:
            counter += 1
            cardToUpdate = (cardId, bug.get('id'))
            cardsToUpdate.append(cardToUpdate)
            if not pretend:
                # update the card to 'ready for signoff'
                # and make sure it's in this iteration
                cardParams = {
                    'card[properties][][name]': mingleStatusField,
                    'card[properties][][value]': mingleResolvedStatus
                }
                mingle.updateCard(cardId, cardParams)
                cardParams = {
                    'card[properties][][name]': mingleIterationPropertyName,
                    'card[properties][][value]': mingleResolvedIteration
                }
                mingle.updateCard(cardId, cardParams)
    bingle.info('Number of bug cards updated: %s' % counter)
    bingle.info("Mingle cards/bugs updated updated:")
    for cardToUpdate in cardsToUpdate:
        bingle.info('%scards/%s, http://bugzilla.wikimedia.org/%s' %
                   (mingleUrlBase, cardToUpdate[0], cardToUpdate[1]))


def execute(standalone=False, pretend=False):
    bzSearchParams = getBzSearchParams()
    bugs = fetchBugsResolved(bzSearchParams)
    reconcileMingle(bugs, options.pretend)
    if standalone and not pretend:
        # update pickle
        bingle.updatePickleTime()


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-c", "--config", dest="config",
                      help="Path to bingle config file", default="bingle.ini")
    parser.add_option("-p", "--pretend", action="store_true", dest="pretend",
                      default=False, help="Run in 'pretend' mode")
    (options, args) = parser.parse_args()

    config = ConfigParser.ConfigParser()
    config.read(options.config)
    auth = {'username': config.get('auth', 'username'),
            'password': config.get('auth', 'password')}
    debug = config.getboolean('debug', 'debug')
    picklePath = config.get('paths', 'picklePath') + '_resolved'
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
    statusResolved = config.get('bingle', 'statusResolved')
    mingleStatusField = config.get('bingle', 'mingleStatusField')
    mingleResolvedStatus = config.get('bingle', 'mingleResolvedStatus')
    mingleIterationPropertyName = config.get('bingle',
                                             'mingleIterationPropertyName')
    mingleResolvedIteration = config.get('bingle', 'mingleResolvedIteration')
    mingleIgnoreResolved = [item.strip() for item in config.get(
        'bingle', 'mingleIgnoreResolved').split(',')]

    bingle = Bingle(debug=debug, picklePath=picklePath)
    bingle.info("Pretend mode: %s" % options.pretend)
    bingle.info("Ignoring bugs in: %s" % mingleIgnoreResolved)

    # prepare Mingle instance
    mingle = Mingle(auth, apiBaseUrl)

    fromTime = bingle.getTimeFromPickle()
    execute(standalone=True, pretend=options.pretend)
