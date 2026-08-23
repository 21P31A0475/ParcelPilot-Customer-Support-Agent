import json
import os
from datetime import datetime

ACTION_FILE=os.path.join(os.path.dirname(__file__),'action_log.json')

def prepare_escalation(ticket_id,reason,priority='P2'):
    return {'action_type':'create_escalation','ticket_id':ticket_id,'reason':reason,'priority':priority,'status':'AWAITING_CONFIRMATION'}

def prepare_ticket_update(ticket_id,note,status=''):
    return {'action_type':'update_ticket','ticket_id':ticket_id,'note':note,'status':status or 'UNCHANGED','status_flag':'AWAITING_CONFIRMATION','confirmation_required':True}

def prepare_follow_up(ticket_id,task,due_date='next business day'):
    return {'action_type':'create_follow_up','ticket_id':ticket_id,'task':task,'due_date':due_date,'status':'AWAITING_CONFIRMATION'}

def execute_action(action):
    if action.get('status')!='APPROVED':
        return {'success':False,'message':'Action was not approved.'}
    action['executed_at']=datetime.now().isoformat()
    action['result']='SIMULATED_ACTION_CREATED'
    old=[]
    if os.path.exists(ACTION_FILE):
        try:
            old=json.load(open(ACTION_FILE,'r',encoding='utf-8'))
        except Exception:
            old=[]
    old.append(action)
    json.dump(old,open(ACTION_FILE,'w',encoding='utf-8'),indent=2)
    return {'success':True,'action':action}
