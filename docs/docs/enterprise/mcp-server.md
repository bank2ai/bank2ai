---
title: Enterprise MCP server
sidebar_position: 2
description: A production-grade Bank2AI MCP server for banks, with hardening, observability, and SLAs.
---

# Enterprise MCP server

Bancony's enterprise MCP server is a production-grade implementation of the [Bank2AI specification](/docs/specification/overview), targeted at banks that need more than a reference implementation can provide.

## What it adds over the open-source library

- **Hardening.** Input validation, rate limits, and structured rejection of out-of-policy calls (e.g. transfers above configured thresholds without secondary confirmation).
- **Observability.** First-class tracing and metrics covering every Bank2AI tool call — latency, error rate, top failing inputs — exportable to standard OpenTelemetry backends.
- **Auth integration.** Pre-built adapters for the most common bank identity providers; SSO; per-customer authorization scopes.
- **Compliance posture.** Audit logging tailored for financial services; role-based access controls; deployment patterns reviewed for common regulatory frameworks.
- **Operational support.** SLAs, escalation paths, security advisories, and a documented upgrade path tracking the open spec.

## How it relates to `bank2ai`

The enterprise server is **fully compliant with the open spec** — drift tests pass, schemas are unchanged. Skills built against the open standard work against the enterprise server unmodified. Banks moving from the open library to the enterprise server keep their handler interfaces; only the surrounding plumbing changes.

## When to consider it

| You are likely to want this if… | You probably don't need it if… |
| --- | --- |
| You're a regulated bank deploying Bank2AI in production. | You're prototyping or running an internal pilot. |
| You need SLAs and a named escalation path. | You're comfortable maintaining your own ops. |
| You need pre-built auth adapters and audit logging. | You already have those primitives in your stack. |

[Get in touch](./contact) to discuss a deployment.
