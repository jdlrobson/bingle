import pickle
import requests
import feedparser
import json
from datetime import datetime


class Bingle:

    def __init__(self, picklePath='bingle.pickle', debug=False, feedUrl=None):
        self.setDebug(debug)
        self.setPicklePath(picklePath)
        if feedUrl is not None:
            self.setFeedUrl(feedUrl)

    def setPicklePath(self, picklePath):
        self.picklePath = picklePath
        debug = "Pickle path: %s" % picklePath
        self.info(debug)

    def setDebug(self, debug):
        if not isinstance(debug, bool):
            raise TypeError('Debug param must be a boolean')
        self.debug = debug

    def info(self, out):
        if self.debug is True:
            print "[INFO] %s" % out

    def getBugzillaFeedUrl(self, feedUrl):
		# hack! forced UTC timezone, could cause problems
        fromTime = self.getTimeFromPickle()
        if fromTime is not None:
            feedUrl = feedUrl + '&v1=%s' % fromTime
        self.setPickleTimeNow()
        return feedUrl

    def setPickleTimeNow(self):
        now = datetime.now().strftime('%Y-%m-%d %H:%M UTC')
        self.newPickleTime = now

    def getTimeFromPickle(self):
        try:
            pFile = open(self.picklePath, 'rb')
            fromTime = pickle.load(pFile)
            pFile.close()
        except:
            self.info("Pickle file could not be opened")
            fromTime = None
        debug = "From time: %s" % fromTime
        self.info(debug)
        return fromTime

    def updatePickleTime(self, time=None):
        if not time:
            time = self.newPickleTime
        debug = "Pickling time: %s" % time
        self.info(debug)
        self.pickleTime(time)

    def pickleTime(self, timeToPickle):
        pFile = open(self.picklePath, 'w+b')
        pickle.dump(timeToPickle, pFile)
        pFile.close()

    def generateBugCardName(self, bugId, bugName):
        # remove extraneous spaces mid-string; do the same here
        bugName = ' '.join(bugName.split())
        return '[Bug %s] %s' % (bugId, bugName.replace("'", "\'"))

    def getFeedEntries(self):
        feed = feedparser.parse(self.feedUrl)
        self.info("Number of bugs found: %d" % len(feed.entries))
        return feed

    def getBugEntries(self, payload):
        self.setPickleTimeNow()
        response = requests.get('https://bugzilla.wikimedia.org/jsonrpc.cgi', params=payload)
        response.raise_for_status()
        self.info("Number of bugs found: %d" % len(response.json().get('result',{}).get('bugs')))
        return response.json().get('result',{}).get('bugs', {})

    def getBugComments(self, payload, bug_id):
        response = requests.get('https://bugzilla.wikimedia.org/jsonrpc.cgi', params=payload)
        response.raise_for_status()
        self.info("Number of comments found: %d" % len(response.json().get('result', {}).get('bugs', {}).get('%s' % bug_id).get('comments')))
        return response.json().get('result', {}).get('bugs', {}).get('%s' % bug_id)

    def addBugComment(self, payload,  bug_id):
        headers = {'content-type': 'application/json'}
        response = requests.post('https://bugzilla.wikimedia.org/jsonrpc.cgi', data=json.dumps(payload), headers=headers)
        response.raise_for_status()
        self.info("Posted comment %s to bug %s" % (payload.get('params', {})[0].get('comment'), bug_id))

    def setFeedUrl(self, feedUrl):
        self.feedUrl = self.getBugzillaFeedUrl(feedUrl)
        self.info(self.feedUrl)
