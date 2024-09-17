import streamlit as st
import os
import json
import pandas as pd
import plotly.express as px
from google.cloud import firestore

db = firestore.Client.from_service_account_json("../firestore_key.json")
ADMIN_MAIL = os.environ.get('ADMIN_MAIL')


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
            'start': min(datetimes),
            'end': max(datetimes),
            'email': chat_data['user_info']['email'],
            'chat_id': chat_data['chat_id'],
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


hide_col, refresh_col = st.columns(2)
with hide_col:
    hide_admin = st.toggle("Verberg Admin")
with refresh_col:
    if st.button(":material/refresh: Refresh data"):
        get_chat_data.clear()
        get_feedback_data.clear()

tab_chat, tab_feedback = st.tabs(['Chat', 'Feedback'])

with tab_chat:
    df = get_chat_data()
    if hide_admin:
        df = df[df.email != ADMIN_MAIL]
    st.write(
        px.bar(
            (
                df.groupby(df.start.dt.date)[['chat_id']]
                .count()
                .reset_index()
                .rename(columns={'chat_id': 'Aantal', 'start': 'Datum'})
            ),
            x='Datum',
            y='Aantal',
            height=300
        )
    )

    event = st.dataframe(df,
                         on_select="rerun",
                         selection_mode='single-row',
                         column_config={'messages': None, 'avatar': st.column_config.ImageColumn("Avatar")})

    if event.selection.rows:
        df_chat = pd.DataFrame(df.iloc[event.selection.rows[0]]['messages'])
        chat_dialog(df_chat)

with tab_feedback:
    df = get_feedback_data()

    if df.empty:
        st.write("Nog geen feedback ontvangen")
    else:
        st.write(df)
