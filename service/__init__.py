"""Local detection service (Milestone 2, spec 5.1).

This package is the ONLY code that loads the watermark key on behalf of
clients. Clients talk to it through `python -m service`, one JSON request on
stdin and one JSON response on stdout, so attack code never shares memory
with the key. See service/README.md for the design.
"""
