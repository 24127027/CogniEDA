# Bootstrap — Target Design

## Current implementation

This directory contains no Python bootstrap implementation. There is no `dependency_container.py`, root application factory, worker bootstrap or startup lifecycle in current source.

## Target design

A future bootstrap package may:

- load validated configuration;
- create database/session factories;
- initialize the tool manager and executor registry;
- construct planner and worker services;
- expose explicit application/worker entrypoints.

Do not add phantom modules to architecture diagrams or runtime documentation before they exist and are tested.
