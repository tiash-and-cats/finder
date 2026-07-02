import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finder_proj.settings")
django.setup()

import html.parser
import urllib.request
import urllib.parse
import urllib.robotparser
import time
import random
from api.models import Indexed
from urllib.error import HTTPError, URLError
from datetime import datetime
import sys, re

# constants
UA = "Finder/LucasTheSpider"
MAXDEPTH = 100
INDENT = 4
IGNORETAGS = ("SCRIPT", "STYLE", "NOSCRIPT", "TEXTAREA", "TEMPLATE")
DATEFORMAT = "%a, %d %b %Y %H:%M:%S GMT"
NAVBAR_SIGNATURE = None
LOGFILE = open("crawl.log", "w")

# global vars
visited = set()

# functions
def start_crawl(fname):
    printlog("Started crawl")
    with open(fname) as f:
        for x in f.readlines():
            crawl(x, None, 0, 0)
    printlog("Ended crawl")

def printlog(*args):
    print(f"[{datetime.now().strftime(DATEFORMAT)}]", *args, file=LOGFILE)
    LOGFILE.flush()

# main (recursive) crawling function
def crawl(url, orig, depth, indent, first=True, prevpath=None):
    if url.startswith("javascript:") or url.startswith("mailto:"): return
    if url == orig: return
    if url == prevpath: return
    parsed = urllib.parse.urlparse(url)
    parsed = parsed._replace(query="")
    if parsed.netloc == "":
        if parsed.path == "":
            print(f"{' '*indent}({parsed.geturl()}) fragments are to be ignored, returning")
            return
        else:
            if not url.startswith("/"):
                parsed = urllib.parse.urlparse(orig + "/" + url)
            else:
                oparse = urllib.parse.urlparse(orig)
                parsed = urllib.parse.urlparse(oparse.scheme + "://" + oparse.netloc + url)
    parsed = parsed._replace(fragment="")
    if parsed.scheme == "":
        parsed = parsed._replace(scheme="https")
    if parsed.path.find(".") > -1:
        # Remove the last segment by trimming the path
        new_path = "/".join(parsed.path.rstrip('/').split('/')[:-1]) + "/"
        
        # Construct the new URL
        new_url = urllib.parse.urljoin(parsed.scheme + "://" + parsed.netloc, new_path)
        parsed = urllib.parse.urlparse(new_url)
    parsed = parsed._replace(path=parsed.path.rstrip("/"))
    canonical = parsed.geturl()
    if canonical in visited:
        return
    visited.add(canonical)
    printlog('parsed.path.rstrip("/"):', parsed.path.rstrip("/"))
    if parsed.geturl() == prevpath: return
    print(f"{' '*indent}crawling site {parsed.geturl()}")
    if depth == MAXDEPTH: 
        print(f"{' '*(indent+INDENT)}reached maximum depth, returning")
        return
    robots = urllib.robotparser.RobotFileParser()
    robots.set_url(urllib.parse.urljoin(parsed.scheme + "://" + parsed.netloc, "robots.txt"))
    req = urllib.request.Request(parsed.geturl(), headers={"User-Agent": UA})
    try:
        robots.read()
    except (URLError, ValueError):
        print(f"{' '*(indent+INDENT)}robots.txt parsing failed, returning")
        return
    try:
        if robots.can_fetch(UA, parsed.geturl()):
            res = urllib.request.urlopen(req)
            if not res.getheader("Content-Type", "").startswith("text/html"):
                print(f"{' '*(indent+INDENT)}Content-Type is not text/html, returning")
                return
            text = res.read()
            enc = re.search(r'(?:encoding|charset)=([\w-]+)', res.getheader("Content-Type"))
            try:
                enc = enc[1]
            except TypeError:
                enc = "utf-8"
        else:
            print(f"{' '*(indent+INDENT)}robots.txt disallowed, returning")
            return
    except HTTPError as e:
        if e.code != 429:
            print(f"{' '*(indent+INDENT)}request failed, returning")
            return
        else:
            if retry_after_header := e.headers.get("Retry-After"):
                if retry_after := parse_retry_after(retry_after):
                    print(f"{' '*(indent+INDENT)}too many requests, trying again after {retry_after} secs")
                    time.sleep(retry_after)
                    crawl(url, orig, depth, indent, first, prevpath)
                    return
                else:
                    print(f"{' '*(indent+INDENT)}too many requests, invalid Retry-After value or Retry-After is a date, returning")
                    return
            else:
                print(f"{' '*(indent+INDENT)}too many requests, trying again after 5 secs")
                time.sleep(5)
                crawl(url, orig, depth, indent, first, prevpath)
                return
    try:
        info = getinfo(parsed.geturl(), text.decode(enc), first)
    except UnicodeDecodeError:
        print(f"{' '*(indent+INDENT)}failed to decode page, returning")
        return
    if not info["lang"].startswith("en"):
        print(f"{' '*(indent+INDENT)}language is not English, returning")
        return
    if not Indexed.objects.all().filter(url=parsed.geturl()).exists():
        Indexed(
           url = parsed.geturl(), 
           desc = info["desc"], 
           keywds = info["keywds"], 
           title = info["title"], 
           rank = 1, 
           content = info["content"],
           favicon = info["favicon"],
        ).save()
        print(f"{' '*(indent+INDENT)}new site {parsed.geturl()} added")
    else:
        page = Indexed.objects.get(url=parsed.geturl())
        page.rank += 1
        if (page.title is None or page.title == parsed.geturl()) and info["title"]:
            page.title = info["title"]
            print(f"{' '*(indent+INDENT)}site {parsed.geturl()} title added")
        if page.favicon is None and info["favicon"]:
            if is_relative(info["favicon"]):
                page.favicon = urllib.parse.urljoin(get_parent_url(parsed.geturl()), info["favicon"])
            else:
                page.favicon = info["favicon"]
            print(f"{' '*(indent+INDENT)}site {parsed.geturl()} favicon added")
        page.save()
        print(f"{' '*(indent+INDENT)}site {parsed.geturl()} rank++")
        if not first:
            return
    prev = None
    for x in info["links"]:
        crawl(x, parsed.geturl(), depth + 1, indent + INDENT, False, prev)
        prev = x
    #time.sleep(random.randint(2, 5))

# helpers
def get_parent_url(url):
    parsed = urllib.parse.urlparse(url)
    parent_path = parsed.path.rsplit('/', 1)[0] or '/'
    new_parsed = parsed._replace(path=parent_path, query='', fragment='')
    return urllib.parse.urlunparse(new_parsed)
    
def is_relative(url):
    parsed = urllib.parse.urlparse(url)
    return not parsed.scheme and not parsed.netloc

def parse_retry_after(retry_after):
    try:
        parsed_date = datetime.strptime(retry_after, DATEFORMAT)
        return None  # Explicitly return None if it's a date
    except ValueError:
        try:
            return int(retry_after)  # Return delay in seconds
        except ValueError:
            return None  # Explicitly return None if parsing fails

def get_navbar_signature(links):
    """Return a hashable signature of a list of links, e.g. for <nav>."""
    return tuple(sorted(set(links)))

def getinfo(url, text, is_root=False):
    parser = Parser(url)
    parser.feed(text)

    global NAVBAR_SIGNATURE
    if is_root:
        NAVBAR_SIGNATURE = get_navbar_signature(parser.links)

    # If not root, remove shared nav links
    if not is_root and NAVBAR_SIGNATURE:
        parser.links = [x for x in parser.links if x not in NAVBAR_SIGNATURE]

    return {
        "desc": parser.desc,
        "keywds": parser.keywds,
        "links": parser.links,
        "title": parser.title,
        "content": parser.content,
        "lang": parser.lang,
        "favicon": parser.favicon,
    }

# a single class
class Parser(html.parser.HTMLParser):
    def __init__(self, url):
        # initialize the superclass
        super().__init__()
        
        # used by getinfo():
        # --- the description
        self.desc = ""
        # --- the keywords
        self.keywds = ""
        # --- the title
        self.title = url
        # --- the links
        self.links = []
        # --- the content
        self.content = ""
        # --- the language
        self.lang = "en"
        # --- the favicon
        self.favicon = None
        
        # used only by Parser itself (that's why they're mangled)
        # --- used to check if the next time handle_data() is called, the previous tag was a <title>.
        self.__next_data_is_title = False
        # --- stores the last tag handle_starttag() encountered
        self.__last_tag = ""
    
    def handle_starttag(self, tag, attr):
        # convert the attributes to a dict (so that we can use [...] and .get(...)) 
        # they are normally in a list of tuples of form [(attr, value), (attr, value), ...]
        attr = dict(attr)
        
        # is it (the element) a link (an <a>)?
        if tag.upper() == "A":
            
            # if there is a <a href="..."> attribute (where the link points) and it is not downloadable
            if attr.get("href") is not None and attr.get("download", "false") == "false":
                
                # add it to the list of links
                self.links.append(attr["href"])
        
        # well, is it a <meta> then (stuff for search engines)?
        elif tag.upper() == "META":
            
            # if there is a <meta name="..."> attribute
            if attr.get("name") is not None:
                
                #    <meta name="keywords" content="...">
                # or <meta name="Keywords" content="...">
                # or <meta name="og:keywords" content="...">
                # meaning: the keywords that are associated with this page
                if attr["name"].upper().removeprefix("OG:") == "KEYWORDS":
                    
                    # append the <meta content="..."> attribute to the keywords already there
                    self.keywds += attr["content"]
                
                #    <meta name="description" content="...">
                # or <meta name="Description" content="...">
                # or <meta name="og:description" content="...">
                # meaning: the description of the page
                elif attr["name"].upper().removeprefix("OG:") == "DESCRIPTION":
                    
                    # if there isn't a description already
                    if self.desc == "":
                        
                        # set it to the <meta content="..."> attribute
                        self.desc = attr["content"]
        
        # is it the <link> element (favicons etc.)?
        elif tag.upper() == "LINK":
            
            # if there is a <link rel> and <link href> attr
            if attr.get("rel") is not None and attr.get("href") is not None:
                
                # if the rel="icon" (favicon)
                if attr["rel"] == "icon":
                    
                    # save the favicon URL
                    self.favicon = attr["href"]
        
        # is it the title of the page (the <title> element)?
        elif tag.upper() == "TITLE":
            
            # pass it to handle_data() then as a page title
            self.__next_data_is_title = True
        
        # is it the root element?
        elif tag.upper() == "HTML":
            
            # if there is a lang attr
            if attr.get("lang") is not None:
                
                # set the language
                self.lang = attr["lang"]
        
        # otherwise, just pass it to handle_data()
        else:
            self.__last_tag = tag
    
    def handle_data(self, data):
        
        # checking if handle_starttag() has passed the title
        if self.__next_data_is_title:
            
            # if it has, set the title
            self.__next_data_is_title = False
            self.title = data
        
        # if handle_starttag() has just passed a random element, and we have not been told to ignore it
        elif self.__last_tag.upper() not in IGNORETAGS:
            
            # if the content length is <= 500
            if len(self.content) <= 500:
                
                # add the captured data to the content there
                self.content += data

if __name__ == "__main__":
    start_crawl(sys.argv[1])