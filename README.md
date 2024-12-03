# CVE-2024-43328

## Index
* [📌 Analysis](#📌-analysis)
    * [1. 개요](#1-개요)
    * [2. 취약점 분석](#2-취약점-분석)
* [📌 PoC](#📌-poc)
    * [1. 시나리오](#1-시나리오)
    * [2. PHP 파일 추가](#2-php-파일-추가)
    * [3. 취약점 시연](#3-취약점-시연)
* [📌 패치확인](#📌-패치확인)

## 📌 Analysis

### 1. 개요

CVE-2024-43328 취약점은 WordPress의 [EmbedPress](https://wordpress.org/plugins/embedpress/) 플러그인 4.0.9 버전 이하에서 `page_type` 파라미터에 의한 LFI(Local File Include) 취약점입니다.

이 취약점은 EmbedPress 플러그인의 대시보드에서 메뉴를 불러올 때 `page_type` 파라미터를 통해 템플릿 파일을 로드하는 과정에서 발생합니다. `page_type` 파라미터에 상위 경로(`../`) 문자를 포함시키면 서버의 모든 PHP 파일에 접근할 수 있는 Local File Include 취약점이 발생합니다.

### 2. 취약점 분석

EmbedPress 플러그인의 대시보드를 들어가면 각 메뉴를 URL 파라미터 `page_type` 을 통해 템플릿을 로드합니다.

![image-001](images/image-001.png)

템플릿 로드 소스코드는 EmbedPress 플러그인 `EmbedpressSettings.php` 의 `render_settings_page` 함수이고, 해당 함수에서 URL 파라미터 `page_type` 을 가져와 변수 `$template` 를 초기화합니다.

![image-002](images/image-002.png)

이어서 `$template` 변수는 `main-template.php` 파일에서 참조되어 최종적으로 `include_once` 함수에서 템플릿(`EmbedPress/Ends/Back/Settings/templates` 경로에 있는 PHP 파일)을 불러오게 됩니다.

![image-003](images/image-003.png)

따라서, 이 취약점은 템플릿 파일명을 전달하는 URL 파라미터 `page_type`에 상위 경로(`../`)를 포함시켜 서버에 존재하는 모든 PHP 파일을 불러올 수 있게 만듭니다.

## 📌 PoC

### 1. 시나리오

LFI(Local File Include) 취약점은 일반적으로 `/etc/passwd` 파일을 불러오는 PoC로 검증하지만, CVE-2024-43328 취약점은 PHP 파일만 로드할 수 있습니다. 따라서 이번 PoC는 미리 준비된 PHP 파일을 특정 경로에 추가하고 이를 로드하는 방식으로 구성했습니다.

### 2. PHP 파일 추가

웹 루트 디렉터리 경로에 `info.php` 이름을 가지는 파일을 생성하고 해당 파일에 아래의 코드를 입력합니다.

```php
<?php
    phpinfo();
?>
```

![image.png](images/image-004.png)

### 3. 취약점 시연

이후 WordPress 사이트에 Administrator 계정으로 로그인한 뒤, EmbedPress 플러그인 대시보드로 이동한 다음 URL 파라미터 `page_type` 에 페이로드(`../../../../../../../../info`)를 입력하면 웹 서버에 저장된 `info.php` 파일이 정상적으로 로드되어 phpinfo() 함수가 실행된 결과를 확인할 수 있습니다.

최종 URL은 다음과 같습니다.

```
http://localhost:8080/wp-admin/admin.php?page=embedpress&page_type=../../../../../../../../info
```

![image-005](images/image-005.png)

이를 통해 EmbedPress 플러그인의 Local File Include 취약점이 정상적으로 동작하는 것을 확인할 수 있습니다.

## 📌 패치 확인

CVE-2024-43328 취약점에 영향을 받는 EmbedPress 플러그인 4.0.9 이하 버전에서는 URL 파라미터 page_type에 `sanitize_file_name` 함수를 사용했지만, 패치된 4.0.10 버전 이후부터는 `sanitize_text_field` 함수를 사용하여 상위 경로(`../`)와 같은 특수문자를 제거하여 Local File Include 취약점을 방지했습니다.

> [https://plugins.trac.wordpress.org/changeset?sfp_email=&sfph_mail=&reponame=&old=3134433%40embedpress&new=3132586%40embedpress&sfp_email=&sfph_mail=](https://plugins.trac.wordpress.org/changeset?sfp_email=&sfph_mail=&reponame=&old=3134433%40embedpress&new=3132586%40embedpress&sfp_email=&sfph_mail=)
> 

![image-006](images/image-006.png)