import datetime
import json
import os
import uuid

import streamlit as st
from openai import OpenAI

from utils import Prompts, read_cv, vacature_check, AVATAR_IMAGE, extra_informatie, save_conversation


@st.dialog("Toestemming en introductie")
def toestemming():
    st.write('''
             Dit is een chatbot gebaseerd op een groot taalmodel (LLM) die zich voordoet als Erik. Hiervoor 
             wordt een openAI model gebruikt en worden jou berichten naar openAI gestuurd.
             Hoewel de chatbot zijn best doet om nauwkeurige en nuttige informatie te bieden,
             kan hij fouten maken in zijn antwoorden, of zelfs lariekoek verkondigen. Het is raadzaam om de antwoorden
             die je krijgt altijd te verifiëren met mijn cv, of natuurlijk met de echte Erik.  
             
             Om gebruik te maken van de ze chatbot moet je inloggen met LinkedIn, deze website ontvangt 
             dan je naam en email adres. Deze gegevens worden pas opgeslagen nadat je je eerste 
             bericht hebt verstuurd. Ook de chat geschiedenis zal worden opgeslagen.  
             Alleen ik, Erik van Egmond, kan bij deze gegevens.
             
             Bedankt voor je begrip!
        ''')

    if st.checkbox("Akkoord", value=('akkoord' in st.session_state) and st.session_state.akkoord):
        if st.button('👍 Kom gezellig binnen'):
            st.session_state.akkoord = True
            st.rerun()
    else:
        if st.button('👋 Doei!'):
            st.session_state.akkoord = False
            del st.session_state.userinfo
            del st.session_state.messages
            del st.session_state.token
            del st.session_state.chat_id
            st.rerun()


@st.dialog("feedback")
def feedback():
    with st.form(key='feedback_form'):
        category = st.selectbox(
            "Waar heb je feedback over", ("Kwaliteit antwoorden", "Technische problemen", "Anders"),
            index=None,
            placeholder="Kies een optie"

        )
        text = st.text_area(label='Feedback', height=50)
        if st.form_submit_button(label='Submit'):
            with open(os.path.join('feedback', f'{uuid.uuid4()}.json'), 'w', encoding='utf-8') as f:
                json.dump({
                    "category": category,
                    "text": text,
                    "context": str(st.session_state.chat_id)
                }, f, indent=4)
            st.rerun()


@st.dialog("Vacature")
def vacature():
    vacature_text = st.text_area('Kopieër de vacature tekst hieronder', height=250)
    if st.button("📄 Klaar!"):
        new_conversation(
            start_prompt=Prompts.system_prompt_start_vacature.format(
                name=st.session_state.userinfo['given_name'],
                cv=read_cv(),
                cv_context=vacature_check(vacature_text),
                vacature_text=vacature_text
            )
        )
        save_conversation()
        st.session_state['show_conversation_starters'] = False
        st.rerun()


def new_conversation(start_prompt=None):
    cv = read_cv()
    open_ai_client = OpenAI()
    if start_prompt is None:
        start_prompt = Prompts.system_prompt_start
    st.session_state.chat_id = uuid.uuid4()
    st.session_state["messages"] = [
        {"role": "system",
         "content": start_prompt.format(name=st.session_state.userinfo['given_name'], cv=cv)
         },
    ]
    response = open_ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=st.session_state.messages
    )
    msg = response.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": msg, 'avatar': AVATAR_IMAGE,
                                      'datetime': datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')})
    st.session_state['show_conversation_starters'] = True


def chat_bot(debug=False):
    open_ai_client = OpenAI()
    if "messages" not in st.session_state:
        new_conversation()
    for msg in st.session_state.messages:
        if msg['role'] != 'system' or debug:
            st.chat_message(msg["role"], avatar=msg.get("avatar", "🤖")).write(msg["content"])
    if prompt := st.chat_input('Type hier je antwoord'):
        st.session_state['show_conversation_starters'] = False
        st.session_state.messages.append(
            {"role": "user",
             "content": prompt,
             'avatar': st.session_state['userinfo']['picture'],
             'datetime': datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')
             })
        st.chat_message("user", avatar=st.session_state['userinfo']['picture']).write(prompt)

        retrieved_information = extra_informatie(prompt)
        if retrieved_information:
            st.session_state.messages.append({"role": "system",
                                              "content": retrieved_information,
                                              'avatar': "🤖",
                                      'datetime': datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')})
            if debug:
                st.chat_message('system', avatar="🤖").write(retrieved_information)

        with st.spinner():
            response = open_ai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=st.session_state.messages
            )
            msg = response.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": msg, 'avatar': AVATAR_IMAGE,
                                      'datetime': datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')})

            st.chat_message("assistant", avatar=AVATAR_IMAGE).write(msg)

        save_conversation()


    if st.session_state.show_conversation_starters:
        conversation_starters()


def conversation_starters():
    with st.container(border=True):
        st.write("Kies 1 van de opties, of begin gewoon met het gesprek.")
        col_vacature, col_ikben = st.columns(2)
        with col_vacature:
            if st.button("Ik heb een vacature", use_container_width=True):
                vacature()
        with col_ikben:
            ikben = st.selectbox(
                "Ik ben",
                ("een niet-technisch", "je oma", 'een kind van 5'),
                label_visibility="collapsed",
                placeholder="Ik ben...",
                index=None
            )
            if ikben == "een niet-technisch":
                new_conversation(start_prompt=Prompts.system_prompt_start_manager)
            elif ikben == "je oma":
                new_conversation(start_prompt=Prompts.system_prompt_start_oma)
            elif ikben == 'een kind van 5':
                new_conversation(start_prompt=Prompts.system_prompt_start_kind)
            if ikben:
                st.session_state['show_conversation_starters'] = False
                st.rerun()
