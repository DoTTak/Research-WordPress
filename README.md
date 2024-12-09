# CVE-2024-10828

## Index
* [📌 Analysis](#📌-analysis)
    * [1. 개요](#1-개요)
    * [2. 취약점 분석](#2-취약점-분석)
    * [3. ROP Chain](#3-rop-chain)
* [📌 PoC](#📌-poc)
    * [1. PoC 시연](#1-poc-시연)
    * [2. PoC 코드 구현 실행](#2-poc-코드-구현-실행)
* [📌 패치확인](#📌-패치확인)

## 📌 Analysis

### 1. 개요

CVE-2024-10828은 Advanced Order Export For WooCommerce 플러그인의 취약점으로, PHP 객체 주입(Object Injection) 취약점이 발견되었습니다.

해당 취약점은 Advanced Order Export For WooCommerce 플러그인을 통해 주문 기록을 내보낼 때, ‘Try to convert serialized valudes’ 옵션이 활성화된 경우 입력값에 대한 필터링을 수행하지 않아 신뢰할 수 없는 입력값의 역직렬화(deserialization)가 발생하는 취약점이 존재합니다.

특히 이번 취약점의 경우 POP 체인이 존재하여 서버의 임의 파일을 삭제할 수 있습니다.

### 2. 취약점 분석

Advanced Order Export For WooCommerce 플러그인을 설치할 경우 WooCommerce 플러그인 대시보드 메뉴에 Export Orders 메뉴가 추가됩니다.

![images](images/images-001.png)

해당 메뉴에서는 주문 목록을 XLS, CSV, XML 등 다양한 포맷으로 내보낼 수 있으며, 필터링 기능을 통해 특정 조건에 맞는 주문 데이터만 선택적으로 내보낼 수 있습니다.

이때, ‘Misc settings’ 메뉴에서 ‘Try to convert serialized values’ 옵션을 선택할 경우 데이터베이스에서 직렬화된 값을 변환하여 역직렬화를 수행하게 됩니다. 

![images](images/images-002.png)

위와 같이 ‘Try to convert serialized values’ 옵션을 설정할 경우 주문 목록을 내보낼 때, 주문 데이터가 `maybe_unserialize` 함수의 인자로 전달됩니다.

![images](images/images-003.png)

`maybe_unserialize` 함수의 인자로 전달되는 값을 확인하기 위해 코드를 아래와 같이 변경할 경우 로그 출력 결과는 다음과 같습니다.

```php
if ( $options['convert_serialized_values'] ) {
	$arr = maybe_unserialize( $row[ $field ] );
	error_log("[*]" . $field . ": " . $row[$field]);
	if ( is_array($arr) ) $row[$field] = join(",", $arr);
}
```

![images](images/images-004.png)

로그 결과를 살펴 보면 위 입력 데이터는 주문 시 입력한 주문 및 배송 정보인 것을 확인할 수 있습니다.

![images](images/images-005.png)

따라서, 상품 주문 시 입력하는 주문 및 배송 정보에 직렬화된 PHP 객체를 삽입하면 PHP Object Injection 취약점이 발생할 수 있습니다.

### 3. POP Chain

Advanced Order Export For WooCommerce 플러그인에는 POP(Property-Oriented Programming) 체인이 존재합니다.

플러그인 내 `classes/PHPExcel/Shared/XMLWriter.php` 파일의 `PHPExcel_Shared_XMLWriter` 클래스에는 매직 메서드 `__destruct`가 정의되어 있습니다. 이 메서드는 인스턴스 변수 `tempFileName`을 `unlink` 함수의 인자로 전달하여 파일을 삭제합니다.

![images](images/images-006.png)

따라서, 주문 및 배송 정보에 `PHPExcel_Shared_XMLWriter` 클래스의 인스턴스 변수 `$tempFileName`에 임의 파일 경로가 포함된 직렬화된 객체를 삽입하면, 이 객체가 `maybe_unserialize` 함수를 통해 역직렬화됩니다. 그 결과 `PHPExcel_Shared_XMLWriter` 클래스의 `__destruct` 메서드가 실행되어 지정된 경로의 파일이 삭제됩니다.

## 📌 PoC

### 1. PoC 시연

임의의 상품을 주문하고 배송 정보의 주소를 아래의 데이터로 입력합니다.(나머지는 아무 값이나 작성합니다.)

```php
O:25:"PHPExcel_Shared_XMLWriter":1:{s:12:"tempFileName";s:27:"/var/www/html/wp-config.php";}
```

![images](images/images-007.png)

이때, 주소에 입력한 데이터(직렬화된 객체 데이터)는 코드로 변환하면 다음과 같습니다.

```php
$object = new PHPExcel_Shared_XMLWriter();
$object->tempFileName = '/var/www/html/wp-config.php';
```

이어서 주문을 완료하면, WooCommerce 대시보드 주문 목록에 방금 주문한 정보를 확인할 수 있으며 아래와 같이 직렬화된 객체 데이터가 저장된 것을 확인할 수 있습니다.

![images](images/images-008.png)

다음으로, Advanced Order Export For WooCommerce 플러그인의 대시보드(`/wp-admin/admin.php?page=wc-order-export#segment=common`)에서 'Misc settings' 설정의 'Try to convert serialized values' 옵션을 활성화하고 ‘Save settings’ 버튼을 눌러 설정을 저장합니다.

![images](images/images-009.png)

이후 ‘Export’ 버튼을 클릭하여 주문 데이터를 내보냅니다.

![images](images/images-010.png)

그 결과, `/var/www/html/wp-config.php` 파일이 삭제되어 아래와 같이 Alert 함수가 발생합니다.

> `wp-config.php` 파일을 삭제할 경우 워드프레스가 정상적으로 동작하지 않게 되며, 웹 서버의 데이터베이스 연결 정보가 포함된 중요한 설정 파일이 삭제되어 웹사이트가 완전히 중단될 수 있습니다. 이를 통해 이를 통해 공격자는 웹사이트를 사용 불능 상태로 만들거나, 재설치 과정에서 악의적인 설정을 주입할 수 있는 기회를 얻을 수 있습니다.
> 

![images](images/images-011.png)

이후 워드프레스 사이트로 다시 접속 할 경우 워드프레스 재설치 페이지가 등장합니다.

![images](images/images-012.png)

즉, 주소에 입력한 직렬화된 객체 데이터는 Advanced Order Export For WooCommerce 플러그인에서 주문 데이터를 내보낼 때, `maybe_unserialize` 함수의 인자로 배송 정보로 `O:25:"PHPExcel_Shared_XMLWriter":1:{s:12:"tempFileName";s:27:"/var/www/html/wp-config.php";}` 가 전달되어 `PHPExcel_Shared_XMLWriter` 클래스의 인스턴스가 생성되고, 이 객체의 `tempFileName` 속성에 삭제하고자 하는 파일 경로인 `/var/www/html/wp-config.php` 가 설정됩니다. 그 후 객체가 소멸될 때 `__destruct` 메서드가 호출되어 해당 메서드에 정의된 코드 `unlik` 에 의해 해당 파일이 삭제됩니다.

### 2. PoC 코드 구현 실행

`poc.py` 는 위 PoC 시연에 대한 내용을 담고 있습니다. 코드를 실행하려면 코드 하단에 WordPress 주소, 관리자 ID/PW, 삭제할 파일 경로(`tempFileName`)을 설정 합니다.

![images](images/images-013.png)

이후, 아래의 명령어를 통해 `PoC.py` 를 실행합니다.

> `필요 모듈` requests, bs4
> 

```bash
python poc.py
```

![images](images/images-014.png)

이후, 워드프레스 사이트에 접속할 경우 `/wp-config.php` 파일이 삭제되어 다음과 같이 재설치 페이지가 등장합니다.

![images](images/images-015.png)

## 📌 패치 확인

패치된 버전 3.5.6에서는 역직렬화 함수 `maybe_unserialize` 대신 `unserialize` 함수를 사용하고 `['allowed_classes' => false]` 옵션을 추가하여 PHP Object Injection 취약점을 방지하고 있습니다.

![images](images/images-016.png)

`allowed_classes` 옵션을 `false` 로 설정할 경우, 역직렬화된 객체가 생성되지 않고 대신 모든 객체가 `PHP stdClass` 객체로 변환됩니다. 이를 통해 임의의 클래스 인스턴스가 생성되는 것을 방지하여 PHP Object Injection 취약점을 효과적으로 차단할 수 있습니다.

> `PHP stdClass`는 PHP의 기본 빈 객체 클래스입니다. 이 클래스는 사용자 정의 메서드나 속성이 없는 범용 객체 컨테이너로 사용됩니다. 따라서, 매직 메서드(__construct, __destruct 등)가 정의되어 있지 않아 악의적인 코드 실행의 위험이 없습니다.
>