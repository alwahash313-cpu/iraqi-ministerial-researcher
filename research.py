
import json
import os
import re
import time
import unicodedata
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

SUBJECTS = {
    "اللغة العربية": ["العربي", "اللغة العربية", "عربي"],
    "اللغة الإنجليزية": ["الإنكليزي", "الانكليزي", "اللغة الإنجليزية", "اللغة الانجليزية", "انكليزي", "انجليزي"],
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

CONTENT_TYPES = [
    "مرشحات",
    "أسئلة وزارية سابقة",
    "ملخصات ومراجعات",
    "شروحات وحلول",
]

SEARCH_TYPES = {
    "مرشحات": [
        f"مرشحات الثالث متوسط {CURRENT_YEAR}",
        "مرشحات وزاري الثالث متوسط",
        "توقعات امتحان الثالث متوسط",
    ],
    "أسئلة وزارية سابقة": [
        "اسئلة وزارية الثالث متوسط",
        "اسئلة وزارية الدور الأول الثالث متوسط",
        "اسئلة وزارية الدور الثاني الثالث متوسط",
        "اسئلة وزارية الدور الثالث الثالث متوسط",
        "اسئلة وزارية التمهيدي الثالث متوسط",
        "حلول الاسئلة الوزارية الثالث متوسط",
    ],
    "ملخصات ومراجعات": [
        "ملخص الثالث متوسط",
        "مراجعة مركزة الثالث متوسط",
        "مراجعة ليلة الامتحان الثالث متوسط",
    ],
    "شروحات وحلول": [
        "شرح الثالث متوسط وحل التمارين",
        "حل تمارين كتاب الثالث متوسط",
        "شرح وحلول الثالث متوسط",
    ],
}

SCHOOL_TERMS = [
    "الثالث متوسط",
    "الثالث المتوسط",
    "ثالث متوسط",
    "ثالث المتوسط",
]

EXCLUDED_TERMS = [
    "جدول امتحانات",
    "جدول الامتحان",
    "جدول الدوام",
    "نتائج الثالث",
    "نتائج اعتراضات",
    "نتائج الامتحانات",
    "عداد الوقت",
    "الوقت المتبقي",
    "موعد الامتحان",
    "مواعيد الامتحانات",
    "تقليص المواد",
    "الحذوفات",
    "تعطيل الدوام",
    "عطلة رسمية",
    "اخبار وزارة",
    "تعيينات",
    "رواتب",
]


def normalize(text):
    text = unicodedata.normalize("NFKC", str(text or "")).lower()
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ى", "ي").replace("ة", "ه")
    text = re.sub(r"[ـًٌٍَُِّْ]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def contains_any(text, words):
    value = normalize(text)
    return any(normalize(word) in value for word in words)


def detect_subject(title, fallback):
    text = normalize(title)

    checks = [
        ("اللغة الإنجليزية", ["انكليزي", "انجليزي", "اللغه الانجليزيه", "اللغه الانكليزيه"]),
        ("الاجتماعيات", ["اجتماعيات", "جغرافيه", "تاريخ", "وطنيه"]),
        ("التربية الإسلامية", ["اسلاميه", "التربيه الاسلاميه"]),
        ("اللغة العربية", ["عربي", "اللغه العربيه", "قواعد العربي"]),
        ("الرياضيات", ["رياضيات"]),
        ("الكيمياء", ["كيمياء"]),
        ("الفيزياء", ["فيزياء"]),
        ("الأحياء", ["احياء"]),
    ]

    for subject, words in checks:
        if contains_any(text, words):
            return subject

    return fallback


def is_relevant(title):
    text = normalize(title)

    if not contains_any(text, SCHOOL_TERMS):
        return False

    if contains_any(text, EXCLUDED_TERMS):
        return False

    return True


def detect_type(title):
    text = normalize(title)

    # المرشحات يجب أن تكون مذكورة بوضوح في العنوان
    if contains_any(text, [
        "مرشحات",
        "مرشحه",
        "توقعات وزاريه",
        "توقعات الامتحان",
        "الاسئله المتوقعه",
        "اسئله متوقعه",
    ]):
        return "مرشحات"

    # الأسئلة الوزارية السابقة
    if contains_any(text, [
        "اسئله وزاريه",
        "اسئلة وزارية",
        "اسئله وزاري",
        "الاسئله الوزاريه",
        "حل الاسئله الوزاريه",
        "حلول الاسئله الوزاريه",
        "امتحان وزاري",
        "الدور الاول",
        "الدور الثاني",
        "الدور الثالث",
        "التمهيدي",
    ]):
        return "أسئلة وزارية سابقة"

    # الشروحات والدروس
    if contains_any(text, [
        "شرح",
        "محاضره",
        "محاضرات",
        "حل تمارين",
        "حلول التمارين",
        "حل اسئله",
        "حل الاسئله",
    ]):
        return "شروحات وحلول"

    # الملخصات والمراجعات
    if contains_any(text, [
        "ملخص",
        "مراجعه",
        "مراجعة",
        "مركزه",
        "مركزة",
        "ليله الامتحان",
        "ليلة الامتحان",
    ]):
        return "ملخصات ومراجعات"

    return ""


def detect_year(text):
    value = str(text or "")

    # معالجة السنة الدراسية مثل 2025/2026
    match = re.search(r"(20\d{2})\s*[/\-]\s*(20\d{2})", value)
    if match:
        return match.group(2)

    match = re.search(r"(20\d{2})", value)
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


def get_published_year(pub_date):
    try:
        date = parsedate_to_datetime(pub_date)
        return str(date.year)
    except Exception:
        return ""


def search_news(subject, keyword, search_group):
    aliases = SUBJECTS[subject]
    subject_query = " OR ".join(f'"{name}"' for name in aliases[:3])

    query = (
        f'"الثالث متوسط" العراق '
        f'({subject_query}) "{keyword}"'
    )

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

            if actual_subject != subject:
                continue

            detected_type = detect_type(title)

            # لا نعتمد على كلمة البحث وحدها لتصنيف النتيجة
            if not detected_type:
                continue

            title_year = detect_year(title)
            published_year = get_published_year(pub_date)

            year = title_year or published_year

            items.append({
                "subject": actual_subject,
                "title": title,
                "source": source,
                "url": link,
                "published_at": pub_date,
                "keyword": keyword,
                "content_type": detected_type,
                "search_group": search_group,
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

        for search_group, keywords in SEARCH_TYPES.items():
            for keyword in keywords:
                print(f"  - {search_group}: {keyword}")

                found = search_news(subject, keyword, search_group)

                for result in found:
                    if result["url"] not in seen_urls:
                        seen_urls.add(result["url"])
                        results.append(result)

                time.sleep(1)

    # الأحدث أولاً داخل كل تصنيف، مع الاحتفاظ بكل السنوات
    results.sort(
        key=lambda item: (
            item["content_type"] != "مرشحات",
            not item["is_current_year"],
            item["year"],
            item["published_at"],
        ),
        reverse=True,
    )

    now = datetime.now().astimezone().isoformat(timespec="seconds")

    data = {
        "updated_at": now,
        "results": results,
        "subjects": list(SUBJECTS.keys()),
        "content_types": CONTENT_TYPES,
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
