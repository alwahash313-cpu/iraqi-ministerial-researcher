
import feedparser
from urllib.parse import quote_plus
from datetime import datetime
from pathlib import Path
import re
import html

SUBJECTS = {
    "اللغة العربية": ["عربي", "قواعد", "أدب", "إنشاء"],
    "اللغة الإنكليزية": ["إنكليزي", "انكليزي", "English"],
    "الرياضيات": ["رياضيات"],
    "الكيمياء": ["كيمياء"],
    "الفيزياء": ["فيزياء"],
    "الأحياء": ["أحياء", "احياء"],
    "الاجتماعيات": ["اجتماعيات", "تاريخ", "جغرافية", "وطنية"],
    "الإسلامية": ["إسلامية", "اسلامية"],
    "اللغة الكردية": ["كردي", "كردية"],
}

EXCLUDE_TERMS = [
    "السادس الابتدائي",
    "السادس الاعدادي",
    "السادس الإعدادي",
    "السادس العلمي",
    "السادس الادبي",
    "السادس الأدبي",
    "الثالث الابتدائي",
    "الاول المتوسط",
    "الأول المتوسط",
    "الثاني المتوسط",
    "الرابع العلمي",
    "الخامس العلمي",
]

def clean(text):
    text = html.unescape(text or "")
    return re.sub(r"<[^>]+>", "", text).strip()

def search(query):
    url = (
        "https://news.google.com/rss/search?q="
        + quote_plus(query)
        + "&hl=ar&gl=IQ&ceid=IQ:ar"
    )
    feed = feedparser.parse(url)
    return feed.entries

def is_third_intermediate(title, summary=""):
    text = (title + " " + summary).lower()

    required_terms = [
        "الثالث المتوسط",
        "ثالث متوسط",
        "الثالث متوسط",
        "ثالث المتوسط",
    ]

    if not any(term in text for term in required_terms):
        return False

    if any(term in text for term in EXCLUDE_TERMS):
        return False

    return True

def classify(title):
    text = title.lower()

    if any(word in text for word in [
        "وزاري", "وزاريات", "اسئلة وزارية", "أسئلة وزارية"
    ]):
        return "وزاريات"

    if any(word in text for word in [
        "مرشحات", "مرشحة", "المرشحات"
    ]):
        return "مرشحات غير مضمونة"

    if any(word in text for word in [
        "حلول", "حل اسئلة", "حل أسئلة", "اجوبة", "أجوبة"
    ]):
        return "حلول وأسئلة"

    if any(word in text for word in [
        "مراجعة", "ملخص", "ملزمة"
    ]):
        return "مراجعات وملخصات"

    return "نتيجة تحتاج مراجعة"

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    results = []
    seen = set()

    for subject, keywords in SUBJECTS.items():
        for keyword in keywords:
            query = (
                f'"الثالث المتوسط" العراق "{keyword}" '
                f'(وزاريات OR مرشحات OR مراجعة OR امتحانات OR حلول) '
                f'-"السادس الإعدادي" -"السادس الابتدائي" '
                f'-"الأول المتوسط" -"الثاني المتوسط"'
            )

            try:
                entries = search(query)
            except Exception as error:
                print(f"تعذر البحث عن {subject}: {error}")
                continue

            for entry in entries:
                title = clean(entry.get("title", ""))
                summary = clean(entry.get("summary", ""))
                link = entry.get("link", "")

                if not title or not link:
                    continue

                if not is_third_intermediate(title, summary):
                    continue

                if link in seen:
                    continue

                seen.add(link)

                published = entry.get(
                    "published",
                    "التاريخ غير متوفر"
                )

                results.append({
                    "subject": subject,
                    "title": title,
                    "link": link,
                    "published": published,
                    "type": classify(title),
                })

    output = [
        "# الباحث الوزاري العراقي",
        "",
        "## نتائج الثالث المتوسط العراقي فقط",
        "",
        f"تاريخ التقرير: {today}",
        "",
        "> البحث يجمع نتائج عامة من Google News RSS. "
        "المرشحات غير مؤكدة ويجب التحقق من المصادر.",
        "",
    ]

    if not results:
        output.extend([
            "لم تظهر نتائج مطابقة للشروط في هذا البحث.",
            "قد توجد مواد منشورة لم تظهر بسبب حدود البحث.",
            "",
        ])

    for subject in SUBJECTS:
        subject_results = [
            item for item in results
            if item["subject"] == subject
        ]

        output.extend([f"## {subject}", ""])

        if not subject_results:
            output.extend([
                "لم تظهر نتائج مطابقة حالياً.",
                "",
            ])
            continue

        for item in subject_results:
            output.extend([
                f"### {item['title']}",
                f"- التصنيف: {item['type']}",
                f"- تاريخ النشر: {item['published']}",
                f"- الرابط: {item['link']}",
                "",
            ])

    Path("reports").mkdir(exist_ok=True)
    Path("reports/latest.md").write_text(
        "\n".join(output),
        encoding="utf-8"
    )

    print(
        f"اكتمل البحث. عدد النتائج المطابقة: {len(results)}"
    )

if __name__ == "__main__":
    main()
