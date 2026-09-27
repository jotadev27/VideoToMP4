FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv libpython3.10 ca-certificates nsis binutils \
    libgl1 libegl1 libopengl0 libglib2.0-0 libfontconfig1 libdbus-1-3 \
    libxkbcommon0 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 \
    libxcb-keysyms1 libxcb-render-util0 libxcb-xinerama0 libxcb-xkb1 \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --no-cache-dir PySide6==6.8.3 imageio-ffmpeg==0.6.0 pyinstaller==6.22.0
WORKDIR /source
