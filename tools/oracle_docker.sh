#!/bin/bash
# Grade a task in its own image without Harbor: build environment/, then in a
# fresh container either run solution/solve.sh (the oracle) or copy in a
# submission folder, and run tests/test.sh the way Harbor does.
#
#     tools/oracle_docker.sh <task-dir>                 # oracle
#     tools/oracle_docker.sh <task-dir> <submission>    # grade these files instead
#
# Prints the per-check pytest lines and the reward. It is a pre-flight check;
# the oracle of record is still `harbor run -a oracle`.
set -euo pipefail

# The cloud sandbox does not keep a Docker daemon alive between sessions; start
# one if none answers and this shell may.
if ! docker info >/dev/null 2>&1 && command -v dockerd >/dev/null && [ "$(id -u)" = 0 ]; then
    (dockerd >/tmp/dockerd.log 2>&1 &)
    for _ in $(seq 1 30); do docker info >/dev/null 2>&1 && break; sleep 1; done
fi

TASK="$(cd "$1" && pwd)"
SUB="${2:-}"
TAG="oracle-$(basename "$TASK" | tr 'A-Z' 'a-z' | cut -c1-60)"

# Pre-flight image. In this cloud sandbox the internet is reachable only
# through an HTTPS proxy that re-signs TLS, so two things in the task's own
# Dockerfile cannot run as written: the plain-HTTP apt layer, and pip without
# the proxy's CA. The grader never uses what apt installs (bash/curl/git are
# for Harbor's agents), so that layer is dropped, and pip is pointed at the
# CA. Base image, pip pins and input/ - everything the verifier touches - are
# unchanged. Set PREFLIGHT_RAW=1 on a normal network to build the Dockerfile
# exactly as shipped.
CTX="$(mktemp -d)"
trap 'rm -rf "$CTX"' EXIT
cp -a "$TASK/environment/." "$CTX/"
if [ -z "${PREFLIGHT_RAW:-}" ] && [ -f /root/.ccr/ca-bundle.crt ]; then
    cp /root/.ccr/ca-bundle.crt "$CTX/.preflight-ca.crt"
    sed -i -e '/^RUN apt-get/,/apt\/lists/d' \
           -e '/^FROM /a COPY .preflight-ca.crt /tmp/ca.crt\nENV PIP_CERT=/tmp/ca.crt' \
           "$CTX/Dockerfile"
fi
docker build -q --network host -t "$TAG" "$CTX" >/dev/null

args=(--rm --network none
      -v "$TASK/tests:/tests:ro"
      -v "$TASK/solution:/solution:ro")
if [ -n "$SUB" ]; then
    args+=(-v "$(cd "$SUB" && pwd):/submission:ro")
    step='cp -a /submission/. /app/'
else
    step='bash /solution/solve.sh >/dev/null'
fi

docker run "${args[@]}" "$TAG" bash -c "
    set -e
    $step
    bash /tests/test.sh >/tmp/test-stdout.txt 2>&1 || true
    grep -E '^(PASSED|FAILED) ' /tmp/test-stdout.txt | sed 's/ - .*//' || true
    tail -1 /tmp/test-stdout.txt
    echo \"reward: \$(cat /logs/verifier/reward.txt)\"
"
