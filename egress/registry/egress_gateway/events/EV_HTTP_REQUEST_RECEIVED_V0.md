# EV_HTTP_REQUEST_RECEIVED_V0

## Header

- **Artifact Code:** EV_HTTP_REQUEST_RECEIVED_V0
- **Artifact Kind:** event
- **Governed By:** CONSTITUTION_EVENT_V0
- **Version:** v0
- **Status:** draft
- **Supersedes:** NONE
- **Dependencies:** NONE

---

## 1. Fact

An inbound HTTP request has passed structural admission schema validation.

## 2. Schema

| Field | Type | Required | Format |
|-------|------|----------|--------|
| route | string | yes | |
| method | string | yes | |
| ti_code | string | yes | |
| timestamp | string | yes | date-time |

---

## Machine

```yaml
ev_code: EV_HTTP_REQUEST_RECEIVED_V0
version: v0
governed_by: fb.constitution::CONSTITUTION_EVENT_V0

core:
  summary: HTTP request passed structural admission
  description: Emitted when an inbound HTTP request passes admission schema validation

  schema:
    route:
      type: string
      required: true
    method:
      type: string
      required: true
    ti_code:
      type: string
      required: true
    timestamp:
      type: string
      format: date-time
      required: true
```
