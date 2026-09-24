# Harbor CLI task image — offline, file-deliverable.
#
# Carries three things: a shell for the agent, the read-only fixtures, and the
# python deps the vendored verifier engine needs. Installing the grader's deps
# at build time (rather than in tests/test.sh) keeps verification independent of
# network conditions at run time.
# python:3.12-slim-bookworm, pinned to the registry's immutable multi-arch
# index digest so the image cannot drift under the tag.
FROM python@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e

# curl + ca-certificates: Harbor's installed agents (claude-code, codex, ...)
# bootstrap node via nvm inside this container during agent setup.
RUN apt-get update && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        git \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# The engine's third-party imports are exactly pydantic, jsonpath_ng and
# tenacity; the pins match infra/task-harness/requirements.txt so a verdict in
# here means what it means in the harness. tenacity arrives via the judge module,
# which is imported at package init even though these tasks never call a judge —
# omitting it fails the whole test collection, not just the rubric path.
RUN pip install --no-cache-dir \
        "pytest==8.4.1" \
        "pytest-json-ctrf==0.3.5" \
        "pydantic==2.12.5" \
        "jsonpath-ng>=1.6,<2" \
        "tenacity>=9.0,<10"

WORKDIR /app

# Read-only task inputs. The prompt refers to these as `input/`.
COPY input/ /app/input/
RUN chmod -R a-w,a+rX /app/input
