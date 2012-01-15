#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Bot to upload all images from the site of the US Navy (Navy News Service located at http://www.navy.mil/view_photos_top.asp

http://www.navy.mil/view_single.asp?id=<the id>
The images have ids from 0 to about 77000 in October 2009.
Start and end can be controlled with -start_id and -end_id

Screen scraping is done with BeautifulSoup so this needs to be installed.

'''
import sys, os, StringIO, hashlib, base64
import os.path
import urllib, re
from urllib import FancyURLopener
from datetime import datetime
from BeautifulSoup import BeautifulSoup 
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, upload
import config


def downloadPhoto(photoUrl = ''):
    '''
    Download the photo and store it in a StrinIO.StringIO object.

    TODO: Add exception handling
    '''
    imageFile=urllib.urlopen(photoUrl).read()
    return StringIO.StringIO(imageFile)

def findDuplicateImages(photo = None, site = wikipedia.getSite(u'commons', u'commons')):
    '''
    Takes the photo, calculates the SHA1 hash and asks the mediawiki api for a list of duplicates.

    TODO: Add exception handling, fix site thing
    '''
    hashObject = hashlib.sha1()
    hashObject.update(photo.getvalue())
    return site.getFilesFromAnHash(base64.b16encode(hashObject.digest()))

def getMetadata(url):
    '''
    Get all the metadata for a single image and store it in the photoinfo dict
    '''
    metadata = {}

    imagePage = urllib.urlopen(url)
    data = imagePage.read()
    soup = BeautifulSoup(data)    
    tiflink = soup.find('a', href=re.compile('http://lcweb2.loc.gov/pnp/habshaer/.*\.tif'))
    if not tiflink:
	#print u'Not found at %s' %(url,)
	return False
    metadata['tifurl'] = tiflink.get('href')
   
    soup = BeautifulSoup(data)
    # imagelinks = soup.findAll('a', href=re.compile('http://www.loc.gov/pictures/collection/hh/item/.*'))
    metafields = soup.findAll('meta')#, attribname=re.compile('dc.*'))

    for metafield in metafields:
	name = metafield.get('name')
	content = metafield.get('content')
	if name:
	    if name==u'dc.identifier' and content.startswith(u'http://hdl.loc.gov/loc.pnp/'):
		metadata[name]=content
		metadata[u'identifier']=content.replace(u'http://hdl.loc.gov/loc.pnp/', u'')

	    elif name.startswith(u'dc.'):
		metadata[name]=content
    # Do something with county extraction
    
    match=re.match(u'^.*,(?P<county>[^,]+),(?P<state>[^,]+)', metadata['dc.title'], re.DOTALL)
    if match:
	metadata[u'county'] = match.group(u'county').strip()
	metadata[u'state'] = match.group(u'state').strip()

    return metadata
    ''' 
    url = 'http://www.navy.mil/view_single.asp?id=' + str(photo_id)
    navyPage = urllib.urlopen(url)

    data = navyPage.read()

    soup = BeautifulSoup(data)
    
    if soup.find("meta", {'name' : 'HI_RES_IMAGE'}):
	photoinfo['url'] = soup.find("meta", {'name' : 'HI_RES_IMAGE'}).get('content')
    if soup.find("meta", {'name' : 'MED_RES_IMAGE'}):
	photoinfo['url_medium'] = soup.find("meta", {'name' : 'MED_RES_IMAGE'}).get('content')
	
    if soup.find("meta", {'name' : 'DESCRIPTION'}):
	photoinfo['fulldescription'] = soup.find("meta", {'name' : 'DESCRIPTION'}).get('content')
    if soup.find("meta", {'name' : 'ALT_TAG'}):
	photoinfo['shortdescription'] = soup.find("meta", {'name' : 'ALT_TAG'}).get('content')

    if photoinfo.get('url') and photoinfo.get('fulldescription') and photoinfo.get('shortdescription'):
	photoinfo['navyid'] = getNavyIdentifier(photoinfo['url'])
	photoinfo['description'] = re.sub(u'\w*-\w*-\w*-\w*[\r\n\s]+', u'', photoinfo['fulldescription'])
	#photoinfo['description'] = cleanDescription(photoinfo['fulldescription'])
	photoinfo['author'] = getAuthor(photoinfo['fulldescription'])
	(photoinfo['date'], photoinfo['location']) = getDateAndLocation(photoinfo['fulldescription'])
	photoinfo['ship'] = getShip(photoinfo['fulldescription'])
	
	return photoinfo
    else:
	# Incorrect photo_id
	return False
    '''

def getNavyIdentifier(url):
    result = url
    result = result.replace(u'http://www.navy.mil/management/photodb/photos/', u'')
    result = result.replace(u'.jpg', u'')
    return result

def getAuthor(description):
    authorregex = []
    authorregex.append(u'\((U.S. [^\)]+)[\\/]\s?Released\)')
    authorregex.append(u'(U.S. \s?Navy photo by .*)\(RELEASED\)')

    for regex in authorregex:
	matches = re.search(regex, description, re.I)
	if  matches:
	    return matches.group(1)
    
    #Nothing matched
    return u'U.S. Navy photo<!-- Please update this from the description field-->'

def getShip(description):
    # Try to find a USS ...(...) ship
    shipRegex = u'(USNS|USS) [^\(]{1,25}\([^\)]+\)'

    matches = re.search(shipRegex, description, re.I)
    if matches:
	#print matches.group(0)
        return matches.group(0)
    else:
	# No ship found
        return u''

def getDateAndLocation(description):
    '''
    Get date and location.
    Is one regex so I might as well build one function for it
    '''
    date = u''
    location = u'unknown'
    #dateregex = u'\(([^\)]+\d\d\d\d)\)'
    #locationregex = u'^([^\(^\r^\n]+)\(([^\)]+\d\d\d\d)\)'
    regexlist = []
    regexlist.append(u'^([^\(^\r^\n]+)\(([^\)]+\d\d\d\d)\)')
    regexlist.append(u'^([^\r^\n]+)\s([^\s]* \d{1,2}, \d\d\d\d)\s+(-|--|&ndash)')
    #matches = re.search(regex, description, re.MULTILINE)
    for regex in regexlist:
        matches = re.search(regex, description, re.MULTILINE)
        if  matches:
	    date = matches.group(2)
	    location = matches.group(1)
	    location = location.strip()
	    location = location.rstrip(',')
	    location = re.sub(u'\w*-\w*-\w*-\w*\s', u'', location)
            return (date, location)
    return (date, location)


def getDescription(metadata):
    '''
    Generate a description for a file
    '''
		    
    description = u'{{User:Multichill/HABS\n'
    for key, value in metadata.iteritems():
	description = description + u'|' + key + u'=%(' + key + u')s\n'
    description = description + u'}}\n'
	
    return description % metadata

def getTitle(metadata):
    '''
    Build a valid title for the image to be uploaded to.
    '''
    title = metadata['dc.title']
    if len(title)>120:
	title = title[0 : 120]
	title = title.strip()

    if title.startswith(u' - '):
	title = title[3:]
    identifier = metadata['identifier'].replace(u'/', u'.')

    title = u'%s_-_LOC_-_%s_.tif' % (title, identifier)

    title = re.sub(u"[<{\\[]", u"(", title)
    title = re.sub(u"[>}\\]]", u")", title)
    title = re.sub(u"[ _]?\\(!\\)", u"", title)
    title = re.sub(u",:[ _]", u", ", title)
    title = re.sub(u"[;:][ _]", u", ", title)
    title = re.sub(u"[\t\n ]+", u" ", title)
    title = re.sub(u"[\r\n ]+", u" ", title)
    title = re.sub(u"[\n]+", u"", title)
    title = re.sub(u"[?!]([.\"]|$)", u"\\1", title)
    title = re.sub(u"[&#%?!]", u"^", title)
    title = re.sub(u"[;]", u",", title)
    title = re.sub(u"[/+\\\\:]", u"-", title)
    title = re.sub(u"--+", u"-", title)
    title = re.sub(u",,+", u",", title)
    title = re.sub(u"[-,^]([.]|$)", u"\\1", title)
    title = title.replace(u" ", u"_")
    title = title.replace(u"__", u"_")
    title = title.replace(u"..", u".")
    title = title.replace(u"._.", u".")
    
    return title




def processPhoto(url):
    '''
    Work on a single photo at 
    http://www.navy.mil/view_single.asp?id=<photo_id>    
    get the metadata, check for dupes, build description, upload the image
    '''
    print url

    # Get all the metadata
    metadata = getMetadata(url)
    if not metadata:
	# No image at the page
	return False

    photo = downloadPhoto(metadata['tifurl'])

    duplicates = findDuplicateImages(photo)
    #duplicates = False
    # We don't want to upload dupes
    if duplicates:
        wikipedia.output(u'Found duplicate image at %s' % duplicates.pop())
	# The file is at Commons so return True
        return True

    description = getDescription(metadata)
    title = getTitle(metadata)

    wikipedia.output(title)
    #wikipedia.output(description)

    bot = upload.UploadRobot(metadata['tifurl'], description=description, useFilename=title, keepFilename=True, verifyDescription=False, targetSite = wikipedia.getSite('commons', 'commons'))
    bot.upload_image(debug=False)
    return True

def processSearchPage(page_id):
    #url = 'http://www.loc.gov/pictures/collection/hh/item/ak0003.color.570352c/'
    url = 'http://www.loc.gov/pictures/search/?fa=displayed%%3Aanywhere&sp=%s&co=hh&st=list' %(str(page_id),)
    #url = 'http://www.loc.gov/pictures/search/?fa=displayed%3Aanywhere&sp=18473&co=hh&st=list'

    imageurls = set()

    searchPage = urllib.urlopen(url)
    data = searchPage.read()
    soup = BeautifulSoup(data)
    #allTags = soup.findAll(True)
    imagelinks = soup.findAll('a', href=re.compile('http://www.loc.gov/pictures/collection/hh/item/.*'))
    
    # First collect all links. Set will remove the dupes
    for imagelink in imagelinks:
	imageurls.add(imagelink.get('href'))
    # Now work on the actual urls
    for imageurl in imageurls:
	processPhoto(imageurl)


def processSearchPages(start_id=1, end_id=20000):
    '''
    Loop over a bunch of images
    '''
    last_id = start_id
    for i in range(start_id, end_id):
        success = processSearchPage(page_id=i)
	if success:
	    last_id=i
    return last_id

def processLatestPhotos():
    '''
    Upload the photos at http://www.navy.mil/view_photos_top.asp?sort_type=0&sort_row=8
    '''
    url = 'http://www.navy.mil/view_photos_top.asp?sort_type=0&sort_row=8'
    latestPage = urllib.urlopen(url)
    data = latestPage.read()

    regex = u'<td valign="bottom"><a href="view_single.asp\?id=(\d+)"><img border=0'

    for match in re.finditer (regex, data):
	processPhoto(int(match.group(1)))

def main(args):
    '''
    Main loop.
    '''
    start_id = 1
    end_id   = 18473
    single_id = 0
    #latest = False
    #updaterun = False
    site = wikipedia.getSite('commons', 'commons')
    #updatePage = wikipedia.Page(site, u'User:BotMultichillT/Navy_latest') 
    #interval=100

    for arg in wikipedia.handleArgs():
        if arg.startswith('-start_id'):
            if len(arg) == 9:
                start_id = wikipedia.input(u'What is the id of the search page you want to start at?')
            else:
                start_id = arg[10:]
        elif arg.startswith('-end_id'):
            if len(arg) == 7:
                end_id = wikipedia.input(u'What is the id of the search page you want to end at?')
            else:
                end_id = arg[8:]
	elif arg.startswith('-id'):
	    if len(arg) == 3:
		single_id = wikipedia.input(u'What is the id of the search page you want to transfer?')
	    else:
		single_id = arg[4:]

    if single_id > 0:
	processSearchPage(page_id=int(single_id))
    else:       
	last_id = processSearchPages(int(start_id), int(end_id))

         
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print u'All done'