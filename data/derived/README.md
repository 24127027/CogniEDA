# Derived Data

Place reproducible outputs here when they are material analytical inputs or outputs.

Every derived dataset should have:

- an explicit transform or provenance note
- a reproducible source path or upstream `DataProfile` reference in preprocessing history
- its own version identity
- a fresh `DataProfile`

If the derivation cannot be explained and reproduced, it should not be stored as a durable dataset version.
