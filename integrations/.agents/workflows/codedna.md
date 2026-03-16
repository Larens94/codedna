---
description: CodeDNA v0.5 — how to read, write, and edit Python files in this project
---

# CodeDNA v0.5 Protocol

This project uses CodeDNA. Every source file carries its own context in a Python-native module docstring.

## Reading a file

1. Read the **module docstring** at the top of the file first (first 8–12 lines)
2. Note `deps:` → symbols you must not break
3. Note `exports:` → symbols you must not rename or remove
4. Note `rules:` → hard constraints that apply everywhere in this file
5. For any function, check its Google-style docstring for `Depends:` and `Rules:`

## Editing a file

1. Before writing any logic: re-read `rules:` in the module docstring and `Rules:` in the function docstring
2. Apply all cascade changes mentioned in `Modifies:` sections and call-site comments
3. Do not change `exports:` signatures without explicit user instruction

## Creating a file

Every new Python source file must start with:

```python
"""filename.py — <what it does, ≤15 words>.

deps:    other_file.py → symbol | none
exports: public_function(arg) -> return_type
used_by: consumer_file.py → consumer_function
tables:  table_name(col1, col2) | none
rules:   <hard constraint agents must never violate>
"""
```

## Critical functions

For functions that cross file boundaries, add:

```python
def my_function(arg: type) -> return_type:
    """Short description.

    Depends: other_file.symbol — what contract it imposes.
    Rules:   What the agent MUST or MUST NOT do here.
    """
    raw = get_external_data()  # includes X — filter Y below
```

## Planning across a codebase

Read only the module docstring (first 8–12 lines) of each file. Build a dependency graph from `deps:`/`exports:`. Load only the relevant files in full.

## Inline hyperlink tags (still valid)

```python
def my_function():
    # @REQUIRES-READ: other.py → symbol_name  (must read before writing)
    # @MODIFIES-ALSO: another.py → fn()        (update after editing this)
    # @SEE: config.py → CONSTANT              (read if uncertain)
```

## Semantic variable naming

```python
# CodeDNA style — type + shape + domain + origin
list_dict_orders_from_db = db.query(sql)
str_html_view_rendered = render(query_fn)
int_cents_price_from_request = req.json["price"]
```
