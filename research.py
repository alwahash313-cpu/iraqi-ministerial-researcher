
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path


# ==================================================
# إعدادات المشروع
# ==================================================

CURRENT_YEAR = datetime.now().year

BASE_DIR = Path(__file__).resolve().parent
REPORT_DIR = BASE_DIR / "reports"

REPORT_JSON = REPORT_DIR / "latest.json"
REPORT_MD = REPORT_DIR / "latest.md"

RSS_URL = "https://news.google.com/rss/search"

USER_AGENT = (
    "Mozilla/5.0 "
    "(compatible; IraqiMinisterialResearcher/2.0)"
)

REQUEST_TIMEOUT = 25
REQUEST_DELAY = 0.5


# ==================================================
# المواد الدراسية
# ==================================================

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


# ==================================================
# أنواع المحتوى
# ==================================================

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


CONTENT_TYPES = [
    "مرشحات",
    "أسئلة وزارية سابقة",
    "ملخصات ومراجعات",
    "شروحات وحلول",
]


# ==================================================
# استبعاد الدول والمناهج الأجنبية
# ==================================================

FOREIGN_INDICATORS = [
    "مصر",
    "المصري",
    "المصرية",
    "وزارة التربية والتعليم المصرية",
    "الثالثة الاعدادية",
    "الثالث الاعدادي",
    "ثالثة اعدادي",
    "تالتة اعدادي",
    "الصف التاسع",
    "التاسع سوريا",
    "التاسع لبنان",
    "البكالوريا السورية",
    "التوجيهي",
    "الأردن",
    "الاردن",
    "السعودية",
    "السعودي",
    "الكويت",
    "الإمارات",
    "الامارات",
    "قطر",
    "البحرين",
    "عمان",
    "المغرب",
    "الجزائر",
    "تونس",
    "ليبيا",
    "السودان",
    "اليمن",
    "المنهج المصري",
    "المنهج السوري",
    "المنهج الأردني",
    "المنهج السعودي",
    "المنهج الكويتي",
]


# ==================================================
# كلمات الأخبار المستبعدة
# ==================================================

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
    "التقديم للمدارس",
]


EDUCATION_WORDS = [
    "وزاري",
    "وزارية",
    "الثالث متوسط",
    "ثالث متوسط",
    "الثالث المتوسط",
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


# ==================================================
# معالجة النصوص والأرقام
# ==================================================

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
        "٠": "0",
        "١": "1",
        "٢": "2",
        "٣": "3",
        "٤": "4",
        "٥": "5",
        "٦": "6",
        "٧": "7",
        "٨": "8",
        "٩": "9",
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


# ==================================================
# تحديد الصف الدراسي العراقي
# ==================================================

def has_iraqi_grade(text):
    normalized_text = normalize(text)

    grade_patterns = [
        r"الثالث\s+متوسط",
        r"ثالث\s+متوسط",
        r"الثالث\s+المتوسط",
        r"الثالث\s+المتوسط\s+العراقي",
    ]

    return any(
        re.search(pattern, normalized_text)
        for pattern in grade_patterns
    )


def is_foreign_content(title, source=""):
    text = normalize(title + " " + source)

    return contains_any(text, FOREIGN_INDICATORS)


def is_iraqi_content(title, source=""):
    combined_text = title + " " + source

    if is_foreign_content(title, source):
        return False

    # لا نقبل المحتوى الذي لا يذكر صف الثالث متوسط العراقي
    if not has_iraqi_grade(combined_text):
        return False

    # عبارة الثالث متوسط مستخدمة في تسمية الصف العراقي.
    # نستخدمها مع استبعاد مؤشرات الدول والمناهج الأجنبية.
    return True


# ==================================================
# تحديد المادة
# ==================================================

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

    matches.sort(
        key=lambda item: item[1],
        reverse=True
    )

    return matches[0][0]


# ==================================================
# استبعاد الأخبار
# ==================================================

def is_excluded_news(title):
    return contains_any(title, EXCLUDED_PHRASES)


# ==================================================
# تحديد نوع المحتوى
# ==================================================

def detect_type(title, search_group):
    if is_excluded_news(title):
        return None

    text = normalize(title)

    prediction_words = [
        "مرشحات",
        "مرشحه",
        "مرشحين",
        "توقعات الامتحان",
        "توقعات وزاري",
        "اسئله متوقعه",
    ]

    if contains_any(text, prediction_words):
        return "مرشحات"

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

    if contains_any(text, previous_question_words):
        return "أسئلة وزارية سابقة"

    summary_words = [
        "ملخص",
        "ملخصات",
        "مراجعه مركزه",
        "مراجعه",
        "مراجعة ليلة الامتحان",
        "مراجعه نهائيه",
    ]

    if contains_any(text, summary_words):
        return "ملخصات ومراجعات"

    explanation_words = [
        "شرح",
        "حلول",
        "حل تمارين",
        "حل اسئله",
        "اجوبه",
        "حل الكتاب",
    ]

    if contains_any(text, explanation_words):
        return "شروحات وحلول"

    return None


# ==================================================
# استخراج السنة الدراسية
# ==================================================

def detect_year(title):
    text = normalize(title)

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

    years = re.findall(r"20\d{2}", text)

    if years:
        return years[0]

    return None


# ==================================================
# تحديد الدور الامتحاني
# ==================================================

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


# ==================================================
# التحقق من صلة النتيجة
# ==================================================

def is_relevant(title, subject, source=""):
    if not title or not subject:
        return False

    if is_excluded_news(title):
        return False

    if not is_iraqi_content(title, source):
        return False

    detected = detect_subject(title)

    # إذا ظهرت مادة مختلفة نرفض النتيجة
    if detected and detected != subject:
        return False

    text = normalize(title)

    has_subject = any(
        normalize(alias) in text
        for alias in SUBJECTS[subject]
    )

    has_education_topic = contains_any(
        text,
        EDUCATION_WORDS
    )

    return has_subject and has_education_topic


# ==================================================
# قراءة تاريخ النشر
# ==================================================

def parse_published_date(value):
    if not value:
        return None

    try:
        date = parsedate_to_datetime(value)

        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        return date.astimezone(timezone.utc).isoformat()

    except Exception:
        try:
            date = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )

            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)

            return date.astimezone(timezone.utc).isoformat()

        except Exception:
            return None


# ==================================================
# جلب بيانات XML
# ==================================================

def fetch_xml(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=REQUEST_TIMEOUT
    ) as response:
        return response.read()


# ==================================================
# البحث في Google News والمواقع
# ==================================================

def search_news(query):
    params = {
        "q": query,
        "hl": "ar",
        "gl": "IQ",
        "ceid": "IQ:ar",
    }

    url = RSS_URL + "?" + urllib.parse.urlencode(params)

    try:
        xml_data = fetch_xml(url)

        root = ET.fromstring(xml_data)

        items = root.findall(".//item")

        results = []

        for item in items:
            title = item.findtext(
                "title",
                ""
            ).strip()

            link = item.findtext(
                "link",
                ""
            ).strip()

            pub_date = item.findtext(
                "pubDate",
                ""
            ).strip()

            source_element = item.find("source")

            source = ""
            source_url = ""

            if source_element is not None:
                source = (
                    source_element.text or ""
                ).strip()

                source_url = (
                    source_element.attrib.get("url", "")
                ).strip()

            if not title or not link:
                continue

            results.append({
                "title": title,
                "url": link,
                "source": source or "Google News",
                "source_url": source_url,
                "published_at": parse_published_date(
                    pub_date
                ),
            })

        return results

    except Exception as error:
        print(f"Web search error: {error}")
        return []


# ==================================================
# البحث في YouTube
# ==================================================

def search_youtube(query):
    params = {
        "search_query": query,
    }

    url = (
        "https://www.youtube.com/feeds/videos.xml?"
        + urllib.parse.urlencode(params)
    )

    try:
        xml_data = fetch_xml(url)

        root = ET.fromstring(xml_data)

        namespace = {
            "atom": "http://www.w3.org/2005/Atom"
        }

        results = []

        for entry in root.findall(
            "atom:entry",
            namespace
        ):
            title = entry.findtext(
                "atom:title",
                "",
                namespace
            ).strip()

            link_element = entry.find(
                "atom:link",
                namespace
            )

            video_url = ""

            if link_element is not None:
                video_url = link_element.attrib.get(
                    "href",
                    ""
                )

            published = entry.findtext(
                "atom:published",
                "",
                namespace
            )

            author = entry.findtext(
                "atom:author/atom:name",
                "YouTube",
                namespace
            )

            if title and video_url:
                results.append({
                    "title": title,
                    "url": video_url,
                    "source": author,
                    "source_url": "https://www.youtube.com",
                    "published_at": parse_published_date(
                        published
                    ),
                })

        return results

    except Exception as error:
        print(f"YouTube search error: {error}")
        return []


# ==================================================
# تحديد المنصة من المصدر الحقيقي
# ==================================================

def detect_platform(item):
    url = str(item.get("url", "")).lower()

    source_url = str(
        item.get("source_url", "")
    ).lower()

    source = normalize(
        item.get("source", "")
    )

    combined = url + " " + source_url + " " + source

    if (
        "youtube.com" in combined
        or "youtu.be" in combined
    ):
        return "YouTube"

    if (
        "t.me" in combined
        or "telegram.me" in combined
        or "telegram" in source
    ):
        return "Telegram"

    return "Web"


# ==================================================
# البحث حسب المادة ونوع المحتوى والمنصة
# ==================================================

def collect_results():
    all_results = []
    seen_urls = set()

    for subject in SUBJECTS:
        print(f"\nSearching subject: {subject}")

        for search_group, keywords in SEARCH_TYPES.items():
            for keyword in keywords:

                base_query = (
                    f'"الثالث متوسط" '
                    f'"{subject}" '
                    f'"{keyword}" '
                    f'العراق'
                )

                searches = [
                    (
                        "Web",
                        search_news,
                        base_query,
                    ),
                    (
                        "Telegram",
                        search_news,
                        base_query + " site:t.me",
                    ),
                    (
                        "Telegram",
                        search_news,
                        base_query + " site:telegram.me",
                    ),
                    (
                        "YouTube",
                        search_youtube,
                        base_query,
                    ),
                ]

                for requested_platform, search_function, query in searches:
                    print(
                        f"  {requested_platform}: {query}"
                    )

                    found_items = search_function(query)

                    for item in found_items:
                        title = item["title"]
                        url = item["url"]
                        source = item.get("source", "")

                        if not url or url in seen_urls:
                            continue

                        if not is_relevant(
                            title,
                            subject,
                            source
                        ):
                            continue

                        content_type = detect_type(
                            title,
                            search_group
                        )

                        if not content_type:
                            continue

                        detected_subject = detect_subject(title)

                        if (
                            detected_subject
                            and detected_subject != subject
                        ):
                            continue

                        platform = detect_platform(item)

                        # لا ننسب نتيجة إلى Telegram
                        # إلا إذا دل المصدر الحقيقي عليه
                        if (
                            requested_platform == "Telegram"
                            and platform != "Telegram"
                        ):
                            continue

                        # بحث YouTube يجب أن ينتج رابط فيديو
                        if (
                            requested_platform == "YouTube"
                            and platform != "YouTube"
                        ):
                            continue

                        seen_urls.add(url)

                        year = detect_year(title)

                        result = {
                            "subject": subject,
                            "title": title,
                            "source": source,
                            "platform": platform,
                            "url": url,
                            "published_at": item.get(
                                "published_at"
                            ),
                            "keyword": keyword,
                            "content_type": content_type,
                            "search_group": search_group,
                            "year": year,
                            "exam_round": detect_exam_round(
                                title
                            ),
                            "is_current_year": (
                                year == str(CURRENT_YEAR)
                                if year and "/" not in year
                                else False
                            ),
                        }

                        all_results.append(result)

                    time.sleep(REQUEST_DELAY)

    return all_results


# ==================================================
# حفظ JSON
# ==================================================

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

        "country": "العراق",

        "grade": "الثالث المتوسط العراقي",

        "subjects": list(SUBJECTS.keys()),

        "content_types": CONTENT_TYPES,

        "platforms": [
            "YouTube",
            "Telegram",
            "Web",
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


# ==================================================
# حفظ تقرير Markdown
# ==================================================

def save_markdown(results):
    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    lines = [
        "# الباحث الوزاري العراقي",
        "",
        "- الدولة: العراق",
        "- الصف: الثالث المتوسط",
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
                "لا توجد نتائج عراقية مطابقة حالياً.",
                "",
            ])
            continue

        for item in subject_results:
            lines.extend([
                f"### {item['title']}",
                "",
                f"- النوع: {item['content_type']}",
                f"- المنصة: {item['platform']}",
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


# ==================================================
# تشغيل البحث
# ==================================================

def main():
    print("=" * 50)
    print("الباحث الوزاري العراقي")
    print("البحث مخصص للثالث المتوسط العراقي فقط")
    print("=" * 50)

    results = collect_results()

    results.sort(
        key=lambda item: (
            item["subject"],
            item["content_type"],
            item["year"] or "",
        )
    )

    save_json(results)
    save_markdown(results)

    print("\n" + "=" * 50)
    print(f"Total Iraqi results: {len(results)}")
    print(f"JSON saved: {REPORT_JSON}")
    print(f"Markdown saved: {REPORT_MD}")
    print("=" * 50)


if __name__ == "__main__":
    main()
