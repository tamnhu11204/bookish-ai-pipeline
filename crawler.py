import requests
from bs4 import BeautifulSoup
import json
import time
import random
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# --- CẤU HÌNH ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
]

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Referer": "https://www.fahasa.com/",
}

CATEGORY_URL_TEMPLATE = "https://www.fahasa.com/sach-trong-nuoc/van-hoc-trong-nuoc/sach-to-mau-danh-cho-nguoi-lon.html?order=num_orders&limit=24&p={page}"
MAX_PAGES_TO_CRAWL = 10


def get_random_headers():
    return {
        **HEADERS,
        "User-Agent": random.choice(USER_AGENTS),
    }


def save_cookies(driver, path="cookies.pkl"):
    import pickle

    try:
        pickle.dump(driver.get_cookies(), open(path, "wb"))
        print("Đã lưu cookie.")
    except Exception as e:
        print(f"Lỗi khi lưu cookie: {e}")


def load_cookies(driver, path="cookies.pkl"):
    import pickle

    try:
        cookies = pickle.load(open(path, "rb"))
        for cookie in cookies:
            driver.add_cookie(cookie)
        print("Đã tải cookie.")
    except FileNotFoundError:
        print(
            "Không tìm thấy file cookie. Chạy không headless để giải CAPTCHA thủ công."
        )
        driver.get("https://www.fahasa.com")
        time.sleep(90)  # Tăng thời gian chờ CAPTCHA
        save_cookies(driver)


def get_product_urls_from_page(driver, page_url, page_num):
    """Lấy link, tên, giá, discount, hình ảnh từ trang danh mục bằng Selenium."""
    products = []
    try:
        print(f"Đang tải trang danh mục: {page_url}")
        driver.get(page_url)
        print("Đang chờ tải danh mục và giải CAPTCHA nếu có...")
        time.sleep(90)  # Tăng thời gian chờ

        # Cuộn trang
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # Chờ phần tử danh mục
        WebDriverWait(driver, 90).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.category-products.row")
            )
        )

        # Tìm số trang tối đa từ phân trang
        soup = BeautifulSoup(driver.page_source, "html.parser")
        max_pages = MAX_PAGES_TO_CRAWL
        pagination = soup.find("div", class_="pages", id="pagination")
        if pagination:
            page_links = pagination.find_all(
                "a", onclick=re.compile(r"catalog_ajax\.Page_change\(\d+\)")
            )
            if page_links:
                last_page = page_links[-1].text.strip()
                if last_page.isdigit():
                    max_pages = min(int(last_page), MAX_PAGES_TO_CRAWL)
                    print(f"Đã tìm thấy {max_pages} trang từ phân trang.")

        # Tìm thẻ category-products
        category_products = soup.find("div", class_="category-products row")
        if not category_products:
            print("Không tìm thấy thẻ category-products row.")
            return products, max_pages

        # Tìm các sản phẩm trong <ul id="products_grid">
        product_grid = category_products.find("ul", id="products_grid")
        if not product_grid:
            print("Không tìm thấy ul#products_grid.")
            return products, max_pages

        product_items = product_grid.find_all("li")
        print(f"Tìm thấy {len(product_items)} sản phẩm trên trang danh mục {page_num}.")

        for item in product_items:
            # Tìm tên và link sản phẩm
            a_tag = item.find("h2", class_="product-name-no-ellipsis")
            if a_tag:
                a_tag = a_tag.find("a")
                href = a_tag.get("href") if a_tag else None
                name = a_tag.text.strip() if a_tag else "Không có tên"
            else:
                continue

            # Tìm giá
            price_div = item.find("div", class_="price-label")
            price = 0
            discount = 0
            if price_div:
                price_span = price_div.find("p", class_="special-price")
                if price_span:
                    price_span = price_span.find("span", class_="price")
                    price_str = (
                        price_span.text.strip()
                        .replace("đ", "")
                        .replace(".", "")
                        .replace("&nbsp;", "")
                    )
                    price = int(re.sub(r"\D", "", price_str)) if price_str else 0
                discount_span = price_div.find("span", class_="discount-percent")
                if discount_span:
                    discount_str = (
                        discount_span.text.strip().replace("%", "").replace("-", "")
                    )
                    discount = (
                        int(re.sub(r"\D", "", discount_str)) if discount_str else 0
                    )

            # Tìm ảnh (bỏ qua fhs_img_frame_block)
            img_tag = item.find("div", class_="product images-container")
            img_url = ""
            if img_tag:
                img = img_tag.find("img", class_="lazyloaded")
                img_url = img.get("src") if img else ""

            if href:
                products.append(
                    {
                        "url": href,
                        "name": name,
                        "price": price,
                        "discount": discount,
                        "img": [img_url] if img_url else [],
                    }
                )

        return products, max_pages
    except Exception as e:
        print(f"Lỗi khi crawl danh mục {page_url}: {e}")
        with open(
            f"page_source_error_page_{page_num}.html", "w", encoding="utf-8"
        ) as f:
            f.write(driver.page_source)
        print(f"Đã lưu page_source_error_page_{page_num}.html")
        return products, MAX_PAGES_TO_CRAWL


def get_book_details(driver, book_url, initial_data):
    """Lấy chi tiết đầy đủ từ trang sản phẩm."""
    try:
        driver.get("https://www.fahasa.com")
        load_cookies(driver)
        print(f"Đang tải trang chi tiết: {book_url}")
        driver.get(book_url)
        time.sleep(5)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Tìm tên sản phẩm
        name_tag = soup.find("div", class_="fhs_name_product_mobile")
        if name_tag:
            full_name = name_tag.text.strip()
            name = re.split(r" - Tặng Kèm| - Độc Quyền", full_name)[0].strip()
        else:
            name_tag = soup.find("div", class_="title-product")
            name = (
                name_tag.text.strip()
                if name_tag
                else initial_data.get("name", "Không có tên")
            )

        # Tìm giá hiện tại
        price_tag = soup.find("p", class_="special-price")
        price = initial_data.get("price", 0)
        if price_tag:
            price_span = price_tag.find("span", class_="price")
            if price_span:
                price_str = (
                    price_span.text.strip()
                    .replace("đ", "")
                    .replace(".", "")
                    .replace("&nbsp;", "")
                )
                price = int(re.sub(r"\D", "", price_str)) if price_str else price

        # Tìm giá cũ và phần trăm giảm giá
        old_price_tag = soup.find("p", class_="old-price")
        discount = initial_data.get("discount", 0)
        if old_price_tag:
            old_price_span = old_price_tag.find("span", class_="price")
            if old_price_span:
                old_price_str = (
                    old_price_span.text.strip()
                    .replace("đ", "")
                    .replace(".", "")
                    .replace("&nbsp;", "")
                )
                price = int(re.sub(r"\D", "", old_price_str)) if old_price_str else 0
            discount_span = old_price_tag.find("span", class_="discount-percent")
            if discount_span:
                discount_str = (
                    discount_span.text.strip().replace("%", "").replace("-", "")
                )
                discount = int(re.sub(r"\D", "", discount_str)) if discount_str else 0

        # Tìm tất cả link ảnh
        images = initial_data.get("img", [])
        lightgallery_div = soup.find("div", class_="lightgallery")
        if lightgallery_div:
            image_links = lightgallery_div.find_all("a", class_="include-in-gallery")
            for link in image_links:
                href = link.get("href")
                if href:
                    images.append(href)
        images = list(set(images))

        # Tìm mô tả
        description_div = soup.find("div", id="product_tabs_description_contents")
        description = (
            re.sub(r"\s+", " ", description_div.text.strip())
            if description_div
            else "Không có mô tả."
        )

        # Tìm bảng chi tiết
        details = {}
        info_table = soup.find("table", class_="data-table table-additional")
        if info_table:
            for row in info_table.find_all("tr"):
                label_tag = row.find("th", class_="table-label")
                value_tag = row.find("td")
                if label_tag and value_tag:
                    key = label_tag.text.strip()
                    value_div = value_tag.find("div", class_="attribute_link_container")
                    value = (
                        value_div.text.strip() if value_div else value_tag.text.strip()
                    )
                    details[key] = value

        author_name = details.get("Tác giả", "Không có tác giả")
        publisher_name = details.get("NXB", "Không có NXB")
        supplier_name = details.get("Tên Nhà Cung Cấp", "Không có nhà cung cấp")
        format_name = details.get("Hình thức", "Không có hình thức")
        language_name = details.get("Ngôn Ngữ", "Không có ngôn ngữ")

        publish_year_str = details.get("Năm XB", "")
        publish_year = int(publish_year_str) if publish_year_str.isdigit() else None

        page_str = details.get("Số trang", "0")
        pages = int(page_str) if page_str.isdigit() else 0

        weight_str = details.get("Trọng lượng (gr)", "0")
        weight_gr = int(re.sub(r"\D", "", weight_str)) if weight_str else 0

        dimensions_str = details.get("Kích Thước Bao Bì", "Không có kích thước")

        return {
            "name": name,
            "author_name": author_name,
            "publisher_name": publisher_name,
            "supplier_name": supplier_name,
            "publish_year": publish_year,
            "page": pages,
            "weight_gr": weight_gr,
            "dimensions_str": dimensions_str,
            "format_name": format_name,
            "language_name": language_name,
            "description": description,
            "price": price,
            "discount": discount,
            "img": images,
            "category_name": "Tiểu thuyết",
        }
    except Exception as e:
        print(f"Lỗi khi crawl chi tiết {book_url}: {e}")
        initial_data["description"] = "Không lấy được mô tả."
        initial_data["author_name"] = "Không có tác giả"
        initial_data["publisher_name"] = "Không có NXB"
        initial_data["supplier_name"] = "Không có nhà cung cấp"
        initial_data["publish_year"] = None
        initial_data["page"] = 0
        initial_data["weight_gr"] = 0
        initial_data["dimensions_str"] = "Không có kích thước"
        initial_data["format_name"] = "Không có hình thức"
        initial_data["language_name"] = "Không có ngôn ngữ"
        initial_data["discount"] = initial_data.get("discount", 0)
        return initial_data


def main():
    all_books_data = []
    print("--- BẮT ĐẦU QUÁ TRÌNH CRAWL DỮ LIỆU SÁCH TỪ FAHASA ---")

    # Khởi tạo ChromeDriver một lần
    chrome_options = Options()
    # chrome_options.add_argument("--headless=new")  # Bật headless sau khi test
    chrome_options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    print("Đang khởi tạo ChromeDriver...")
    driver = webdriver.Chrome(
        service=Service(r"E:\bookish-ai-pipeline\chromedriver.exe"),
        options=chrome_options,
    )

    max_pages = MAX_PAGES_TO_CRAWL
    for page in range(1, max_pages + 1):
        page_url = CATEGORY_URL_TEMPLATE.format(page=page)
        print(f"\n[Trang {page}/{max_pages}] Đang xử lý...")

        products, new_max_pages = get_product_urls_from_page(driver, page_url, page)
        max_pages = min(max_pages, new_max_pages)
        if not products:
            print(
                f"Không tìm thấy sản phẩm nào ở trang {page}, thử lại trang tiếp theo."
            )
            continue  # Bỏ qua trang rỗng thay vì dừng

        print(f" -> Tìm thấy {len(products)} sản phẩm.")

        for prod in products:
            print(f"  -> Đang crawl chi tiết từ: {prod['url']}")
            book_details = get_book_details(driver, prod["url"], prod)
            if book_details.get("author_name") != "Không có tác giả":
                all_books_data.append(book_details)
                print(f"    => Thành công: {book_details['name']}")
            else:
                print(f"    => Bỏ qua vì thiếu tác giả.")

            time.sleep(random.uniform(3, 5))

        # Lưu kết quả trung gian sau mỗi trang
        output_filename = f"crawled_books_sach_to_mau_danh_cho_nguoi_lon_page_{page}.json"
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(all_books_data, f, indent=4, ensure_ascii=False)
        print(f"Đã lưu kết quả trung gian vào '{output_filename}'")

        # Nghỉ ngẫu nhiên giữa các trang để tránh bị chặn
        time.sleep(random.uniform(5, 10))

        # Mô phỏng nhấp vào trang tiếp theo
        if page < max_pages:
            try:
                next_page_link = driver.find_element(
                    By.XPATH, f'//a[@onclick="catalog_ajax.Page_change({page + 1})"]'
                )
                next_page_link.click()
                print(f"Đã nhấp vào trang {page + 1}")
                time.sleep(10)  # Chờ AJAX tải
            except Exception as e:
                print(f"Không nhấp được vào trang {page + 1}: {e}")
                # Nếu không nhấp được, tiếp tục với URL trang tiếp theo

    # Đóng driver
    driver.quit()

    # Lưu kết quả cuối cùng
    final_output_filename = "crawled_books_sach_to_mau_danh_cho_nguoi_lon.json"
    with open(final_output_filename, "w", encoding="utf-8") as f:
        json.dump(all_books_data, f, indent=4, ensure_ascii=False)

    print(f"\n--- HOÀN TẤT ---")
    print(f"Đã crawl {len(all_books_data)} cuốn sách vào '{final_output_filename}'")


if __name__ == "__main__":
    main()
