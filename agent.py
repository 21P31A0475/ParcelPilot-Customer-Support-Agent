from langchain_core.outputs import chat_result
import asyncio
import json
import os
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt
from typing import TypedDict, Annotated, List
import re
from config import OPENAI_MODEL, ALLOWED_ROLE, ALLOWED_CUSTOMER

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

SERVER={
    'ParcelPilot':{
        'url':os.environ['MCP_SERVER_URL'],
        'transport':'streamable_http',
        'headers':{
            'Authorization':f"Bearer {os.environ['FASTMCP_TOKEN']}"
        }
    }
}

class AgentState(TypedDict):
    messages: Annotated[List, add_messages]
    action: dict
    approved: bool
    customer : str 
    role: str

def System_Prompt():
    return SystemMessage(content='''You are the ParcelPilot internal support agent.

You MUST use the available tools to investigate every factual support question before answering. Do not answer from memory when account, order, ticket, policy, agreement, SOP, or product information is needed.
Tool selection:
- If the user gives a ticket ID such as TKT-504, call ticket_lookup first.
- If the user gives an order ID such as ORD-1001, call order_lookup first.
- If the user asks about a named customer/account, call account_lookup when the account is needed.
- If the question asks about policy, SLA, cancellation, service credit, product behavior, or a customer agreement, call document_search.
- For questions that require both operational data and policy, call the needed data tool and then document_search.

Current decision source priority:
1. Signed customer agreement
2. Current Support Policy
3. Current Product Operations documentation
4. Historical tickets are context only and never policy authority.

The deprecated Support Policy v2 must not be used for current requests.
Preflight evidence may already be provided before you answer.
If preflight evidence contains the requested information, use that evidence directly.
Do not say that a tool failed or that information is unavailable when the evidence already contains the answer.
For customer-specific questions, prefer the signed customer agreement when it is present and active.
For state-changing work, first investigate and prepare the action. Never claim the action was completed before human approval and execution.

You are an internal ParcelPilot support/operations assistant. Do not expose information outside the authorised business context.
The currently authorized customer context is the configured customer. Do not disclose or retrieve another customer's confidential agreement, SLA, cancellation terms, service credits, pricing, or account-specific information.
If the user asks for information belonging to another customer, refuse the request and offer to provide information for the authorized customer instead.''')
    
async def Build_Agent():
    client = MultiServerMCPClient(SERVER)
    tools = await client.get_tools()
    tool_map = {tool.name: tool for tool in tools}

    llm = ChatOpenAI(model=OPENAI_MODEL,api_key=OPENAI_API_KEY)
    llm_with_tools = llm.bind_tools(tools)

    def Call_model(State: AgentState):
        messages = [System_Prompt()] + State['messages']

        result = llm_with_tools.invoke(messages)

        return {'messages': [result]}

    async def First_lookup(State: AgentState):
        """Use a simple trainer-style router to guarantee the first factual lookup.

        The LLM still reasons and can call tools later. This node only makes sure an obvious ticket/order/account/document question has source evidence
        before the first answer."""
        
        if not State['messages']:
            return {'messages': []}

        user_text = State['messages'][-1].content
        text = str(user_text)
        low = text.lower()
        new_messages = []

        ticket_ids = re.findall(r'\bTKT-\d+\b', text, flags=re.I)
        order_ids = re.findall(r'\bORD-\d+\b', text, flags=re.I)

        if ticket_ids and 'ticket_lookup' in tool_map:
            result = await tool_map['ticket_lookup'].ainvoke({'ticket_id': ticket_ids[0], 'account_id': ''})
            new_messages.append(SystemMessage(content='Preflight ticket evidence:\n' + json.dumps(result, default=str)))
            return {'messages': new_messages}

        if order_ids and 'order_lookup' in tool_map:
            result = await tool_map['order_lookup'].ainvoke({'order_id': order_ids[0], 'account_id': ''})
            new_messages.append(SystemMessage(content='Preflight order evidence:\n' + json.dumps(result, default=str)))
            return {'messages': new_messages}

        customer = ''
        if 'northstar' in low:
            customer = 'Northstar Logistics'
        elif 'lumenworks' in low:
            customer = 'LumenWorks'
        elif 'beacon retail' in low:
            customer = 'Beacon Retail'
        elif 'axis labs' in low:
            customer = 'Axis Labs'
               
        if customer and ALLOWED_CUSTOMER:
            if customer.lower() != ALLOWED_CUSTOMER.lower():
                new_messages.append(SystemMessage(content=(
                            f"AUTHORIZATION BLOCK: The user is authorized for "
                            f"{ALLOWED_CUSTOMER} only. The requested customer "
                            f"{customer} is outside the authorized customer context. "
                            f"Do not retrieve, disclose, or summarize that customer's "
                            f"agreement, SLA, pricing, cancellation terms, service "
                            f"credits, or other customer-specific information."
                        )
                    )
                )
                return {'messages': new_messages}

        if customer and 'account_lookup' in tool_map:
            result = await tool_map['account_lookup'].ainvoke({'account_id': '', 'customer_name': customer})
            new_messages.append(SystemMessage(content='Preflight account evidence:\n' + json.dumps(result, default=str)))

        document_words = ['policy', 'sla', 'response target', 'p1', 'p2', 'p3','cancel', 'cancellation', 'fee', 'service credit', 'credit',
            'agreement', 'contract', 'booked', 'picked_up', 'picked up','delivered', 'product', 'known issue', 'bulk upload', 'webhook']
        
        pattern_words = [ 'repeated issue','repeated issues','repeated ticket','repeated tickets','issue pattern','issue patterns',
            'ticket pattern','ticket patterns','recurring issue','recurring issues','common issues','common problems']

        if any(word in low for word in pattern_words) and 'proactive_issue_detection' in tool_map:
            result = await tool_map['proactive_issue_detection'].ainvoke({})

        new_messages.append(SystemMessage(content='Preflight repeated-issue evidence:\n'+ json.dumps(result, default=str)))
        
        if any(word in low for word in document_words) and 'document_search' in tool_map:
            result = await tool_map['document_search'].ainvoke({'query': text, 'customer': customer})
            new_messages.append(SystemMessage(content='Preflight document evidence:\n' + json.dumps(result, default=str)))
        return {'messages': new_messages}

    tool_node = ToolNode(tools)

    def Check_action(State: AgentState):
        action = {}
        for message in reversed(State['messages']):
            if isinstance(message, ToolMessage):
                try:
                    value = json.loads(message.content) if isinstance(message.content, str) else message.content
                    if isinstance(value, dict) and (value.get('status') == 'AWAITING_CONFIRMATION' or value.get('status_flag') == 'AWAITING_CONFIRMATION'):
                        action = value
                        break
                except Exception:
                    pass
        return {'action': action}

    def Human_review(State: AgentState):
        approval = interrupt({'message': 'Approve this action?', 'action': State['action']})
        approved = str(approval).lower() in ['yes', 'y', 'approve', 'approved', 'true']
        return {'approved': approved}

    def Execute_action(State: AgentState):
        from action_tools import execute_action
        action = dict(State['action'])
        if not State['approved']:
            result = {'success': False, 'message': 'Action cancelled. No data was changed.'}
        else:
            action['status'] = 'APPROVED'
            result = execute_action(action)
        return {'messages': [AIMessage(content=json.dumps(result, indent=2))], 'action': {}, 'approved': False}

    def Route_after_tools(State: AgentState):
        if State.get('action'):
            return 'Human_review'
        return 'agent'

    graph = StateGraph(AgentState)
    graph.add_node('First_lookup', First_lookup)
    graph.add_node('agent', Call_model)
    graph.add_node('tools', tool_node)
    graph.add_node('Check_action', Check_action)
    graph.add_node('Human_review', Human_review)
    graph.add_node('Execute_action', Execute_action)

    graph.add_edge(START, 'First_lookup')
    graph.add_edge('First_lookup', 'agent')
    graph.add_conditional_edges('agent', tools_condition)
    graph.add_edge('tools', 'Check_action')
    graph.add_conditional_edges('Check_action', Route_after_tools, {'Human_review': 'Human_review', 'agent': 'agent'})
    graph.add_edge('Human_review', 'Execute_action')
    graph.add_edge('Execute_action', 'agent')

    memory = InMemorySaver()
    chatbot = graph.compile(checkpointer=memory)
    return chatbot

async def main():
    chatbot = await Build_Agent()
    config = {'configurable': {'thread_id': 'user_1'}}
    print('ParcelPilot AI Support Agent. Type exit to stop.')
    while True:
        query = input('You: ')
        if query.lower() == 'exit':
            break
        result = await chatbot.ainvoke(
            {'messages': [HumanMessage(content=query)],'action': {},'approved': False,'role': ALLOWED_ROLE,'customer': ALLOWED_CUSTOMER},config=config)
        print('Assistant:', result['messages'][-1].content)

if __name__ == '__main__':
    asyncio.run(main())
