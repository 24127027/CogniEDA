# Bootstrap — Target Design

## Current implementation

This directory contains no Python bootstrap implementation. The current
in-process composition root is `src/application/runtime.py`, with external
factory loading in `src/application/runtime_loader.py`. There is no
`dependency_container.py`, worker bootstrap, or startup lifecycle here.

## Target design

A future bootstrap package may:

- load validated configuration;
- create database/session factories;
- initialize the tool manager and executor registry;
- construct planner and worker services;
- expose explicit application/worker entrypoints.

Do not add phantom modules to architecture diagrams or runtime documentation before they exist and are tested.
