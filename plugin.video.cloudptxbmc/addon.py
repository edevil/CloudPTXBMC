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
import CommonFunctions as common

# Show qrcode window definitions
# Should be closed after anykey
class QRCodePopupWindow(xbmcgui.WindowDialog):
    def __init__(self, linha1, linha2, linha3, qrcodefile):
        XBFONT_LEFT = 0x00000000
        XBFONT_RIGHT = 0X00000001
        XBFONT_CENTER_X = 0X00000002
        XBFONT_CENTER_Y = 0X00000004
        XBFONT_TRUNCATED = 0X00000008

        # Relative resolutions to 1920x1080 (1080p)
        self.setCoordinateResolution(0)

        self.addControl(xbmcgui.ControlImage(x=610, y=190, width=700, height=700, filename=os.path.join(MEDIADIR, "background_qrcode.png")))
        self.addControl(xbmcgui.ControlImage(x=710, y=240, width=500, height=500, filename=qrcodefile))
        self.addControl(xbmcgui.ControlLabel(x=610, y=760, width=700, height=25, label=linha1, alignment=XBFONT_CENTER_X))
        self.addControl(xbmcgui.ControlLabel(x=610, y=800, width=700, height=25, label=linha2, alignment=XBFONT_CENTER_X))
        self.addControl(xbmcgui.ControlLabel(x=610, y=840, width=700, height=25, label=linha3, alignment=XBFONT_CENTER_X))

    def onAction(self, action):
        ACTION_PREVIOUS_MENU = 10
        #if action == ACTION_PREVIOUS_MENU:
        self.close()

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
API_USERINFO_URL = CLOUDPT_API_URL + '/1/Account/Info'

IMAGE_MIMES = set(['image/jpeg', 'image/png', 'image/tiff', 'image/x-ms-bmp', 'image/gif'])
AUDIO_MIMES = set(['audio/mpeg', 'audio/mp4', 'audio/x-flac', 'audio/mp4'])
VIDEO_MIMES = set(['video/quicktime', 'video/mp4', 'video/mpeg', 'video/x-msvideo', 'video/x-ms-wmv', 'video/x-matroska'])

ADDONID = 'plugin.video.cloudptxbmc'
settings = xbmcaddon.Addon(id=ADDONID)

MEDIADIR = os.path.join(xbmc.translatePath(settings.getAddonInfo('path')),'resources', 'media')

rsession = requests.Session()

language = settings.getLocalizedString
dbg = settings.getSetting("settings.debug") == "true"
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
            plugin.redirect(plugin.url_for(endpoint='browse_video', path='/'))
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
        
        # Force login if we don't have auth info
        url = plugin.url_for('login')
        plugin.redirect(url)

    return items


@plugin.route('/browse_image<path>')
def browse_image(path):

    pDialog = xbmcgui.DialogProgress()
    ret = pDialog.create(language(30000), language(30018))

    # fetch files from root dir
    auth = OAuth1(OAUTH_CONSUMER_KEY, OAUTH_CONSUMER_SECRET, storage['oauth_token_key'], storage['oauth_token_secret'])
    signer = oauthlib.oauth1.Client(client_key=OAUTH_CONSUMER_KEY,
                                    client_secret=OAUTH_CONSUMER_SECRET,
                                    resource_owner_key=storage['oauth_token_key'],
                                    resource_owner_secret=storage['oauth_token_secret'],
                                    signature_type=oauthlib.oauth1.SIGNATURE_TYPE_QUERY)
    resp_list = rsession.get(API_METADATA_URL + path, auth=auth)

    if resp_list.status_code == 200:
        api_res = resp_list.json()
        plugin.log.info(api_res)

        photosize = settings.getSetting('settings.photos.size')

        totalItems = len(api_res['contents'])
        itemCount = 0

        items = []
        
        for entry in api_res['contents']:
            itemCount = itemCount + 1
            pDialog.update( float(itemCount)/float(totalItems)*100, os.path.basename(entry['path']).encode('utf-8') )
            #xbmc.sleep(1000)

            if entry['is_dir']:
                items.append({
                    'label': os.path.basename(entry['path']),
                    'path': plugin.url_for(endpoint='browse_image', path=entry['path'].encode('utf-8')),
                })
            elif entry['mime_type'] in IMAGE_MIMES:
                item = {
                    'label': os.path.basename(entry['path']),
                    #'path': plugin.url_for(
                    #    endpoint='play_media',
                    #    path=entry['path'].encode('utf-8'),
                    #),
                    'is_playable': True,
                }

                # the slideshow stuff does not seem to support receiving plugin:// URLs...
                # this is a problem because these URLs will only work for 300s

                # Use thumb or original from settings
                if (photosize == '1'):
                    file_url, _, _ = signer.sign(API_THUMB_URL + urllib.quote(entry['path'].encode('utf-8')) + '?size=xl')
                else:
                    file_url, _, _ = signer.sign(API_FILES_URL + urllib.quote(entry['path'].encode('utf-8')))

                # file_url, _, _ = signer.sign(API_FILES_URL + urllib.quote(entry['path'].encode('utf-8')))
                item['path'] = file_url

                if entry['thumb_exists']:
                    thumb_url, _, _ = signer.sign(API_THUMB_URL + urllib.quote(entry['path'].encode('utf-8')) + '?size=m&format=png')
                    item['thumbnail'] = thumb_url

                items.append(item)

        pDialog.close()

        return plugin.finish(items)
    else:
        pDialog.close()

        plugin.log.error(resp_list)
        plugin.log.error(resp_list.content)
        plugin.notify(msg=language(30011), title=language(30012), delay=5000)
        return plugin.finish(succeeded=False)


@plugin.route('/browse_audio<path>')
def browse_audio(path):

    pDialog = xbmcgui.DialogProgress()
    ret = pDialog.create(language(30000), language(30018))

    # fetch files from root dir
    auth = OAuth1(OAUTH_CONSUMER_KEY, OAUTH_CONSUMER_SECRET, storage['oauth_token_key'], storage['oauth_token_secret'])
    signer = oauthlib.oauth1.Client(client_key=OAUTH_CONSUMER_KEY,
                                    client_secret=OAUTH_CONSUMER_SECRET,
                                    resource_owner_key=storage['oauth_token_key'],
                                    resource_owner_secret=storage['oauth_token_secret'],
                                    signature_type=oauthlib.oauth1.SIGNATURE_TYPE_QUERY)
    resp_list = rsession.get(API_METADATA_URL + path, auth=auth)

    if resp_list.status_code == 200:
        api_res = resp_list.json()
        plugin.log.info(api_res)

        totalItems = len(api_res['contents'])
        itemCount = 0

        items = []
        for entry in api_res['contents']:

            itemCount = itemCount + 1
            pDialog.update( float(itemCount)/float(totalItems)*100, os.path.basename(entry['path']).encode('utf-8') )
            #xbmc.sleep(1000)

            if entry['is_dir']:
                items.append({
                    'label': os.path.basename(entry['path']),
                    'path': plugin.url_for(endpoint='browse_audio', path=entry['path'].encode('utf-8')),
                })
            elif entry['mime_type'] in AUDIO_MIMES:
                item = {
                    'label': os.path.basename(entry['path']),
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

        pDialog.close()

        return items
    else:

        pDialog.close()

        plugin.log.error(resp_list)
        plugin.log.error(resp_list.content)
        plugin.notify(msg=language(30011), title=language(30012), delay=5000)
        return plugin.finish(succeeded=False)


@plugin.route('/browse_video<path>')
def browse_video(path):

    pDialog = xbmcgui.DialogProgress()
    ret = pDialog.create(language(30000), language(30018))

    auth = OAuth1(OAUTH_CONSUMER_KEY, OAUTH_CONSUMER_SECRET, storage['oauth_token_key'], storage['oauth_token_secret'])
    signer = oauthlib.oauth1.Client(client_key=OAUTH_CONSUMER_KEY,
                                    client_secret=OAUTH_CONSUMER_SECRET,
                                    resource_owner_key=storage['oauth_token_key'],
                                    resource_owner_secret=storage['oauth_token_secret'],
                                    signature_type=oauthlib.oauth1.SIGNATURE_TYPE_QUERY)
    resp_list = rsession.get(API_METADATA_URL + path, auth=auth)

    if resp_list.status_code == 200:
        api_res = resp_list.json()
        plugin.log.info(api_res)


        totalItems = len(api_res['contents'])
        itemCount = 0

        items = []
        #items.append({
        #    'label': 'SSL Video from sandbox',
        #    'path' : 'https://sandbox.eep.pt/xbmc/video.mov',
        #    'is_playable' : True
        #    })
        #items.append({
        #    'label': 'NOSSL Video from sandbox',
        #    'path' : 'http://sandbox.eep.pt/xbmc/video.mov',
        #    'is_playable' : True
        #    })
        #items.append({
        #    'label': 'SSL MP4 from sandbox',
        #    'path' : 'https://sandbox.eep.pt/xbmc/video.mp4',
        #    'is_playable' : True
        #    })
        #items.append({
        #    'label': 'NOSSL MP4 from sandbox',
        #    'path' : 'http://sandbox.eep.pt/xbmc/video.mp4',
        #    'is_playable' : True
        #    })

        for entry in api_res['contents']:

            itemCount = itemCount + 1
            pDialog.update( float(itemCount)/float(totalItems)*100, os.path.basename(entry['path']).encode('utf-8') )
            #xbmc.sleep(1000)

            if entry['is_dir']:
                items.append({
                    'label': os.path.basename(entry['path']),
                    'path': plugin.url_for(endpoint='browse_video', path=entry['path'].encode('utf-8')),
                })
            elif entry['mime_type'] in VIDEO_MIMES:
                item = {
                    'label': os.path.basename(entry['path']),
                    'path': plugin.url_for(
                        endpoint='play_media',
                        path=entry['path'].encode('utf-8'),
                    ),
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

        pDialog.close()
        return items
    else:
        pDialog.close()
        plugin.log.error(resp_list)
        plugin.log.error(resp_list.content)
        plugin.notify(msg=language(30011), title=language(30012), delay=5000)
        return plugin.finish(succeeded=False)


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
        plugin.notify(msg=language(30014), title=language(30012), delay=5000)
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

    #dialog = xbmcgui.Dialog()
    #dialog.ok(language(30007), language(30008), compressed_url, language(30009))

    # Show qrcode along with URL
    import tempfile
    qrcodefile = tempfile.gettempdir() + '/' + 'cloudptQRCode.jpg'

    import pyqrcode
    qr_image = pyqrcode.MakeQRImage(compressed_url, rounding = 5, fg = "black", bg = "White", br = False)
    qr_image.save(qrcodefile)

    qrwindow = QRCodePopupWindow(language(30008), compressed_url, language(30009), qrcodefile)
    qrwindow.doModal()
    del qrwindow

    # phase 3 - obtain verifier
    verifier = common.getUserInputNumbers(language(30010))
    plugin.log.info('Got verifier: {0}'.format(verifier))

    if len(verifier) == 0:
        plugin.notify(msg=language(30015), title=language(30012), delay=5000)
    else:
        try:
            # phase 4 - obtain authenticated access token
            oauth = OAuth1Session(OAUTH_CONSUMER_KEY,
                          client_secret=OAUTH_CONSUMER_SECRET,
                          resource_owner_key=request_token['oauth_token'],
                          resource_owner_secret=request_token['oauth_token_secret'],
                          verifier=verifier)
            access_token = oauth.fetch_access_token(OAUTH_ACCESS_TOKEN_URL)
            storage['oauth_token_key'] = access_token['oauth_token']
            storage['oauth_token_secret'] = access_token['oauth_token_secret']

            # We need some user info now
            auth = OAuth1(OAUTH_CONSUMER_KEY, OAUTH_CONSUMER_SECRET, storage['oauth_token_key'], storage['oauth_token_secret'])
            signer = oauthlib.oauth1.Client(client_key=OAUTH_CONSUMER_KEY,
                                    client_secret=OAUTH_CONSUMER_SECRET,
                                    resource_owner_key=storage['oauth_token_key'],
                                    resource_owner_secret=storage['oauth_token_secret'],
                                    signature_type=oauthlib.oauth1.SIGNATURE_TYPE_QUERY)
            resp_userinfo = rsession.get(API_USERINFO_URL, auth=auth)
            if resp_userinfo.status_code == 200:
                api_res = resp_userinfo.json()
                settings.setSetting("settings.user.name", api_res['display_name'])
                settings.setSetting("settings.user.email", api_res['email'])
            else:
                # TODO
                # This may leave some inconsistency if we have a user but could not get its info
                # Maybe we should clean up the tokens if we don't have user info?
                plugin.log.error(resp_userinfo)
                plugin.log.error(resp_userinfo.content)
                plugin.notify(msg=language(30015), title=language(30012), delay=5000)
        
            url = plugin.url_for('index')
            plugin.redirect(url)
        except:
            plugin.notify(msg=language(30015), title=language(30012), delay=5000)



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
