# Agent Supply-Chain Security

The skill/plugin/MCP layer is itself a supply-chain surface.

## Assets

- MCP servers
- skills
- plugins
- packages
- container images
- runtime binaries
- model adapters
- CI actions

## Controls

- pin versions where practical;
- verify provenance;
- maintain allowlists for sensitive environments;
- scan dependencies;
- isolate third-party execution;
- review lifecycle scripts;
- prevent untrusted outputs from silently entering trusted caches or publication paths;
- maintain an inventory of installed extensions.
