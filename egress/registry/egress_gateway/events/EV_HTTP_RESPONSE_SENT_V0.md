# EV_HTTP_RESPONSE_SENT_V0

## Header

- **Artifact Code:** EV_HTTP_RESPONSE_SENT_V0
- **Artifact Kind:** event
- **Governed By:** CONSTITUTION_EVENT_V0
- **Version:** v0
- **Status:** draft
- **Supersedes:** NONE
- **Dependencies:** NONE

---

## 1. Fact

An HTTP response has been sent to the client after egress mapping.

## 2. Schema

| Field | Type | Required | Format |
|-------|------|----------|--------|
| http_status | integer | yes | |
| result_status | string | yes | |
| trace_id | string | yes | |
| timestamp | string | yes | date-time |

---

## Machine

```yaml
ev_code: EV_HTTP_RESPONSE_SENT_V0
version: v0
governed_by: fb.constitution::CONSTITUTION_EVENT_V0

core:
  summary: HTTP response sent to client
  description: Emitted after egress mapping produces final HTTP response

  schema:
    http_status:
      type: integer
      required: true
    result_status:
      type: string
      required: true
    trace_id:
      type: string
      required: true
    timestamp:
      type: string
      format: date-time
      required: true
```
