# The container pure-Python tool packages are vendored in.
#
# A separate image from the C one for one reason: picpro requires Python 3.12,
# above the 3.10 in ubuntu:22.04, and the C image's base is pinned for a
# reason that does not apply here. Pure-Python packages contain no compiled
# artifact, so there is no glibc floor to protect and no reason to widen the C
# image's base just to reach a newer interpreter.
#
# Pinned by digest like the C image, so a rebuild produces the same vendored
# dependency set rather than whatever the tag has moved to.

FROM python:3.12-slim@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9

ENV DEBIAN_FRONTEND=noninteractive

# git because the patch queue is applied with `git apply`, and the system pip
# is deliberately left as the image ships it: the vendoring run is what proves
# the package installs with the pip a user's own interpreter has.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN git config --system --add safe.directory '*'
