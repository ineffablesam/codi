---
description: "Serverpod protocol model template"
---
class: {{model_name}}
{{#if create_table}}table: {{table_name}}{{/if}}
fields:
{{#each fields}}
  {{name}}: {{type}}{{#if nullable}}?{{/if}}
{{/each}}
{{#if has_indexes}}
indexes:
{{#each indexes}}
  {{name}}:
    fields: {{fields}}
    {{#if unique}}unique: true{{/if}}
{{/each}}
{{/if}}
