#!/usr/bin/env python

import ConfigParser
import re
import json
import requests
import sys

from config import *
from lib.bingle import Bingle
from lib.mingle import Mingle
from bingle import createDictionaryFromPropertiesList


def getBzSearchParams(bingle, fromTime=None):
    bzSearchParams = {
        'product': product,
        'component': component,
        'status': [statusResolved]
    }
    if fromTime:
        bzSearchParams['last_change_time'] = fromTime
    bingle.info(bzSearchParams)
    return bzSearchParams


def fetchBugsResolved(bingle, bzSearchParams):
    bugzillaPayload = {
        'method': 'Bug.search',
        'params': json.dumps([bzSearchParams])
    }
    bugs = bingle.getBugEntries(bugzillaPayload)
    bingle.info('Number of bugs: %s' % len(bugs))
    return bugs


def reconcileMingle(bingle, mingle, bugs, pretend=True):
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
        status = mingle.getCardById(cardId).getPropertyByName(mingleStatusField)
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


def execute(bingle, mingle, standalone=False, pretend=False, fromTime=None):
    bzSearchParams = getBzSearchParams(bingle, fromTime)
    bugs = fetchBugsResolved(bingle, bzSearchParams)
    reconcileMingle(bingle, mingle, bugs, options.pretend)
    if standalone and not pretend:
        # update pickle
        bingle.updatePickleTime()


if __name__ == "__main__":
    # config overrides
    config = ConfigParser.ConfigParser()
    config.read(options.config)
    picklePath = config.get('paths', 'picklePath') + '_resolved'
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
    execute(standalone=True, pretend=options.pretend, bingle=bingle,
            mingle=mingle)
