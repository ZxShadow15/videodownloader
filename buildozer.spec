[app]

# App information
title = Video Downloader
package.name = videodownloader
package.domain = com.personal.videodownloader

# Source information
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,html,css,js

# Version info
version = 1.0
version.regex = __version__ = ['"]([^'"]*)['"]
version.filename = %(source.dir)s/main.py

# Requirements
requirements = python3,kivy==2.1.0,flask,flask-sqlalchemy,yt-dlp,ffmpeg-python,sqlalchemy,werkzeug,requests,urllib3

# Python version
osx.python_version = 3
osx.kivy_version = 2.1.0

# Android specific
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,WAKE_LOCK
android.api = 30
android.minapi = 21
android.sdk = 30
android.ndk = 23b
android.private_storage = True
android.accept_sdk_license = True

# Icons and graphics
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png

# Orientation
orientation = portrait

[buildozer]

# Log level (0 = error, 1 = info, 2 = debug)
log_level = 2

# Build directory
build_dir = ./.buildozer

# Bin directory
bin_dir = ./bin
