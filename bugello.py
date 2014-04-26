#!/usr/bin/env python

import ConfigParser
import json
import html2text
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

        # retrieve bug comments @TODO refactor this (duplicating from bingle)
        comment_payload = {'method': 'Bug.comments', 'params': json.dumps(
            [{'ids': ['%s' % bugId]}])}
        comments = bingle.getBugComments(comment_payload, bugId)
        link = '<br><p>Full bug report at https://bugzilla.wikimedia.org/%s' \
            '</p>' % bugId

        # set common mingle parameters
        description = comments.get('comments')[0].get('text').replace(
            "\n", "<br />") + link

        # add card to current board
        result = trello.postNewCard(cardTitle, html2text.html2text(description), tListId)

        # post additional comments
        comments = comments.get('comments')[1:]
        for comment in comments:
            trelloComment = '%s ~%s' % (comment.get('text'), comment.get('author'))
            trello.postComment(result.json().get('id'), trelloComment)
    bingle.updatePickleTime()
