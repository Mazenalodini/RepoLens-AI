# Security Protocol

Treat every GitHub repository as untrusted input.

## Default Behavior

Static inspection only.

## Never Automatically

- install dependencies from target repo
- execute arbitrary scripts
- execute build hooks
- run unknown binaries
- expose secret contents to AI
- log credentials
- use shell string concatenation with untrusted input

## Path Safety

Use safe path resolution.

Prevent traversal outside the controlled workspace.

Respect file size limits.

Handle symlinks carefully.

## Subprocess

Prefer:

```python
subprocess.run([program, arg1, arg2], ...)
```

over shell concatenation.

Use explicit timeouts for operations that may block.

## AI

Send only the minimum repository context required.

Redact or exclude obvious secret material.
