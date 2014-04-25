#!/usr/bin/env python

import ConfigParser
import json
from optparse import OptionParser
from lib.bingle import Bingle
from lib.trello import Trello


if __name__ == "__main__":
    # config stuff
    parser = OptionParser()
    parser.add_option("-c", "--config", dest="config",
                      help="Path to bugello config file", default="bugello.ini")
    (options, args) = parser.parse_args()
    config = ConfigParser.ConfigParser()
    config.optionxform = str # needed to preserve case of option names
    config.read(options.config)
    trelloConfig = config.items('trello')
    debug = config.getboolean('debug', 'debug')
    picklePath = config.get('paths', 'picklePath')
    product = config.get('bugzilla', 'product').split(',')
    component = config.get('bugzilla', 'component').split(',')

    trello = Trello(config=trelloConfig, debug=debug)
    tListId = trello.getBugListId()

    bingle = Bingle(debug=debug, picklePath=picklePath)
    # @TODO update to use API rather than feeds
    fromTime = bingle.getTimeFromPickle()
    params = {
        'product': product,
        'status': ['UNCONFIRMED', 'NEW'],
        'last_change_time': fromTime
    }
    if len(component[0]) > 1:
        params['component'] = component

    bugzillaPayload = {
        'method': 'Bug.search',
        'params': json.dumps([params])
    }

    for entry in bingle.getBugEntries(bugzillaPayload):
        cardExists = False
        bugId = entry.get('id', '---')
        bugTitle = entry.get('summary').encode('UTF-8', 'ignore')
        if trello.prefixBugTitle:
            cardTitle = bingle.generateBugCardName(bugId, bugTitle)
            searchString = bingle.getBugCardPrefix(bugId)
            cards = trello.searchCardsByName(searchString)
            if len(cards):
                cardExists = True
        else:
            cardTitle = bugTitle
            # 1 look for existence of the card
            cards = trello.searchCardsByName(cardTitle)
            # check if we actually have a match
            # it looks like the API search query might do a fuzzy search, so we want to
            # make sure we only get a full match
            for card in cards:
                if card['name'] == cardTitle:
                    cardExists = True
        if cardExists:
            if debug:
                print "Card %s already exists." % cardTitle
            continue

        bugUrl = 'https://bugzilla.wikimedia.org/%s' % entry.get('id')
        # add card to current board
        trello.postNewCard(cardTitle, bugUrl, tListId)
    bingle.updatePickleTime()
