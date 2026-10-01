---
name: fde-catalog-enhancement
description: Specialized expertise for building and optimizing retail Product Catalog agents.
---

# Catalog Enhancement Expertise

Use this skill when you are tasked with building, refactoring, or optimizing agents that handle retail product catalogs.

## 🎯 Domain Context
A Product Catalog Agent (PCA) is responsible for:
- **Normalization**: Standardizing raw vendor data into a consistent schema.
- **Enrichment**: Adding missing attributes (colors, materials, features) using LLM reasoning.
- **Categorization**: Mapping products to a standard taxonomy (e.g., Google Product Taxonomy).
- **SEO Optimization**: Generating consumer-friendly titles and descriptions.

## 🛠 Required ADK Patterns
When developing for this domain, prioritize these ADK patterns:
1. **ParallelAgent**: For large-scale batch processing of product SKUs.
2. **SequentialAgent**: For multi-stage enrichment pipelines (Clean -> Enrich -> Validate).
3. **MCP Tools**: Integrate with `BigQuery` for catalog storage and `GCS` for asset management.

## 📝 Example OpenSpec Snippet
```markdown
## Catalog Enhancement Core Features
- [ ] Product Normalization (Brand, Title, SKU)
- [ ] Attribute Extraction (Color, Style, Size)
- [ ] Category Classification (Taxonomy Mapping)
```
