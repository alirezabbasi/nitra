# EPIC-28: Retrieval Context and AI Audit Trail

## Scope
- Persist AI retrieval evidence and governance audit events.
- Close HLD Section 6 gaps for `retrieved_context` and `audit_event`.

## Deliverables
- Schema and contracts for retrieval context payloads and policy audit events.
- LLM interaction guardrails with traceable context references.
- Incident and compliance views for hallucination/policy-violation analysis.

## Acceptance
- AI-assisted decisions are auditable end-to-end with retained retrieval evidence.

## Commit Slices
1. `feat(ai): add retrieved_context and audit_event persistence`
2. `feat(ai): enforce policy guardrail event logging`
3. `test(ai): add audit and retrieval evidence integrity tests`
