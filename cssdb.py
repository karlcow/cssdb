"""
script to extract CSS values given a list of CSS properties
and their location in the specification.

FIXME: ouput data into a suitable JSON format
FIXME: create a config file
FIXME: check if the cache directory exists and create it if not
"""
from bs4 import BeautifulSoup
import urllib2
import urlparse
import logging
import os


# We surely need a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# create a file handler
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
# create a logging format
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(handler)


# To adjust for your own needs
CACHEDIR = "/Users/karl/code/cssdb/cache/"
# This is using the list of Jens Meiert with a few fixes.
# JENSLISTURL = "http://meiert.com/en/indices/css-properties/"
JENSLISTURL = "file:///Users/karl/code/cssdb/jens-css-list.html"
DICTTEST = {
    u'list-style-image': u'http://www.w3.org/TR/css3-lists/#propdef-list-style-image',
    u'box-decoration-break': u'http://www.w3.org/TR/css3-break/#break-decoration',
    u'text-emphasis-color': u'http://www.w3.org/TR/css-text-decor-3/#text-emphasis-color-property',
    u'border-bottom': u'http://www.w3.org/TR/css3-background/#the-border-shorthands'
    }


def jenslist(link):
    """Parse Jens List and extract a dictionary"""
    jenslist = urllib2.urlopen(link)
    soup = BeautifulSoup(jenslist, "html5lib")
    alist = soup.find(class_='alt').find('tbody').find_all('a')
    properties = {}
    for a in alist:
        properties[a.text] = a['href']
    return properties

def extract_values(css_property, spec, fragment, spec_type):
    """When given a property name and its location in the spec,
    it extracts the list of values for this property."""
    if spec_type == 'w3c':
        if spec.find(id=fragment).find_parent("table", attrs={"class": "propdef"}):
            # When the fragment is pointing inside the definition table
            values = spec.find(id=fragment).find_parent("table", attrs={"class": "propdef"}).find_next("tr").find_next("tr").text
        else:
            # When the fragment is pointing to a section header
            values = spec.find(id=fragment).find_next("table", attrs={"class": "propdef"}).find_next("tr").find_next("tr").text
    elif spec_type == 'w3ccss2':
        values = spec.find("a", attrs={"name": fragment}).find_next("td").find_next("td").text
    elif spec_type == 'whatwg':
        values = spec.find(id=fragment).find_next(class_="css-property").find_next("td").text
    else:
        values = ''
        logger.warn('We could not extract values. Not a known spec type')
    lines = [i.rstrip() for i in values.splitlines()]
    css_values = " ".join(" ".join(lines).split())
    return css_property, css_values


def has_spec_type(spec_uri):
    """define if it's a W3C spec or a WHATWG spec"""
    if spec_uri.find('w3.org') >= 0:
        # W3C URI
        if spec_uri.find('CSS2') >= 0:
            spec_type = 'w3ccss2'
        else:
            spec_type = 'w3c'
    elif spec_uri.find('whatwg.org') >= 0:
        # WHATWG URI
        spec_type = 'whatwg'
    else:
        # WHATTHEHELL
        spec_type = ''
        logger.warn('Not a known spec type')
    return spec_type

def cached(spec_uri, spec_type):
    """It returns the locally cached_uri for the specification."""
    logger.debug('cached(spec_uri): The spec URI is %s', spec_uri)
    cached_uri = ''
    if spec_type == 'w3c':
        # we remove the last '/'
        spec_uri = spec_uri[:-1]
        # we keep the string after the last '/'
        name = spec_uri[spec_uri.rfind('/')+1:]
        cached_uri = "file://%s%s.html" % (CACHEDIR, name)
    elif spec_type == 'w3ccss2':
        name = spec_uri[spec_uri.rfind('/')+1:]
        cached_uri = "file://%scss2-%s" % (CACHEDIR, name)
    elif spec_type == 'whatwg':
        name = spec_uri[spec_uri.rfind('/')+1:]
        cached_uri = "file://%swhatwg-%s" % (CACHEDIR, name)
    else:
        logger.warn('This URI %s is not of a known type', spec_uri)
    logger.debug('The cached URI is %s', cached_uri)
    return cached_uri

def in_cache(cached_uri):
    """Checked if the cached_uri exists"""
    filename_path = cached_uri[7:]
    if os.path.isfile(filename_path):
        logger.debug('Document is in cache for %s', filename_path)
        cached = True
    else:
        logger.debug('Document is NOT in cache for %s', filename_path)
        cached = False
    return cached

def create_cache(spec_uri, cached_uri):
    """Create a cache for a spec_uri"""
    filename_path = cached_uri[7:]
    try:
        f = urllib2.urlopen(spec_uri)
        logger.debug('Opening %s', spec_uri)
        with open(filename_path, 'w') as local_caching:
            local_caching.write(f.read())
            logger.debug('Saving a cached document for %s', spec_uri)
            return True
    except urllib2.URLError, e:
        logger.error('The spec document does NOT exist: %s %s', e.reason , spec_uri)
        return False

def get_spec(cached_uri):
    """Download the specification and
    return a BeautifulSoup parsed document."""
    try:
        page = urllib2.urlopen(cached_uri)
        logger.debug('Processing the cached document %s', cached_uri)
    except urllib2.URLError, e:
        logger.error('The cached document does NOT exist: %s %s', e.reason , cached_uri)
    spec = BeautifulSoup(page, "html5lib")
    return spec

def main():
    """ Main logic of the code """
    logger.info('Start processing the CSS properties')
    propdict = jenslist(JENSLISTURL)
    # propdict = DICTTEST
    for i, (css_property, property_uri) in enumerate(propdict.iteritems()):
        fragment=''
        logger.info('--------')
        spec_uri, fragment = urlparse.urldefrag(property_uri)
        spec_type = has_spec_type(spec_uri)
        cached_uri = cached(spec_uri, spec_type)
        if not in_cache(cached_uri):
            create_cache(spec_uri, cached_uri)
        spec = get_spec(cached_uri)
        logger.info('spec_uri: %s', property_uri)
        css_property, css_values = extract_values(css_property, spec, fragment, spec_type)
        if css_values != '':
            logger.info('property: %s', css_property)
            logger.info('fragment: %s', fragment)
            logger.info('%s', css_values)
        else:
            logger.info('FAIL: property: %s, spec_uri: %s', css_property, property_uri)
if __name__ == '__main__':
    main()
