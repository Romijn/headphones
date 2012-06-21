#  This file is part of Headphones.
#
#  Headphones is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Headphones is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Headphones.  If not, see <http://www.gnu.org/licenses/>.

import os
import glob, urllib2

import lib.simplejson as simplejson

import headphones
from headphones import helpers, logger

lastfm_apikey = "690e1ed3bc00bc91804cd8f7fe5ed6d4"

class Cache(object):
    """
    This class deals with getting, storing and serving up artwork (album 
    art, artist images, etc) and info/descriptions (album info, artist descrptions)
    to and from the cache folder. This can be called from within a web interface, 
    for example, using the helper functions getInfo(id) and getArtwork(id), to utilize the cached
    images rather than having to retrieve them every time the page is reloaded.
    
    So you can call cache.getArtwork(id) which will return an absolute path
    to the image file on the local machine, or if the cache directory
    doesn't exist, or can not be written to, it will return a url to the image.
    
    Call cache.getInfo(id) to grab the artist/album info; will return the text description
    
    The basic format for art in the cache is <musicbrainzid>.<date>.<url including extension>
    and for info it is <musicbrainzid>.<date>.txt
    """
    
    path_to_art_cache = os.path.join(headphones.CACHE_DIR, 'artwork')
    path_to_info_cache = os.path.join(headphones.CACHE_DIR, 'info')
    
    id = None
    id_type = None # 'artist' or 'album'
    
    artwork_files = []
    info_files = []
    
    def __init__(self):
        
        pass
        
    def _exists(self, type):
        
        if type == 'artwork':
            
            self.artwork_files = glob.glob(os.path.join(self.path_to_art_cache, self.id + '*'))
            
            if self.artwork_files:
                return True
            else:
                return False
                
        else:
            
            self.info_files = glob.glob(os.path.join(self.path_to_info_cache, self.id + '*'))
            
            if self.info_files:
                return True
            else:
                return False
                
    def _get_age(self, date):
        # There's probably a better way to do this
        split_date = date.split('-')
        days_old = int(split_date[0])*365 + int(split_date[1])*30 + int(split_date[2])
        
        return days_old
        
    
    def _is_current(self, file):
        
        base_filename = os.path.basename(file)
        date = base_filename.split('.')[1]
        
        # Calculate how old the cached file is based on todays date & file date stamp
        # helpers.today() returns todays date in yyyy-mm-dd format
        if self._get_age(helpers.today()) - self._get_age(date) < 30:
            return True
        else:
            return False
        
    def get_artwork_from_cache(self, id, id_type):
        '''
        Pass a musicbrainz id to this function, and a type (either artist or album)
        '''
        
        self.id = id
        self.id_type = id_type
        
        if self._exists('artwork') and self._is_current(self.artwork_files[0]):
            return self.artwork_files[0]
        else:
            self._update_cache()
            if self._exists('artwork'):
                return self.artwork_files[0]
                
    def get_info_from_cache(self, id, id_type):
        
        self.id = id
        self.id_type = id_type
        
        if self._exists('info') and self._is_current(self.info_files[0]):
            f = open(self.info_files[0], 'r').read()
            return f
        else:
            self._update_cache()
            if self._exists('info'):
                f = open(self.info_files[0],'r').read()
                return f

    def _update_cache(self):
        '''
        Since we call the same url for both info and artwork, we'll update both at the same time
        '''
        
        url = "http://ws.audioscrobbler.com/2.0/?method=" + self.id_type + ".getInfo&mbid=" + self.id + "&api_key=" + lastfm_apikey + "&format=json"

        logger.debug('Retrieving artist information from: ' + url)
        try:
            result = urllib2.urlopen(url).read()
            artist = simplejson.JSONDecoder().decode(result)
            artist_bio = artist['artist']['bio']['content']
            artist_image_url = artist['artist']['image'][4]['#text']
        except:
            logger.warn('Could not open url: ' + url)
            return

        if artist_bio:
            
            # Make sure the info dir exists:
            if not os.path.isdir(self.path_to_info_cache):
                try:
                    os.makedirs(self.path_to_info_cache)
                except Exception, e:
                    logger.error('Unable to create info cache dir. Error: ' + e)
                    
            # Delete any old files and replace it with a new one
            for info_file in self.info_files:
                try:
                    os.remove(info_file)
                except:
                    logger.error('Error deleting file from the cache: ' + info_file)
                    
            bio_path = os.path.join(self.path_to_info_cache, self.id + '.' + helpers.today() + '.txt')
            try:    
                f = open(bio_path, 'w')
                f.write(artist_bio)
                f.close()
            except Exception, e:
                logger.error('Unable to write to the cache dir: ' + e)
                
        if artist_image_url:
            
            try:
                artwork = urllib2.urlopen(artist_image_url).read()
            except Exception, e:
                logger.error('Unable to open url "' + artist_image_url + '". Error: ' + str(e))
                
            if artwork:
                
                # Make sure the info dir exists:
                if not os.path.isdir(self.path_to_art_cache):
                    try:
                        os.makedirs(self.path_to_art_cache)
                    except Exception, e:
                        logger.error('Unable to create artwork cache dir. Error: ' + str(e))
                #Delete the old stuff
                for artwork_file in self.artwork_files:
                    try:
                        os.remove(artwork_file)
                    except:
                        logger.error('Error deleting file from the cache: ' + artwork_file)
                        
                artwork_path = os.path.join(self.path_to_art_cache, self.id + '.' + helpers.today() + '.' + artist_image_url.replace('/','%%%').replace(':','_%_'))
                try:
                    f = open(artwork_path, 'wb')
                    f.write(artwork)
                    f.close()
                except Exception, e:
                    logger.error('Unable to write to the cache dir: ' + str(e))
                    
def getArtwork(id, id_type):
    
    c = Cache()
    artwork_path = c.get_artwork_from_cache(id, id_type)
    return artwork_path
    
def getInfo(id, id_type):
    
    c = Cache()
    info_path = c.get_info_from_cache(id, id_type)
    return info_path
                    
def getArtworkURL(id, id_type):

    c = Cache()
    artwork_path = c.get_artwork_from_cache(id, id_type)
    filename = os.path.basename(artwork_path)
    encoded_url = filename.split('.')[2:]
    normal_url = encoded_url.replace('%%%','/').replace('_%_',':')
    return normal_url