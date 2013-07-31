import sys
import os.path

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources/lib'))

from xbmcswift2 import Plugin
from xbmcswift2 import xbmc, xbmcgui, xbmcaddon
from requests_oauthlib import OAuth1Session, OAuth1
import requests
from datetime import datetime, timedelta
from xml.dom.minidom import parseString
import oauthlib
import urllib


plugin = Plugin()
storage = plugin.get_storage('storage')

OAUTH_CONSUMER_KEY = 'fa1c9359-984c-40af-bed0-18854a1f4647'
OAUTH_CONSUMER_SECRET = '137108407390855967187518585103907027345'

OAUTH_REQUEST_TOKEN_URL = 'https://cloudpt.pt/oauth/request_token'
OAUTH_AUTHORIZE_TOKEN_URL = 'https://cloudpt.pt/oauth/authorize'
OAUTH_ACCESS_TOKEN_URL = 'https://cloudpt.pt/oauth/access_token'

PUNY_URL = 'http://services.sapo.pt/PunyURL/GetCompressedURLByURL'

CLOUDPT_API_URL = 'https://api.cloudpt.pt'
CLOUDPT_API_CONTENT_URL = 'https://api-content.cloudpt.pt'

API_METADATA_URL = CLOUDPT_API_URL + '/1/Metadata/cloudpt'
API_SEARCH_URL = CLOUDPT_API_URL + '/1/Search/cloudpt/'
API_MEDIA_URL = CLOUDPT_API_URL + '/1/Media/cloudpt'
API_THUMB_URL = CLOUDPT_API_CONTENT_URL + '/1/Thumbnails/cloudpt'
API_FILES_URL = CLOUDPT_API_CONTENT_URL + '/1/Files/cloudpt'

IMAGE_MIMES = set(['image/jpeg', 'image/png', 'image/tiff', 'image/x-ms-bmp', 'image/gif'])
AUDIO_MIMES = set(['audio/mpeg', 'audio/mp4', 'audio/x-flac', 'audio/mp4'])
VIDEO_MIMES = set(['video/quicktime', 'video/mp4', 'video/mpeg', 'video/x-msvideo', 'video/x-ms-wmv'])

rsession = requests.Session()

settings = xbmcaddon.Addon(id='plugin.video.cloudptxbmc')
temporary_path = xbmc.translatePath(settings.getAddonInfo('profile'))

@plugin.route('/')
def index():
    plugin.log.info(plugin.request.args)
    if 'oauth_token_secret' in storage and 'oauth_token_key' in storage:
        has_login = True
    else:
        has_login = False

    items = []

    if has_login:

        content_type = plugin.request.args.get('content_type')
        if not content_type:
            url = plugin.url_for(endpoint='show_content_types')
            return plugin.redirect(url)
        if isinstance(content_type, (list, tuple)):
            content_type = content_type[0]

        if content_type == 'video':
            plugin.redirect(plugin.url_for('browse_video'))
        elif content_type == 'audio':
            plugin.redirect(plugin.url_for(endpoint='browse_audio', path='/'))
        elif content_type == 'image':
            plugin.redirect(plugin.url_for(endpoint='browse_image', path='/'))
        else:
            plugin.notify('Unkown content_type: {0}'.format(content_type))

        item = {
            'label': 'Logout',
            'path': plugin.url_for('logout'),
        }
        items.append(item)
    else:
        item = {
            'label': 'Login',
            'path': plugin.url_for('login'),
        }
        items.append(item)

    return items


@plugin.route('/browse_image<path>')
def browse_image(path):
    # fetch files from root dir
    auth = OAuth1(OAUTH_CONSUMER_KEY, OAUTH_CONSUMER_SECRET, storage['oauth_token_key'], storage['oauth_token_secret'])
    signer = oauthlib.oauth1.Client(client_key=OAUTH_CONSUMER_KEY,
                                    client_secret=OAUTH_CONSUMER_SECRET,
                                    resource_owner_key=storage['oauth_token_key'],
                                    resource_owner_secret=storage['oauth_token_secret'],
                                    signature_type=oauthlib.oauth1.SIGNATURE_TYPE_QUERY)
    resp_list = rsession.get(API_METADATA_URL + path, auth=auth)

    items = []
    if resp_list.status_code == 200:
        api_res = resp_list.json()
        plugin.log.info(api_res)

        for entry in api_res['contents']:
            if entry['is_dir']:
                items.append({
                    'label': entry['path'],
                    'path': plugin.url_for(endpoint='browse_image', path=entry['path'].encode('utf-8')),
                })
            elif entry['mime_type'] in IMAGE_MIMES:
                item = {
                    'label': entry['path'],
                    #'path': plugin.url_for(
                    #    endpoint='play_media',
                    #    path=entry['path'].encode('utf-8'),
                    #),
                    'is_playable': True,
                }

                # the slideshow stuff does not seem to support receiving plugin:// URLs...
                # this is a problem because these URLs will only work for 300s
                file_url, _, _ = signer.sign(API_FILES_URL + urllib.quote(entry['path'].encode('utf-8')))
                item['path'] = file_url

                if entry['thumb_exists']:
                    thumb_url, _, _ = signer.sign(API_THUMB_URL + urllib.quote(entry['path'].encode('utf-8')) + '?size=m&format=png')
                    item['thumbnail'] = thumb_url

                items.append(item)

    return plugin.finish(items, view_mode='thumbnail')


@plugin.route('/browse_audio<path>')
def browse_audio(path):
    # fetch files from root dir
    auth = OAuth1(OAUTH_CONSUMER_KEY, OAUTH_CONSUMER_SECRET, storage['oauth_token_key'], storage['oauth_token_secret'])
    signer = oauthlib.oauth1.Client(client_key=OAUTH_CONSUMER_KEY,
                                    client_secret=OAUTH_CONSUMER_SECRET,
                                    resource_owner_key=storage['oauth_token_key'],
                                    resource_owner_secret=storage['oauth_token_secret'],
                                    signature_type=oauthlib.oauth1.SIGNATURE_TYPE_QUERY)
    resp_list = rsession.get(API_METADATA_URL + path, auth=auth)

    items = []
    if resp_list.status_code == 200:
        api_res = resp_list.json()
        plugin.log.info(api_res)

        for entry in api_res['contents']:
            if entry['is_dir']:
                items.append({
                    'label': entry['path'],
                    'path': plugin.url_for(endpoint='browse_audio', path=entry['path'].encode('utf-8')),
                })
            elif entry['mime_type'] in AUDIO_MIMES:
                item = {
                    'label': entry['path'],
                    'path': plugin.url_for(
                        endpoint='play_media',
                        path=entry['path'].encode('utf-8'),
                    ),
                    'is_playable': True,
                }

                if entry['thumb_exists']:
                    thumb_url, _, _ = signer.sign(API_THUMB_URL + urllib.quote(entry['path'].encode('utf-8')) + '?size=m&format=png')
                    item['thumbnail'] = thumb_url

                items.append(item)

    return items


@plugin.route('/browse_video')
def browse_video():
    auth = OAuth1(OAUTH_CONSUMER_KEY, OAUTH_CONSUMER_SECRET, storage['oauth_token_key'], storage['oauth_token_secret'])
    signer = oauthlib.oauth1.Client(client_key=OAUTH_CONSUMER_KEY,
                                    client_secret=OAUTH_CONSUMER_SECRET,
                                    resource_owner_key=storage['oauth_token_key'],
                                    resource_owner_secret=storage['oauth_token_secret'],
                                    signature_type=oauthlib.oauth1.SIGNATURE_TYPE_QUERY)
    search_params = {'query': '*', 'mime_type': VIDEO_MIMES}
    resp_search = rsession.get(API_SEARCH_URL, params=search_params, auth=auth)
    plugin.log.info(resp_search.json())

    items = []
    if resp_search.status_code == 200:
        api_res = resp_search.json()

        for entry in api_res:

            item = {
                'label': entry['path'],
                'path': plugin.url_for(
                    endpoint='play_media',
                    path=entry['path'].encode('utf-8'),
                ),
                'is_playable': True,
            }

            if entry['thumb_exists']:
                thumb_url, _, _ = signer.sign(API_THUMB_URL + urllib.quote(entry['path'].encode('utf-8')) + '?size=m&format=png')
                item['thumbnail'] = thumb_url

            items.append(item)

    return plugin.finish(items, view_mode='thumbnail')


@plugin.route('/play_media<path>')
def play_media(path):
    auth = OAuth1(OAUTH_CONSUMER_KEY, OAUTH_CONSUMER_SECRET, storage['oauth_token_key'], storage['oauth_token_secret'])
    signer = oauthlib.oauth1.Client(client_key=OAUTH_CONSUMER_KEY,
                                    client_secret=OAUTH_CONSUMER_SECRET,
                                    resource_owner_key=storage['oauth_token_key'],
                                    resource_owner_secret=storage['oauth_token_secret'],
                                    signature_type=oauthlib.oauth1.SIGNATURE_TYPE_QUERY)
    resp_media = rsession.post(API_MEDIA_URL + path, auth=auth)
    if resp_media.status_code == 200:
        api_res = resp_media.json()
        return plugin.set_resolved_url(api_res['url'])
    elif resp_media.status_code == 403:
        # could not create link. Let's try a direct API link
        file_url, _, _ = signer.sign(API_FILES_URL + urllib.quote(path))
        return plugin.set_resolved_url(file_url)
    else:
        plugin.log.error(resp_media)
        plugin.log.error(resp_media.content)
        plugin.notify(msg='Could not play file', title='Error', delay=5000)
        return plugin.finish(succeeded=False)


@plugin.route('/content_types')
def show_content_types():
    items = (
        { 'label': 'Video',
          'path': plugin.url_for(
              endpoint='index',
              content_type='video',
          )
        },
        { 'label': 'Audio',
          'path': plugin.url_for(
              endpoint='index',
              content_type='audio',
          )
        },
        { 'label': 'Image',
          'path': plugin.url_for(
              endpoint='index',
              content_type='image',
          )
        },
    )
    return plugin.finish(items)


@plugin.route('/login')
def login():

    # phase 1 - obtain authorization URL
    oauth = OAuth1Session(OAUTH_CONSUMER_KEY, client_secret=OAUTH_CONSUMER_SECRET, callback_uri='oob')
    request_token = oauth.fetch_request_token(OAUTH_REQUEST_TOKEN_URL)
    authorization_url = oauth.authorization_url(OAUTH_AUTHORIZE_TOKEN_URL)
    plugin.log.info('Authorization URL: {0}'.format(authorization_url))

    # phase 2 - compress URL and show it
    expires = (datetime.now() + timedelta(hours=1)).isoformat()
    puny_params = {'url': authorization_url, 'random': '1', 'expires': expires}
    resp_puny = rsession.get(PUNY_URL, params=puny_params)
    compressed_url = parseString(resp_puny.content).getElementsByTagName('ascii')[0].childNodes[0].nodeValue
    dialog = xbmcgui.Dialog()
    dialog.ok('Open URL in browser', compressed_url)

    # phase 3 - obtain verifier
    verifier = plugin.keyboard(heading='Insert verifier')
    plugin.log.info('Got verifier: {0}'.format(verifier))

    # phase 4 - obtain authenticated access token
    oauth = OAuth1Session(OAUTH_CONSUMER_KEY,
                          client_secret=OAUTH_CONSUMER_SECRET,
                          resource_owner_key=request_token['oauth_token'],
                          resource_owner_secret=request_token['oauth_token_secret'],
                          verifier=verifier)
    access_token = oauth.fetch_access_token(OAUTH_ACCESS_TOKEN_URL)
    storage['oauth_token_key'] = access_token['oauth_token']
    storage['oauth_token_secret'] = access_token['oauth_token_secret']

    url = plugin.url_for('index')
    plugin.redirect(url)


@plugin.route('/logout')
def logout():
    if 'oauth_token_key' in storage:
        del storage['oauth_token_key']
    if 'oauth_token_secret' in storage:
        del storage['oauth_token_secret']

    url = plugin.url_for('index')
    plugin.redirect(url)


if __name__ == '__main__':
    plugin.run()
