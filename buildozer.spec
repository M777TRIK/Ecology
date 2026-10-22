[app]
title = Bybit Scanner
package.name = bybitscanner
package.domain = com.m777trik
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0

requirements = python3,kivy,plyer,requests,pandas,numpy,urllib3,chardet,idna,certifi

android.permissions = INTERNET, POST_NOTIFICATIONS, FOREGROUND_SERVICE
android.api = 33
android.accept_sdk_license = True
android.skip_update = False
android.build_tools_version = 34.0.0
android.minapi = 23
android.archs = arm64-v8a
orientation = portrait
fullscreen = 0
