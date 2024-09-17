import streamlit as st
from streamlit_oauth import OAuth2Component
import os
import requests
from dotenv import load_dotenv
from components import toestemming, feedback, new_conversation, chat_bot
import gettext

from google.cloud import firestore

_ = gettext.gettext
load_dotenv()

# Set constants
AUTHORIZE_URL = os.environ.get('AUTHORIZE_URL')
TOKEN_URL = os.environ.get('TOKEN_URL')
REFRESH_TOKEN_URL = os.environ.get('REFRESH_TOKEN_URL')
REVOKE_TOKEN_URL = os.environ.get('REVOKE_TOKEN_URL')
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REDIRECT_URI = os.environ.get('REDIRECT_URI')
SCOPE = os.environ.get('SCOPE')
APP_ENV = os.environ.get('APP_ENV')
ADMIN_MAIL = os.environ.get('ADMIN_MAIL')

st.set_page_config(page_title=_('Gesprek met Erik'), page_icon='💬', layout="centered", initial_sidebar_state="auto",
                   menu_items=None)

db = firestore.Client.from_service_account_json("../firestore_key.json")

if 'show_conversation_starters' not in st.session_state:
    st.session_state['show_conversation_starters'] = True

debug = False
if 'userinfo' in st.session_state and st.session_state.userinfo['email'] == ADMIN_MAIL:
    admin = True
else:
    admin = False

oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, REFRESH_TOKEN_URL, REVOKE_TOKEN_URL)

with st.sidebar:
    if admin:
        debug = st.toggle('Debug')

    if st.button("Toestemming en introductie", key='toestemming_button_sidebar'):
        toestemming()

    if st.session_state.get('akkoord') and st.session_state.get('userinfo'):
        if st.button("Nieuw gesprek"):
            new_conversation()
        if st.button("Feedback"):
            feedback()

    if debug:
        with st.expander('Session State'):
            st.json(st.session_state)

if APP_ENV == 'dev':
    st.warning('Running in dev-mode', icon="⚠️")
    st.session_state.userinfo = {
        "name": "Erik van Egmond",
        "locale": {
            "country": "US",
            "language": "en"
        },
        "given_name": "Erik",
        "family_name": "van Egmond",
        "email": ADMIN_MAIL,
        "picture": "🧑‍💻"
    }


def main_page():
    st.title("💬 Gesprek met Erik")

    if "akkoord" not in st.session_state:
        toestemming()
        st.write("Deze site is alleen te gebruiken na toestemming")
    elif st.session_state.akkoord:
        if 'userinfo' in st.session_state:
            chat_bot(debug=debug)
        elif 'token' not in st.session_state:
            # If not, show authorize button
            result = oauth2.authorize_button("Login with LinkedIn", REDIRECT_URI, SCOPE)
            if result and 'token' in result:
                # If authorization successful, save token in session state
                st.session_state.token = result.get('token')
                st.rerun()
        else:
            # If token exists in session state, retrieve linkedin data
            res = requests.get('https://api.linkedin.com/v2/userinfo',
                               headers={'Authorization': f'Bearer {st.session_state['token']['access_token']}'})
            st.session_state.userinfo = res.json()
            new_conversation()
            st.rerun()
    else:
        st.write(
            "Deze site is alleen te gebruiken na toestemming.\n\n Geef toestemming via het menu aan de linker kant.")


page_list = [st.Page(main_page, title='Chat', default=True, icon=":material/chat_bubble:"),
             st.Page('app_pages/hoe_werkt_het.py', title="Hoe werkt het?", icon=":material/question_mark:")]

if admin:
    page_list += [
        st.Page(
            "app_pages/dashboard.py",
            title="Dashboard",
            icon=":material/dashboard:"
        ),
        st.Page(
            "app_pages/test_utils.py",
            title="Test utils",
            icon=":material/labs:"
        ),
        st.Page(
            "app_pages/reload_data.py",
            title="Reload data",
            icon=":material/refresh:"
        ),
    ]

pg = st.navigation(page_list)
pg.run()
