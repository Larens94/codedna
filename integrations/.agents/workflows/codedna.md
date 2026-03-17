---
description: CodeDNA v0.6 — how to read, write, and edit Python files in this project
---

# CodeDNA v0.6 Protocol

This project uses CodeDNA. Every source file carries its own context in a Python-native module docstring.

## Reading a file

1. Read the **module docstring** at the top of the file first (first 8–12 lines)
2. Note `exports:` → symbols you must not rename or remove
3. Note `used_by:` → callers that depend on this file's exports
4. Note `rules:` → hard constraints that apply everywhere in this file
5. For any function, check its docstring for `Rules:`

## Editing a file

1. Before writing any logic: re-read `rules:` in the module docstring and `Rules:` in the function docstring
2. Check `used_by:` and `cascade:` targets after changes
3. Do not change `exports:` signatures without explicit user instruction
4. If you discover a constraint or fix a bug, add a `Rules:` annotation for the next agent

## Creating a file

Every new Python source file must start with:

```python
"""filename.py — <what it does, ≤15 words>.

exports: public_function(arg) -> return_type
used_by: consumer_file.py → consumer_function
tables:  table_name(col1, col2) | none
rules:   <hard constraint agents must never violate>
"""
```

## Critical functions

For functions with non-obvious domain constraints, add:

```python
def my_function(arg: type) -> return_type:
    """Short description.

    Rules:   What the agent MUST or MUST NOT do here.
    """
```

## Planning across a codebase

Read `.codedna` first for the project overview. Then read only the module docstring (first 8–12 lines) of each file. Build a graph from `exports:`/`used_by:`. Load only the relevant files in full.

## Semantic variable naming

```python
# CodeDNA style — type + shape + domain + origin
list_dict_orders_from_db = db.query(sql)
str_html_view_rendered = render(query_fn)
int_cents_price_from_request = req.json["price"]
```
