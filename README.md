license: to be generated

to revisit:
- what is purpose of common_schemas.py?
- defi_schemas.py
- nft_schemas.py
- portfolio_service.py -> get_spl_balances
- sentiment_service.py
- query_router.py

generalize datasources methods, to consider request body and return structure & refactor into modules + changes to be made in main that's delegating the args:
- helius method -> getBalances -> generalise to extend to include other methods with more parameters https://www.helius.dev/docs/api-reference/rpc/http-methods
- helius method -> getAsset -> generalise to extend to include other methods with more parameters https://www.helius.dev/docs/api-reference/das/getasset

useful features to integrate:
- mapping identities to wallets
- tool for identifying whale wallets etc e.g. https://www.nansen.ai/whale-alert if complex analysis needed or from jupiter exchange etc
- transaction history for wallets
- portfolio tracking & summary
- priority fee recommendations

long term goals / vision:
- richer data sources (e.g. on-chain data, off-chain data, social media sentiment) + more providers where needed (eg. magic eden, opensea, etc), on demand and users can choose/add their own
- more comprehensive intent classification, entity recognition, and entity linking via multi-stage pipelines
- personalizatiion of the search experience (e.g. user profiles, user preferences, credentials enabled services) + specialized endpoints catering to specific services (eg. large batch transaction processing, etc)
- more analytics capabilities (ie. sorting, )
- train our own models that is specialized for searching and indexing blockchains for business queries
- test more complex queries based on user profiles by establishing a community of users and knowing their needs

cool addresses to test with according to Nansen:
- 4EtAJ1p8RjqccEVhEhaYnEgQ6kA4JHR8oYqyLFwARUj6 (labeled "90D Smart Trader" with significant profit in TRUMP token)
- HWdeCUjBvPP1HJ5oCJt7aNsvMWpWoDgiejUWvfFX6T7R (labeled "Multiple Memecoin Whale" with profit in FARTCOIN)
- fwHknyxZTgFGytVz9VPrvWqipW2V4L4D99gEb831t81 (labeled "Top 100 on AI16Z Leaderboard" with profit in AI16Z token)   
