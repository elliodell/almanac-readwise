# Native adapter

This is the canonical adapter source for the Almanac Readwise Books branch.
Copy `ReadwiseBooks.cpp` and `ReadwiseBooks.h` to `src/integrations/` in the
companion CrossPoint Highlighting fork and apply `PluginEvents.patch`.
The patch is based on CrossPoint Highlighting commit
`86f8a06e18e8613cb355f30eeadf17cd2a2dbf29`.

The companion needs its existing verified Readwise root certificate,
`WifiPowerSaveGuard`, and SecureClient hostname-verification fix, plus the explicit stale-connection
retry opt-out in the companion’s `scripts/patch_readwise_tls.py`. These files
are not standalone firmware and are not compatible with an unmodified upstream
checkout by copying the adapter alone. Build and install instructions are in
the companion fork. Keep both source copies identical when maintaining them.

The mirror declaration is deliberately separate from Almanac's HTTP request:
the existing request continues to deliver to Almanac. `readwise-books-v1`
captures only `reader.session`, uses its own durable queue, and is optional via
protected SD configuration. Unknown mirror names have no effect. Old firmware
ignores the new declaration and continues ordinary Almanac operation.

The adapter and integration follow this repository's MIT license. CrossPoint
integration and test scaffolding derive from the MIT-licensed CrossPoint Reader
project and the CrossPoint Highlighting fork; preserve their existing notices.
