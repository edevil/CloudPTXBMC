import sys
import os.path

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources/lib'))

from xbmcswift2 import Plugin
from xbmcswift2 import xbmc, xbmcgui
from requests_oauthlib import OAuth1Session, OAuth1
import requests
from datetime import datetime, timedelta
from xml.dom.minidom import parseString

plugin = Plugin()
storage = plugin.get_storage('storage')

OAUTH_CONSUMER_KEY = 'fa1c9359-984c-40af-bed0-18854a1f4647'
OAUTH_CONSUMER_SECRET = '137108407390855967187518585103907027345'

OAUTH_REQUEST_TOKEN_URL = 'https://cloudpt.pt/oauth/request_token'
OAUTH_AUTHORIZE_TOKEN_URL = 'https://cloudpt.pt/oauth/authorize'
OAUTH_ACCESS_TOKEN_URL = 'https://cloudpt.pt/oauth/access_token'

PUNY_URL = 'http://services.sapo.pt/PunyURL/GetCompressedURLByURL'

API_METADATA_URL = 'https://api.cloudpt.pt/1/Metadata/cloudpt'

rsession = requests.Session()

@plugin.route('/')
def index():
    if 'oauth_token_secret' in storage and 'oauth_token_key' in storage:
        has_login = True
    else:
        has_login = False

    items = []
    if has_login:
        # fetch files from root dir
        auth = OAuth1(OAUTH_CONSUMER_KEY, OAUTH_CONSUMER_SECRET, storage['oauth_token_key'], storage['oauth_token_secret'])
        resp_list = rsession.get(API_METADATA_URL + '/', auth=auth)
        if resp_list.status_code == 200:
            plugin.log.info(resp_list.json())

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
