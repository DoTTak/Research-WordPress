# CVE-2024-6695

## Index
* [📌 Analysis](#📌-analysis)
    * [1. 개요](#1-개요)
    * [2. 취약점 분석](#2-취약점-분석)
* [📌 PoC](#📌-poc)
    * [1. 회원가입 페이지 생성](#1-회원가입-페이지-생성)
    * [2. 자동 로그인 활성화](#2-자동-로그인-활성화)
    * [3. 회원가입 요청 패킷 Intercept](#3-회원가입-요청-패킷-intercept)
* [📌 패치 확인](#📌-패치-확인)

## 📌 Analysis

### 1. 개요

`CVE-2024-6695` 취약점은 WordPress의 User Profile Builder – Beautiful User Registration Forms, User Profiles & User Role Editor 플러그인(이하, Profile Builder 플러그인)에서 발견된 인증 우회 취약점입니다. 이 취약점은 Profile Builder 플러그인이 회원가입 과정에서 이메일 유효성 검사 및 중복 이메일 검사를 제대로 수행하지 않아 발생합니다. 공격자가 기존 사용자의 이메일 주소를 알고 있다면 해당 계정으로 로그인할 수 있으며, 관리자 이메일을 알고 있는 경우에는 관리자 권한으로도 로그인이 가능합니다.

단, 해당 취약점을 이용하려면 Profile Builder 플러그인의 설정 중 `Automatically Log In` 설정을 활성화 해야합니다.

### 2. 취약점 분석

Profile Builder 플러그인에서 제공하는 회원가입 페이지는 다음과 같습니다. 해당 회원가입 페이지에서는 사용자명(Username), 이메일(E-mail), 비밀번호(Password), 비밀번호 확인(Repeat Password)을 입력하여 회원가입을 진행할 수 있습니다.

![image](images/image-001.png)

위 페이지에서 회원가입 요청이 발생하면 `/wp-content/plugins/profile-builder/front-end/default-fields/email/email.php` 파일의 `wppb_check_email_value` 함수를 통해 이메일 주소의 유효성과 중복 여부를 검사합니다.

중복 검사 과정에서는 유저 테이블(`$wpdb->users`)을 조회하여 입력된 이메일(`$request_data['email']`)이 기존 사용자의 이메일(`user_email`)과 일치하는지 확인합니다.(line 95 ~ 99)

![image](images/image-002.png)

이때, 중복 이메일 검사를 수행할 때 입력한 이메일(`$request_data['email']`)에 공백이 포함된 경우, 기존에 존재하는 이메일과 정확히 일치하지 않아 중복 검사를 우회할 수 있게 됩니다.

```php
'admin@example.com' != ' admin@example.com'
```

또한, Profile Builder 플러그인의 `Automatically Log In` 옵션이 활성화된 경우 회원가입 이후 자동 로그인을 수행하는데 이는 `/wp-content/plugins/profile-builder/front-end/class-formbuilder.php` 파일의 `wppb_log_in_user` 함수 호출에 의해 동작합니다.

이때, 함수 `wppb_log_in_user` 는 로그인 정보를 가져오기 위해 `get_user_by('email', trim( sanitize_email($_POST['email'])));` 구문을 이용하는데, 이는 회원가입 시 입력된 이메일 주소에서 공백을 제거(trim)하고 이를 기준으로 사용자를 조회하는 구문입니다.(line 219)

![image](images/image-003.png)

따라서, 공격자가 회원가입 시 기존 사용자의 이메일 주소 앞뒤에 공백을 추가하면 이메일 중복 검사를 우회할 수 있습니다. 이후 로그인 과정에서는 공백이 제거된 이메일 주소로 사용자를 조회하기 때문에, 결과적으로 기존 사용자의 계정으로 로그인이 가능해집니다.

## 📌 PoC

### 1. 회원가입 페이지 생성

회원가입 페이지는 Profile Builder 플러그인 대시보드의 Basic Information 메뉴(`/wp-admin/admin.php?page=profile-builder-basic-info`)에서 `Create Form Pages` 버튼을 클릭하여 생성할 수 있습니다.

![image](images/image-004.png)

`Create Form Pages` 버튼을 클릭하면 아래와 같이 총 3개의 페이지(프로필 수정, 로그인, 회원가입)가 생성된 것을 확인하실 수 있습니다.

![image](images/image-005.png)

### 2. 자동 로그인 활성화

Profile Builder 플러그인 대시보드의 설정 메뉴(`/wp-admin/admin.php?page=profile-builder-general-settings`)에서 다음과 같이 `Automatically Log In` 옵션을 활성화합니다.

![image](images/image-006.png)

### 3. 회원가입 요청 패킷 Intercept

회원가입 페이지 양식에 맞춰 정보를 입력하고 이메일 입력란(`E-mail`)에는 기존 사용자의 이메일 주소를 입력합니다.

![image](images/image-007.png)

이후 Proxy 도구를 이용하여 Intercept 된 상태에서 회원가입을 요청하여 패킷을 확인합니다. 그 다음 요청 데이터 `email` 의 앞 또는 뒤에 공백을 추가한 뒤 Forward를 수행합니다.

![image](images/image-008.png)

그럼 다음과 같이 회원가입에 성공했다는 메시지를 응답받게 됩니다.

![image](images/image-009.png)

이후에는 `Automatically Log In` 옵션에 의해 자동으로 로그인 요청을 수행하게 되는데, 이는 다음과 같이 Intercept 된 상태에서도 확인 가능합니다. 

![image](images/image-010.png)

이때, 자동 로그인 요청에 대한 응답 데이터를 보면 `Set-Cookie` 헤더에 로그인 처리 된 세션 정보를 확인하실 수 있습니다.

### 4. 특정 사용자(관리자) 로그인 확인

그 결과 `Set-Cookie` 헤더에 담긴 세션 정보는 페이지를 요청할 때 요청 헤더의 `Cookie` 에 포함되어 요청이 이루어지므로 다음과 같이 회원가입 시 입력한 기존 사용자의 이메일 주소로 로그인이 이루어진것을 확인하실 수 있습니다.

![image](images/image-011.png)

## 📌 패치 확인

패치된 코드를 살펴보면 이메일 중복 검사를 수행하기 전에 `trim` 함수를 사용하여 입력된 이메일의 앞뒤 공백을 제거하는 것을 확인할 수 있습니다. 따라서 공격자가 기존 사용자의 이메일 주소 앞뒤에 공백을 추가하더라도 중복 검사 과정에서 공백이 제거되어 비교되므로, 더 이상 이메일 중복 검사를 우회할 수 없게 되었습니다.

https://plugins.trac.wordpress.org/changeset?sfp_email=&sfph_mail=&reponame=&old=3116169%40profile-builder&new=3116169%40profile-builder&sfp_email=&sfph_mail=#file10

![image](images/image-012.png)