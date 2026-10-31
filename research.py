
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path


# ==========================================
# إعدادات المشروع
# ==========================================

CURRENT_YEAR = datetime.now().year
BASE_DIR = Path(__file__).resolve().parent
REPORT_DIR = BASE_DIR / "reports"

REPORT_JSON = REPORT_DIR / "latest.json"
REPORT_MD = REPORT_DIR / "latest.md"

RSS_URL = "https://news.google.com/rss/search"

SUBJECTS = {
    "اللغة العربية": [
        "اللغة العربية",
        "عربي",
        "قواعد اللغة العربية",
        "الأدب العربي",
    ],
    "اللغة الإنجليزية": [
        "اللغة الإنجليزية",
        "اللغة الانكليزية",
        "اللغة الإنكليزية",
        "الانكليزي",
        "الإنجليزي",
        "انكليزي",
        "إنكليزي",
        "English",
    ],
    "الرياضيات": [
        "الرياضيات",
        "رياضيات",
        "الجبر",
        "الهندسة",
    ],
    "الكيمياء": [
        "الكيمياء",
        "كيمياء",
    ],
    "الفيزياء": [
        "الفيزياء",
        "فيزياء",
    ],
    "الأحياء": [
        "الأحياء",
        "احياء",
        "علم الأحياء",
        "علم الحياة",
    ],
    "الاجتماعيات": [
        "الاجتماعيات",
        "اجتماعيات",
        "التاريخ",
        "الجغرافية",
        "الجغرافيا",
        "الوطنية",
    ],
    "التربية الإسلامية": [
        "التربية الإسلامية",
        "التربية الاسلامية",
        "اسلامية",
        "إسلامية",
    ],
}


SEARCH_TYPES = {
    "مرشحات حديثة": [
        "مرشحات وزاري",
        "مرشحات الثالث متوسط",
        "توقعات امتحان وزاري",
    ],
    "أسئلة وزارية سابقة": [
        "اسئلة وزارية الثالث متوسط",
        "اسئلة امتحانات وزارية مع الحل",
        "اسئلة وزارية الدور الاول والثاني",
        "اسئلة تمهيدي وزاري",
    ],
    "ملخصات ومراجعات": [
        "ملخص الثالث متوسط",
        "مراجعة مركزة الثالث متوسط",
        "مراجعة ليلة الامتحان",
    ],
    "شروحات وحلول": [
        "شرح وحل تمارين الثالث متوسط",
        "حلول اسئلة الثالث متوسط",
        "حلول الكتاب الثالث متوسط",
    ],
}


# كلمات الأخبار التي لا نريد تصنيفها كمواد دراسية
EXCLUDED_PHRASES = [
    "جدول الامتحانات",
    "جدول امتحانات",
    "جدول الدور الاول",
    "جدول الدور الثاني",
    "موعد الامتحانات",
    "موعد الامتحان",
    "نتائج الثالث",
    "نتائج الامتحانات",
    "اعتراضات",
    "فتح باب الاعتراض",
    "الوقت المتبقي",
    "العد التنازلي",
    "كم يوم متبقي",
    "عطلة رسمية",
    "تعطيل الدوام",
    "وزارة التربية تعلن",
    "التقديم للمدارس",
]


EDUCATION_WORDS = [
    "وزاري",
    "وزارية",
    "الثالث متوسط",
    "ثالث متوسط",
    "ملخص",
    "مراجعة",
    "مرشحات",
    "اسئلة",
    "أسئلة",
    "حلول",
    "شرح",
    "تمارين",
    "امتحان",
    "امتحانات",
    "منهج",
    "كتاب",
    "فصل",
    "موضوع",
]


# ==========================================
# معالجة النصوص
# ==========================================

def normalize(text):
    text = str(text or "").lower()

    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ة": "ه",
        "ى": "ي",
        "ؤ": "و",
        "ئ": "ي",
        "ـ": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def contains_any(text, words):
    normalized_text = normalize(text)

    return any(
        normalize(word) in normalized_text
        for word in words
    )


# ==========================================
# تحديد المادة
# ==========================================

def detect_subject(title):
    normalized_title = normalize(title)

    matches = []

    for subject, aliases in SUBJECTS.items():
        for alias in aliases:
            normalized_alias = normalize(alias)

            if normalized_alias in normalized_title:
                matches.append(
                    (subject, len(normalized_alias))
                )

    if not matches:
        return None

    matches.sort(key=lambda item: item[1], reverse=True)
    return matches[0][0]


# ==========================================
# تحديد نوع المحتوى
# ==========================================

def is_excluded_news(title):
    return contains_any(title, EXCLUDED_PHRASES)


def detect_type(title, search_group):
    normalized_title = normalize(title)

    # لا نصنف جداول الامتحانات والأخبار كأسئلة وزارية
    if is_excluded_news(title):
        return None

    # المرشحات
    prediction_words = [
        "مرشحات",
        "مرشحه",
        "مرشحين",
        "توقعات الامتحان",
        "توقعات وزاري",
        "اسئله متوقعه",
    ]

    if contains_any(normalized_title, prediction_words):
        return "مرشحات"

    # الأسئلة الوزارية السابقة
    previous_question_words = [
        "اسئله وزاريه",
        "اسئله وزاري",
        "الاسئله الوزاريه",
        "حل اسئله وزاريه",
        "اسئلة دور",
        "اسئلة تمهيدي",
        "اسئلة امتحان وزاري",
        "دفتر الاسئلة الوزارية",
    ]

    if contains_any(normalized_title, previous_question_words):
        return "أسئلة وزارية سابقة"

    # الملخصات والمراجعات
    summary_words = [
        "ملخص",
        "ملخصات",
        "مراجعه مركزه",
        "مراجعه",
        "مراجعة ليلة الامتحان",
        "مراجعه نهائيه",
    ]

    if contains_any(normalized_title, summary_words):
        return "ملخصات ومراجعات"

    # الشروحات والحلول
    explanation_words = [
        "شرح",
        "حلول",
        "حل تمارين",
        "حل اسئله",
        "اجوبه",
        "حل الكتاب",
    ]

    if contains_any(normalized_title, explanation_words):
        return "شروحات وحلول"

    # إذا لم نستطع التأكد، لا نخمن نوع المحتوى
    return None


# ==========================================
# استخراج السنة الدراسية
# ==========================================

def detect_year(title):
    text = normalize(title)

    # السنة الدراسية الكاملة مثل 2025/2026
    academic_year = re.search(
        r"(20\d{2})\s*[/\-]\s*(20\d{2})",
        text
    )

    if academic_year:
        return (
            academic_year.group(1)
            + "/"
            + academic_year.group(2)
        )

    # سنة منفردة
    years = re.findall(r"20\d{2}", text)

    if years:
        return years[0]

    return None


# ==========================================
# تحديد الدور الامتحاني
# ==========================================

def detect_exam_round(title):
    text = normalize(title)

    round_patterns = [
        (r"الدور\s*الاول", "الدور الأول"),
        (r"الدور\s*الثاني", "الدور الثاني"),
        (r"الدور\s*الثالث", "الدور الثالث"),
        (r"التمهيدي", "التمهيدي"),
        (r"الخارجي", "التمهيدي"),
    ]

    for pattern, label in round_patterns:
        if re.search(pattern, text):
            return label

    return None


# ==========================================
# التحقق من صلة النتيجة بالدراسة
# ==========================================

def is_relevant(title, subject, keyword):
    if not title or not subject:
        return False

    if is_excluded_news(title):
        return False

    detected = detect_subject(title)

    # لا نقبل نتيجة تنتمي إلى مادة أخرى
    if detected and detected != subject:
        return False

    text = normalize(title)

    has_subject = any(
        normalize(alias) in text
        for alias in SUBJECTS[subject]
    )

    has_school_level = contains_any(
        text,
        [
            "الثالث متوسط",
            "ثالث متوسط",
            "الثالث المتوسط",
            "الثالث المتوسط العراقي",
        ]
    )

    has_education_topic = contains_any(
        text,
        EDUCATION_WORDS
    )

    # البحث نفسه مخصص للثالث المتوسط.
    # نقبل عنوان المادة إذا كان واضحاً أنه محتوى دراسي.
    if has_subject and has_education_topic:
        return True

    if has_school_level and has_education_topic:
        return True

    return False


# ==========================================
# قراءة تاريخ النشر
# ==========================================

def parse_published_date(value):
    if not value:
        return None

    try:
        date = parsedate_to_datetime(value)

        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        return date.astimezone(timezone.utc).isoformat()

    except Exception:
        return None


# ==========================================
# البحث في Google News RSS
# ==========================================

def search_news(query):
    params = {
        "q": query,
        "hl": "ar",
        "gl": "IQ",
        "ceid": "IQ:ar",
    }

    url = RSS_URL + "?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(compatible; IraqiMinisterialResearcher/1.0)"
            )
        }
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=25
        ) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)
        items = root.findall(".//item")

        results = []

        for item in items:
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            pub_date = item.findtext("pubDate", "").strip()

            source_element = item.find("source")

            source = ""

            if source_element is not None:
                source = (source_element.text or "").strip()

            if not title or not link:
                continue

            results.append({
                "title": title,
                "url": link,
                "source": source or "Google News",
                "published_at": parse_published_date(pub_date),
            })

        return results

    except Exception as error:
        print(f"Search error: {error}")
        return []


# ==========================================
# تجهيز النتائج
# ==========================================

def collect_results():
    all_results = []
    seen_urls = set()

    for subject, aliases in SUBJECTS.items():
        print(f"\nSearching: {subject}")

        for search_group, keywords in SEARCH_TYPES.items():
            for keyword in keywords:

                # نستخدم اسم المادة مع عبارة البحث
                subject_name = subject

                query = (
                    f'"الثالث متوسط" '
                    f'"{subject_name}" '
                    f'"{keyword}"'
                )

                print(f"  Query: {query}")

                found_items = search_news(query)

                for item in found_items:
                    title = item["title"]
                    url = item["url"]

                    if url in seen_urls:
                        continue

                    if not is_relevant(
                        title,
                        subject,
                        keyword
                    ):
                        continue

                    content_type = detect_type(
                        title,
                        search_group
                    )

                    if not content_type:
                        continue

                    detected_subject = detect_subject(title)

                    if detected_subject and detected_subject != subject:
                        continue

                    seen_urls.add(url)

                    year = detect_year(title)

                    result = {
                        "subject": subject,
                        "title": title,
                        "source": item["source"],
                        "url": url,
                        "published_at": item["published_at"],
                        "keyword": keyword,
                        "content_type": content_type,
                        "search_group": search_group,
                        "year": year,
                        "exam_round": detect_exam_round(title),
                        "is_current_year": (
                            year == str(CURRENT_YEAR)
                            if year and "/" not in year
                            else False
                        ),
                    }

                    all_results.append(result)

                # مهلة بسيطة بين طلبات البحث
                time.sleep(1)

    return all_results


# ==========================================
# حفظ JSON
# ==========================================

def save_json(results):
    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    report = {
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "current_year": CURRENT_YEAR,

        "subjects": list(SUBJECTS.keys()),

        "content_types": [
            "مرشحات",
            "أسئلة وزارية سابقة",
            "ملخصات ومراجعات",
            "شروحات وحلول",
        ],

        "total": len(results),

        "results": results,
    }

    REPORT_JSON.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


# ==========================================
# حفظ تقرير Markdown
# ==========================================

def save_markdown(results):
    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    lines = [
        "# الباحث الوزاري العراقي",
        "",
        f"تاريخ التحديث: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"عدد النتائج: {len(results)}",
        "",
    ]

    for subject in SUBJECTS:
        subject_results = [
            item for item in results
            if item["subject"] == subject
        ]

        lines.extend([
            f"## {subject}",
            "",
        ])

        if not subject_results:
            lines.extend([
                "لا توجد نتائج مطابقة حالياً.",
                "",
            ])
            continue

        for item in subject_results:
            lines.extend([
                f"### {item['title']}",
                "",
                f"- النوع: {item['content_type']}",
                f"- المصدر: {item['source']}",
                f"- السنة: {item['year'] or 'غير محددة'}",
                f"- الدور: {item['exam_round'] or 'غير محدد'}",
                f"- تاريخ النشر: {item['published_at'] or 'غير محدد'}",
                f"- الرابط: {item['url']}",
                "",
            ])

    REPORT_MD.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )


# ==========================================
# تشغيل البحث
# ==========================================

def main():
    print("=" * 45)
    print("الباحث الوزاري العراقي")
    print("=" * 45)

    results = collect_results()

    # ترتيب النتائج حسب المادة ثم النوع
    results.sort(
        key=lambda item: (
            item["subject"],
            item["content_type"],
            item["year"] or "",
        ),
        reverse=False
    )

    save_json(results)
    save_markdown(results)

    print("\n" + "=" * 45)
    print(f"Total results: {len(results)}")
    print(f"JSON saved: {REPORT_JSON}")
    print(f"Markdown saved: {REPORT_MD}")
    print("=" * 45)


if __name__ == "__main__":
    main()
