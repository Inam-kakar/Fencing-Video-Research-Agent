# Architecture Decision Records

This directory stores Architecture Decision Records, abbreviated as ADRs.

Create an ADR when a decision affects:

- Architecture boundaries
- Database schema strategy
- External services
- Public interfaces
- Dependency selection
- Performance strategy
- Security
- Data compatibility
- Deployment strategy

## Naming convention

```text
0001-short-decision-title.md
0002-next-decision-title.md
```

## ADR template

Copy the following template into a new file whenever an important architecture decision is made.

```markdown
# ADR-NNNN: Decision title

## Status

Proposed | Accepted | Superseded | Rejected

## Context

Describe the problem, constraints, and relevant existing behavior.

## Decision

Describe the selected approach precisely.

## Alternatives considered

Describe realistic alternatives.

## Reasons for rejection

Explain why each alternative was not selected.

## Consequences

Describe positive and negative consequences.

## Performance impact

Describe runtime, memory, database, API, or operational effects.

## Security impact

Describe security, privacy, credential, and data-access effects.

## Migration and compatibility

Describe compatibility risks and required migration work.

## Reversibility

Explain how the decision could be changed or rolled back.
```