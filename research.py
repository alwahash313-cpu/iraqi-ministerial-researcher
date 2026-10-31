
import json
import os
import re
import time
import unicodedata
from datetime import datetime
from urllib.parse import quote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

SUBJECTS = {
    "اللغة العربية": ["العربي", "اللغة العربية", "عربي"],
    "اللغة الإنجليزية": ["الإنكليزي", "الانكليزي", "اللغة الإنجليزية", "اللغة الانجليزية", "انكليزي"],
    "الرياضيات": ["الرياضيات", "رياضيات"],
    "الكيمياء": ["الكيمياء", "كيمياء"],
    "الفيزياء": ["الفيزياء", "فيزياء"],
    "الأحياء": ["الأحياء", "الاحياء", "أحياء", "احياء"],
    "الاجتماعيات": ["الاجتماعيات", "اجتماعيات", "الجغرافية", "التاريخ", "الوطنية"],
    "التربية الإسلامية": ["الإسلامية", "الاسلامية", "التربية الإسلامية", "التربية الاسلامية", "اسلامية"],
}

CURRENT_YEAR = datetime.now().year
OUTPUT_DIR = "reports"
os.makedirs(OUTPUT_DIR, exist_ok=True)

SEARCH_TYPES = {
    "مرشحات حديثة": [
        f"مرشحات {CURRENT_YEAR}",
        "مرشحات وزاري",
        "توقعات الامتحان الوزاري",
    ],
    "أسئلة وزارية سابقة": [
        "اسئلة وزارية الدور الأول",
        "اسئلة وزارية الدور الثاني",
        "اسئلة وزارية الدور الثالث",
        "اسئلة وزارية التمهيدي",
        "حلول الاسئلة الوزارية",
    ],
    "ملخصات ومراجعات": [
        "ملخص",
        "مراجعة مركزة",
        "مراجعة ليلة الامتحان",
    ],
    "شروحات وحلول": [
        "شرح وحل تمارين",
        "حلول واجوبة",
    ],
}


def normalize(text):
    text = unicodedata.normalize("NFKC", str(text or "")).lower()
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ى", "ي").replace("ة", "ه")
    text = re.sub(r"[ـًٌٍَُِّْ]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def detect_subject(title, fallback):
    text = normalize(title)

    # نبحث عن المادة الحقيقية في عنوان النتيجة أولاً
    checks = [
        ("اللغة الإنجليزية", ["انكليزي", "انجليزي", "اللغة الانجليزية", "اللغة الانكليزية"]),
        ("الاجتماعيات", ["اجتماعيات", "جغرافيه", "تاريخ", "وطنيه"]),
        ("التربية الإسلامية", ["اسلاميه", "التربيه الاسلاميه"]),
        ("اللغة العربية", ["عربي", "اللغه العربيه"]),
        ("الرياضيات", ["رياضيات"]),
        ("الكيمياء", ["كيمياء"]),
        ("الفيزياء", ["فيزياء"]),
        ("الأحياء", ["احياء"]),
    ]

    for subject, words in checks:
        if any(normalize(word) in text for word in words):
            return subject

    return fallback


def detect_type(title, keyword):
    text = normalize(title)

    if any(word in text for word in ["مرشحات", "مرشحه", "توقعات", "متوقعات"]):
        return "مرشحات"

    if any(word in text for word in [
        "اسئله وزاريه", "اسئلة وزارية", "الدور الاول",
        "الدور الثاني", "الدور الثالث", "التمهيدي",
        "التمهيدي", "امتحان وزاري"
    ]):
        return "أسئلة وزارية سابقة"

    if any(word in text for word in ["حلول", "اجوبه", "اجوبة", "حل اسئله"]):
        return "حلول وأجوبة"

    if any(word in text for word in ["شرح", "محاضره", "محاضرة", "تمارين"]):
        return "شروحات وحلول"

    if any(word in text for word in ["ملخص", "مراجعه", "مراجعة", "مركزه"]):
        return "ملخصات ومراجعات"

    if "مرشحات" in keyword:
        return "مرشحات"

    if "اسئلة" in keyword:
        return "أسئلة وزارية سابقة"

    return "ملخصات ومراجعات"


def detect_year(text):
    match = re.search(r"(20[1-3][0-9])", str(text or ""))
    return match.group(1) if match else ""


def detect_round(text):
    value = normalize(text)

    if "الدور الاول" in value:
        return "الدور الأول"
    if "الدور الثاني" in value:
        return "الدور الثاني"
    if "الدور الثالث" in value:
        return "الدور الثالث"
    if "التمهيدي" in value:
        return "التمهيدي"

    return ""


def is_relevant(title):
    text = normalize(title)

    school_terms = [
        "الثالث متوسط",
        "الثالث المتوسط",
        "ثالث متوسط",
        "ثالث المتوسط",
    ]

    return any(normalize(term) in text for term in school_terms)


def search_news(subject, keyword, content_type):
    query = f'"الثالث متوسط" العراق "{subject}" "{keyword}"'

    url = (
        "https://news.google.com/rss/search?q="
        + quote(query)
        + "&hl=ar&gl=IQ&ceid=IQ:ar"
    )

    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    try:
        with urlopen(request, timeout=25) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)
        items = []

        for item in root.findall(".//item"):
            title = item.findtext("title", default="").strip()
            link = item.findtext("link", default="").strip()
            pub_date = item.findtext("pubDate", default="").strip()

            source_element = item.find("source")
            source = (
                source_element.text.strip()
                if source_element is not None and source_element.text
                else "Google News"
            )

            if not title or not link:
                continue

            if not is_relevant(title):
                continue

            actual_subject = detect_subject(title, subject)

            # لا نضع النتيجة في مادة أخرى إذا كان عنوانها يحدد مادة مختلفة
            if actual_subject != subject:
                continue

            detected_type = detect_type(title, keyword)
            year = detect_year(title) or detect_year(pub_date)

            items.append({
                "subject": actual_subject,
                "title": title,
                "source": source,
                "url": link,
                "published_at": pub_date,
                "keyword": keyword,
                "content_type": detected_type,
                "search_group": content_type,
                "year": year,
                "exam_round": detect_round(title),
                "is_current_year": year == str(CURRENT_YEAR),
            })

        return items

    except Exception as exc:
        print(f"تعذر البحث عن {subject} - {keyword}: {exc}")
        return []


def main():
    results = []
    seen_urls = set()

    for subject in SUBJECTS:
        print(f"\nالبحث في مادة: {subject}")

        for content_type, keywords in SEARCH_TYPES.items():
            for keyword in keywords:
                print(f"  - {content_type}: {keyword}")

                found = search_news(subject, keyword, content_type)

                for result in found:
                    if result["url"] not in seen_urls:
                        seen_urls.add(result["url"])
                        results.append(result)

                time.sleep(1)

    # ترتيب النتائج: المرشحات الحديثة أولاً، ثم بقية المحتوى
    results.sort(
        key=lambda item: (
            item["content_type"] != "مرشحات",
            item["year"] != str(CURRENT_YEAR),
            item["published_at"],
        ),
        reverse=False,
    )

    now = datetime.now().astimezone().isoformat(timespec="seconds")

    data = {
        "updated_at": now,
        "results": results,
        "subjects": list(SUBJECTS.keys()),
        "content_types": [
            "مرشحات",
            "أسئلة وزارية سابقة",
            "ملخصات ومراجعات",
            "شروحات وحلول",
        ],
        "total": len(results),
    }

    json_path = os.path.join(OUTPUT_DIR, "latest.json")
    md_path = os.path.join(OUTPUT_DIR, "latest.md")

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    with open(md_path, "w", encoding="utf-8") as file:
        file.write("# الباحث الوزاري العراقي\n\n")
        file.write(f"آخر تحديث: {now}\n\n")
        file.write(f"عدد النتائج: {len(results)}\n\n")

        for subject in SUBJECTS:
            file.write(f"## {subject}\n\n")

            subject_results = [
                item for item in results
                if item["subject"] == subject
            ]

            if not subject_results:
                file.write("لم تُعثر على نتائج لهذه المادة.\n\n")
                continue

            for item in subject_results:
                year = item["year"] or "السنة غير محددة"
                round_name = item["exam_round"] or "الدور غير محدد"

                file.write(f"- [{item['title']}]({item['url']})\n")
                file.write(f"  - التصنيف: {item['content_type']}\n")
                file.write(f"  - السنة: {year}\n")
                file.write(f"  - الدور: {round_name}\n")
                file.write(f"  - المصدر: {item['source']}\n\n")

    print(f"\nاكتمل البحث. عدد النتائج: {len(results)}")
    print(f"تم إنشاء: {json_path} و {md_path}")


if __name__ == "__main__":
    main()
