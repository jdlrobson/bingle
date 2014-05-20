#/usr/bin/env python
import ConfigParser
import feedparser
#from config import *

feed_url_chrome = 'https://wmf.ci.cloudbees.com/job/MobileFrontend-en.m.wikipedia.beta.wmflabs.org-linux-chrome/rssAll'
feed_url_firefox = 'https://wmf.ci.cloudbees.com/job/MobileFrontend-en.m.wikipedia.beta.wmflabs.org-linux-firefox/rssAll'

if __name__ == "__main__":
    def check_broken_status(url):
        feed = feedparser.parse(url)
        broken_for_builds = 0
        url = None
        for entry in feed.entries:
            if 'normal' in entry.title:
                break
            if 'broken' in entry.title:
                if not url:
                    url = entry.link
                broken_for_builds += 1
            else:
                broken_for_builds = 0

        return {
            'url': url,
            'numfails': broken_for_builds
        }
    
    chrome = check_broken_status(feed_url_chrome)
    firefox = check_broken_status(feed_url_firefox)
    if firefox['numfails'] > 2 or chrome['numfails'] > 2:
        cardTitle = 'Selenium tests at unacceptable fail rate'
        description = 'Tests have been failing for an unacceptable time.\n\n'
        if chrome['numfails'] > 0:
            description += 'Chrome: %s consecutive failures.\n%s\n'%(chrome['numfails'], chrome['url'])
        if firefox['numfails'] > 0:
            description += 'Firefox: %s consecutive failures.\n%s\n'%(firefox['numfails'], firefox['url'])
        # post the card
        config = ConfigParser.ConfigParser()
        debug = config.getboolean('debug', 'debug')
        trelloConfig = config.items('trello')
        trello = Trello(config=trelloConfig, debug=debug)
        tListId = trello.getBugListId()
        result = trello.postNewCard(cardTitle, description, tListId)

    