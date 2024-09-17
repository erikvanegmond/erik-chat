import streamlit as st
import os
import json
import pandas as pd
import plotly.express as px
from google.cloud import firestore

db = firestore.Client.from_service_account_json("../firestore_key.json")
ADMIN_MAIL = os.environ.get('ADMIN_MAIL')

st.session_state.page = 'dashboard'


@st.dialog("Chat", width='large')
def chat_dialog(df_chat):
    st.dataframe(df_chat,
                 column_order=['avatar', 'role', 'datetime', 'content'],
                 column_config={'avatar': st.column_config.ImageColumn("Avatar")})


@st.cache_data
def get_chat_data():
    data = []
    posts_ref = db.collection("chats")
    # for doc in db.get_all(posts_ref.list_documents()):
    for doc in posts_ref.stream():
        chat_data = doc.to_dict()
        datetimes = [x['datetime'] for x in chat_data['conversation'] if 'datetime' in x]
        data.append({
            'name': chat_data['user_info']['name'],
            'avatar': chat_data['user_info']['picture'],
            'conversation_length': len(chat_data['conversation']),
            'chat_type': chat_data.get("chat_type"),
            'start': min(datetimes),
            'end': max(datetimes),
            'email': chat_data['user_info']['email'],
            'chat_id': chat_data['chat_id'],
            'session_id': chat_data.get('session_id'),
            'messages': chat_data['conversation']
        })
    df = pd.DataFrame(data).sort_values(by='start', ascending=False).reset_index(drop=True)
    df['start'] = pd.to_datetime(df.start, format='%d-%m-%Y %H:%M:%S')
    return df


@st.cache_data
def get_feedback_data():
    data = []
    posts_ref = db.collection("feedback")
    for doc in posts_ref.stream():
        feedback_data = doc.to_dict()
        data.append({
            'category': feedback_data['category'],
            'text': feedback_data['text'],
            'context': feedback_data['context'],
        })

    if data:
        return pd.DataFrame(data)
    return pd.DataFrame()


@st.cache_data
def get_session_data():
    data = []
    posts_ref = db.collection("sessions")
    for doc in posts_ref.stream():
        session_data = doc.to_dict()
        data.append({
            'session_start': session_data.get('session_start'),
            'session_id': session_data.get('session_id'),
            'session_activity': session_data.get('session_activity'),
            'session_length': len(session_data.get('session_activity')),
            'user': session_data.get('user_info', {}).get('email') if session_data.get('user_info', {}) else None,
        })

    if data:
        df = pd.DataFrame(data)
        df['session_start'] = pd.to_datetime(df.session_start, format='%d-%m-%Y %H:%M:%S')
        df = pd.DataFrame(data).sort_values(by='session_start', ascending=False).reset_index(drop=True)

        return df
    return pd.DataFrame()


hide_col, refresh_col = st.columns(2)
with hide_col:
    hide_admin = st.toggle("Verberg Admin")
with refresh_col:
    if st.button(":material/refresh: Refresh data"):
        get_chat_data.clear()
        get_feedback_data.clear()
        get_session_data.clear()

tab_chat, tab_feedback, tab_session = st.tabs(['Chat', 'Feedback', 'Sessions'])

with tab_chat:
    df_chat = get_chat_data()
    if hide_admin:
        df_chat = df_chat[df_chat.email != ADMIN_MAIL]
    st.write(
        px.bar(
            (
                df_chat.groupby(df_chat.start.dt.date)[['chat_id']]
                .count()
                .reset_index()
                .rename(columns={'chat_id': 'Aantal', 'start': 'Datum'})
            ),
            x='Datum',
            y='Aantal',
            height=300
        )
    )

    event = st.dataframe(df_chat,
                         on_select="rerun",
                         selection_mode='single-row',
                         column_config={'messages': None, 'avatar': st.column_config.ImageColumn("Avatar")})

    if event.selection.rows:
        df_chat_messages = pd.DataFrame(df_chat.iloc[event.selection.rows[0]]['messages'])
        chat_dialog(df_chat_messages)

with tab_feedback:
    df_feedback = get_feedback_data()

    if df_feedback.empty:
        st.write("Nog geen feedback ontvangen")
    else:
        st.write(df_feedback)

with tab_session:
    df_session = get_session_data()
    df_session['has_chat'] = df_session.session_id.apply(lambda x: x in df_chat.session_id.values)
    event = st.dataframe(df_session, on_select="rerun",
                         selection_mode='single-row',
                         column_config={'session_id': None, 'session_activity': None, })
    if event.selection.rows:
        session = df_session.iloc[event.selection.rows[0]]
        st.header("Session Data")
        st.write(f"Session id: {session.session_id}")
        st.write(pd.DataFrame(session.session_activity))
