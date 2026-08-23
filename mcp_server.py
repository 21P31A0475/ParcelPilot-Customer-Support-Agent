from fastmcp import FastMCP
from data_tools import get_account,get_order,get_ticket,find_repeated_issues
from document_tools import search_documents
from action_tools import prepare_escalation,prepare_ticket_update,prepare_follow_up

mcp=FastMCP('ParcelPilot Support Tools')

@mcp.tool()
def account_lookup(account_id:str='',customer_name:str=''):
    """Look up ParcelPilot account information."""
    return get_account(account_id or None,customer_name or None)

@mcp.tool()
def order_lookup(order_id:str='',account_id:str=''):
    """Look up a ParcelPilot order or shipment."""
    return get_order(order_id or None,account_id or None)

@mcp.tool()
def ticket_lookup(ticket_id:str='',account_id:str=''):
    """Look up a ParcelPilot support ticket."""
    return get_ticket(ticket_id or None,account_id or None)

@mcp.tool()
def document_search(query:str,customer:str=''):
    """Search the supplied ParcelPilot PDFs."""
    return search_documents(query,customer or '')

@mcp.tool()
def proactive_issue_detection():
    """Find repeated issue patterns across the supplied tickets."""
    return find_repeated_issues()

@mcp.tool()
def prepare_escalation_action(ticket_id:str,reason:str,priority:str='P2'):
    """Prepare an escalation. Confirmation is required before execution."""
    return prepare_escalation(ticket_id,reason,priority)

@mcp.tool()
def prepare_ticket_update_action(ticket_id:str,note:str,status:str=''):
    """Prepare a ticket update. Confirmation is required before execution."""
    return prepare_ticket_update(ticket_id,note,status)

@mcp.tool()
def prepare_follow_up_action(ticket_id:str,task:str,due_date:str='next business day'):
    """Prepare a follow-up task. Confirmation is required before execution."""
    return prepare_follow_up(ticket_id,task,due_date)

if __name__=='__main__':
    mcp.run(transport='streamable-http',host='0.0.0.0',port=8000)
