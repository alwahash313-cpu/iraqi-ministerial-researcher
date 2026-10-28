
import os
import re
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

import feedparser

SUBJECTS = {
    "اللغة العربية": ["عربي", "قواعد", "أدب"],
    "اللغة الإنكليزية": ["انكليزي", "إنكليزي"],
    "الرياضيات": ["رياضيات"],
    "الكيمياء": ["كيمياء"],
    "الفيزياء": ["فيزياء"],
    "الأحياء": ["أحياء", "احياء"],
    "الاجتماعيات": ["اجتماعيات", "تاريخ", "جغرافية", "وطنية"],
    "الإسلامية": ["إسلامية", "اسلامية"],
    "اللغة الكردية والمواد الأخرى": ["كردي", "علوم"],
}

PLATFORMS = [
    ("الويب العام", ""),
    ("فيسبوك", "site:facebook.com"),
    ("إنستغرام", "site:instagram.com"),
    ("تيليغرام", "site:t.me"),
]

def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()

def get_date(entry):
    for field in ("published", "updated"):
        try:
            value = entry.get(field)
            if value:
                return parsedate_to_datetime(value).strftime("%Y-%m-%d")
        except Exception:
            pass
    return "تاريخ النشر غير متاح"

def search(query):
    url = (
        "https://news.google.com/rss/search?q="
        + quote_plus(query)
        + "&hl=ar&gl=IQ&ceid=IQ:ar"
    )
    feed = feedparser.parse(url)
    results = []

    for entry in feed.entries[:8]:
        link = clean(entry.get("link"))
        title = clean(entry.get("title"))
        if not link or not title:
            continue

        source = entry.get("source", {})
        if not isinstance(source, dict):
            source = {}

        results.append({
            "title": title,
            "link": link,
            "date": get_date(entry),
            "source": clean(source.get("title", "")) or "غير محدد",
        })

    return results

def classify(title):
    text = title.lower()
    if any(word in text for word in [
        "وزاري", "وزاريات", "الدور الأول", "الدور الاول",
        "الدور الثاني", "تمهيدي"
    ]):
        return "أسئلة وزارية محتملة - تحقق من السنة والمصدر"
    return "مرشحات أو مراجعة - غير مؤكدة"

def main():
    os.makedirs("reports", exist_ok=True)
    now = datetime.now(ZoneInfo("Asia/Baghdad"))

    output = [
        "# باحث الوزاريات والمرشحات - الثالث المتوسط العراقي",
        "",
        f"آخر بحث: {now:%Y-%m-%d %H:%M} بتوقيت بغداد",
        "",
        "مصدر البحث: Google News RSS.",
        "تُجرّب عبارات مخصصة للويب وفيسبوك وإنستغرام وتيليغرام.",
        "هذه الطريقة لا تضمن ظهور جميع منشورات المنصات.",
        "التصنيف آلي أولي ولا يثبت أن السؤال رسمي أو أن المرشح صحيح.",
        "",
    ]

    seen = set()
    total = 0

    for subject, keywords in SUBJECTS.items():
        output.extend([f"## {subject}", ""])
        subject_count = 0

        queries = []
        for keyword in keywords:
            queries.append(
                f'"الثالث المتوسط" العراق {keyword} '
                f'(وزاريات OR مرشحات OR مراجعة OR امتحانات)'
            )

            for platform, domain in PLATFORMS[1:]:
                queries.append(
                    f'site:{domain.split(":")[1]} '
                    f'"الثالث المتوسط" العراق {keyword} '
                    f'(وزاريات OR مرشحات OR مراجعة)'
                )

        for query in queries:
            try:
                entries = search(query)
            except Exception as error:
                print(f"تعذر البحث عن {subject}: {error}")
                continue

            for entry in entries:
                link = entry["link"]
                if link in seen:
                    continue

                seen.add(link)
                subject_count += 1
                total += 1

                output.extend([
                    f"### {subject_count}. {entry['title']}",
                    f"- التصنيف: {classify(entry['title'])}",
                    f"- المصدر: {entry['source']}",
                    f"- تاريخ النشر: {entry['date']}",
                    f"- عبارة البحث: {query}",
                    f"- الرابط: {link}",
                    "",
                ])

            time.sleep(1)

        if subject_count == 0:
            output.extend([
                "لم تظهر نتائج بهذه العبارات في البحث الحالي.",
                "",
            ])

    output.extend([
        "---",
        f"عدد الروابط الفريدة: {total}",
        "",
        "تنبيه: عدم ظهور نتائج لا يعني عدم وجود منشورات.",
        "قد لا تكون بعض المنشورات العامة مفهرسة، ولا يشمل البحث",
        "المجموعات الخاصة أو المحتوى المحجوب عن الوصول العام.",
    ])

    with open("reports/latest.md", "w", encoding="utf-8") as file:
        file.write("\n".join(output))

    print(f"انتهى البحث. عدد الروابط الفريدة: {total}")

if __name__ == "__main__":
    main()
