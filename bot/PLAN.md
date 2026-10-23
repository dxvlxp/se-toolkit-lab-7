# Bot implementation plan

## Task 1 — Plan and scaffold

Build a Telegram bot for the existing LMS backend. Separate command handlers from the Telegram transport: handlers receive input and service clients and return response text. The CLI entry point will support `--test` without a Telegram token or network connection to Telegram. Add configuration loading from environment variables and the ignored `.env.bot.secret` file. Keep dependency declarations in `bot/pyproject.toml` and use uv for installation and locking.

## Task 2 — Backend integration

Implement an LMS client with Bearer authentication, bounded request timeouts, and readable errors that preserve the actual failure reason. Connect `/health`, `/labs`, and `/scores <lab>` to real endpoints. Verify the backend response formats before formatting task scores. Handle missing arguments, unknown commands, empty results, unavailable services, and invalid JSON without raw tracebacks.

## Task 3 — Natural language routing

Define function schemas for all nine required backend endpoints. Let the LLM select tools, validate arguments, execute calls, and return their results to the conversation until the model produces an answer. Bound the tool loop and report service failures. Add inline keyboard actions through the same handler layer. Do not replace model routing with keyword matching.

## Task 4 — Containerization and documentation

Create a bot Dockerfile using a committed uv lockfile. Add the bot to the existing Compose network with a restart policy. Configure backend access using the service name and document access to the host LLM proxy. Document environment variables, build commands, logs, and verification steps in README.

## Verification and delivery

Track each task with an issue and a focused branch. Use scoped Conventional Commits and pull requests into this fork. Review interfaces between modules before requesting a classmate review. Run CLI checks for happy paths and failures, then verify live data, tool chaining, and Telegram responses on the VM. Record only checks actually performed; deployment remains unverified until the VM and Telegram checks succeed. Keep credentials out of commits and preserve prior work in the existing history.
