This is a tool to import bugreports from Bugzilla and create Mingle or Trello cards from those reports. More to come!

## Requirements
* feedparser: https://code.google.com/p/feedparser/
* requests: http://docs.python-requests.org/en/latest/

## To use
*  Prepare a Bugzilla atom feed to follow 
*  Copy bingle.ini.example to bingle.ini
*  Update config vars to your own
*  $ python bingle.py

You can optionally configure bingle to run regularly (eg via cron) - it keeps
track of the last time it ran. If you use a bugzilla atom feed that uses bug
creation date as one of its params, bingle will update the timestamp to the
last time it ran, thereby fetching only bugs that have been added since the
last time bingle was executed.

## Preparing a Bugzilla atom feed for Bingle/Bugello
Bingle expects your Bugzilla atom feed to contain a timestamp in the query
string (specifically the 'v1' query string item). This can use this to find
particular Bugzilla items since a specific period of time - in Bingle's case,
it will update the v1 query string item with the timestamp of the last time
Bingle ran. However, Bingle is not yet that smart. If you Bugzilla atom feed
URL contains a timestamp in the v1 parameter, you will need to REMOVE the
v1 query param from the URL in your ini file. A little confusing, yes, and
something that would be nice to improve. If you're scratching your head over
this, read on.

This is parituclarly useful if you want Bingle to, say, find all bugs for a
particular product that have been created since the last time Bingle ran. To
prepare your atom feed, go into Bugzilla and click into 'Advanced search'.
Prepare your search query as you normally would (remember, this query should
return all of the bugs that you will want to import into Mingle or Trello).
At the end of the 'Advanced search' form, you should see a section called
'Custom search'. Set the dropdown to 'Creation date', 'is greater than', then
whatever date (the specific date you enter doesn't actually matter here -
Bingle will handle applying the correct timestamp at runtime). Hit 'search'.
At the bottom of the search results, you should see a link to 'Feed'. Click
that. Copy/paste the resulting URL into your bingle.ini ([urls]/bugzillaFeed).
Be sure to REMOVE the '&v1=<some timestamp>' from the URL.

## First run
If you follow the above example for generating your Bugzilla feed, the first
time Bingle runs, it will find all bugs that match your search criteria that
have been created since... forever. Subsequent runs will search for bugs
created since the last time Bingle ran.
