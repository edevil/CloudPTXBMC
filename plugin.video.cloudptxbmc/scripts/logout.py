
from xbmcswift2 import xbmc, xbmcgui, xbmcaddon, Plugin

__addon_id__ = 'plugin.video.cloudptxbmc'
__addon_name__ = 'CloudPT XBMC'

# Somehow, xbmc crashes without these. Probably because it's an outside script
plugin = Plugin(__addon_name__, __addon_id__, 'addon.py')

storage = plugin.get_storage('storage')
settings = xbmcaddon.Addon(id='plugin.video.cloudptxbmc')

# Get current username
currentUser = settings.getSetting( "settings.user.name" )

# Clear oauth info from storage and remove username from settings

if 'oauth_token_key' in storage:
	del storage['oauth_token_key']
if 'oauth_token_secret' in storage:
	del storage['oauth_token_secret']

# This should not be needed. Still...
storage.sync()


settings.setSetting("settings.user.name", "")
settings.setSetting("settings.user.email", "")

# Show logged of info
xbmcgui.Dialog().ok('Logout','User "%s" logged off.' % currentUser)

