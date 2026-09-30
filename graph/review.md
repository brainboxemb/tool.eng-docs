# Engineering graph review

Source revision: 86deb06231a8d4fce64ffe877f82edaa7ba803bb
Source graph: sphinx-needs tool.eng-docs graph example 1.0

Engineering objects and outgoing relations come from the Sphinx-Needs export.
Incoming relations below are derived from those outgoing relations.
Diagram identities are references to existing engineering objects.

## Overview

| Object | Type | Authored outgoing | Generated incoming | Diagram refs |
| --- | --- | ---: | ---: | ---: |
| [GOAL-1](#goal-1) | goal | 0 | 1 | 0 |
| [REQ-1](#req-1) | req | 1 | 2 | 0 |
| [Service](#service) | arch | 1 | 0 | 1 |
| [VC-1](#vc-1) | vc | 1 | 0 | 0 |
| [Worker](#worker) | arch | 0 | 0 | 1 |

## GOAL-1

Type: goal (Goal)  
Title: Provide a service  
Source: source.md:5

### Authored outgoing

_None._

### Generated incoming

- derived_from <- **REQ-1**

### Diagram references

_None._

## REQ-1

Type: req (Requirement)  
Title: Service response  
Source: source.md:12

### Authored outgoing

- derived_from -> **GOAL-1**

### Generated incoming

- satisfies <- **Service**
- verifies <- **VC-1**

### Diagram references

_None._

## Service

Type: arch (Architecture Element)  
Title: Service  
Source: source.md:20

### Authored outgoing

- satisfies -> **REQ-1**

### Generated incoming

_None._

### Diagram references

- examples/graph/diagrams/system.yaml:12 (diagram=graph-example, node=service)

## VC-1

Type: vc (Verification Case)  
Title: Service response verification  
Source: source.md:35

### Authored outgoing

- verifies -> **REQ-1**

### Generated incoming

_None._

### Diagram references

_None._

## Worker

Type: arch (Architecture Element)  
Title: Worker  
Source: source.md:28

### Authored outgoing

_None._

### Generated incoming

_None._

### Diagram references

- examples/graph/diagrams/system.yaml:16 (diagram=graph-example, node=service)
