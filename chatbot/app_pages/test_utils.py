import os
import streamlit as st
from stqdm import stqdm
from utils import vacature_check, extra_informatie, werkgever_uit_prompt
import weaviate
from weaviate.classes.query import MetadataQuery
import json

from google.cloud import firestore

# Authenticate to Firestore with the JSON account key.
db = firestore.Client.from_service_account_json("../firestore_key.json")

tab_vacature, tab_weaviate, tab_extra_info, tab_werkgevers, tab_firestore = st.tabs(
    ["Vacatures", "Weaviate", "Extra informatie", 'Werkgevers', 'Firestore']
)
with tab_vacature:
    st.header("Vacature check")

    vacature_text = st.text_area('Kopieër de vacature tekst hieronder', height=250)
    if vacature_text:
        st.write(vacature_check(vacature_text=vacature_text, debug=True))

with tab_weaviate:
    st.header("Weaviate")

    weaviate_query = st.text_input(label='Weaviate text query')
    hybrid = st.toggle("Hybrid search")
    if weaviate_query:
        with weaviate.connect_to_local() as client:
            cv_collection = client.collections.get("CV")
            if hybrid:
                response = cv_collection.query.hybrid(
                    query=weaviate_query,
                    query_properties=['chunk'],
                    limit=10,
                    return_metadata=MetadataQuery(score=True, explain_score=True),
                )
            else:
                response = cv_collection.query.near_text(
                    query=weaviate_query,
                    limit=10,
                    return_metadata=MetadataQuery(distance=True),
                    distance=.2
                )

        for obj in response.objects:
            st.write(obj.metadata.distance or obj.metadata.score, obj.properties['bedrijf'],
                     obj.properties['chunking_strategy'])
            st.text(obj.properties['chunk'])

with tab_extra_info:
    st.header("Extra informatie")
    prompt = st.text_input("Prompt", key="PromptExtraInfo")
    if prompt.strip():
        st.write(extra_informatie(prompt))

with tab_werkgevers:
    st.header("Werkgevers")
    prompt = st.text_input("Prompt", key='PromptWerkgevers')
    if prompt.strip():
        st.write(werkgever_uit_prompt(prompt))

with tab_firestore:
    if st.button("Load Conversations to Firestore"):
        for root, _, files in os.walk('conversations'):
            for filename in stqdm(files):
                with open(os.path.join(root, filename), 'r', encoding='utf-8') as f:
                    chat_data = json.load(f)
                    doc_ref = db.collection("chats").document(chat_data['chat_id'])
                    doc_ref.set(chat_data)

    if st.button("Load Feedback to Firestore"):
        for root, _, files in os.walk('feedback'):
            for filename in stqdm(files):
                with open(os.path.join(root, filename), 'r', encoding='utf-8') as f:
                    chat_data = json.load(f)
                    doc_ref = db.collection("feedback").document(filename.rpartition('.')[0])
                    doc_ref.set(chat_data)
