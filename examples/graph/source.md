# Engineering graph example

This file illustrates the **authoring** source. `eng-docs graph` does not parse
this Markdown; Sphinx-Needs owns the engineering objects and exports
`needs.json`.

```{goal} Provide a service
:id: GOAL-1

The example system should provide one reusable service capability.
```

```{req} Service response
:id: REQ-1
:derived_from: GOAL-1

The system shall provide a response through the service boundary.
```

```{arch} Service
:id: Service
:satisfies: REQ-1

The Service owns the implementation responsibility for REQ-1.
```

```{vc} Service response verification
:id: VC-1
:verifies: REQ-1

Exercise the Service and verify a valid response.
```
