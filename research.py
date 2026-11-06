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
    "(compatible; IraqiMinisterialResearcher/3.0)"
)

TIMEOUT = 25
DELAY = 0.5


# ==================================================
# المواد الدراسية
# ==================================================

SUBJECTS = {
    "اللغة العربية": [
        "اللغة العربية",
        "عربي",
        "قواعد",
        "أدب",
        "إنشاء",
    ],

    "اللغة الإنجليزية": [
        "اللغة الإنجليزية",
        "انكليزي",
        "إنكليزي",
        "English",
    ],

    "الرياضيات": [
        "الرياضيات",
        "رياضيات",
        "جبر",
        "هندسة",
    ],

    "الكيمياء": [
        "الكيمياء",
        "كيمياء",
        "مسائل الكيمياء",
    ],

    "الفيزياء": [
        "الفيزياء",
        "فيزياء",
    ],

    "الأحياء": [
        "الأحياء",
        "احياء",
        "أحياء",
        "علوم",
    ],

    "الاجتماعيات": [
        "الاجتماعيات",
        "اجتماعيات",
        "تاريخ",
        "جغرافية",
        "وطنية",
    ],

    "التربية الإسلامية": [
        "التربية الإسلامية",
        "اسلامية",
        "إسلامية",
        "قرآن",
    ],
}


# ==================================================
# أنواع المحتوى
# ==================================================

SEARCH_TYPES = {
    "مرشحات": [
        "مرشحات الثالث متوسط",
        "مرشحات الثالث المتوسط الوزارية",
        "توقعات الثالث متوسط",
    ],

    "أسئلة وزارية": [
        "أسئلة وزارية الثالث متوسط",
        "اسئلة الثالث المتوسط مع الحل",
        "أسئلة امتحانات الثالث متوسط",
    ],

    "ملخصات ومراجعة": [
        "ملخص الثالث متوسط",
        "مراجعة الثالث المتوسط",
        "ملزمة الثالث متوسط",
    ],

    "شرح وحلول": [
        "شرح الثالث متوسط",
        "حلول الثالث المتوسط",
        "حل تمارين الثالث متوسط",
    ],
}


CONTENT_TYPES = list(SEARCH_TYPES.keys())


# ==================================================
# كلمات الاستبعاد
# ==================================================

FOREIGN_INDICATORS = [
    "مصر",
    "المصري",
    "سوريا",
    "السوري",
    "لبنان",
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
]


EXCLUDED_PHRASES = [
    "جدول العطل",
    "العطلة الصيفية",
    "نتائج السادس",
    "نتائج الثالث الابتدائي",
    "نتائج القبول",
    "اعتراضات النتائج",
    "مواعيد الدوام",
    "التعيينات",
]


EXCLUDED_GRADES = [
    "السادس الابتدائي",
    "السادس الاعدادي",
    "السادس الإعدادي",
    "السادس العلمي",
    "السادس الادبي",
    "السادس الأدبي",
    "الثالث الابتدائي",
    "الثالث الإعدادي",
    "الثالث الاعدادي",
    "الأول المتوسط",
    "الاول المتوسط",
    "الثاني المتوسط",
    "الرابع العلمي",
    "الخامس العلمي",
]


EDUCATION_WORDS = [
    "الثالث المتوسط",
    "الثالث متوسط",
    "ثالث متوسط",
    "ثالث المتوسط",
    "طلاب الثالث",
    "طلبة الثالث",
    "وزارة التربية العراقية",
    "المنهج العراقي",
    "العراق",
    "العراقي",
]


# ==================================================
# توحيد النصوص العربية
# ==================================================

def normalize(text):
    text = str(text or "").lower()

    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ى": "ي",
        "ة": "ه",
        "ؤ": "و",
        "ئ": "ي",
        "ـ": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    arabic_numbers = {
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

    for old, new in arabic_numbers.items():
        text = text.replace(old, new)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ==================================================
# التحقق من الصف الدراسي
# ==================================================

def has_iraqi_grade(text):
    text = normalize(text)

    patterns = [
        r"الثالث\s+متوسط",
        r"الثالث\s+المتوسط",
        r"ثالث\s+متوسط",
        r"ثالث\s+المتوسط",
        r"طلاب\s+الثالث",
        r"طلبة\s+الثالث",
        r"الثالث\s+متوسط\s+العراقي",
    ]

    return any(
        re.search(pattern, text)
        for pattern in patterns
    )


def is_foreign_content(text):
    text = normalize(text)

    return any(
        normalize(word) in text
        for word in FOREIGN_INDICATORS
    )


def is_iraqi_content(text):
    text = normalize(text)

    if not has_iraqi_grade(text):
        return False

    if is_foreign_content(text):
        return False

    for grade in EXCLUDED_GRADES:
        if normalize(grade) in text:
            return False

    return True


# ==================================================
# تحديد المادة الدراسية
# ==================================================

def detect_subject(text):
    text = normalize(text)

    for subject, keywords in SUBJECTS.items():
        for keyword in keywords:
            if normalize(keyword) in text:
                return subject

    return None


# ==================================================
# تحديد نوع المحتوى
# ==================================================

def detect_type(text):
    text = normalize(text)

    for content_type, keywords in SEARCH_TYPES.items():
        for keyword in keywords:
            if normalize(keyword) in text:
                return content_type

    return None


# ==================================================
# استبعاد الأخبار غير التعليمية
# ==================================================

def is_excluded_news(text):
    text = normalize(text)

    for phrase in EXCLUDED_PHRASES:
        if normalize(phrase) in text:
            return True

    return False


# ==================================================
# تحديد السنة الدراسية
# ==================================================

def detect_year(text):
    text = normalize(text)

    years = re.findall(
        r"20[0-9]{2}",
        text
    )

    if years:
        return years[-1]

    return None


# ==================================================
# تحديد الدور الامتحاني
# ==================================================

def detect_exam_round(text):
    text = normalize(text)

    if "الدور الاول" in text:
        return "الدور الأول"

    if "الدور الثاني" in text:
        return "الدور الثاني"

    if "الدور الثالث" in text:
        return "الدور الثالث"

    if "تمهيدي" in text:
        return "التمهيدي"

    return None


# ==================================================
# التحقق من ملاءمة النتيجة
# ==================================================

def is_relevant(title, description=""):
    text = normalize(
        str(title) + " " + str(description)
    )

    if not is_iraqi_content(text):
        return False

    if is_excluded_news(text):
        return False

    subject = detect_subject(text)

    if not subject:
        return False

    content_type = detect_type(text)

    if not content_type:
        return False

    return True


# ==================================================
# تاريخ النشر
# ==================================================

def parse_published_date(value):
    if not value:
        return None

    try:
        date = parsedate_to_datetime(value)

        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        return date.isoformat()

    except Exception:
        return None


# ==================================================
# جلب بيانات RSS
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
        timeout=TIMEOUT
    ) as response:

        return response.read()


# ==================================================
# البحث في Google News
# ==================================================

def search_news(query):
    results = []

    params = {
        "q": query,
        "hl": "ar",
        "gl": "IQ",
        "ceid": "IQ:ar",
    }

    url = (
        RSS_URL
        + "?"
        + urllib.parse.urlencode(params)
    )

    try:
        xml_data = fetch_xml(url)

        root = ET.fromstring(xml_data)

        for item in root.findall(".//item"):

            title = item.findtext("title", "")
            link = item.findtext("link", "")
            description = item.findtext(
                "description",
                ""
            )

            source = item.findtext(
                "source",
                "Google News"
            )

            published = item.findtext(
                "pubDate",
                ""
            )

            if not title or not link:
                continue

            results.append({
                "title": title.strip(),
                "url": link.strip(),
                "description": description.strip(),
                "source": source.strip(),
                "published_at": parse_published_date(
                    published
                ),
            })

    except Exception as error:
        print(
            f"News search error: {error}"
        )

    return results


# ==================================================
# البحث عن يوتيوب وتلغرام عبر الأخبار المفهرسة
# ==================================================

def search_platform(query, platform):
    if platform == "YouTube":
        search_query = (
            query + " site:youtube.com"
        )

    elif platform == "Telegram":
        search_query = (
            query + " site:t.me OR site:telegram.me"
        )

    else:
        search_query = query

    return search_news(search_query)


# ==================================================
# تحديد المنصة
# ==================================================

def detect_platform(item):
    url = normalize(item.get("url", ""))
    source = normalize(item.get("source", ""))
    title = normalize(item.get("title", ""))

    if "youtube.com" in url or "youtu.be" in url:
        return "YouTube"

    if "youtube" in source or "youtube" in title:
        return "YouTube"

    if "t.me" in url or "telegram.me" in url:
        return "Telegram"

    if "telegram" in source:
        return "Telegram"

    return "Web"


# ==================================================
# جمع النتائج
# ==================================================

def collect_results():
    collected = []
    seen = set()

    for subject, subject_keywords in SUBJECTS.items():

        print(f"\nSearching: {subject}")

        for content_type, search_keywords in SEARCH_TYPES.items():

            for subject_keyword in subject_keywords:

                for search_keyword in search_keywords:

                    query = (
                        f'"الثالث المتوسط" '
                        f'"{subject_keyword}" '
                        f'"{search_keyword}" '
                        f'العراق'
                    )

                    print(
                        f"Searching: {query}"
                    )

                    search_results = search_news(
                        query
                    )

                    for item in search_results:

                        title = item.get(
                            "title",
                            ""
                        )

                        description = item.get(
                            "description",
                            ""
                        )

                        combined_text = (
                            title + " " + description
                        )

                        if not is_relevant(
                            title,
                            description
                        ):
                            continue

                        detected_subject = detect_subject(
                            combined_text
                        )

                        detected_type = detect_type(
                            combined_text
                        )

                        # عدم قبول نتيجة من مادة مختلفة
                        if detected_subject != subject:
                            continue

                        if detected_type != content_type:
                            continue

                        url = item.get("url", "").strip()

                        if url in seen:
                            continue

                        seen.add(url)

                        year = detect_year(
                            combined_text
                        )

                        result = {
                            "subject": subject,
                            "title": title,
                            "source": item.get(
                                "source",
                                "Google News"
                            ),
                            "platform": detect_platform(
                                item
                            ),
                            "url": url,
                            "published_at": item.get(
                                "published_at"
                            ),
                            "keyword": search_keyword,
                            "content_type": content_type,
                            "search_group": content_type,
                            "year": year,
                            "exam_round": detect_exam_round(
                                combined_text
                            ),
                            "is_current_year": (
                                year == str(CURRENT_YEAR)
                                if year else False
                            ),
                        }

                        collected.append(result)

                    time.sleep(DELAY)

            # البحث عن نتائج يوتيوب
            for subject_keyword in subject_keywords:

                query = (
                    f'"الثالث المتوسط" '
                    f'"{subject_keyword}" '
                    f'"{content_type}" العراق'
                )

                youtube_results = search_platform(
                    query,
                    "YouTube"
                )

                for item in youtube_results:

                    title = item.get("title", "")
                    description = item.get(
                        "description",
                        ""
                    )

                    if not is_relevant(
                        title,
                        description
                    ):
                        continue

                    combined_text = (
                        title + " " + description
                    )

                    if detect_subject(
                        combined_text
                    ) != subject:
                        continue

                    if detect_type(
                        combined_text
                    ) != content_type:
                        continue

                    url = item.get("url", "").strip()

                    if not url or url in seen:
                        continue

                    seen.add(url)

                    year = detect_year(
                        combined_text
                    )

                    collected.append({
                        "subject": subject,
                        "title": title,
                        "source": item.get(
                            "source",
                            "YouTube"
                        ),
                        "platform": "YouTube",
                        "url": url,
                        "published_at": item.get(
                            "published_at"
                        ),
                        "keyword": content_type,
                        "content_type": content_type,
                        "search_group": content_type,
                        "year": year,
                        "exam_round": detect_exam_round(
                            combined_text
                        ),
                        "is_current_year": (
                            year == str(CURRENT_YEAR)
                            if year else False
                        ),
                    })

                time.sleep(DELAY)

            # البحث عن نتائج تلغرام العامة المفهرسة
            for subject_keyword in subject_keywords:

                query = (
                    f'"الثالث المتوسط" '
                    f'"{subject_keyword}" '
                    f'"{content_type}" العراق'
                )

                telegram_results = search_platform(
                    query,
                    "Telegram"
                )

                for item in telegram_results:

                    title = item.get("title", "")
                    description = item.get(
                        "description",
                        ""
                    )

                    if not is_relevant(
                        title,
                        description
                    ):
                        continue

                    combined_text = (
                        title + " " + description
                    )

                    if detect_subject(
                        combined_text
                    ) != subject:
                        continue

                    if detect_type(
                        combined_text
                    ) != content_type:
                        continue

                    url = item.get("url", "").strip()

                    if not url or url in seen:
                        continue

                    seen.add(url)

                    year = detect_year(
                        combined_text
                    )

                    collected.append({
                        "subject": subject,
                        "title": title,
                        "source": item.get(
                            "source",
                            "Telegram"
                        ),
                        "platform": "Telegram",
                        "url": url,
                        "published_at": item.get(
                            "published_at"
                        ),
                        "keyword": content_type,
                        "content_type": content_type,
                        "search_group": content_type,
                        "year": year,
                        "exam_round": detect_exam_round(
                            combined_text
                        ),
                        "is_current_year": (
                            year == str(CURRENT_YEAR)
                            if year else False
                        ),
                    })

                time.sleep(DELAY)

    return collected


# ==================================================
# الأرشيف التراكمي
# ==================================================

def load_previous_results():

    if not REPORT_JSON.exists():
        return []

    try:
        report = json.loads(
            REPORT_JSON.read_text(
                encoding="utf-8"
            )
        )

        results = report.get(
            "results",
            []
        )

        if isinstance(results, list):

            return [
                item
                for item in results
                if isinstance(item, dict)
            ]

    except Exception as error:
        print(
            f"Archive error: {error}"
        )

    return []


def merge_results(old_results, new_results):

    merged = []
    seen = set()

    for item in old_results + new_results:

        url = str(
            item.get("url", "")
        ).strip()

        title_key = (
            normalize(item.get("title", "")),
            item.get("subject", ""),
            item.get("content_type", ""),
        )

        if url:
            key = ("url", url)
        else:
            key = ("title", title_key)

        if key in seen:
            continue

        seen.add(key)
        merged.append(item)

    return merged


# ==================================================
# استرجاع نتيجة الكيمياء المحذوفة
# ==================================================

def restore_chemistry_result():

    return {
        "subject": "الكيمياء",

        "title": (
            "#مرشحات ليله الامتحان "
            "#مسائل الكيمياء "
            "#الفصل الاول "
            "#الثالث المتوسط - YouTube"
        ),

        "source": "YouTube",
        "platform": "YouTube",

        "url": (
            "https://news.google.com/rss/articles/"
            "CBMiXEFVX3lxTE5jSnB5WEYtalFtZnNFWEhLYXdkM0swYnMw"
            "V0pjYXhoVkFKMVlieHF3aUN4OGFPWHZSUFpoMUZIODNxV3RpeWJL"
            "X25DWHpyaURYenpxZmZTb1p3NFI2?oc=5"
        ),

        "published_at": "2025-05-29T07:00:00+00:00",

        "keyword": "مرشحات الثالث متوسط",
        "content_type": "مرشحات",
        "search_group": "مرشحات حديثة",

        "year": None,
        "exam_round": None,
        "is_current_year": False,
    }


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

        "subjects": list(
            SUBJECTS.keys()
        ),

        "platforms": [
            "YouTube",
            "Telegram",
            "Web",
        ],

        "content_types": CONTENT_TYPES,

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
# حفظ التقرير النصي
# ==================================================

def save_markdown(results):

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    lines = []

    lines.append(
        "# الباحث الوزاري العراقي"
    )

    lines.append("")

    lines.append(
        f"تاريخ التحديث: "
        f"{datetime.now(timezone.utc).isoformat()}"
    )

    lines.append("")

    lines.append(
        "المرحلة: الثالث المتوسط العراقي"
    )

    lines.append("")

    lines.append(
        f"عدد النتائج المؤرشفة: {len(results)}"
    )

    lines.append("")
    lines.append("---")
    lines.append("")

    for subject in SUBJECTS:

        subject_results = [
            item
            for item in results
            if item.get("subject") == subject
        ]

        lines.append(
            f"## {subject}"
        )

        lines.append("")

        if not subject_results:
            lines.append(
                "لا توجد نتائج محفوظة حالياً."
            )

            lines.append("")
            continue

        for item in subject_results:

            lines.append(
                f"### {item.get('title', 'بدون عنوان')}"
            )

            lines.append("")

            lines.append(
                f"- النوع: {item.get('content_type', '')}"
            )

            lines.append(
                f"- المصدر: {item.get('source', '')}"
            )

            lines.append(
                f"- المنصة: {item.get('platform', '')}"
            )

            lines.append(
                f"- السنة: {item.get('year') or 'غير محددة'}"
            )

            lines.append(
                f"- الرابط: {item.get('url', '')}"
            )

            lines.append("")

    REPORT_MD.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )


# ==================================================
# تشغيل الباحث
# ==================================================

def main():

    print("=" * 50)

    print(
        "الباحث الوزاري العراقي"
    )

    print(
        "البحث مخصص للثالث المتوسط العراقي فقط"
    )

    print(
        "الأرشيف التراكمي مفعل"
    )

    print("=" * 50)

    # تحميل الأرشيف السابق
    old_results = load_previous_results()

    # استرجاع نتيجة الكيمياء إذا كانت مفقودة
    chemistry = restore_chemistry_result()

    old_results = merge_results(
        old_results,
        [chemistry]
    )

    print(
        f"Old archived results: {len(old_results)}"
    )

    # البحث عن نتائج جديدة
    new_results = collect_results()

    print(
        f"New search results: {len(new_results)}"
    )

    # دمج النتائج القديمة والجديدة
    results = merge_results(
        old_results,
        new_results
    )

    # ترتيب النتائج
    results.sort(
        key=lambda item: (
            item.get("subject", ""),
            item.get("content_type", ""),
            item.get("year") or "",
        )
    )

    # حفظ الملفات
    save_json(results)

    save_markdown(results)

    print("=" * 50)

    print(
        f"Total archived results: {len(results)}"
    )

    print(
        f"JSON saved: {REPORT_JSON}"
    )

    print(
        f"Markdown saved: {REPORT_MD}"
    )

    print("=" * 50)


if __name__ == "__main__":
    main()
