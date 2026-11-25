# ======== Add to aerohealth/settings.py (merge, don't replace the file) ========

# 1) INSTALLED_APPS: add these five lines (keep everything already there, including 'accounts')
#     'django.contrib.sites',
#     'allauth',
#     'allauth.account',
#     'allauth.socialaccount',
#     'allauth.socialaccount.providers.google',

# 2) MIDDLEWARE: add these two lines right AFTER 'django.contrib.auth.middleware.AuthenticationMiddleware',
#     'allauth.account.middleware.AccountMiddleware',
#     'accounts.middleware.ProfileRequiredMiddleware',

# 3) Paste at the bottom of the file:
import os
SITE_ID = 1
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
LOGIN_REDIRECT_URL = '/'
ACCOUNT_EMAIL_VERIFICATION = 'none'            # Google already verifies the email
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*']             # username is generated automatically for Google users
SOCIALACCOUNT_AUTO_SIGNUP = True               # straight on to /complete-profile/
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.environ.get('GOOGLE_CLIENT_ID', ''),
            'secret': os.environ.get('GOOGLE_CLIENT_SECRET', ''),
            'key': '',
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}
# (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET come from your .env file)
