#/usr/bin/env python
import ConfigParser
import re
import requests
from optparse import OptionParser
from lib.trello import Trello

def check_broken_status(url):
    headers = {'content-type': 'application/json'}
    response = requests.get(url + '/api/json?pretty=true', headers=headers)
    data = response.json()
    project = data['displayName']
    last_success = data['lastSuccessfulBuild']['number']
    last_failure = data['lastUnsuccessfulBuild']['number']
    # check if the last fail was more recent then the success
    if last_failure > last_success:
        # we are in an error state. How many errors?
        broken_for_builds = last_failure - last_success
    else:
        broken_for_builds = 0

    return {
        'url': url,
        'project': project,
        'last_passed': last_success,
        'num_fails': broken_for_builds
    }

def is_dupe(trello, cardTitle):
    prefix = cardTitle[0:cardTitle.find(']')+1]
    cards = trello.searchCardsByName(prefix)
    if len(cards) > 0:
        return True
    else:
        return False

def make_card(trello, info):
    build = info['last_passed']
    project = info['project']
    args = {
        'build': build,
        'project': project,
        'url': info['url']
    }
    cardTitle = '[%(project)s Build > %(build)s] Failing Selenium tests!'%args
    description = 'Tests have been failing since build %(build)s.\n\n %(url)s\n'%args

    # post the card
    if build is None:
        print "Ignoring. Can't find a recent build that passed for %s"%project
    elif not is_dupe(trello, cardTitle):
        tListId = trello.getBugListId()
        print "Posting card for %s with title %s"%(project, cardTitle)
        result = trello.postNewCard(cardTitle, description, tListId, labels='red')
    else:
        print 'Ignoring. Card with title %s already exists.'%cardTitle

def init(config):
    trelloConfig = config.items('trello')
    trello = Trello(config=trelloConfig, debug=True)
    try:
        threshold = int(config.get('selenium', 'threshold'))
    except KeyError:
        threshold = 3

    try:
        project_url = config.get( 'selenium', 'projectUrl' )
        urls = project_url.split( '\n' )
        print urls
        for url in urls:
            status = check_broken_status(url)
            failures = status['num_fails']
            print "%s failures in %s."%(failures,status['project'])
            if failures >= threshold:
                print "Making card."
                make_card(trello, status)
    except ConfigParser.NoOptionError:
        print 'Please set projectUrl variable in section selenium in bugello.ini'

if __name__ == "__main__":
    # config stuff
     parser = OptionParser()
     parser.add_option("-c", "--config", dest="config",
                       help="Path to bugello config file", default="bugello.ini")
     (options, args) = parser.parse_args()
     config = ConfigParser.ConfigParser()
     config.optionxform = str # needed to preserve case of option names
     config.read(options.config)
     init(config)
