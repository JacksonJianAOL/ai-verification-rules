# Public AI verification domain rule union

This repository contains public routing domain lists only. It contains no
proxy nodes, subscription URLs, credentials, or personal configuration.

Priority: MetaCubeX `anthropic`, `hcaptcha`, and `cloudflare`, followed by
domains in flyingparanoia/ProxyRules `OpenAI.yaml` not already covered by those
MetaCubeX lists. A local `withpersona.com` suffix entry covers Persona subdomains.

The generated files use native `DOMAIN` / `DOMAIN-SUFFIX` rule-list syntax.
Sources and content hashes are recorded in `rules/manifest.json`. Domain coverage
is derived from the listed upstream authors; this project does not discover new
verification hosts itself or guarantee service/account availability.

GitHub Actions requests an update every six hours, plus manual dispatch. GitHub
may delay scheduled runs or disable schedules in an inactive public repository.
Failed download/validation preserves the last committed rule files.

Upstreams:
- https://github.com/MetaCubeX/meta-rules-dat
- https://github.com/flyingparanoia/ProxyRules

Run locally with `python -m pip install -r requirements.txt`, then
`python sync_rules.py`. Configure client rules with a URL to the published `.list`
file and the desired local proxy policy. Client refresh scheduling is independent
of the repository schedule; neither is a real-time discovery feed.
