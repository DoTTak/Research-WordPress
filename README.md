# Research-WordPress-CVE

> This repository is dedicated to analyzing and researching CVE vulnerabilities discovered in WordPress.

## CVE LIST
|CVE|Vulnerbility|CVSS(3.x)|Version|
|:-:|:----------:|:-------:|:---------------:|
|[CVE-2024-4439](https://github.com/DoTTak/Research-WordPress-CVE/tree/CVE-2024-4439)|Stored XSS|7.2|WP < 6.5.2|
|[CVE-2024-27956](https://github.com/DoTTak/Research-WordPress-CVE/tree/CVE-2024-27956)|SQL Injection|9.9|`plugin` Automatic <= 3.92.0|
|[CVE-2024-52427](https://github.com/DoTTak/Research-WordPress-CVE/tree/CVE-2024-52427)|Server Side Include(RCE)|8.8|`plugin` Event Tickets with Ticket Scanner <= 2.3.11|
|[CVE-2024-43328](https://github.com/DoTTak/Research-WordPress-CVE/tree/CVE-2024-43328)|Local File Inclusion(LFI)|8.8|`plugin` EmbedPress <= 4.0.9|
|[CVE-2024-10828](https://github.com/DoTTak/Research-WordPress-CVE/tree/CVE-2024-10828)|PHP Object Injection|8.1|`plugin` Advanced Order Export For WooCommerce <= 3.5.5|
|[CVE-2024-10124](https://github.com/DoTTak/Research-WordPress-CVE/tree/CVE-2024-10124)|Improper Access Control(Authentication Bypass)|9.8|`plugin` Vayu Blocks – Gutenberg Blocks for WordPress & WooCommerce <= 1.1.1|

## Information

### Docker
|Image|Tag|Port Forwarding|Environment|
|:---:|:-:|:--:|:----|
|php|8.3-apache|8080:80| |
|mariadb|lts| - | <ul><li>`MARIADB_DATABASE` wp</li><li>`MARIADB_ROOT_PASSWORD` !root1234</li></ul> |
|phpmyadmin|latest|8888:80| |


### Submodule
|Submodule|Version|Path|
|:-------:|:-----:|:--:|
|WordPress|6.7.1|`web/app`|


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
