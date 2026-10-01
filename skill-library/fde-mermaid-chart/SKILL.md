---
name: fde-mermaid-chart
description: Expert in designing and generating standardized Mermaid diagrams for Readme documentation and technical specifications.
---

# Mermaid Chart Skill

Expert in creating high-fidelity technical diagrams using Mermaid syntax. This skill ensures consistency, readability, and visual appeal in documentation across all projects.

## Visual Standards

To maintain a premium, high-contrast look (optimized for dark mode), use the following standards:

| Component Type | Node Style | Description |
| :--- | :--- | :--- |
| **Root / Entry** | `style ID fill:#f9f,stroke:#333,stroke-width:3px,color:#000` | Pink box, **Black text**, Thick border |
| **Highlight / Target** | `style ID fill:#bbf,stroke:#333,stroke-width:2px,color:#000` | Blue box, **Black text**, Medium border |
| **Standard File** | `style ID fill:#fff,stroke:#333,stroke-width:1px,color:#000` | White box, **Black text** |
| **Folder / Subgraph** | `fill:#cfe2f3,color:#000` or `#d9ead3,color:#000` | Blue/Green background, **Black text** |
| **Agent / Lifecycle** | `style ID fill:#cfe2f3,stroke:#0b5394,color:#000` | Light Blue, **Black text** |
| **Tool / Workflow** | `style ID fill:#d9ead3,stroke:#38761d,color:#000` | Light Green, **Black text** |

## Implementation Guidelines

### 1. Flowcharts (Architecture & Logic)
- **Orientation**: Prefer `flowchart TD` (Top-Down) for hierarchy and `flowchart LR` (Left-Right) for linear processes.
- **Labels**: Use clear, concise labels inside brackets (e.g., `NodeID[Descriptive Label]`).
- **Standard ADK Pattern**:
  ```mermaid
  flowchart TD
      User[User Request] --> Agent[Orchestrator Agent]
      Agent --> Tool1[Search Tool]
      Agent --> Tool2[Write Tool]
      
      style User fill:#f9f,stroke:#333,stroke-width:3px,color:#000
      style Agent fill:#cfe2f3,stroke:#0b5394,stroke-width:1px,color:#000
      style Tool1 fill:#d9ead3,stroke:#38761d,stroke-width:1px,color:#000
      style Tool2 fill:#d9ead3,stroke:#38761d,stroke-width:1px,color:#000
  ```

### 2. Sequence Diagrams (Interactions)
- Use `sequenceDiagram` for multi-agent or agent-tool interactions.
- Avoid excessive styling; focus on the flow of messages (e.g., `Agent ->> Tool: Request`).

### 3. Class Diagrams (Schemas)
- Use `classDiagram` to represent directory structures or data models if a flowchart is too horizontal.

## Best Practices
- **KISS**: Keep It Simple and Small. Break massive diagrams into smaller, linked components.
- **Contrast**: Ensure text is readable against the background fill.
- **Clarity**: Use standard Mermaid shapes (e.g., `{}` for decisions, `[[]]` for subroutines).
