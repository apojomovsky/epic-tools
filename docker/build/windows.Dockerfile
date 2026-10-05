# The container Windows tool packages cross-compile in.
#
# Same ubuntu:22.04 base as the Linux C image, pinned by the same digest: one
# base keeps the digests aligned, and a PE binary inherits no glibc floor so
# nothing about Windows asks for newer. mingw-w64 is the cross toolchain both
# C tools build with, and libz-mingw-w64-dev feeds minipro's Windows link. No
# libusb dev package: no Windows binary links libusb. pkg-config stays because
# minipro's Makefile refuses to configure without the binary itself.
#
# Only build tooling lives here. Nothing from the epic8 ecosystem is
# installed: each package fetches its own pinned upstream source and verifies
# the digest inside the build.

FROM ubuntu:22.04@sha256:79676deb51ebb02885b0b9d33788e78a37cf1045ad79d1bb04c6a222c3556b3d

ENV DEBIAN_FRONTEND=noninteractive

# gcc/g++-mingw-w64 for the cross compilers, libz-mingw-w64-dev for minipro's
# static zlib, make plus pkg-config for the upstream Makefiles, git because
# the patch queue is applied with `git apply`, python3 because the container
# half of the build driver runs in it, ca-certificates/curl for HTTPS fetches.
RUN apt-get update && apt-get install -y --no-install-recommends \
        make \
        pkg-config \
        gcc-mingw-w64-x86-64 \
        g++-mingw-w64-x86-64 \
        libz-mingw-w64-dev \
        git \
        python3 \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# git apply refuses a patch that touches a file it considers dubious, and the
# build runs as the invoking host uid, which git does not know. Without this
# the queue fails on the first patch with "detected dubious ownership".
RUN git config --system --add safe.directory '*'
