#!/usr/bin/env python

import ConfigParser
import re
import json
import requests
from optparse import OptionParser
from cgi import escape as htmlEscape

from lib.bingle import Bingle
from lib.mingle import Mingle


def createDictionaryFromPropertiesList(properties):
    return dict((key.strip(), value.strip()) for key, value in (prop.split(',')
                for prop in properties.split(';') if prop.find(',') > -1))


def postComments(auth, apiBaseUrl, comments, mingle_id):
    pos = mingle_id.rfind('/') + 1
    mingle_id = mingle_id[pos:]
    mingle_id = mingle_id.replace('.xml', '')
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    url = '%s%s/%s/comments.xml' % (apiBaseUrl, 'cards', mingle_id)
    # the first comment is already used in the summary of the mingle card.
    comments = comments.get('comments')[1:]
    for comment in comments:
        payload = {'comment[content]': '%s\n#%s' % (
            comment.get('text'), mingle_id)}
        response = requests.post(url,
                                 data=payload,
                                 auth=(auth.get(
                                       'username'), auth.get('password')),
                                 headers=headers)


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-c", "--config", dest="config",
                      help="Path to bingle config file", default="bingle.ini")
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

    bingle = Bingle(debug=debug, picklePath=picklePath)

    # prepare Mingle instance
    mingle = Mingle(auth, apiBaseUrl)

    fromTime = bingle.getTimeFromPickle()
    bugzillaPayload = {'method': 'Bug.search', 'params': json.dumps([{
        'product': product,
        'component': component,
        'status': ['UNCONFIRMED', 'NEW'],
        'last_change_time': fromTime,
    }])}
    for bug in bingle.getBugEntries(bugzillaPayload):
        bingle.info("Bug XML: %s" % bug)
        # see if there's a mingle card matching this bug
        if len(bugIdFieldName) > 0:
            foundBug = mingle.findCardNumByBugId(
                bugCard, bug.get('id'), bugIdFieldName)
        else:
            foundBug = mingle.findCardNumByBugName(
                bugCard, bug.get('id'), bug.get('summary'))
        bingle.info(mingle.dumpRequest())
        if len(foundBug) > 0:
            bingle.info('Existing card(s) %s match bug %s, so skip it.' % (
                ','.join([str(m['Number']) for m in foundBug]),
                bug.get('id')))
            continue
        else:
            bingle.info('Did not find card matching bug %s, so add it.'
                        % (bug.get('id')))

        # retrieve bug comments
        comment_payload = {'method': 'Bug.comments', 'params': json.dumps(
            [{'ids': ['%s' % bug.get('id')]}])}
        comments = bingle.getBugComments(comment_payload, bug.get('id'))
        link = '<br><p>Full bug report at https://bugzilla.wikimedia.org/%s' \
            '</p>' % bug.get('id')

        bugCardName = mingle.generateMingleBugCardName(
            bug.get('id', '---'), bug.get('summary').encode('ascii', 'ignore'))
        # set common mingle parameters
        description = htmlEscape(
            comments.get('comments')[0].get('text')).replace(
            "\n", "<br />") + link

        cardParams = {
            'card[name]': bugCardName,
            'card[card_type_name]': bugCard,
            'card[description]': description,
            'card[created_by]': auth['username'],
        }

        cardLocation = mingle.addCard(cardParams)
        bingle.info(mingle.dumpRequest())

        postComments(auth, apiBaseUrl, comments, cardLocation)

        # set custom mingle properties
        properties = {}
        for key, value in bugzillaProperties.iteritems():
            properties[value] = bug.get(key, '')

        properties.update(mingleProperties)

        for prop, value in properties.iteritems():
            propName = prop.strip('\'').strip('"')
            propValue = mapping.get(value, value).strip('\'').strip('"')
            cardParams = {
                'card[properties][][name]': propName,
                'card[properties][][value]': propValue
            }
            mingle.updateCardByLocation(cardLocation, cardParams)

        bingle.info(mingle.dumpRequest())

        # include bug ID if configured as a property
        if len(bugIdFieldName):
            bugId = bug.get('id')
            cardParams = {
                'card[properties][][name]': bugIdFieldName,
                'card[properties][][value]': bugId,
            }
            mingle.updateCardByLocation(cardLocation, cardParams)
            bingle.info(mingle.dumpRequest())

        # post comment with mingle card it back to bugzilla bug
        pos = cardLocation.rfind('/')
        cardId = cardLocation[pos:-4]
        comment = 'Prioritization and scheduling of this bug is tracked on ' \
            'Mingle card %scards%s' % (mingleUrlBase, cardId)
        bugzilla_payload = {
            'jsonrpc': '1.1',
            'method': 'Bug.add_comment', 'id': 1,
            'params': [{
                'id': '%s' % bug.get('id'),
                'Bugzilla_login': config.get('auth_bugzilla', 'username'),
                'Bugzilla_password': config.get('auth_bugzilla', 'password'),
                'comment': comment
            }]
        }
        bingle.addBugComment(bugzilla_payload, bug.get('id'))

    bingle.updatePickleTime()
