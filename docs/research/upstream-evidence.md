# Upstream retrieval ledger

Retrieved 2026-10-21–22. Read-only GitHub API metadata/tree/release/open-issue samples and raw source retrieval; official docs through web. No candidate installed, run or security-certified. Raw source remains in ignored `.cache/phase1-evidence`; this ledger preserves references and byte hashes without vendoring implementations.

## Repository snapshots

Latest is GitHub latest-release endpoint at retrieval, not package compatibility or newest release across every ecosystem.

| Repository | Inspected commit | Commit UTC | Observed release / published UTC | License API label |
|---|---|---|---|---|
| [basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory) | `8df7e90441e353d8ef88454d72e8d0a775e880f1` | 2026-10-21T16:31:27Z | [v0.23.2](https://github.com/basicmachines-co/basic-memory/releases/tag/v0.23.2) / 2026-08-25T20:44:29Z | AGPL-3.0 |
| [casbin/casbin](https://github.com/casbin/casbin) | `c35c93d29063b8bc3bc2ef30b09943d344a289f4` | 2026-10-21T00:39:25Z | [v3.11.0](https://github.com/apache/casbin/releases/tag/v3.11.0) / 2026-08-20T02:57:58Z | Apache-2.0 |
| [coddingtonbear/obsidian-local-rest-api](https://github.com/coddingtonbear/obsidian-local-rest-api) | `7c603fbc42918bd9ec6f34ab5b46300bac0d0eaa` | 2026-10-17T16:21:28Z | [5.5.2](https://github.com/coddingtonbear/obsidian-local-rest-api/releases/tag/5.5.2) / 2026-10-17T16:23:52Z | MIT |
| [getzep/graphiti](https://github.com/getzep/graphiti) | `8e320f880e7d169a907dbf2a7ac4188586c03b55` | 2026-10-21T02:47:23Z | [v0.31.2](https://github.com/getzep/graphiti/releases/tag/v0.31.2) / 2026-10-20T17:25:21Z | Apache-2.0 |
| [letta-ai/letta](https://github.com/letta-ai/letta) | `8816d3a8516893bfdc0fa14bfb1235226012e295` | 2026-10-18T22:28:01Z | [0.16.8](https://github.com/letta-ai/letta/releases/tag/0.16.8) / 2026-05-14T17:14:24Z | Apache-2.0 |
| [mem0ai/mem0](https://github.com/mem0ai/mem0) | `2c81af3bbe27d9bccb09c772d583df9e9be72ee5` | 2026-10-21T01:16:17Z | [ts-v3.3.1](https://github.com/mem0ai/mem0/releases/tag/ts-v3.3.1) / 2026-09-25T17:36:35Z | Apache-2.0 |
| [openfga/openfga](https://github.com/openfga/openfga) | `22c4d5ddf4d5969bee10c24e468a5acfbcf26837` | 2026-10-20T14:14:32Z | [v1.22.0](https://github.com/openfga/openfga/releases/tag/v1.22.0) / 2026-10-06T19:29:35Z | Apache-2.0 |
| [topoteretes/cognee](https://github.com/topoteretes/cognee) | `37f788bd287750e10d7610173e5332b3843f6ebd` | 2026-10-16T20:07:34Z | [v1.6.5](https://github.com/topoteretes/cognee/releases/tag/v1.6.5) / 2026-10-16T20:10:50Z | Apache-2.0 |

GitHub API returned HTTP 403 rate limits for PyCasbin, Obsidian Git and SilverBullet. Direct branch sources were retrieved; exact source commit is unknown. Obsidian Git release page showed 2.42.0 (2026-10-18). PyCasbin release page showed v2.8.0 while retrieved master metadata said 2.6.1: source/package mapping remains unresolved. SilverBullet source reports 2.12.1, not verified as a published release. Original Letta points to letta-code; current runtime source was retrieved on main without a commit pin. Obsidian application build/source not inspected.

## File manifest

Pinned source links where metadata succeeded; otherwise mutable branch explicitly shown. SHA-256 identifies retrieved bytes, not correctness. Some files were retrieved for context without full line-by-line review; no exhaustive code audit claimed. Findings are in [assessment](reuse-assessment.md).

| Repository / revision basis | Source | SHA-256 |
|---|---|---|
| basicmachines-co/basic-memory / `8df7e90441e353d8ef88454d72e8d0a775e880f1` | [LICENSE](https://github.com/basicmachines-co/basic-memory/blob/8df7e90441e353d8ef88454d72e8d0a775e880f1/LICENSE) | `8486a10c4393cee1c25392769ddd3b2d6c242d6ec7928e1414efff7dfb2f07ef` |
| basicmachines-co/basic-memory / `8df7e90441e353d8ef88454d72e8d0a775e880f1` | [pyproject.toml](https://github.com/basicmachines-co/basic-memory/blob/8df7e90441e353d8ef88454d72e8d0a775e880f1/pyproject.toml) | `e796ec644f41b265fec988be61c187e91c4ce7102cd2f231b2cf12b40bafad50` |
| basicmachines-co/basic-memory / `8df7e90441e353d8ef88454d72e8d0a775e880f1` | [src/basic_memory/api/v2/routers/accepted_content_router.py](https://github.com/basicmachines-co/basic-memory/blob/8df7e90441e353d8ef88454d72e8d0a775e880f1/src/basic_memory/api/v2/routers/accepted_content_router.py) | `786c1343a6a0e5d5c3575c4c1ba7b60678e959a6baa4c14ce2864c759b263fde` |
| basicmachines-co/basic-memory / `8df7e90441e353d8ef88454d72e8d0a775e880f1` | [src/basic_memory/api/v2/routers/scoped_search_router.py](https://github.com/basicmachines-co/basic-memory/blob/8df7e90441e353d8ef88454d72e8d0a775e880f1/src/basic_memory/api/v2/routers/scoped_search_router.py) | `6ba49f8dccb913f71f544fd964114da5253349f8677c962f2de4dedce661a415` |
| basicmachines-co/basic-memory / `8df7e90441e353d8ef88454d72e8d0a775e880f1` | [src/basic_memory/index/local_watch.py](https://github.com/basicmachines-co/basic-memory/blob/8df7e90441e353d8ef88454d72e8d0a775e880f1/src/basic_memory/index/local_watch.py) | `92496cfce570ad555951e35eba8c7dd0acd866d546fac31dac51e2ac7f5395ed` |
| basicmachines-co/basic-memory / `8df7e90441e353d8ef88454d72e8d0a775e880f1` | [src/basic_memory/index/local_wiki_projection.py](https://github.com/basicmachines-co/basic-memory/blob/8df7e90441e353d8ef88454d72e8d0a775e880f1/src/basic_memory/index/local_wiki_projection.py) | `791772db9c916bfe82bb6f248a02180142e4efd3b094817eb1cf83f650db68e1` |
| basicmachines-co/basic-memory / `8df7e90441e353d8ef88454d72e8d0a775e880f1` | [src/basic_memory/index/watch_service.py](https://github.com/basicmachines-co/basic-memory/blob/8df7e90441e353d8ef88454d72e8d0a775e880f1/src/basic_memory/index/watch_service.py) | `959ecff26f39a2f2589632bb6bc255b57ac5ef86792ddf417fc5435a2d62b3dc` |
| basicmachines-co/basic-memory / `8df7e90441e353d8ef88454d72e8d0a775e880f1` | [src/basic_memory/markdown/entity_parser.py](https://github.com/basicmachines-co/basic-memory/blob/8df7e90441e353d8ef88454d72e8d0a775e880f1/src/basic_memory/markdown/entity_parser.py) | `3e28a2d710b8a2ee0ba202ff5a2508e2a976d9188e6d20176b949b03909ef934` |
| basicmachines-co/basic-memory / `8df7e90441e353d8ef88454d72e8d0a775e880f1` | [src/basic_memory/markdown/plugins.py](https://github.com/basicmachines-co/basic-memory/blob/8df7e90441e353d8ef88454d72e8d0a775e880f1/src/basic_memory/markdown/plugins.py) | `8f265eb06d656976c16c6d8762eebc71fb1ad09453b67cbeea97cc49919b4e6e` |
| basicmachines-co/basic-memory / `8df7e90441e353d8ef88454d72e8d0a775e880f1` | [src/basic_memory/picoschema/validator.py](https://github.com/basicmachines-co/basic-memory/blob/8df7e90441e353d8ef88454d72e8d0a775e880f1/src/basic_memory/picoschema/validator.py) | `5e4fbd8ebf41b9a51739bfc4c01332b97846f9d8ba894fa4a86bef8b2a24ac00` |
| basicmachines-co/basic-memory / `8df7e90441e353d8ef88454d72e8d0a775e880f1` | [src/basic_memory/services/entity_service.py](https://github.com/basicmachines-co/basic-memory/blob/8df7e90441e353d8ef88454d72e8d0a775e880f1/src/basic_memory/services/entity_service.py) | `719ffefeece4b75c763d33b4cb6f7cdad1c9af051f848ef1dec5729cfddb1c2b` |
| basicmachines-co/basic-memory / `8df7e90441e353d8ef88454d72e8d0a775e880f1` | [src/basic_memory/services/search_service.py](https://github.com/basicmachines-co/basic-memory/blob/8df7e90441e353d8ef88454d72e8d0a775e880f1/src/basic_memory/services/search_service.py) | `6e22413b975d5f9a1c404cd90d728eecf28e94dec3f0f6bf4a72d662e5f8d4ae` |
| basicmachines-co/basic-memory / `8df7e90441e353d8ef88454d72e8d0a775e880f1` | [tests/index/test_watch_delete_unresolves_inbound_relation.py](https://github.com/basicmachines-co/basic-memory/blob/8df7e90441e353d8ef88454d72e8d0a775e880f1/tests/index/test_watch_delete_unresolves_inbound_relation.py) | `ad28cb3bd766dfd6209eb327109ac8f334631bfc4f51171f8566ffda9431213f` |
| casbin/pycasbin / `master` | [casbin/core_enforcer.py](https://github.com/casbin/pycasbin/blob/master/casbin/core_enforcer.py) | `5629043713f6865e796fea0499b1be73c852894c5f3ad76977a90958d656c1a0` |
| casbin/pycasbin / `master` | [examples/abac_model.conf](https://github.com/casbin/pycasbin/blob/master/examples/abac_model.conf) | `5771a6bd8928a51e99846ffa354fc337621d0e78993e5a3fac64159bdf4c765d` |
| casbin/pycasbin / `master` | [examples/rbac_with_deny_model.conf](https://github.com/casbin/pycasbin/blob/master/examples/rbac_with_deny_model.conf) | `73f831d56a53f2f326a82368a6b531e4b09ab48f0abe707b723ac7389038cbc6` |
| casbin/pycasbin / `master` | [LICENSE](https://github.com/casbin/pycasbin/blob/master/LICENSE) | `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4` |
| casbin/pycasbin / `master` | [pyproject.toml](https://github.com/casbin/pycasbin/blob/master/pyproject.toml) | `4bb6fb41b8bed43a7e6c33bde6ad9864d99e7b959001763b37254e5d4b592109` |
| casbin/pycasbin / `master` | [requirements.txt](https://github.com/casbin/pycasbin/blob/master/requirements.txt) | `f53134b157def7b5e674bbbb235dff963a3d5a1cf89f928558746f1aaca4cf71` |
| casbin/pycasbin / `master` | [tests/test_enforcer.py](https://github.com/casbin/pycasbin/blob/master/tests/test_enforcer.py) | `eb0d8f5eb413c990d7f1f9884bbfe118eb305d1645bcb52abe870ac8f6ec6574` |
| coddingtonbear/obsidian-local-rest-api / `7c603fbc42918bd9ec6f34ab5b46300bac0d0eaa` | [LICENSE](https://github.com/coddingtonbear/obsidian-local-rest-api/blob/7c603fbc42918bd9ec6f34ab5b46300bac0d0eaa/LICENSE) | `c9414415db6e70597f6ae3d8d08a3b7d550d78700a11436c17cff6506dd3676a` |
| coddingtonbear/obsidian-local-rest-api / `7c603fbc42918bd9ec6f34ab5b46300bac0d0eaa` | [package.json](https://github.com/coddingtonbear/obsidian-local-rest-api/blob/7c603fbc42918bd9ec6f34ab5b46300bac0d0eaa/package.json) | `0224c4f9e1c5d8c6b80c57051532903720ba471cad72b49beeb868f581caef07` |
| coddingtonbear/obsidian-local-rest-api / `7c603fbc42918bd9ec6f34ab5b46300bac0d0eaa` | [src/mcpHandler.ts](https://github.com/coddingtonbear/obsidian-local-rest-api/blob/7c603fbc42918bd9ec6f34ab5b46300bac0d0eaa/src/mcpHandler.ts) | `d8baf57dfca701a2d286a97abb55b693e03a83803a09fc712e3be49212da1709` |
| coddingtonbear/obsidian-local-rest-api / `7c603fbc42918bd9ec6f34ab5b46300bac0d0eaa` | [src/requestHandler.ts](https://github.com/coddingtonbear/obsidian-local-rest-api/blob/7c603fbc42918bd9ec6f34ab5b46300bac0d0eaa/src/requestHandler.ts) | `77e1f853873ba0baa02a070358180eb227012260e07719632ffd491ccfba9e35` |
| coddingtonbear/obsidian-local-rest-api / `7c603fbc42918bd9ec6f34ab5b46300bac0d0eaa` | [src/vaultOperations.ts](https://github.com/coddingtonbear/obsidian-local-rest-api/blob/7c603fbc42918bd9ec6f34ab5b46300bac0d0eaa/src/vaultOperations.ts) | `d2214970d95d6169cf9ac5b33cb3065cf38c0ac320993feff08fbdd745626a2a` |
| getzep/graphiti / `8e320f880e7d169a907dbf2a7ac4188586c03b55` | [graphiti_core/edges.py](https://github.com/getzep/graphiti/blob/8e320f880e7d169a907dbf2a7ac4188586c03b55/graphiti_core/edges.py) | `637732ae4291ca0e5b53e43dd92be6f46a91e352719cb7ea1570ebab7d5d0e33` |
| getzep/graphiti / `8e320f880e7d169a907dbf2a7ac4188586c03b55` | [graphiti_core/graphiti.py](https://github.com/getzep/graphiti/blob/8e320f880e7d169a907dbf2a7ac4188586c03b55/graphiti_core/graphiti.py) | `4e456b2255196d13466e31d13d0f5790e85d611731cbdfa733abfb3091f24040` |
| getzep/graphiti / `8e320f880e7d169a907dbf2a7ac4188586c03b55` | [LICENSE](https://github.com/getzep/graphiti/blob/8e320f880e7d169a907dbf2a7ac4188586c03b55/LICENSE) | `2825300b20d7b951209835a4a331f29e24725a39d65168e4b831df53aa372650` |
| getzep/graphiti / `8e320f880e7d169a907dbf2a7ac4188586c03b55` | [pyproject.toml](https://github.com/getzep/graphiti/blob/8e320f880e7d169a907dbf2a7ac4188586c03b55/pyproject.toml) | `fa842260cb2724ef5142ebee50395149dee51d224372bccfeb084a63655563ba` |
| letta-ai/letta-code / `main` | [LICENSE](https://github.com/letta-ai/letta-code/blob/main/LICENSE) | `036e78b9d7dd33ae5b378fdda973b4aad7901c8d8371a0ae40fae1f6659a89d0` |
| letta-ai/letta-code / `main` | [package.json](https://github.com/letta-ai/letta-code/blob/main/package.json) | `80ff2d59f09aca706a73477b283838c447eddee1372053c2d703ed98f21259ef` |
| letta-ai/letta-code / `main` | [src/index.ts](https://github.com/letta-ai/letta-code/blob/main/src/index.ts) | `b55f37d53b096960138f1336e17c6b3b086de1a6430d39f2c4aa1c51377c91a9` |
| letta-ai/letta / `8816d3a8516893bfdc0fa14bfb1235226012e295` | [LICENSE](https://github.com/letta-ai/letta/blob/8816d3a8516893bfdc0fa14bfb1235226012e295/LICENSE) | `984c6db99fc6609803108dfc196762118662cd94b82a456dd9217583f18f3612` |
| letta-ai/letta / `8816d3a8516893bfdc0fa14bfb1235226012e295` | [README.md](https://github.com/letta-ai/letta/blob/8816d3a8516893bfdc0fa14bfb1235226012e295/README.md) | `67ec50661bb95db1839101863f08eaaa3cae3f2cc804adb2250a058393e56417` |
| mem0ai/mem0 / `2c81af3bbe27d9bccb09c772d583df9e9be72ee5` | [LICENSE](https://github.com/mem0ai/mem0/blob/2c81af3bbe27d9bccb09c772d583df9e9be72ee5/LICENSE) | `0bbcbe931c353293a2fafce08326181dfeea0e568c566afd4ce8337a70f5e219` |
| mem0ai/mem0 / `2c81af3bbe27d9bccb09c772d583df9e9be72ee5` | [mem0/memory/main.py](https://github.com/mem0ai/mem0/blob/2c81af3bbe27d9bccb09c772d583df9e9be72ee5/mem0/memory/main.py) | `f329ca4a17af1fbefb32ac10d4cc7ae7ddbdb7435a87eb74c30915cff98b8b7c` |
| mem0ai/mem0 / `2c81af3bbe27d9bccb09c772d583df9e9be72ee5` | [pyproject.toml](https://github.com/mem0ai/mem0/blob/2c81af3bbe27d9bccb09c772d583df9e9be72ee5/pyproject.toml) | `d4bc078a05cc7b9d677bbf4d0b262cfc532495b5aadeded053ac84fd90b6e974` |
| openfga/openfga / `22c4d5ddf4d5969bee10c24e468a5acfbcf26837` | [cmd/run/run.go](https://github.com/openfga/openfga/blob/22c4d5ddf4d5969bee10c24e468a5acfbcf26837/cmd/run/run.go) | `4c95563a0ad272d2ce89fe907161459447e416eeee713745574a5d5030f6e29d` |
| openfga/openfga / `22c4d5ddf4d5969bee10c24e468a5acfbcf26837` | [LICENSE](https://github.com/openfga/openfga/blob/22c4d5ddf4d5969bee10c24e468a5acfbcf26837/LICENSE) | `1c46d7b2bed94d457d745f28cabeb31f8d6c81dd9035bc5d24039989ee1e1bff` |
| openfga/openfga / `22c4d5ddf4d5969bee10c24e468a5acfbcf26837` | [pkg/server/commands/check.go](https://github.com/openfga/openfga/blob/22c4d5ddf4d5969bee10c24e468a5acfbcf26837/pkg/server/commands/check.go) | `4c021e12769acaa714bdd26ec40fa79e8f4a48001a1b0e1bcf511bd557af6cf0` |
| openfga/openfga / `22c4d5ddf4d5969bee10c24e468a5acfbcf26837` | [pkg/server/commands/list_objects.go](https://github.com/openfga/openfga/blob/22c4d5ddf4d5969bee10c24e468a5acfbcf26837/pkg/server/commands/list_objects.go) | `729af8fa34f7937c8dfac152df7084f1a803698c6528f28fe2fe4c6a89235ee1` |
| silverbulletmd/silverbullet / `main` | [Cargo.toml](https://github.com/silverbulletmd/silverbullet/blob/main/Cargo.toml) | `b3bcbb667bd6459ee51d67026865ec6872ffcd8ba0ec69e67abcf59ef987af36` |
| silverbulletmd/silverbullet / `main` | [LICENSE.md](https://github.com/silverbulletmd/silverbullet/blob/main/LICENSE.md) | `ccf525a3b5c9ac8d843e118932036e6517d4d603f9ff3e474522b632c3996c65` |
| silverbulletmd/silverbullet / `main` | [README.md](https://github.com/silverbulletmd/silverbullet/blob/main/README.md) | `29806b792de1b6a449f794869a342f542e4599de358046b5b7172ecd404dffdb` |
| silverbulletmd/silverbullet / `main` | [server/src/lib.rs](https://github.com/silverbulletmd/silverbullet/blob/main/server/src/lib.rs) | `0cebd6bdddda1f831a00512d1b91cb20a1a2e818cb01257dde75c3bf3df2874a` |
| silverbulletmd/silverbullet / `main` | [server/src/router.rs](https://github.com/silverbulletmd/silverbullet/blob/main/server/src/router.rs) | `5f51bf1f32e90b41394a9ff7d1aa3ae346e1f8ac9e30b3179ac3ce93efe1ffe2` |
| silverbulletmd/silverbullet / `main` | [version.ts](https://github.com/silverbulletmd/silverbullet/blob/main/version.ts) | `cdec0d4cc5d84f7fe657f3ec5de79621ac2631a9d23d21638ff095fb56eaa1a2` |
| topoteretes/cognee / `37f788bd287750e10d7610173e5332b3843f6ebd` | [cognee/api/v1/cognify/cognify.py](https://github.com/topoteretes/cognee/blob/37f788bd287750e10d7610173e5332b3843f6ebd/cognee/api/v1/cognify/cognify.py) | `34369d26032dd8fb1b78e8774d9b0cba4ffcb91915af01c5c88e936b7709f7d1` |
| topoteretes/cognee / `37f788bd287750e10d7610173e5332b3843f6ebd` | [cognee/api/v1/search/search.py](https://github.com/topoteretes/cognee/blob/37f788bd287750e10d7610173e5332b3843f6ebd/cognee/api/v1/search/search.py) | `552077550e6307f8662b06d34634f3c8a4d7e9c6f8b2d859c3cbefdac161688f` |
| topoteretes/cognee / `37f788bd287750e10d7610173e5332b3843f6ebd` | [cognee/modules/data/methods/get_authorized_existing_datasets.py](https://github.com/topoteretes/cognee/blob/37f788bd287750e10d7610173e5332b3843f6ebd/cognee/modules/data/methods/get_authorized_existing_datasets.py) | `3504feadd4f0a482514d6ad94cd380bdf8aa7cad48ded5130e8f5df4d57329c7` |
| topoteretes/cognee / `37f788bd287750e10d7610173e5332b3843f6ebd` | [cognee/modules/users/permissions/methods/get_effective_capabilities.py](https://github.com/topoteretes/cognee/blob/37f788bd287750e10d7610173e5332b3843f6ebd/cognee/modules/users/permissions/methods/get_effective_capabilities.py) | `771fe4c5eca79298668a1b6c0ea6255db03a514ea84e9c4dc5e1575982e0f639` |
| topoteretes/cognee / `37f788bd287750e10d7610173e5332b3843f6ebd` | [LICENSE](https://github.com/topoteretes/cognee/blob/37f788bd287750e10d7610173e5332b3843f6ebd/LICENSE) | `a471e34908f50c3f120e9a56f3c30cb34e133e4ede01a9cbd5ce718fc358ecd4` |
| topoteretes/cognee / `37f788bd287750e10d7610173e5332b3843f6ebd` | [pyproject.toml](https://github.com/topoteretes/cognee/blob/37f788bd287750e10d7610173e5332b3843f6ebd/pyproject.toml) | `a5ca3c4a4e0ad74e812cb06c7c707b62b42e241d5c5ab8013e01ac46ebc7892c` |
| Vinzent03/obsidian-git / `master` | [LICENSE](https://github.com/Vinzent03/obsidian-git/blob/master/LICENSE) | `b9c17ede4874ca24c60e397096cfb51c33fc1474b8bdb0cf02e90ace5912cada` |
| Vinzent03/obsidian-git / `master` | [manifest.json](https://github.com/Vinzent03/obsidian-git/blob/master/manifest.json) | `7ad98e8cce157e9846b47941c6a7cb9b022bc9d5c6d11782290e7a7a164b470d` |
| Vinzent03/obsidian-git / `master` | [package.json](https://github.com/Vinzent03/obsidian-git/blob/master/package.json) | `7f352821d8418afc34f3dd62655e84ac54b7b5d5c940740ffa9b2c63222551ea` |
| Vinzent03/obsidian-git / `master` | [src/automaticsManager.ts](https://github.com/Vinzent03/obsidian-git/blob/master/src/automaticsManager.ts) | `1984431ac35d7572d4a1867617fff31daed222e3dda49d1305b6b706f9ce38dc` |
| Vinzent03/obsidian-git / `master` | [src/gitManager/gitManager.ts](https://github.com/Vinzent03/obsidian-git/blob/master/src/gitManager/gitManager.ts) | `d1006d1084f046147bdc66f184121aa6d92e1a4ce90c790c5ae08b81738c6b6c` |
| Vinzent03/obsidian-git / `master` | [src/gitManager/simpleGit.ts](https://github.com/Vinzent03/obsidian-git/blob/master/src/gitManager/simpleGit.ts) | `d5f98cb56084e2f27229cab52c6bbbc7db444bd1f362272448f8f9475d72c26f` |
| Vinzent03/obsidian-git / `master` | [src/main.ts](https://github.com/Vinzent03/obsidian-git/blob/master/src/main.ts) | `6796ca85d02437913dc3b23f82cf29144c25677f7cf1e144006dff96ff5843ed` |

## Bounded relevant issue sample

API open-state title/URL metadata, not reproduced defects. PR labels explicit. Graphiti PR 2040 and Casbin discussion 1702 additionally read via web; most bodies not retrieved.

| Repository | Open report at retrieval | Evidence |
|---|---|---|
| basicmachines-co/basic-memory | [Issue #1800: [FEATURE] Explore an optional file-metadata interoperability experiment](https://github.com/basicmachines-co/basic-memory/issues/1800) | metadata only unless noted above |
| basicmachines-co/basic-memory | [Issue #1796: Resolve folder case on write so notes don't split into case-only twin folders](https://github.com/basicmachines-co/basic-memory/issues/1796) | metadata only unless noted above |
| basicmachines-co/basic-memory | [Issue #1783: Hermes integration reads bm's project registry from ~/.basic-memory even when XDG_CONFIG_HOME is set](https://github.com/basicmachines-co/basic-memory/issues/1783) | metadata only unless noted above |
| topoteretes/cognee | [Issue #6215: [Bug]: CloudClient.add() does not unwrap DataItem objects passed by local add() in remote mode](https://github.com/topoteretes/cognee/issues/6215) | metadata only unless noted above |
| topoteretes/cognee | [Issue #6214: [Bug]: NativeLiteLLMAdapter budget errors on plain-text path are retried instead of converted to LLMPaymentRequiredError](https://github.com/topoteretes/cognee/issues/6214) | metadata only unless noted above |
| topoteretes/cognee | [Issue #6213: [Bug]: cognee.add() via remote client ignores node_set, run_in_background, and dataset_id](https://github.com/topoteretes/cognee/issues/6213) | metadata only unless noted above |
| getzep/graphiti | [Issue #2049: [Bug] GeminiEmbedder defaults to text-embedding-001, which the Gemini API does not list](https://github.com/getzep/graphiti/issues/2049) | metadata only unless noted above |
| getzep/graphiti | [Issue #2043: [Bug] OpenAIGenericClient ignores configured small_model](https://github.com/getzep/graphiti/issues/2043) | metadata only unless noted above |
| getzep/graphiti | [PR #2040: fix(mcp): enforce group_id on UUID-addressed tools](https://github.com/getzep/graphiti/pull/2040) | metadata only unless noted above |
| mem0ai/mem0 | [Issue #7704: docs: AGENTS.md files still reference removed mem0/graphs package](https://github.com/mem0ai/mem0/issues/7704) | metadata only unless noted above |
| mem0ai/mem0 | [Issue #7701: CLI: expose memory history through a history command](https://github.com/mem0ai/mem0/issues/7701) | metadata only unless noted above |
| mem0ai/mem0 | [Issue #7700: REST API drops message name before infer=False actor attribution](https://github.com/mem0ai/mem0/issues/7700) | metadata only unless noted above |
| casbin/casbin | [Issue #1702: How to achieve transaction consistency between Casbin policy operations and other database operations?](https://github.com/apache/casbin/issues/1702) | metadata only unless noted above |
| openfga/openfga | [Issue #3355: Bug: Failed migration left invalid index in databse](https://github.com/openfga/openfga/issues/3355) | metadata only unless noted above |
| openfga/openfga | [PR #3347: fix(storage): stop ReadChanges from skipping changes of concurrent writes](https://github.com/openfga/openfga/pull/3347) | metadata only unless noted above |
| coddingtonbear/obsidian-local-rest-api | [PR #394: Compare the API key in constant time](https://github.com/coddingtonbear/obsidian-local-rest-api/pull/394) | metadata only unless noted above |

## Retrieval gaps

Initial Basic Memory sync/service paths, original Letta agent.py, old SilverBullet Deno/server.ts paths and top-level Obsidian Git gitManager.ts did not resolve. Repository trees/README led to current watcher/index, letta-code entrypoint, SilverBullet Rust router and nested Git manager source. Failed guesses are not absence-of-feature evidence. Firecrawl tools unavailable; read-only shell network access required approved escalation. No credentials printed/saved.

## Adoption verification checklist

1. Resolve actual dependency release to immutable source; compare used files/licenses against this ledger, especially floating source and PyCasbin source/release mismatch.
2. Trace all relevant ingress/read/search/count/graph/history/write paths; inspect issue bodies/fixes/security advisories.
3. Run proposed P01?P04 in chosen deployment; source checks do not certify ACL or crash safety.
4. Review redistributed artifact/dependency license graph and actual egress/resource/runtime/platform cost.
5. Record actual code avoided versus adapter/patch maintenance before adoption.
