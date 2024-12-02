#!/bin/sh

###
# current files
###
# Git에서 추적하지 않는 파일과 폴더를 깨끗이 지워서 초기화합니다.
git clean -fd 

# 'db' 폴더를 완전히 삭제해서 데이터베이스를 초기 상태로 만듭니다.
rm -rf db

###
# submodule
###
# 'web/app' 디렉토리로 이동합니다.
cd web/app

# 이 디렉토리도 Git에서 추적하지 않는 파일과 폴더를 정리합니다.
git clean -fd
