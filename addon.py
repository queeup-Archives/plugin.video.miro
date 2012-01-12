# -*- coding: utf-8 -*-

# Debug
Debug = True

# Imports
import re, string, urllib, urllib2, simplejson, feedparser
import md5, os, shutil, tempfile, time, errno
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

__addon__ = xbmcaddon.Addon(id='plugin.video.miro')
__info__ = __addon__.getAddonInfo
__plugin__ = __info__('name')
__version__ = __info__('version')
__icon__ = __info__('icon')
__fanart__ = __info__('fanart')
__path__ = __info__('path')
__cachedir__ = __info__('profile')
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

# Fanart
xbmcplugin.setPluginFanart(int(sys.argv[1]), __fanart__)

class Main:
  def __init__(self):
    if ("action=playyoutubevideo" in sys.argv[2]):
      self.PlayYouTubeVideo()
    elif ("action=categories" in sys.argv[2]):
      self.Categories()
    elif ("action=getdirectory" in sys.argv[2]):
      self.GetDirectory()
    elif ("action=getfeed" in sys.argv[2]):
      self.GetFeed()
    elif ("action=getmirofeed" in sys.argv[2]):
      self.GetMiroFeed()
    else:
      self.START()

  def START(self):
    if Debug: self.LOG('\nSTART function')
    category = [{'title':'Categories', 'url':'https://www.miroguide.com/api/list_categories?datatype=json', 'action':'categories'},
                {'title':'Languages', 'url':'https://www.miroguide.com/api/list_languages?datatype=json', 'action':'categories'},
                {'title':'New Channels', 'url':'http://feeds.feedburner.com/miroguide/new', 'action':'getmirofeed'},
                {'title':'Featured Channels', 'url':'http://feeds.feedburner.com/miroguide/featured', 'action':'getmirofeed'},
                {'title':'Popular Channels', 'url':'http://feeds.feedburner.com/miroguide/popular', 'action':'getmirofeed'},
                {'title':'Top Rated Channels', 'url':'http://feeds.feedburner.com/miroguide/toprated', 'action':'getmirofeed'},
                {'title':'HD Channels', 'url':'https://www.miroguide.com/rss/tags/HD', 'action':'getmirofeed'},
                #{'title':'Search for Feed...', 'url':'https://www.miroguide.com/rss/search/', 'action':'getmirofeed'},
                ]
    for i in category:
      listitem = xbmcgui.ListItem(i['title'], iconImage='DefaultFolder.png', thumbnailImage=__icon__)
      parameters = '%s?action=%s&url=%s&title=%s' % (sys.argv[0], i['action'], urllib.quote_plus(i['url']), i['title'])
      xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(parameters, listitem, True)])
    # Sort methods and content type...
    xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_NONE)
    # End of directory...
    xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

  def Categories(self):
    if Debug: self.LOG('\nCategories function')
    categories = simplejson.loads(fetcher.fetch(self.Arguments('url'), CACHE_TIME))
    if self.Arguments('title') == 'Categories':
      filter = 'category'
    else: filter = 'language'
    for category in categories:
      title = category['name']
      listitem = xbmcgui.ListItem(title, iconImage='DefaultFolder.png', thumbnailImage=__icon__)
      parameters = '%s?action=getdirectory&title=%s&filter=%s' % (sys.argv[0], urllib.quote_plus(title), filter)
      xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(parameters, listitem, True)])
    # Sort methods and content type...
    xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_NONE)
    # End of directory...
    xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

  def GetDirectory(self, sort='popular', limit='50'):
    if Debug: self.LOG('\nGetDirectory function')
    url = MIRO_API + 'get_channels?datatype=json&filter=%s&filter_value=%s&sort=%s' % (self.Arguments('filter'), self.Arguments('title'), sort)
    if limit != '':
      url += '&limit=' + limit

    results = simplejson.loads(fetcher.fetch(url.replace(' ', '+'), CACHE_TIME))
    for entry in results:
      title = entry['name']
      subtitle = entry['publisher']
      feedUrl = entry['url']
      if not feedUrl: continue
      if not len(entry['item']): continue
      try: thumb = entry['thumbnail_url']
      except: pass
      summary = entry['description']
      listitem = xbmcgui.ListItem(title, iconImage='DefaultVideo.png', thumbnailImage=thumb)
      listitem.setInfo(type='video',
                       infoLabels={'title' : title,
                                   'plot' : summary,
                                   'director' : subtitle
                                   })
      parameters = '%s?action=getfeed&url=%s' % (sys.argv[0], urllib.quote_plus(feedUrl))
      xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(parameters, listitem, True)])
    # Sort methods and content type...
    xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE)
    # End of directory...
    xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

  def GetMiroFeed(self, query=''):
    if Debug: self.LOG('\nGetMiroFeed function')
    feedHtml = fetcher.fetch(self.Arguments('url') + query.replace(' ', '+'))
    encoding = feedHtml.split('encoding="')[1].split('"')[0]
    feedHtml = feedHtml.decode(encoding, 'ignore').encode('utf-8')

    feed = feedparser.parse(feedHtml)
    for item in feed['items']:
      infoLabels = {}
      title = infoLabels['title'] = item.title.replace('&#39;', "'").replace('&amp;', '&')
      if isinstance(title, str): # BAD: Not true for Unicode strings!
        try:
          title = infoLabels['title'] = title.encode('utf-8', 'replace') #.encode('utf-8')
        except:
          continue #skip this, it likely will bork
      try:
        infoLabels['date'] = item.updated
      except:
        infoLabels['date'] = ''
      subtitle = infoLabels['date']
      soup = self.StripTags(item.description)#, convertEntities=BSS.HTML_ENTITIES
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
      feddUrl = feedUrl.replace(' ', '%20')

      listitem = xbmcgui.ListItem(title, iconImage='DefaultVideo.png', thumbnailImage=thumb)
      listitem.setInfo(type='video', infoLabels=infoLabels)
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

  def GetFeed(self, title2="", folderthumb=""):
    if Debug: self.LOG('\nGetFeed function')
    feedHtml = fetcher.fetch(self.Arguments('url'))
    encoding = re.search(r"encoding=([\"'])([^\1]*?)\1", feedHtml).group(2) #'
    feedHtml = feedHtml.decode(encoding, 'ignore').encode('utf-8')

    feed = feedparser.parse(feedHtml)
    if 'items' in feed:
      items = feed['items']
    else: items = feed['entries']
    hasInvalidItems = False
    for item in items:
      infoLabels = {}
      #Log(item)
      infoLabels['duration'] = ''
      title = infoLabels['title'] = self.StripTags(item.title.replace('&#39;', "'").replace('&amp;', '&'))
      if isinstance(title, str): # BAD: Not true for Unicode strings!
        try:
          title = infoLabels['title'] = title.encode('utf-8', 'replace') #.encode('utf-8')
        except:
          continue #skip this, it likely will bork
      try:
        date_p = item.date_parsed
        infoLabels['date'] = time.strftime("%d.%m.%Y", date_p)
        #date = item.updated
      except:
        infoLabels['date'] = ''
      subtitle = infoLabels['date']
      soup = self.StripTags(item.description)#, convertEntities=BSS.HTML_ENTITIES
      if item.has_key('subtitle'):
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
        except: thumb = ''
      key = ''
      if item.has_key('itunes_duration'):
            infoLabels['duration'] = item.itunes_duration
      if item.has_key('enclosures'):
        for enclosure in item["enclosures"]:
          key = enclosure['href']
          try:
            infoLabels['size'] = int(enclosure['length'])
          except:
            infoLabels['size'] = ''
      if key == '':
        key = item.link
      if key.count('.torrent') > 0:
        hasInvalidItems = True
        #insert message box re: not supporting torrents here.
        continue
      if key.count('.html') > 0:
        hasInvalidItems = True
        continue
      if key.count('youtube') > 0:
        if key.count('watch') == 0:
          key = 'http://www.youtube.com/watch?v=' + key.split('v/')[-1][:11] #http://www.youtube.com/v/hlkDIYxUrpA&amp;amp;hl=en&amp;amp;fs=1
        thumb = 'http://i.ytimg.com/vi/%s/default.jpg' % key.split("=")[-1]
        #dir.Append(Function(VideoItem(PlayYouTubeVideo, title, date=date, subtitle=subtitle, desc=summary, thumb=thumb, duration=duration), ext='flv', id=key))
        listitem = xbmcgui.ListItem(title, iconImage='DefaultVideo.png', thumbnailImage=thumb)
        listitem.setInfo(type='video', infoLabels=infoLabels)
        parameters = '%s?action=playyoutubevideo&url=%s' % (sys.argv[0], key)
        xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(key, listitem, False)])
      else:
        if thumb == '':
          thumb = __icon__
        listitem = xbmcgui.ListItem(title, iconImage='DefaultVideo.png', thumbnailImage=thumb)
        listitem.setInfo(type='video', infoLabels=infoLabels)
        listitem.setProperty('IsPlayable', 'true')
        xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(key, listitem, False)])
        #if Debug: self.LOG('\nTitle:%s\nPlot:%s\nDate:%s\nDuration:%s\nSize:%s\nThumb:%s\n%s' \
                           #% (infoLabels['title'], infoLabels['plot'], infoLabels['date'], infoLabels['duration'], infoLabels['size'], thumb, '-' * 13))
    # Sort methods and content type...
    xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE)
    if infoLabels['date']:
      xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_DATE)
    if infoLabels['duration']:
      xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_RUNTIME)
    if infoLabels['size']:
      xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_SIZE)
    # End of directory...
    xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

    if hasInvalidItems:
      print ('Invalid items', 'No supported media types found.')

  def PlayYouTubeVideo(sender, id):
    if Debug: self.LOG('\nPlayYouTubeVideo function')
    yt_page = HTTP.Request(id).content
    fmt_url_map = re.findall('"fmt_url_map".+?"([^"]+)', yt_page)[0]
    fmt_url_map = fmt_url_map.replace('\/', '/').split(',')

    fmts = []
    fmts_info = {}

    for f in fmt_url_map:
      (fmt, url) = f.split('|')
      fmts.append(fmt)
      fmts_info[str(fmt)] = url

    index = 0
    if YOUTUBE_FMT[index] in fmts:
      fmt = YOUTUBE_FMT[index]
    else:
      for i in reversed(range(0, index + 1)):
        if str(YOUTUBE_FMT[i]) in fmts:
          fmt = YOUTUBE_FMT[i]
          break
        else:
          fmt = 5

    url = fmts_info[str(fmt)]
    url = url.replace('\\u0026', '&')
    #Log(url)
    return Redirect(url)

  def StripTags(self, str):
    return re.sub(r'<[^<>]+>', '', str)

  def Arguments(self, arg):
    Arguments = dict(part.split('=') for part in sys.argv[2][1:].split('&'))
    return urllib.unquote_plus(Arguments[arg])

  def LOG(self, description):
    xbmc.log("[ADD-ON] '%s v%s': '%s'" % (__plugin__, __version__, description), xbmc.LOGNOTICE)

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

  def fetch(self, url, max_age=0):
    # Use MD5 hash of the URL as the filename
    print url
    filename = md5.new(url).hexdigest()
    filepath = os.path.join(self.cache_dir, filename)
    if os.path.exists(filepath):
      if int(time.time()) - os.path.getmtime(filepath) < max_age:
        if Debug: print 'File exists and reading from cache.'
        return open(filepath).read()
    # Retrieve over HTTP and cache, using rename to avoid collisions
    if Debug: print 'File not yet cached or cache time expired. File reading from URL and try to cache to disk'
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
