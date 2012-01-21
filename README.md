flyer-poke
================================================================================
================================================================================

Pokes people until they self-report they are done with flyering.

STORIES
================================================================================
1. Joe is a member of the ADI, and they are putting on their massive
development push of the year. To get out the word, all the members of
ADI need to go forth and flyer, for that is sadly one of the best ways
to get the word out. However, Joe is still quite human and forgetful:
when his fellow committee member emails him the flyer pdf, he puts it
off and eventually forgets about it a few days later, and the ADI
doesn't get the audience size it wanted. However, his fellow committee
member instead uses flyer-poke, and it nags Joe with daily emails,
reminding him of an unfinished task and filling him with shame. After
a few days, he flyers the fuck out of Schermerhorn and saves the day!

2. Norg is an event organizer: he wants everyone to come to his event,
and he has a sweet flyer so everyone can know about it and come. He
logs onto flyer-poke, signs in with his UNI, tosses the PDF of his
sweet flyer onto the site, and sends to the pre-entered mailing list
of members helping out with flyering. He fires and forgets, relying on
the auto-refresh after mondays to get the flyers reposted after weekly
clearings of flyers.

3. Shog is also an event organizer, but he wants to keep tighter tabs
on how his flunkies are doing, specifically, looking at how fast
people are flyering and punishing them from his skull throne
appropriately. However, no one gives a shit about this feature,
because we are all adults here.

4. Nathan is a software writer: he wants people to flyer, but he also
doesn't want to facilitate spam. He builds flyer-poke to do this,
requiring University IDs to participate, possibly routing mail to only
columbia students, and wielding a biznazty banhammur.


TODO
================================================================================
 * see github issues tracker, that is where all the things are

Wish list:
 * Gamify the process: who's flyered the fastest?
 * Get the flyer generator integrated
 * location survey to group members: decide who flyers where with minimum fuss

Things to check out:
 * http://code.google.com/appengine/docs/python/blobstore/overview.html

INSTALL
================================================================================
 * git clone this guy from github
 * copy over config.py.template to config.py, configure appropriately
 * you'll need to make your own auth endpoint: copy the example of
   WIND_auth.py, which presumes an oauth-like authentication
   scheme. If you don't have one, then you can use openid or facebook
 * get a google account
 * make an appengine app, choose an appropriate subdomain
   (Columbia has flyercu.appspot.com)
 * using the appengine sdk, upload the app to appengine
 * ???
 * PROFIT!!!

USAGE
================================================================================
* If it is not self-explanatory, then I have failed, and I will have
  to impale myself on several sharp spoons. I'll brb.

ACK
================================================================================
 * gae-sessions <https://github.com/dound/gae-sessions>
 * http://blog.notdot.net/2010/01/ReferenceProperty-prefetching-in-App-Engine