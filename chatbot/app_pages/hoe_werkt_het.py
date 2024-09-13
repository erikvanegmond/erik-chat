import streamlit as st
from openai import OpenAI

from utils import Prompts

st.header("Hoe werkt het")

with st.expander("Herschijf de uitleg"):
    ikben = st.selectbox(
        "Ik ben",
        ("best technisch", "een niet-technisch", "je oma", 'een kind van 5'),
        placeholder="Ik ben...",
    )

if ikben == "een niet-technisch":
    system_prompt = """
Herschrijf de volgende tekst zodat deze goed te begrijpen zijn voor mensen zonder technische achtergrond. Bij het gebruik
van jargon, geef ook een uitleg voor de leek.
    """
    st.info('Deze uitleg is herschreven door OpenAI voor mensen zonder technische achtergrond.')
elif ikben == "je oma":
    system_prompt = """
Herschrijf de volgende tekst zodat deze goed te begrijpen zijn voor mensen die heel weinig verstand hebben van 
computers enzo. Vermijd alle jargon. Gebruik metaforen die aansluiten bij mensen van 80 jaar of ouder."""
    st.info('Deze uitleg is herschreven door OpenAI voor voor mensen van 80 jaar oud die heel weinig verstand hebben van computers.')

elif ikben == 'een kind van 5':
    system_prompt = """
Herschrijf de volgende tekst zodat deze goed te begrijpen zijn voor kinderen van vijf. Gebruik korte zinnen.
Vermijd alle jargon. Gebruik metaforen die aansluiten bij de verbeelding van kinderen van 5 jaar oud."""
    st.info('Deze uitleg is herschreven door OpenAI voor voor kinderen van 5.')


uitleg = """
De chatbot is ontworpen om open en duidelijk te communiceren, en biedt complexe informatie op een begrijpelijke manier aan.
Het proces is geoptimaliseerd voor het efficiënt ophalen en genereren van informatie.

### Gebruikte Technologieën
- Chat Interface: Streamlit
- Informatie opslag: Weaviate
- Genereren van antwoorde: OpenAI

### Het proces

0. De chatbot ontvangt een start prompt waarin het persona (Erik) wordt omschreven
1. De gebruiker begint een gesprek met de chatbot.
2. De gebruiker typt een vraag of verzoek in de chatinterface.
3. De chatbot gebruikt de vector database Weaviate om relevante informatie uit het CV van Erik te extraheren.
4. De relevante informatie wordt verwerkt in een nieuw prompt voor de chatbot.
4. Met behulp van OpenAI worden antwoorden gegenereerd op basis van de opgehaalde informatie en de vraag van de gebruiker.
5. Het gegenereerde antwoord wordt teruggestuurd naar de gebruiker in de chatinterface.

Na het ontvangen van het antwoord kan de gebruiker besluiten om de chat te beëindigen of door te gaan met het stellen van meer vragen.

### Gebruikte prompts
Prompts zijn een manier om input te geven aan een systeem, meestal om specifieke output of gedrag te genereren. Als je een woord ziet met krulhaakjes er omheen, bijvoorbeeld: {name}, dan wordt op die plek extra informatie toegevoegd in het prompt."""

if ikben != 'best technisch':
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": uitleg}
        ]
    )
    uitleg = response.choices[0].message.content


st.write(uitleg)

for prompt_naam, prompt in [(k,v.strip()) for k, v in Prompts.__dict__.items() if not k.startswith("__") and k != 'extract_werkgever']:
    st.write(f"""#### {prompt_naam.replace('_', ' ').capitalize()}
{prompt}
""")
