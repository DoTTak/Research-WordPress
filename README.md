# Research-WordPress-CVE

> This repository is dedicated to analyzing and researching CVE vulnerabilities discovered in WordPress.


## Information

### Docker
|Image|Tag|Port Forwarding|
|:---:|:-:|:--:|
|php|8.3-apache|8080:80|
|mariadb|lts|8888:80|
|phpmyadmin|latest| - |


### Submodule
|Submodule|Version|Path|
|:-------:|:-----:|:--:|
|WordPress|6.6.2|`web/app`|


## How to run?

### 1. WordPress(submodule) init & update
```bash
$ git submodule init
$ git submodule update
```

### 2. docker-compose up
```bash
$ docker-compose up
```
