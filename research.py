
import os
import re
import time
from datetime import datetime
from urllib.parse import quote_plus
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

import feedparser

SUBJECTS = {
    "اللغة العربية": [
        '"الثالث المتوسط" وزاريات عربي العراق',
        '"الثالث متوسط" مرشحات عربي العراق',
    ],
    "اللغة الإنكليزية": [
        '"الثالث المتوسط" وزاريات انكليزي العراق',
        '"الثالث متوسط" مرشحات انكليزي العراق',
    ],
    "الرياضيات": [
        '"الثالث المتوسط" وزاريات رياضيات العراق',
        '"الثالث متوسط" مرشحات رياضيات العراق',
    ],
    "العلوم": [
        '"الثالث المتوسط" وزاريات علوم العراق',
    ],
    "الكيمياء": [
        '"الثالث المتوسط" وزاريات كيمياء العراق',
        '"الثالث متوسط" مرشحات كيمياء العراق',
    ],
    "الفيزياء": [
        '"الثالث المتوسط" وزاريات فيزياء العراق',
        '"الثالث متوسط" مرشحات فيزياء العراق',
    ],
    "الأحياء": [
        '"الثالث المتوسط" وزاريات احياء العراق',
        '"الثالث متوسط" مرشحات احياء العراق',
    ],
    "الاجتماعيات": [
        '"الثالث المتوسط" وزاريات اجتماعيات العراق',
        '"الثالث متوسط" مرشحات اجتماعيات العراق',
    ],
    "الإسلامية": [
        '"الثالث المتوسط" وزاريات اسلامية العراق',
        '"الثالث متوسط" مرشحات اسلامية العراق',
    ],
}

def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()

def get_date(entry):
    try:
        if entry.get("published"):
            return parsedate_to_datetime(
                entry.published
            ).strftime("%Y-%m-%d")
        if entry.get("updated"):
            return parsedate_to_datetime(
                entry.updated
            ).strftime("%Y-%m-%d")
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

    for entry in feed.entries[:10]:
        link = clean(entry.get("link"))
        title = clean(entry.get("title"))
        if not link or not title:
            continue

        results.append({
            "title": title,
            "link": link,
            "date": get_date(entry),
            "source": clean(
                entry.get("source", {}).get("title", "")
            ) or "المصدر غير محدد",
        })

    return results

def main():
    os.makedirs("reports", exist_ok=True)
    now = datetime.now(ZoneInfo("Asia/Baghdad"))
    output = [
        "# باحث الوزاريات والمرشحات - الثالث المتوسط العراقي",
        "",
        f"تاريخ البحث: {now:%Y-%m-%d %H:%M} بتوقيت بغداد",
        "",
        "> النتائج من بحث الأخبار العام. لم يتم التحقق من كون "
        "المرشحات رسمية، ويجب مراجعة المصدر قبل اعتمادها.",
        "",
    ]

    total = 0
    seen = set()

    for subject, queries in SUBJECTS.items():
        output.extend([f"## {subject}", ""])
        subject_count = 0

        for query in queries:
            try:
                entries = search(query)
            except Exception as error:
                print(f"تعذر البحث: {error}")
                continue

            for entry in entries:
                if entry["link"] in seen:
                    continue
                seen.add(entry["link"])
                subject_count += 1
                total += 1

                title_lower = entry["title"].lower()
                if "وزاري" in title_lower or "وزاريات" in title_lower:
                    kind = "أسئلة وزارية محتملة - يلزم التحقق"
                else:
                    kind = "مرشحات أو مراجعة - غير مؤكدة"

                output.extend([
                    f"### {subject_count}. {entry['title']}",
                    f"- التصنيف: {kind}",
                    f"- المصدر: {entry['source']}",
                    f"- التاريخ: {entry['date']}",
                    f"- الرابط: {entry['link']}",
                    "",
                ])

            time.sleep(1)

        if subject_count == 0:
            output.extend(["لم تظهر نتائج في البحث الحالي.", ""])

    output.extend([
        "---",
        f"عدد الروابط الفريدة: {total}",
        "",
        "تنبيه: هذه النتائج ليست تأكيداً لتسريبات أو أسئلة الامتحان "
        "القادم. البحث يغطّي المصادر العامة المتاحة فقط.",
    ])

    path = "reports/latest.md"
    with open(path, "w", encoding="utf-8") as file:
        file.write("\n".join(output))

    print(f"اكتمل البحث. عدد الروابط: {total}")
    print(f"التقرير: {path}")

if __name__ == "__main__":
    main()
