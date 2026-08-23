# Product Note

**Product:** ParcelPilot AI Support Agent

**User:** authorised ParcelPilot support/operations staff.

**Business problem:** support staff need to combine current policy, SOPs, product documentation, customer agreements and structured account/order/ticket records to solve customer issues.

**Solution:** the agent uses MCP tools to retrieve the relevant information and LangGraph to loop between the LLM and tools. It respects source precedence and refuses to invent unsupported facts.

**Actions:** escalation, ticket update and follow-up are prepared first. A human must approve before the simulated action is written to the action log.

**Guardrails:** current documents only for current decisions; signed customer agreement overrides default policy; historical tickets are context only; conflicts trigger verification; actions are never claimed complete before approval.
