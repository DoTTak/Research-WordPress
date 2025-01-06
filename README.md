# CVE-2024-11930

## Index
* [📌 Analysis](#📌-analysis)
    * [1. 개요](#1-개요)
    * [2. 취약점 분석](#2-취약점-분석)
* [📌 PoC](#📌-poc)
* [📌 패치 확인](#📌-패치-확인)

## 📌 Analysis

### 1. 개요

`CVE-2024-11930` 취약점은 Taskbuilder – WordPress Project & Task Management plugin 플러그인(이하, Taskbuilder 플러그인) 버전 3.0.6 이하에서 발생하는 저장형 크로스 사이트 스크립팅 취약점입니다.

이 플러그인은 프로젝트와 작업을 관리하는 도구로, 페이지나 게시글에 단축 코드(’ShortCode’)를 삽입해 프로젝트의 작업 현황을 표시할 수 있습니다. 이때, 단축 코드 `wppm_tasks` 에 대한 유효성 검사 및 이스케이프 처리가 불충분하여 크로스 사이트 스크립팅 취약점이 발생하게 됩니다.

### 2. 취약점 분석

Taskbuilder 플러그인의 단축 코드가 포함된 페이지나 게시글에 접근하면 `/wp-content/plugins/taskbuilder/includes/frontend/wppm_tasks_shortcode.php` 파일의 `WPPM_Tasks_Shortcode` 클래스에서 `__construct` 메서드가 실행되며, 이후 메서드의 로직에 따라 `wppm_page_inline_script` 함수가 호출됩니다.

![image](images/image-001.png)

이후 `wppm_page_inline_script` 함수는 Javascript 코드를 동적으로 생성하는데, 이 과정에서 PHP의 `echo` 함수를 통해 `this->shortcode_attr['project']` 값이 Javascript 코드에 포함되는 것을 확인할 수 있습니다.

![image](images/image-002.png)

따라서, 페이지 작성 시 단축 코드를 `[wppm_tasks project='foo']` 로 작성할 경우 해당 페이지의 응답 데이터는 단축 코드의 속성 `project` 의 값 `foo` 가 Javascript 코드에 포함됩니다.

![image](images/image-003.png)

![image](images/image-004.png)

다만, 단축 코드의 속성 `project` 값이 응답 데이터에 포함될 때 유효성 검사와 이스케이프 처리가 수행되지 않습니다. 따라서 악의적인 Javascript 코드가 포함된 단축 코드로 페이지를 작성하면 크로스 사이트 스크립팅 취약점이 발생합니다.

> 참고로 아래 단축 코드는 Javascript 코드 중 함수 스코프에 포함됩니다. 이에 아래 단축 코드의 속성 `project` 값에 포함된 `alert` 함수는 해당 함수가 호출되어야 동작하게 됩니다.
> 

```
[wppm_tasks project='foo");alert("XSS']
```

![image](images/image-005.png)

## 📌 PoC

1. WordPress 사이트에 Taskbuilder 플러그인 3.0.6 이하의 버전을 설치 및 활성화합니다.
    
    ![image](images/image-006.png)
    
2. 그다음 Contributor 이상의 권한을 가진 계정으로 새 글 작성 페이지(`/wp-admin/post-new.php`)에 접속하여 아래의 단축 코드를 입력합니다.
    
    > 아래 `project` 의 속성 값은 함수 스코프에 포함되지 않도록 작성되었습니다.
    > 
    
    ```
    [wppm_tasks project='project_attr");}alert(document.cookie);function foo(){alert("']
    ```
    
    ![image](images/image-007.png)
    
3. 이후 해당 단축 코드가 포함된 글에 접속하면 크로스 사이트 스크립팅 취약점이 발생하는 것을 확인할 수 있습니다.
    
    ![image](images/image-008.png)
    

## 📌 패치 확인

단축 코드 속성 `project` 값을 출력할 때, `esc_attr` 함수를 사용하여 이스케이프 처리를 수행하도록 패치되었습니다. 

> https://plugins.trac.wordpress.org/changeset/3210469/taskbuilder/tags/3.0.7/includes/frontend/wppm_tasks_shortcode.php#file1
> 

![image](images/image-009.png)

이를 통해 단축 코드의 속성 값에 포함된 특수 문자들이 HTML 엔티티로 변환되어 자바스크립트 코드의 실행이 방지되는 것을 확인했습니다.

![image](images/image-010.png)