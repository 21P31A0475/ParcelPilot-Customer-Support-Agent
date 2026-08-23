import asyncio
import streamlit as st
from langchain_core.messages import HumanMessage
from agent import Build_Agent

st.set_page_config(page_title='ParcelPilot AI Support Agent')
st.title('ParcelPilot AI Support Agent')
st.caption('Internal support investigation')

if 'chatbot' not in st.session_state:
    st.session_state.chatbot=asyncio.run(Build_Agent())
if 'messages' not in st.session_state:
    st.session_state.messages=[]

for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.write(message['content'])

query=st.chat_input('Ask about an account, order, ticket, policy or action...')
if query:
    st.session_state.messages.append({'role':'user','content':query})
    with st.chat_message('user'):
        st.write(query)
    config={'configurable':{'thread_id':'streamlit_user'}}
    try:
        result=asyncio.run(st.session_state.chatbot.ainvoke({'messages':[HumanMessage(content=query)],'action':{},'approved':False,'role':'support'},config=config))
        answer=result['messages'][-1].content
    except Exception as e:
        answer=f'Unable to complete the request safely: {e}'
    st.session_state.messages.append({'role':'assistant','content':answer})
    with st.chat_message('assistant'):
        st.write(answer)
