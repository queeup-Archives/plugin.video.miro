# -*- coding: utf-8 -*-

# Imports
import os
import re
import sys
import time
import errno
import shelve
import shutil
import hashlib
import tempfile
import urllib
import urllib2
import simplejson
import feedparser
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

# DEBUG
DEBUG = False

__addon__ = xbmcaddon.Addon()
__plugin__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__icon__ = __addon__.getAddonInfo('icon')
__fanart__ = __addon__.getAddonInfo('fanart')
__path__ = __addon__.getAddonInfo('path')
__cachedir__ = __addon__.getAddonInfo('profile')
__language__ = __addon__.getLocalizedString
__settings__ = __addon__.getSetting

CACHE_1MINUTE = 60
CACHE_1HOUR = 3600
CACHE_1DAY = 86400
CACHE_1WEEK = 604800
CACHE_1MONTH = 2592000

CACHE_TIME = CACHE_1HOUR

MIRO_URL = 'http://www.miroguide.com/'
MIRO_API = 'https://www.miroguide.com/api/'

# On windows profile folder not created automaticly
if not os.path.exists(xbmc.translatePath(__cachedir__)):
  if DEBUG:
    print 'Profile folder not exist. Creating now for database!'
  os.mkdir(xbmc.translatePath(__cachedir__))

# Our database
db = shelve.open(xbmc.translatePath(__cachedir__ + 'miro.db'), protocol=2)

# Fanart
xbmcplugin.setPluginFanart(int(sys.argv[1]), __fanart__)


class Main:
  def __init__(self):
    if ("action=playyoutubevideo" in sys.argv[2]):
      self.play_youtube_video()
    elif ("action=categories" in sys.argv[2]):
      self.categories(self.arguments('filter'))
    elif ("action=getdirectory" in sys.argv[2]):
      self.get_directory(self.arguments('filter'), self.arguments('title'))
    elif ("action=getfeed" in sys.argv[2]):
      self.get_feed(self.arguments('url', True))
    elif ("action=getmirofeed" in sys.argv[2]):
      self.get_miro_feed(self.arguments('url', True))
    elif ("action=subscribe" in sys.argv[2]):
      self._subscribe(self.arguments('id'),
                      self.arguments('name', True),
                      self.arguments('feedurl', True),
                      self.arguments('thumbnail_url'),
                      self.arguments('description',))
      self._notification(__language__(30101), __language__(30103))
    elif ("action=unsubscribe" in sys.argv[2]):
      self._unsubscribe(self.arguments('id', False))
      self._notification(__language__(30102), __language__(30104))
    elif ("action=mysubscription" in sys.argv[2]):
      self.get_subscriptions()
    else:
      self.main_menu()

  def main_menu(self):
    if DEBUG:
      self.log('main_menu()')
    category = []
    # If keys exist in miro.db show My Subscription directory.
    if db.keys() != list():
      if DEBUG:
        self.log('My Subscriptions directory activated.')
      category += [{'title':__language__(30201), 'url':'', 'action':'mysubscriptions'}, ]
    db.close()
    category += [{'title':__language__(30202), 'url':'https://www.miroguide.com/api/list_categories?datatype=json', 'action':'categories', 'filter':'category'},
                 {'title':__language__(30203), 'url':'https://www.miroguide.com/api/list_languages?datatype=json', 'action':'categories', 'filter':'language'},
                 {'title':__language__(30204), 'url':'http://feeds.feedburner.com/miroguide/new', 'action':'getmirofeed'},
                 {'title':__language__(30205), 'url':'http://feeds.feedburner.com/miroguide/featured', 'action':'getmirofeed'},
                 {'title':__language__(30206), 'url':'http://feeds.feedburner.com/miroguide/popular', 'action':'getmirofeed'},
                 {'title':__language__(30207), 'url':'http://feeds.feedburner.com/miroguide/toprated', 'action':'getmirofeed'},
                 {'title':__language__(30208), 'url':'https://www.miroguide.com/rss/tags/HD', 'action':'getmirofeed'},
                 #{'title':__language__(30209), 'url':'https://www.miroguide.com/rss/search/', 'action':'getmirofeed'},
                 ]
    for i in category:
      try:
        _filter = i['filter']
      except:
        _filter = ''
      listitem = xbmcgui.ListItem(i['title'], iconImage='DefaultFolder.png', thumbnailImage=__icon__)
      parameters = '%s?action=%s&url=%s&filter=%s' % \
                   (sys.argv[0], i['action'], urllib.quote_plus(i['url']), _filter)
      xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(parameters, listitem, True)])
    # Sort methods and content type...
    xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_NONE)
    # End of directory...
    xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

  def get_subscriptions(self):
    if DEBUG:
      self.log('get_subscriptions()')
    for k, v in db.iteritems():
      _id = k
      name = v['name']
      feedUrl = v['url']
      if not feedUrl:
        continue
      try:
        thumb = v['thumbnail_url']
      except:
        pass
      summary = v['description']
      listitem = xbmcgui.ListItem(name, iconImage='DefaultVideo.png', thumbnailImage=thumb)
      listitem.setInfo(type='video',
                       infoLabels={'title': name,
                                   'plot': summary})
      contextmenu = [(__language__(30102), 'XBMC.RunPlugin(%s?action=unsubscribe&id=%s)' % \
                                                          (sys.argv[0], _id))]
      listitem.addContextMenuItems(contextmenu, replaceItems=False)
      parameters = '%s?action=getfeed&url=%s' % (sys.argv[0], urllib.quote_plus(feedUrl))
      xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(parameters, listitem, True)])
    db.close()
    # Sort methods and content type...
    xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE)
    # End of directory...
    xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

  def categories(self, _filter):
    if DEBUG:
      self.log('categories()')
    categories = simplejson.loads(fetcher.fetch(self.arguments('url', True), CACHE_TIME))
    for category in categories:
      title = category['name']
      listitem = xbmcgui.ListItem(title, iconImage='DefaultFolder.png', thumbnailImage=__icon__)
      parameters = '%s?action=getdirectory&title=%s&filter=%s' % (sys.argv[0], urllib.quote_plus(title), _filter)
      xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(parameters, listitem, True)])
    # Sort methods and content type...
    xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_NONE)
    # End of directory...
    xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

  def get_directory(self, _filter, title, sort='popular'):
    if DEBUG:
      self.log('get_directory()')
    # for next page
    try:
      offset = int(self.arguments('offset')) + 20
    except:
      offset = 0
    url = MIRO_API + 'get_channels?datatype=json&filter=%s&filter_value=%s&sort=%s&offset=%s' % (_filter, title, sort, offset)
    results = simplejson.loads(fetcher.fetch(url, CACHE_TIME))
    totalitem = len([i['id'] for i in results])
    for entry in results:
      _id = entry['id']
      name = entry['name'].encode('utf-8', 'replace')
      publisher = entry['publisher']
      feedUrl = entry['url']
      if not feedUrl:
        continue
      if not len(entry['item']):
        continue
      try:
        thumb = entry['thumbnail_url']
      except:
        pass
      summary = entry['description']
      subscribe_hit_url = entry['subscribe_hit_url']
      subscription_count = entry['subscription_count']
      hi_def = entry['hi_def']
      average_rating = entry['average_rating']
      listitem = xbmcgui.ListItem(name, iconImage='DefaultVideo.png', thumbnailImage=thumb)
      if self._issubscripted(_id):
        overlay = xbmcgui.ICON_OVERLAY_WATCHED
        contextmenu = [(__language__(30102), 'XBMC.RunPlugin(%s?action=unsubscribe&id=%s)' % \
                                                            (sys.argv[0], _id))]
      else:
        overlay = xbmcgui.ICON_OVERLAY_NONE
        contextmenu = [(__language__(30101), 'XBMC.RunPlugin(%s?action=subscribe&id=%s&name=%s&feedurl=%s&thumbnail_url=%s&description=%s)' % \
                                                            (sys.argv[0], _id, urllib.quote_plus(name), urllib.quote_plus(feedUrl), thumb, summary))]
      listitem.setInfo(type='video',
                       infoLabels={'title': name,
                                   'plot': summary,
                                   'director': publisher,
                                   'overlay': overlay})
      listitem.addContextMenuItems(contextmenu, replaceItems=False)
      parameters = '%s?action=getfeed&url=%s' % (sys.argv[0], urllib.quote_plus(feedUrl))
      xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(parameters, listitem, True)])
    # Next Page
    # If less then 20 we are end of the list. No need next page.
    if not totalitem < 20:
      listitem = xbmcgui.ListItem(__language__(30210), iconImage='DefaultVideo.png', thumbnailImage=__icon__)
      parameters = '%s?action=getdirectory&title=%s&filter=%s&offset=%i' % \
                   (sys.argv[0], title, _filter, offset)
      xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(parameters, listitem, True)])
    # Sort methods and content type...
    xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE)
    #xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_MPAA_RATING)
    #xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_RATING)
    # End of directory...
    xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

  def get_miro_feed(self, url):
    if DEBUG:
      self.log('get_miro_feed()')
    feedHtml = fetcher.fetch(url, CACHE_TIME)
    encoding = feedHtml.split('encoding="')[1].split('"')[0]
    feedHtml = feedHtml.decode(encoding, 'ignore').encode('utf-8')

    feed = feedparser.parse(feedHtml)
    for item in feed['items']:
      infoLabels = {}
      if item.link.startswith('http://www.miroguide.com/feeds/'):
        _id = item.link.replace('http://www.miroguide.com/feeds/', '')
      else:
        _id = re.findall('/(.+?).jpeg', item.thumbnail)[0]
      title = infoLabels['title'] = item.title.replace('&#39;', "'").replace('&amp;', '&').replace('&quot;', '"')
      if isinstance(title, str):  # BAD: Not true for Unicode strings!
        try:
          title = infoLabels['title'] = title.encode('utf-8', 'replace')  # .encode('utf-8')
        except:
          continue  # skip this, it likely will bork
      # I put it here because above isinstance code not working well with some languages.
      title = infoLabels['title'] = title.encode('utf-8', 'replace')  # .encode('utf-8')
      try:
        infoLabels['date'] = item.updated
      except:
        infoLabels['date'] = ''
      subtitle = infoLabels['date']
      soup = self._strip_tags(item.description)  # , convertEntities=BSS.HTML_ENTITIES
      try:
        infoLabels['plot'] = soup.contents[0]
      except:
        infoLabels['plot'] = item.description.encode('utf-8', 'ignore')
      thumb = item.thumbnail
      if thumb == '':
          thumb = __icon__
      feedUrl = item["summary_detail"]["value"].replace('amp;', '')
      feedUrl = feedUrl[feedUrl.find('url1=') + 5:]
      feedUrl = feedUrl[:feedUrl.find('&trackback1')].replace('%3A', ':')
      feedUrl = feedUrl.replace(' ', '%20')

      listitem = xbmcgui.ListItem(title, iconImage='DefaultVideo.png', thumbnailImage=thumb)
      if self._issubscripted(_id):
        infoLabels['overlay'] = xbmcgui.ICON_OVERLAY_WATCHED
        contextmenu = [(__language__(30102), 'XBMC.RunPlugin(%s?action=unsubscribe&id=%s)' % \
                                                            (sys.argv[0], _id))]
      else:
        infoLabels['overlay'] = xbmcgui.ICON_OVERLAY_NONE
        contextmenu = [(__language__(30101), 'XBMC.RunPlugin(%s?action=subscribe&id=%s&name=%s&feedurl=%s&thumbnail_url=%s&description=%s)' % \
                                                            (sys.argv[0], _id, urllib.quote_plus(title), urllib.quote_plus(feedUrl), thumb, ''))]
      listitem.setInfo(type='video', infoLabels=infoLabels)
      listitem.addContextMenuItems(contextmenu, replaceItems=False)
      parameters = '%s?action=getfeed&url=%s' % (sys.argv[0], urllib.quote_plus(feedUrl))
      xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(parameters, listitem, True)])
    # Sort methods and content type...
    xbmcplugin.setContent(int(sys.argv[1]), 'movie')
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE)
    if infoLabels['date']:
      xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_DATE)
    # End of directory...
    xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

  def get_feed(self, url):
    if DEBUG:
      self.log('get_feed()')
    feedHtml = fetcher.fetch(url, CACHE_TIME)
    encoding = re.search(r"encoding=([\"'])([^\1]*?)\1", feedHtml).group(2)
    feedHtml = feedHtml.decode(encoding, 'ignore').encode('utf-8')

    feed = feedparser.parse(feedHtml)
    if 'items' in feed:
      items = feed['items']
    else:
      items = feed['entries']
    hasInvalidItems = False
    for item in items:
      infoLabels = {}
      infoLabels['duration'] = ''
      title = infoLabels['title'] = self._strip_tags(item.title.replace('&#39;', "'").replace('&amp;', '&'))
      if isinstance(title, str):  # BAD: Not true for Unicode strings!
        try:
          title = infoLabels['title'] = title.encode('utf-8', 'replace')  # .encode('utf-8')
        except:
          continue  # skip this, it likely will bork
      try:
        date_p = item.date_parsed
        infoLabels['date'] = time.strftime("%d.%m.%Y", date_p)
        #date = item.updated
      except:
        infoLabels['date'] = ''
      subtitle = infoLabels['date']
      soup = self._strip_tags(item.description)  # , convertEntities=BSS.HTML_ENTITIES
      if 'subtitle' in item:
        infoLabels['plot'] = item.subtitle
      else:
        try:
          infoLabels['plot'] = soup.contents[0]
        except:
          infoLabels['plot'] = item.description.encode('utf-8', 'ignore')
      try:
        thumb = item.media_thumbnail[0]['url']
      except:
        try:
          thumb = item.thumbnail
        except:
          thumb = ''
      key = ''
      if 'itunes_duration' in item:
        infoLabels['duration'] = item.itunes_duration
      if 'enclosures' in item:
        for enclosure in item["enclosures"]:
          key = enclosure['href']
          try:
            infoLabels['size'] = int(enclosure['length'])
          except:
            infoLabels['size'] = 0
      if key == '':
        key = item.link
      if key.count('.torrent') > 0:
        hasInvalidItems = True
        #insert message box re: not supporting torrents here.
        continue
      if key.count('.html') > 0:
        hasInvalidItems = True
        continue
      if key.count('youtube.com') > 0:
        if DEBUG:
          self.log('Geting youtube video id to play with plugin.video.youtube add-on')
        video_id = key.split('=')[1].split('&')[0]
        thumb = 'http://i.ytimg.com/vi/%s/default.jpg' % video_id
        key = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s' % (video_id)
      if thumb == '':
          thumb = __icon__
      if hasInvalidItems:
        print ('Invalid items', 'No supported media types found.')
      listitem = xbmcgui.ListItem(title, iconImage='DefaultVideo.png', thumbnailImage=thumb)
      listitem.setInfo(type='video', infoLabels=infoLabels)
      listitem.setProperty('IsPlayable', 'true')
      xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(key, listitem, False)])
    # Sort methods and content type...
    xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    if infoLabels['date']:
      xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE)
    if infoLabels['duration']:
      xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_RUNTIME)
    try:
      if infoLabels['size']:
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_SIZE)
    except:
      pass
    # End of directory...
    xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

  def _strip_tags(self, _str):
    return re.sub(r'<[^<>]+>', '', _str)

  def _subscribe(self, _id, title, url, thumb, desc):
    if DEBUG:
      self.log('_subscribe()')
    try:
      db[str(_id)] = {'name': title,
                     'url': url,
                     'thumbnail_url': thumb,
                     'description': desc}
    finally:
      db.close()

  def _unsubscribe(self, _id):
    if DEBUG:
      self.log('_unubscribe()')
    try:
      del db[str(_id)]
    finally:
      db.close()

  def _issubscripted(self, _id):
    if DEBUG:
      self.log('_issubscripted()')
    if str(_id) in db:
      return True
    else:
      return False
    db.close()

  def _notification(self, title, message):
    if DEBUG:
      self.log('_notification()\ntitle: %s\nmessage: %s' % (title, message))
    xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % \
                                     (title.encode('utf-8', 'ignore'), message.encode('utf-8', 'ignore'), 6000, __icon__))

  def arguments(self, arg, unquote=False):
    _arguments = dict(part.split('=') for part in sys.argv[2][1:].split('&'))
    if unquote:
      return urllib.unquote_plus(_arguments[arg])
    else:
      return _arguments[arg]

  def log(self, description):
    xbmc.log("[ADD-ON] '%s v%s': DEBUG: %s" % (__plugin__, __version__, description.encode('ascii', 'ignore')), xbmc.LOGNOTICE)


class DiskCacheFetcher:
  def __init__(self, cache_dir=None):
    # If no cache directory specified, use system temp directory
    if cache_dir is None:
      cache_dir = tempfile.gettempdir()
    if not os.path.exists(cache_dir):
      try:
        os.mkdir(cache_dir)
      except OSError, e:
        if e.errno == errno.EEXIST and os.path.isdir(cache_dir):
          # File exists, and it's a directory,
          # another process beat us to creating this dir, that's OK.
          pass
        else:
          # Our target dir is already a file, or different error,
          # relay the error!
          raise
    self.cache_dir = cache_dir

  def fetch(self, url, max_age=CACHE_TIME):
    # Use MD5 hash of the URL as the filename
    filename = hashlib.md5(url).hexdigest()
    filepath = os.path.join(self.cache_dir, filename)
    if os.path.exists(filepath):
      if int(time.time()) - os.path.getmtime(filepath) < max_age:
        if DEBUG:
          print 'File exists and reading from cache.'
        return open(filepath).read()
    # Retrieve over HTTP and cache, using rename to avoid collisions
    if DEBUG:
      print 'File not yet cached or cache time expired. File reading from URL and try to cache to disk'
    data = urllib2.urlopen(url).read()
    fd, temppath = tempfile.mkstemp()
    fp = os.fdopen(fd, 'w')
    fp.write(data)
    fp.close()
    shutil.move(temppath, filepath)
    return data

fetcher = DiskCacheFetcher(xbmc.translatePath(__cachedir__))

if __name__ == '__main__':
  Main()