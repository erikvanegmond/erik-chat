import streamlit as st
import os
import json
import pandas as pd
import plotly.express as px


@st.dialog("Chat", width='large')
def chat_dialog(df_chat):
    st.dataframe(df_chat,
                 column_order=['avatar', 'role', 'datetime', 'content'],
                 column_config={'avatar': st.column_config.ImageColumn("Avatar")})

tab_chat, tab_feedback = st.tabs(['Chat', 'Feedback'])

with tab_chat:
    data = []
    for root, _, files in os.walk('conversations'):
        for filename in files:
            with open(os.path.join(root, filename), 'r', encoding='utf-8') as f:
                chat_data = json.load(f)
                datetimes = [x['datetime'] for x in chat_data['conversation'] if 'datetime' in x]
                data.append({
                    'name': chat_data['user_info']['name'],
                    'conversation_length': len(chat_data['conversation']),
                    'start': min(datetimes),
                    'end': max(datetimes),
                    'email': chat_data['user_info']['email'],
                    'chat_id': chat_data['chat_id'],
                })
    df = pd.DataFrame(data).sort_values(by='start', ascending=False).reset_index(drop=True)
    df['start'] = pd.to_datetime(df.start, format='%d-%m-%Y %H:%M:%S')

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

    event = st.dataframe(df, on_select="rerun", selection_mode='single-row')
    if event.selection.rows:
        with open(os.path.join('conversations', df.iloc[event.selection.rows[0]]['chat_id'] + '.json'), 'r',
                  encoding='utf-8') as f:
            chat_data = json.load(f)
        df_chat = pd.DataFrame(chat_data['conversation'])
        chat_dialog(df_chat)


with tab_feedback:
    data = []
    for root, _, files in os.walk('feedback'):
        for filename in files:
            with open(os.path.join(root, filename), 'r', encoding='utf-8') as f:
                feedback_data = json.load(f)
                # st.json(feedback_data)
                data.append({
                    'category': feedback_data['category'],
                    'text': feedback_data['text'],
                    'context': feedback_data['context'],
                })

    if data:
        df = pd.DataFrame(data)
        st.write(df)
    else:
        st.write("Nog geen feedback ontvangen")