import requests
import re
import sys

class Trello:
    appKey = None
    appName = None
    boardBaseName = None
    targetListName = None
    pin = None
    useLatestBoard = False
    prefixBugTitle = False
    debug = False

    def __init__(self, config=None, debug=False):
        if config:
            self.loadConfig(config)
        if debug is True:
            self.debug = True
        self.pinCheck()

    def getBaseParams(self):
        return {
            'key': self.appKey,
            'token': self.pin
        }

    def loadConfig(self, config):
        # expects a list of tuples from ConfigParser.items()
        truths = (1, 'yes', 'true', 'True', 'on', True, '1')
        falses = (0, 'no', 'false', 'False', 'off', False, '0')
        validConfigParams = (
            'appKey',
            'appName',
            'boardBaseName',
            'targetListName',
            'pin',
            'useLatestBoard',
            'prefixBugTitle'
        )
        bools = ('useLatestBoard', 'prefixBugTitle')
        for items in config:
            if items[0] not in validConfigParams:
                continue
            elif items[0] in bools:
                if items[1] in truths:
                    setattr(self, items[0], True)
                elif items[1] in falses:
                    setattr(self, items[0], False)
            else:
                setattr(self, items[0], items[1])

    def getBoardId(self):
        boardQueryParams = {
            'query': self.boardBaseName,
            'modelTypes': 'boards',
            'board_fields': 'name'
        }
        payload = dict(self.getBaseParams().items() + boardQueryParams.items())
        r = requests.get('https://trello.com/1/search', params=payload)
        # don't try/except because if this fails, we can't go further anyway
        r.raise_for_status()
        boards = r.json()['boards']
        if self.useLatestBoard:
            if self.debug:
                print "Searching for latest board..."
            return self.getLatestBoardId(boards)
        else:
            if not len(boards):
                print "No board found by the name %s; exiting." % self.boardBaseName
                sys.exit(1)
            boardId = None
            # in case the query returned multiple boards, pick the right one
            for board in boards:
                if board['name'] == self.boardBaseName:
                    boardId = board['id']
            if not boardId:
                print "Could not find board by name %s." % self.boardBaseName
                sys.exit(1)
        if self.debug:
            print "Using board ID %s" % boards[0]['id']
        return boardId

    def getLatestBoardId(self, boardsJson):
        # sprint names are like: 'Mobile App - Sprint 9'
        # we want to find the latest
        sprintNumRegex = re.compile('sprint (\d+)', re.I|re.U)
        boards = []
        for board in boardsJson:
            sprintNum = sprintNumRegex.search(board['name'])
            if sprintNum:
                # do we really need name? may come in handy
                boards.append(
                    (int(sprintNum.group(1)),
                        board['id'],
                        board['name'])
                )
        if not len(boards):
            print "There are no valid boards for which to add cards."
            exit(1)
        # pick the biggest sprintNum
        boards.sort()
        boardId = boards[-1][1]
        if self.debug:
            print "Board name: %s" % boards[-1][2].encode('UTF-8', 'ignore')
        return boardId

    def searchCardsByName(self, cardTitle):
        cards = None
        cardQueryParams = {
            'query': cardTitle,
            'card_fields': 'name',
            'modelTypes': 'cards'
        }
        payload = dict(self.getBaseParams().items() + cardQueryParams.items())
        try:
            r = requests.get('https://trello.com/1/search', params=payload)
            r.raise_for_status()
            cards = r.json()['cards']
        except requests.exceptions.HTTPError as e:
            if self.debug:
                print "Error querying for: %s" % cardTitle
                print "Reason: %s" % e
        return cards

    def postNewCard(self, cardTitle, bugUrl, tListId):
        newCardParams = {
            'name': cardTitle,
            'desc': bugUrl,
            'idList': tListId,
            'due': None
        }
        payload = dict(self.getBaseParams().items() + newCardParams.items())
        try:
            r = requests.post('https://trello.com/1/cards', params=payload)
            r.raise_for_status()
            return r
        except requests.exceptions.HTTPError as e:
            if self.debug:
                print "Error adding card: %s" % cardTitle
                print "Reason: %s" % e
            sys.exit(-1)

    def pinCheck(self):
        # check for authorization pin
        # note that this seems easier than dealing with oAuth
        # note never expiring pin -
        # maybe make this configurable.
        if not self.pin:
            self.pinPrompt()

    def pinPrompt(self):
        pinUrl = "https://trello.com/1/authorize?key=%s&name=%s&expiration=never&response_type=token&scope=read,write" % \
            (self.appKey, self.appName)
        print "You must add a valid Trello user PIN to your config file."
        print "To get a Trello user PIN, visit:"
        print "%s" % pinUrl
        sys.exit(1)

    def getListIdByName(self, name):
        tListId = None
        boardId = self.getBoardId()
        tListUrl = 'https://trello.com/1/boards/%s/lists' % boardId
        r = requests.get(tListUrl, params=self.getBaseParams())
        # don't try/except, because we can't do anything without this.
        r.raise_for_status()
        tListId = None
        for tList in r.json():
            if tList['name'].lower() == name.lower():
                tListId = tList['id']
                if self.debug:
                    print "List id: %s" % tListId
                break
        if not tListId:
            print "Could not find list: %s" % name
            sys.exit(1)
        return tListId

    def getBugListId(self):
        if not self.targetListName:
            print "No target list name set in config file."
            sys.exit(1)
        return self.getListIdByName(self.targetListName)

    def postComment(self, cardId, comment):
        commentParams = {'text': comment}
        payload = dict(self.getBaseParams().items() + commentParams.items())
        try:
            apiEndpoint = 'https://trello.com/1/cards/%s/actions/comments' % cardId
            r = requests.post(apiEndpoint, params=payload)
            r.raise_for_status()
            return r
        except requests.exceptions.HTTPError as e:
            if self.debug:
                print "Error adding comments for card: %s" % cardId
                print "Reason: %s" % e
            sys.exit(-1)


