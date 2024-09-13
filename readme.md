# Job Interview Bot

Een chat bot waarmee een gesprek met 'Erik' gevoerd kan worden over zijn werkervaring en opleiding. Voor de chat interface wordt gebruik gemaakt van Streamlit, de chat responses worden gegenereerd door OpenAI. Via de vector database Weaviate wordt informatie uit mijn cv gehaald voor Retrieval Augumented Generation (RAG) en meegegeven in de prompts.

Probeer het zelf op https://erik.chat

# Hoe gebruik je het?

## 1. dotenv
```
AUTHORIZE_URL=https://www.linkedin.com/oauth/v2/authorization
TOKEN_URL=https://www.linkedin.com/oauth/v2/accessToken
REFRESH_TOKEN_URL=https://www.linkedin.com/oauth/v2/accessToken
REVOKE_TOKEN_URL=https://www.linkedin.com/oauth/v2/accessToken
CLIENT_ID=<YOUR LINKEDIN CLIENT ID>
CLIENT_SECRET=<YOUR LINKEDIN CLIENT SECRET>
REDIRECT_URI=http://localhost:8501/
SCOPE=openid profile email
APP_ENV=dev
ADMIN_MAIL=<YOUR EMAIL ADRESS>
```

## 2. Run docker 
Run de docker in de root directory, dit zet Weaviate aan.  
`docker compose up`

## 3. Run Streamlit
Run streamlit vanuit de chatbot directory.  
`streamlit run chatbot.py`