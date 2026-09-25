# The container every tool package is built in.
#
# Pinned by digest on purpose. A released binary inherits the build image's
# glibc as its compatibility floor, so this pin is a distribution decision:
# ubuntu:22.04 gives glibc 2.35, the same floor epic-cc's own toolchain
# binaries carry, and a rebuild years from now produces a package with the
# same floor rather than whatever `ubuntu:latest` has drifted to.
#
# Only build tooling for the three upstreams lives here. Nothing from the
# epic8 ecosystem is installed: each package fetches its own pinned upstream
# source and verifies the digest inside the build.

FROM ubuntu:22.04@sha256:79676deb51ebb02885b0b9d33788e78a37cf1045ad79d1bb04c6a222c3556b3d

ENV DEBIAN_FRONTEND=noninteractive

# build-essential/g++ for minipro and pk2cmd, pkg-config plus the two dev
# packages minipro's Makefile hard-requires and refuses to configure without,
# git because the patch queue is applied with `git apply`, python3 and pip
# for picpro's vendoring, and ca-certificates/curl so any future pin that
# fetches over HTTPS works without editing this file.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        libusb-1.0-0-dev \
        zlib1g-dev \
        git \
        python3 \
        python3-pip \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# git apply refuses a patch that touches a file it considers dubious, and the
# build runs as the invoking host uid, which git does not know. Without this
# the queue fails on the first patch with "detected dubious ownership".
RUN git config --system --add safe.directory '*'
