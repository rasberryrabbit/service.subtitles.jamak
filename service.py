# -*- coding: utf-8 -*-

import os
import sys
import xbmc
import urllib
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
import shutil
import unicodedata
import re
import string
import difflib
import HTMLParser
import time
import datetime
import urllib2
import gzip
import zlib
import StringIO
import cookielib

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = unicode(xbmc.translatePath(__addon__.getAddonInfo('path')), 'utf-8')
__profile__ = unicode(xbmc.translatePath(__addon__.getAddonInfo('profile')), 'utf-8')
__resource__ = unicode(xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')), 'utf-8')
__temp__ = unicode(xbmc.translatePath(os.path.join(__profile__, 'temp')), 'utf-8')

# prepare cookie url opener
cookies = cookielib.LWPCookieJar()
handlers = [
    urllib2.HTTPHandler(),
    urllib2.HTTPSHandler(),
    urllib2.HTTPCookieProcessor(cookies)
    ]
opener2 = urllib2.build_opener(*handlers)

def log(module, msg):
    xbmc.log((u"### [%s] - %s" % (module, msg,)).encode('utf-8'))

# remove file and dir with 30 days before / now after time
def clear_tempdir(strpath):
    if xbmcvfs.exists(strpath):
        try:
            low_time = time.mktime((datetime.date.today() - datetime.timedelta(days=15)).timetuple())
            now_time = time.time()
            for file_name in xbmcvfs.listdir(strpath)[1]:
                if sys.platform.startswith('win'):
                    full_path = os.path.join(strpath, file_name)
                else:
                    full_path = os.path.join(strpath.encode('utf-8'), file_name)
                cfile_time = os.stat(full_path).st_mtime
                if low_time >= cfile_time or now_time <= cfile_time:
                    if os.path.isdir(full_path):
                        shutil.rmtree(full_path)
                    else:
                        os.remove(full_path)
        except:
            log(__scriptname__,"error on cleaning temp dir")

clear_tempdir(__temp__)

xbmcvfs.mkdirs(__temp__)

sys.path.append(__resource__)

from engchartohan import engtypetokor

base_url = "http://jamak.kr"
search_url = "http://jamak.kr/bbs/board.php?bo_table=tr_jamak&sca=&sfl=wr_subject&rsc=&stx="
page_str = "&page=%d"
load_page_enum = [1,2,3,4,5,6,7,8,9,10]
load_file_enum = [10,20,30,40,50,60,70,80,90]
max_pages = load_page_enum[int(__addon__.getSetting("max_load_page"))]
max_file_count = load_file_enum[int(__addon__.getSetting("max_load_files"))]
use_titlename = __addon__.getSetting("use_titlename")
user_agent = __addon__.getSetting("user_agent")
use_engkeyhan = __addon__.getSetting("use_engkeyhan")
use_se_ep_check = __addon__.getSetting("use_se_ep_check")

ep_expr = re.compile("(\D+)?(\d{1,2})\D+(\d{1,3})(\D+)?")

main_query = ""

def smart_quote(str):
    ret = ''
    spos = 0
    epos = len(str)
    while spos<epos:
        ipos = str.find('%',spos)
        if ipos == -1:
            ret += urllib.quote_plus(str[spos:])
            spos = epos
        else:
            ret += urllib.quote_plus(str[spos:ipos])
            spos = ipos
            ipos+=1
            # check '%xx'
            if ipos+1<epos:
                if str[ipos] in string.hexdigits:
                    ipos+=1
                    if str[ipos] in string.hexdigits:
                        # pass encoded
                        ipos+=1
                        ret+=str[spos:ipos]
                    else:
                        ret+=urllib.quote_plus(str[spos:ipos])
                else:
                    ipos+=1
                    ret+=urllib.quote_plus(str[spos:ipos])
                spos = ipos
            else:
                ret+=urllib.quote_plus(str[spos:epos])
                spos = epos
    return ret

def prepare_search_string(s):
    s = string.strip(s)
    s = re.sub(r'\(\d\d\d\d\)$', '', s)  # remove year from title
    return s

# 메인 함수로 질의를 넣으면 해당하는 자막을 찾음.
def get_subpages(query,list_mode=0):
    file_count = 0
    page_count = 1
    # main page
    main_query = query
    check_count, file_count = get_list(search_url,max_file_count,list_mode,1)
    # first page    
    if item['mansearch']:
        newquery = smart_quote(query)
    else:
        newquery = urllib.quote_plus(prepare_search_string(query))
    url = search_url+newquery
    while (page_count<=max_pages) and (file_count<max_file_count):
        if max_file_count-file_count>0:
            check_count, new_count = get_list(url,max_file_count-file_count,list_mode,0)
        else:
            check_count = 0
        if check_count==0:
            break
        file_count += new_count
        # next page
        page_count+=1
        url = search_url+newquery+"&page=%d" % (page_count)
    return file_count

def check_ext(str):
    ext_str = [".smi",".srt",".sub",".ssa",".ass",".txt"]
    retval = -1
    for ext in ext_str:
        if str.lower().find(ext)!=-1:
            retval=1
            break
    return retval

# support compressed content
def decode_content (page):
    encoding = page.info().get("Content-Encoding")    
    if encoding in ('gzip', 'x-gzip', 'deflate'):
        content = page.read()
        if encoding == 'deflate':
            data = StringIO.StringIO(zlib.decompress(content))
        else:
            data = gzip.GzipFile('', 'rb', 9, StringIO.StringIO(content))
        page = data.read()
    else:
        page = page.read()
    return page

def read_url(url):
    opener = urllib2.build_opener()
    opener.addheaders = [('User-Agent',user_agent), ('Accept-Encoding','gzip,deflate'), ('Referer',url), ('Connection','Keep-Alive')]
    try:
        rep = opener.open(url)
        res = decode_content(rep)
        rep.close()
    except:
        log(__scriptname__,url)
        res = ""
    return res

# jamak.kr의 페이지를 파싱해서 파일의 이름과 다운로드 주소를 얻어냄.
def get_files(url):
    ret_list = []
    file_pattern = "<a href=\"javascript\:file_download\('([^']+)',\s+?'(.+)',\s+?"
    content_file = read_url(url)
    files = re.findall(file_pattern,content_file)
    for flink,name in files:
        name = name.replace("\\","").replace("\'","_").replace("\"","_")
        # 확장자를 인식해서 표시.
        if check_ext(name)!=-1:
            flink = base_url+"/bbs"+flink[1:]
            ret_list.append([url, name, flink])
    return ret_list
    
def check_season_episode(str_title, se, ep):
    se_ep = 0
    re_str = ep_expr.search(str_title)
    new_season = ""
    new_episode = ""    
    if re_str:
        new_season = re_str.group(2)
        new_episode = re_str.group(3)
    if new_season=="":
        new_season="0"            
    if new_episode=="":
        new_episode="0"
    if se=="":
        se="0"
    if ep=="":
        ep="0"
    if int(new_season)==int(se):
        se_ep = 1
        if int(new_episode)==int(ep):
            se_ep = 2
    return se_ep

# jamak.kr의 페이지의 내용을 추출해서 링크를 얻어냄. 그리고 파일 다운로드 URL을 listbox에 추가.
def get_list(url, limit_file, list_mode, main_page = 0):
    search_pattern = "<td class=\"l_subj\">\s+?<a href='([^']+)'><span>(.+)</span></a>\s+?<span [^>]+>([^<]+)</"
    content_list = read_url(url)
    get_count = 0
    match_count = 0
    # 자막이 없음을 알리는 페이지를 인식.
    lists = re.findall(search_pattern,content_list)
    for link, title_name, sublang in lists:
        if match_count<limit_file:
            link = link.replace("&amp;","&")
            link = base_url+link[link.find("/"):]
            title_name = re.sub("<.*?>","",title_name)
            get_count += 1
            # main page
            if main_page==1:
                if re.search(main_query,title_name,re.I) is None:
                    continue
            if use_se_ep_check == "true":
                if list_mode==1:
                    if 0==check_season_episode(title_name,item['season'],item['episode']):
                        continue
            list_files = get_files(link)
            for furl,name,flink in list_files:
                match_count += 1
                listitem = xbmcgui.ListItem(label          = sublang,
                                            label2         = name if use_titlename == "false" else title_name,
                                            iconImage      = "0",
                                            thumbnailImage = ""
                                            )

                listitem.setProperty( "sync", "false" )
                listitem.setProperty( "hearing_imp", "false" )
                listurl = "plugin://%s/?action=download&url=%s&furl=%s&name=%s" % (__scriptid__,
                                                                                urllib2.quote(furl),
                                                                                urllib2.quote(flink),
                                                                                name
                                                                                )

                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=listurl,listitem=listitem,isFolder=False)
    #return item count
    return get_count, match_count

# 파일을 다운로드, 하루에 7번 다운로드 제한.
def download_file(url,furl,name):
    subtitle_list = []
    local_temp_file = os.path.join(__temp__.encode('utf-8'), name)
    # Get cookie
    req1 = urllib2.Request(url,headers={'User-Agent': user_agent})
    res1 = opener2.open(req1)
    # Download File
    req2 = urllib2.Request(furl,headers={'User-Agent': user_agent})
    res2 = opener2.open(req2)
    local_file_handle = open( local_temp_file, "wb" )
    local_file_handle.write(res2.read())
    local_file_handle.close()
    subtitle_list.append(local_temp_file)
    return subtitle_list
 
def search(item):
    filename = os.path.splitext(os.path.basename(item['file_original_path']))[0]
    lastgot = 0
    list_mode = 0
    if item['mansearch']:
        lastgot = get_subpages(item['mansearchstr'])
        if use_engkeyhan == "true":
            lastgot += get_subpages(engtypetokor(item['mansearchstr']))
    elif item['tvshow']:
        list_mode = 1
        # "title 1e01"
        lastgot = get_subpages("%s %se%.2d" % (item['tvshow'],item['season'],int(item['episode'])),1)
        if lastgot == 0:
            # "title 1x01"
            lastgot = get_subpages("%s %sx%.2d" % (item['tvshow'],item['season'],int(item['episode'])),1)
        if lastgot == 0:
            lastgot = get_subpages(item['tvshow'],1)
    elif item['title'] and item['year']:
        lastgot = get_subpages(item['title'])
    if lastgot == 0 and list_mode != 1:
        lastgot = get_subpages(filename)
        
def normalizeString(str):
    return unicodedata.normalize(
        'NFKD', unicode(unicode(str, 'utf-8'))
        ).encode('ascii', 'ignore')

def get_params(string=""):
    param=[]
    if string == "":
        paramstring=sys.argv[2]
    else:
        paramstring=string
    if len(paramstring)>=2:
        params=paramstring
        cleanedparams=params.replace('?','')
        if (params[len(params)-1]=='/'):
            params=params[0:len(params)-2]
        pairsofparams=cleanedparams.split('&')
        param={}
        for i in range(len(pairsofparams)):
            splitparams={}
            splitparams=pairsofparams[i].split('=')
            if (len(splitparams))==2:
                param[splitparams[0]]=splitparams[1]

    return param

params = get_params()

if params['action'] == 'search' or params['action'] == 'manualsearch':
    item = {}
    item['temp']               = False
    item['rar']                = False
    item['mansearch']          = False
    item['year']               = xbmc.getInfoLabel("VideoPlayer.Year")                         # Year
    item['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season"))                  # Season
    item['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                 # Episode
    item['tvshow']             = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))  # Show
    item['title']              = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))# try to get original title
    item['file_original_path'] = xbmc.Player().getPlayingFile().decode('utf-8')                 # Full path of a playing file
    item['3let_language']      = [] #['scc','eng']
    PreferredSub		      = params.get('preferredlanguage')

    if 'searchstring' in params:
        item['mansearch'] = True
        item['mansearchstr'] = params['searchstring']

    for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
        if lang == "Portuguese (Brazil)":
            lan = "pob"
        else:
            lan = xbmc.convertLanguage(lang,xbmc.ISO_639_2)
            if lan == "gre":
                lan = "ell"

    item['3let_language'].append(lan)

    if item['title'] == "":
        item['title']  = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))      # no original title, get just Title

    if item['episode'].lower().find("s") > -1:                                      # Check if season is "Special"
        item['season'] = "0"                                                          #
        item['episode'] = item['episode'][-1:]

    if ( item['file_original_path'].find("http") > -1 ):
        item['temp'] = True

    elif ( item['file_original_path'].find("rar://") > -1 ):
        item['rar']  = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

    elif ( item['file_original_path'].find("stack://") > -1 ):
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]

    search(item)

elif params['action'] == 'download':
    subs = download_file(urllib2.unquote(params['url']),urllib2.unquote(params['furl']),params['name'])
    for sub in subs:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=sub,listitem=listitem,isFolder=False)


xbmcplugin.endOfDirectory(int(sys.argv[1]))
