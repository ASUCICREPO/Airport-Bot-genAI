#import InvokeAgent as agenthelper
import streamlit as st
import json
import string
import random
import time
from log_setup import logger
import os
import requests

Airport_agent = os.environ['PAGE_TITLE']
website = os.environ['WEBSITE']
api = os.environ['API']

if website.startswith('https://') or website.startswith('http://'):
    linksite = website
else:
    linksite = 'http://' + website

# Streamlit page configuration
st.set_page_config(page_title=Airport_agent, page_icon="💬", layout="wide")
    
def generate_random_string(length):
    logger.info('Creating Random ID ..')
    letters = string.ascii_letters
    ID = ''.join(random.choice(letters) for _ in range(length))
    logger.debug(f'ID: {ID}')
    return ID


if "history" not in st.session_state:
    st.session_state.history = []
    logger.info('New History Created !!')

#Title and Disclaimer
st.markdown(f"<h1 style='font-family: sans-serif;'>{Airport_agent}</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color: #FF0000;'>This website is only for demo purposes. Visit the official website at <a href={linksite}>{website}</a></p>", unsafe_allow_html=True)


st.sidebar.title("**FAQs:**")
st.sidebar.markdown("**1. What are the options for me to reach my terminal from parking ?**")
st.sidebar.markdown("**2. What are the available options for transportation between each terminals ?**")
st.sidebar.markdown("**3. How much full is parking at terminal 4 ?**")
st.sidebar.markdown("**4. I am just done with the security, How much is the walk time to gate B45 at terminal 4 ?**")
st.sidebar.markdown("**5. How much is the wait in regular security line at terminal 7 ?**")
st.sidebar.markdown("**6. How much is the taxi wait time at terminal 1 ?**")

#Displaying all the previous messages
for message in st.session_state.history:
    with st.chat_message("user"):
        st.markdown(message["question"])
    with st.chat_message("assistant"):
        st.markdown(message["answer"])
    
#random ID generator
st.session_state.session_id = generate_random_string(10)

# Display a text box for input
if prompt := st.chat_input("Ex.- What's the parking availability at terminal 8 ?"):

    logger.debug(f'Prompt: {prompt}')
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        event = {
            "sessionId": st.session_state.session_id,
            "prompt": prompt
        }

        #Hitting API
        response = requests.post(api, json=event)
        the_response = response.json()['body']
        the_response = json.loads(the_response)['response']
        logger.debug(f'response: {the_response}')

        #Adding a small delay while displaying to make it like streaming
        for chunk in the_response.split():
            full_response += chunk + " "
            time.sleep(0.1)
            # Add a blinking cursor to simulate typing
            message_placeholder.markdown(full_response + "▌")

        message_placeholder.markdown(full_response)

    #Appending current response in current streamlit session history
    st.session_state.history.append({"question": prompt, "answer": the_response})