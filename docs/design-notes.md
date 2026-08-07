# Design Notes

## Overview

This repository contains a documented Mihomo configuration template focused on desktop and mobile TUN usage.

## Core decisions

- TUN is the primary system interception method.
- LAN, link-local, multicast, and broadcast traffic are excluded at the routing layer.
- Fake-IP is used with explicit real-ip exceptions.
- Sniffer restores domain information from HTTP/TLS/QUIC metadata but avoids unnecessary destination rewriting.
- DNS uses encrypted domestic DoH upstreams, with `direct-nameserver: system` retained for DIRECT traffic.

## Security

Only templates should be stored publicly. Subscription tokens, UUIDs, and private endpoints should stay local.
