import json
import random
from collections import defaultdict
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional

import streamlit as st
import weaviate
from pydantic import BaseModel
from weaviate.collections.classes.filters import Filter
from weaviate.collections.classes.grpc import MetadataQuery, GroupBy
from weaviate.classes.aggregate import GroupByAggregate
from openai import OpenAI
from google.cloud import firestore

firestore_db = firestore.Client.from_service_account_json("../firestore_key.json")
AVATAR_IMAGE = './assets/erik_bot.jpg'


@dataclass(frozen=True)
class Prompts:
    system_prompt_start = """
Jij bent Erik en je hebt nu je eerste gesprek met {name}, een zakelijke relatie die graag meer van je wilt weten.
Houd je antwoorden relatief kort, je gespreksparter kan altijd doorvragen, maar vraag daar niet om. 
Als er gevraagd word om ervaring baseer je antwoord dan alleen op de geleverde context.
Als er gevraagd word om beschikbaarheid geef je aan dat je die vraag niet kan beantwoorden omdat je een chatbot bent.
Beantwoord alle vragen die niet over beschikbaarheid gaan alsof je Erik bent, en niet een chatbot.
Begroet je gesprekspartner en noem diens naam ({name}), stel jezelf vervolgens voor. Dit is je CV: {cv}.
    """
    system_prompt_start_oma = """
Jij bent Erik en je hebt nu een gesprek met je oma ({name}) die graag meer over je werk wilt weten. 
Zorg ervoor dat je antwoorden goed te begrijpen zijn voor mensen die heel weinig verstand hebben van computers enzo. Vermijd alle jargon. 
Gebruik u/uw bij het aanspreken van oma.
Houd je antwoorden relatief kort, je gespreksparter kan altijd doorvragen, maar vraag daar niet om. Gebruik bij het beantwoorden metaforen die aansluiten bij mensen van 80 jaar of ouder.
Als er gevraagd word om ervaring baseer je antwoord dan alleen op de geleverde context.
Als er gevraagd word om beschikbaarheid geef je aan dat je die vraag niet kan beantwoorden omdat je een chatbot bent.
Beantwoord alle vragen die niet over beschikbaarheid gaan alsof je Erik bent, en niet een chatbot.
Stel jezelf voor in het begin van het gesprek. Dit is je CV: {cv}.
    """
    system_prompt_start_kind = """
Je bent Erik en je hebt nu je eerste gesprek met {name}, een vijfjarig kind dat nieuwsgierig is en meer over je wil weten.
Geef korte en simpele antwoorden, zodat {name} het goed kan begrijpen. Laat {name} zelf doorvragen als hij of zij meer wil weten.
Gebruik bij het beantwoorden metaforen die aansluiten bij kinderen van 5.
Als {name} vraagt naar wat je hebt gedaan, vertel dan alleen wat er in je informatie staat.
Als {name} vraagt of je ergens tijd voor hebt, zeg dat je dat niet weet omdat je een chatbot bent.
Beantwoord alle andere vragen alsof jij echt Erik bent en geen chatbot.
Begin het gesprek door {name} vrolijk te begroeten en je voor te stellen. Dit is je CV: {cv}.
    """
    system_prompt_start_niet_technisch = """
Je bent Erik en je hebt nu je eerste gesprek met {name}, een niet-technische zakelijke relatie die graag meer over je wil weten.
Geef duidelijke en beknopte antwoorden, zodat {name} het makkelijk kan volgen. {name} kan altijd doorvragen, maar vraag daar zelf niet om.
Als er gevraagd wordt naar je ervaring, baseer je antwoord dan alleen op de informatie die je hebt gekregen.
Als er gevraagd wordt naar je beschikbaarheid, geef aan dat je die vraag niet kunt beantwoorden omdat je een chatbot bent.
Beantwoord alle andere vragen alsof je Erik bent en geen chatbot.
Begin het gesprek door {name} te begroeten en jezelf voor te stellen. Dit is je CV: {cv}.
    """

    system_prompt_start_vacature = """
Jij bent Erik en je hebt nu je eerste gesprek met {name}, een zakelijke relatie die je een vacature voorlegt. 
Bestudeer de vacature en vertel wat je er van vind. Je bent op zoek naar werk in het data domein waarbij ook geprogrameerd word. Als het werk niet bij je achtergrond of interesse past geeft dit duidelijk aan. 
Wanneer er dingen gevraagd worden waar je geen ervaring mee hebt benoem dit ook, maar vertel ook met welke vergelijkbare dingen je wel ervaring hebt. Benoem deze punten in een bullet-list.
Houd je antwoorden relatief kort, je gespreksparter kan altijd doorvragen, maar vraag daar niet om. 
Als er gevraagd word om ervaring baseer je antwoord dan alleen op de geleverde context.
Als er gevraagd word om beschikbaarheid geef je aan dat je die vraag niet kan beantwoorden omdat je een chatbot bent.
Beantwoord alle vragen die niet over beschikbaarheid gaan alsof je Erik bent, en niet een chatbot.
Stel jezelf voor in het begin van het gesprek. Dit is je CV: {cv}.

Extra informatie op basis van de vacature:
{cv_context}

Vacature:
{vacature_text}

Structureer je antwoord als volgt:
    
    Stel je zelf voor
    Eerste indruk van de vacature
    
    ### Positieve punten:
    - [punt 1]
    - [punt 2]
    - etc
    
    ### Aandachtspunten:
    - [punt 1]
    - [punt 2]
    - etc
    
    concluderend over de vacature
        """
    extra_context = "gebruik, indien van toepassing, ook deze informatie voor volgende antwoorden:  \n{extra_context}"
    extract_werkgever = """
Gegeven de volgende werkgevers, over welke werkgever vraagt de gebruiker? Het kan zijn dat de gebruiker een afkorting van de werkgever gebruikt, probeer ook hiervoor te vinden welke bedoeld wordt.
{werkgevers}
Antwoord alleen met de werkgever, als geen werkgever genoemd wordt antwoord 'None'.
    """


def vacature_check(vacature_text, debug=False):
    open_ai_client = OpenAI()
    with st.status("Vacature aan het besturderen...") as status, weaviate.connect_to_local() as weaviate_client:
        cv_collection = weaviate_client.collections.get("CV")
        status.write("Eisen uit vacature halen...")
        requirements = parse_vacature(open_ai_client, vacature_text)
        requirements = (
                requirements.programming_languages +
                requirements.cloud_platforms +
                requirements.methodologies +
                requirements.operating_systems +
                requirements.databases +
                requirements.tools_libraries +
                requirements.education
        )
        fulfillments = defaultdict(set)
        zinnen = [
            "Controleren of {skill} aanwezig is in het cv.",
            "Het cv doorzoeken op {skill}.",
            "Nakijken of {skill} vermeld wordt in het cv.",
            "Zoek naar {skill} in het cv.",
            "Beoordeel of {skill} in het cv voorkomt.",
            "Het cv analyseren op de aanwezigheid van {skill}.",
            "{skill} opsporen in het cv.",
            "Controleren op {skill} in het cv.",
            "Identificeer {skill} in het cv.",
            "Het cv doorlezen voor informatie over {skill}."
        ]
        for requirement in requirements:
            status.write(random.choice(zinnen).format(skill=requirement))
            response = cv_collection.query.hybrid(
                query=requirement,
                query_properties=['chunk'],
                limit=3,
                return_metadata=MetadataQuery(score=True, explain_score=True),
            )
            for o in response.objects:
                if debug:
                    status.write(o.metadata.score)
                    status.write(o.properties['bedrijf'])
                    status.write(o.properties['chunk'])

                fulfillments[o.properties['bedrijf']].add(o.properties['chunk'])
            if debug:
                status.divider()

        cv_context = []
        for bedrijf, text in fulfillments.items():
            cv_context.append(f'Context bij {bedrijf}: {"\n,".join(text)}')
        cv_context = '\n\n'.join(cv_context)
    return cv_context


def parse_vacature(client, vacature_text):
    class CloudPlatform(str, Enum):
        azure = "Azure"
        gcp = "GCP"
        aws = "AWS"

    class VacatureData(BaseModel):
        company: Optional[str]
        soft_skills: list[str]
        hard_skills: list[str]
        programming_languages: list[str]
        cloud_platforms: list[CloudPlatform]
        methodologies: list[str]
        operating_systems: list[str]
        databases: list[str]
        tools_libraries: list[str]
        education: list[str]

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system",
             "content": "Extract skills from job listing. Hardskills do not contain specific tools"},
            {"role": "user", "content": vacature_text},
        ],
        response_format=VacatureData,
    )

    return completion.choices[0].message.parsed


@st.cache_data
def read_cv():
    with open('assets/cv_summary.txt', 'r', encoding='utf-8') as f:
        cv = f.read()
    return cv

@st.cache_data
def werkgevers_uit_cv():
    with weaviate.connect_to_local() as client:
        collection = client.collections.get("CV")
        werkgevers = ", ".join(
            [
                x.grouped_by.value
                for x in collection.aggregate.over_all(
                    total_count=True,
                    group_by=GroupByAggregate(prop="bedrijf")
                ).groups
            ]
        )
    return werkgevers

def werkgever_uit_prompt(prompt):
    client = OpenAI()
    werkgevers = werkgevers_uit_cv()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": Prompts.extract_werkgever.format(werkgevers=werkgevers)},
            {"role": "user", "content": prompt}
        ]
    )
    if response.choices[0].message.content != "None":
        return response.choices[0].message.content


def extra_informatie(prompt):
    with weaviate.connect_to_local() as weaviate_client:
        cv_collection = weaviate_client.collections.get("CV")
        group_by = GroupBy(
            prop="bedrijf",
            objects_per_group=10,
            number_of_groups=10,
        )
        near_text_kwargs = dict(query=prompt,
                                limit=10,
                                return_metadata=MetadataQuery(distance=True),
                                distance=.2,
                                group_by=group_by)

        if werkgever := werkgever_uit_prompt(prompt):
            near_text_kwargs['filters'] = Filter.by_property('bedrijf').equal(werkgever)

        response = cv_collection.query.near_text(**near_text_kwargs)
        retrieved_information = []
        for bedrijf, bedrijf_chunks in response.groups.items():
            retrieved_information.append(f"\n\nRelevantie informatie bij {bedrijf}:  ")
            for chunk in bedrijf_chunks.objects:
                retrieved_information.append(f"\n* {chunk.properties['chunk']}  ")

        retrieved_information = " ".join(retrieved_information).strip()
        if retrieved_information:
            return Prompts.extra_context.format(extra_context=retrieved_information)


def save_conversation():
    chat_data = {'chat_id': str(st.session_state.chat_id),
     'user_info': st.session_state.userinfo,
     'conversation': st.session_state.messages}

    doc_ref = firestore_db.collection("chats").document(chat_data['chat_id'])
    doc_ref.set(chat_data)

