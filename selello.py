#/usr/bin/env python
import ConfigParser
import re
import feedparser
from optparse import OptionParser
from lib.trello import Trello

def check_broken_status(url):
    feed = feedparser.parse(url)
    broken_for_builds = 0
    url = None
    build = None
    for entry in feed.entries:
        if 'normal' in entry.title:
            build = re.search('#([0-9]+)', entry.title).group(1)
            break
        if 'broken' in entry.title:
            if not url:
                url = entry.link
            broken_for_builds += 1

    return {
        'url': url,
        'last_passed': build,
        'num_fails': broken_for_builds
    }

def is_dupe(trello, cardTitle):
    prefix = cardTitle[0:cardTitle.find(']')+1]
    cards = trello.searchCardsByName(prefix)
    if len(cards) > 0:
        return True
    else:
        return False

def make_card(trello, info, browser):
    build = info['last_passed']
    args = {
        'build': build,
        'browser': browser,
        'url': info['url']
    }
    cardTitle = '[%(browser)s Build > %(build)s] Failing Selenium tests!'%args
    description = 'Tests have been failing since build %(build)s.\n\n %(url)s\n'%args

    # post the card
    if build is None:
        print "Ignoring. Can't find a recent build that passed for %s"%browser
    elif not is_dupe(trello, cardTitle):
        tListId = trello.getBugListId()
        print "Posting card for %s with title %s"%(browser, cardTitle)
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
        feed_url_firefox = config.get( 'selenium', 'firefox' )
        firefox = check_broken_status(feed_url_firefox)
        failures = firefox['num_fails']
        print "Firefox: %s failures."%failures
        if failures >= threshold:
            print "Making card."
            make_card(trello, firefox, 'firefox')
    except ConfigParser.NoOptionError:
        print 'Please set firefox variable in section selenium in bugello.ini'

    try:
        feed_url_chrome = config.get( 'selenium', 'chrome' )
        chrome = check_broken_status(feed_url_chrome)
        failures = chrome['num_fails']
        print "Chrome: %s failures."%failures
        if failures >= threshold:
            print "Making card."
            make_card(trello, chrome, 'chrome')
    except ConfigParser.NoOptionError:
        print 'Please set chrome variable in section selenium in bugello.ini'

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
