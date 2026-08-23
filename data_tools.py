import os
import pandas as pd
from config import DATA_FOLDER

EXCEL_FILE = os.path.join(DATA_FOLDER,'ParcelPilot_Assessment_Data.xlsx')

def load_data():
    accounts = pd.read_excel(EXCEL_FILE,sheet_name='accounts')
    orders = pd.read_excel(EXCEL_FILE,sheet_name='orders')
    tickets = pd.read_excel(EXCEL_FILE,sheet_name='tickets')
    return accounts,orders,tickets

def get_account(account_id=None,customer_name=None):
    accounts,_,_ = load_data()
    result = accounts
    if account_id:
        result = result[result['account_id'].astype(str).str.upper()==str(account_id).upper()]
    if customer_name:
        result = result[result['account_name'].astype(str).str.lower().str.contains(str(customer_name).lower(),na=False)]
    if result.empty:
        return {'found':False,'message':'Account was not found.'}
    return {'found':True,'records':result.fillna('').to_dict('records')}

def get_order(order_id=None,account_id=None):
    _,orders,_ = load_data()
    result = orders
    if order_id:
        result = result[result['order_id'].astype(str).str.upper()==str(order_id).upper()]
    if account_id:
        result = result[result['account_id'].astype(str).str.upper()==str(account_id).upper()]
    if result.empty:
        return {'found':False,'message':'Order was not found.'}
    return {'found':True,'records':result.fillna('').to_dict('records')}

def get_ticket(ticket_id=None,account_id=None):
    _,_,tickets = load_data()
    result = tickets
    if ticket_id:
        result = result[result['ticket_id'].astype(str).str.upper()==str(ticket_id).upper()]
    if account_id:
        result = result[result['account_id'].astype(str).str.upper()==str(account_id).upper()]
    if result.empty:
        return {'found':False,'message':'Ticket was not found.'}
    return {'found':True,'records':result.fillna('').to_dict('records')}

def find_repeated_issues():
    _,_,tickets = load_data()
    groups={}

    for _,row in tickets.fillna('').iterrows():
        text=' '.join(
            str(row.get(c,''))
            for c in ['subject','description','historical_resolution']
        ).lower()

        if 'bulk upload' in text or 'csv' in text:
            issue='bulk upload failure'
        elif 'http 500' in text or 'shipment creation' in text:
            issue='shipment creation issue'
        elif 'delay' in text or 'late' in text or 'webhook' in text:
            issue='shipment status or pickup delay'
        else:
            continue

        groups.setdefault(issue,[]).append({
            'account_id':row.get('account_id',''),
            'ticket_id':row.get('ticket_id','')
        })

    result=[]

    for issue,tickets_for_issue in groups.items():
        customers=set(x['account_id'] for x in tickets_for_issue)

        if len(tickets_for_issue) >= 2:
            result.append({
                'issue': issue,
                'tickets': tickets_for_issue,
                'customer_count': len(customers),
                'ticket_count': len(tickets_for_issue)
            })

    return result
