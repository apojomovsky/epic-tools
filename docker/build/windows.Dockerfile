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

# gcc plus libc6-dev for the native half of a cross build (GMP runs tools it
# builds, and --no-install-recommends omits the C startup files), m4 for
# GMP's configure, xz-utils for GNU .tar.xz archives, gcc/g++-mingw-w64 for
# the cross compilers, libz-mingw-w64-dev for minipro's static zlib, make
# plus pkg-config for the upstream Makefiles (minipro's refuses to configure
# without the binary itself), git for `git apply`, python3 for the container
# half of the build driver, ca-certificates/curl for HTTPS fetches.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libc6-dev \
        m4 \
        xz-utils \
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

# GMP and MPFR for the mingw host, built from pinned sources because Ubuntu
# ships no mingw packages for them and gdb's configure refuses to run
# without GMP 4.2+ and MPFR 3.1.0+. Shared only: the DLLs ride beside the
# .exe in the package, never linked statically. Installed into the mingw
# prefix so the cross compiler finds them with no extra flags.
ENV GMP_VERSION=6.3.0 GMP_SHA256=a3c2b80201b89e68616f4ad30bc66aee4927c3ce50e33929ca819d5c43538898
ENV MPFR_VERSION=4.2.1 MPFR_SHA256=277807353a6726978996945af13e52829e3abd7a9a5b7fb2793894e18f1fcbb2
RUN set -eux; \
    cd /tmp; \
    curl -sSL -o gmp.tar.xz "https://ftp.gnu.org/gnu/gmp/gmp-${GMP_VERSION}.tar.xz"; \
    echo "${GMP_SHA256} gmp.tar.xz" | sha256sum -c -; \
    curl -sSL -o mpfr.tar.xz "https://ftp.gnu.org/gnu/mpfr/mpfr-${MPFR_VERSION}.tar.xz"; \
    echo "${MPFR_SHA256} mpfr.tar.xz" | sha256sum -c -; \
    tar xf gmp.tar.xz; tar xf mpfr.tar.xz; \
    mkdir gmp-build && cd gmp-build; \
    "../gmp-${GMP_VERSION}/configure" --host=x86_64-w64-mingw32 \
        --prefix=/usr/x86_64-w64-mingw32 --disable-static --enable-shared; \
    make -j"$(nproc)"; make install; cd /tmp; \
    mkdir mpfr-build && cd mpfr-build; \
    "../mpfr-${MPFR_VERSION}/configure" --host=x86_64-w64-mingw32 \
        --prefix=/usr/x86_64-w64-mingw32 --disable-static --enable-shared \
        --with-gmp=/usr/x86_64-w64-mingw32; \
    make -j"$(nproc)"; make install; cd /tmp; \
    rm -rf gmp.tar.xz mpfr.tar.xz "gmp-${GMP_VERSION}" "mpfr-${MPFR_VERSION}" \
        gmp-build mpfr-build

# git apply refuses a patch that touches a file it considers dubious, and the
# build runs as the invoking host uid, which git does not know. Without this
# the queue fails on the first patch with "detected dubious ownership".
RUN git config --system --add safe.directory '*'
