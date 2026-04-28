# Knowledge Ingestion

You are ingesting new knowledge into the Frontier agent's knowledge base. The user will provide source material (URLs, file paths, pasted text, or descriptions). Your job is to transform this into well-structured knowledge notes.

## Workflow

1. **Understand the source**: Read or fetch the source material the user provides
2. **Identify the domain**: Determine which subdirectory the content belongs to:
   - `overview/` for system-level descriptions
   - `layout/` for physical architecture (cabinets, chassis, blades, power distribution, cooling infrastructure)
   - `operations/` for operational procedures (power, cooling, compute, interconnect, storage, CEP, scheduling)
   - `telemetry/` for monitoring systems, datasets, hardware topology
3. **Draft the note**: Write a focused markdown note covering one topic
4. **Add cross-references**: Search existing notes with `search_notes` to find related content, then add wikilinks
5. **Update hub.md**: If the note covers a topic not yet listed in `hub.md`, add an entry to the appropriate table
6. **Validate**: Verify the note can be found by `read_note` and that wikilinks point to real files

## Guidelines

- **Split large sources**: If a source covers multiple topics (e.g., both power delivery and cooling), create separate notes for each
- **Preserve technical detail**: Include specific values, thresholds, component identifiers, and procedures. The agent needs precise information to diagnose failures.
- **Use Frontier terminology**: xnames, MSBs, CDUs, PDUs, chassis/blade numbering. Don't simplify or genericize domain-specific terms.
- **Context over completeness**: A focused note with good cross-references is more useful than an exhaustive note that covers everything superficially
