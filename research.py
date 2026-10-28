
import json
import os
from datetime import datetime
from urllib.parse import quote
from urllib.request import Request, urlopen
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

SUBJECTS = {
    "اللغة العربية": ["ملخص", "مرشحات", "اسئلة وزارية"],
    "اللغة الإنجليزية": ["ملخص", "مرشحات", "اسئلة وزارية"],
    "الرياضيات": ["ملخص", "مرشحات", "اسئلة وزارية"],
    "الكيمياء": ["ملخص", "مرشحات", "اسئلة وزارية"],
    "الفيزياء": ["ملخص", "مرشحات", "اسئلة وزارية"],
    "الأحياء": ["ملخص", "مرشحات", "اسئلة وزارية"],
    "الاجتماعيات": ["ملخص", "مرشحات", "اسئلة وزارية"],
    "التربية الإسلامية": ["ملخص", "مرشحات", "اسئلة وزارية"],
}

OUTPUT_DIR = "reports"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def search_news(subject, keyword):
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
        with urlopen(request, timeout=20) as response:
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

            combined = f"{title} {link}".lower()

            if not title or not link:
                continue

            if "الثالث الإعدادي" in combined or "الثالث الاعدادي" in combined:
                continue

            if not any(term in combined for term in [
                "الثالث متوسط",
                "الثالث المتوسط",
                "ثالث متوسط",
                "الثالث-متوسط",
            ]):
                continue

            items.append({
                "subject": subject,
                "title": title,
                "source": source,
                "url": link,
                "published_at": pub_date,
                "keyword": keyword,
            })

        return items

    except Exception as exc:
        print(f"تعذر البحث عن {subject} - {keyword}: {exc}")
        return []


def main():
    results = []
    seen_urls = set()

    for subject, keywords in SUBJECTS.items():
        print(f"البحث في مادة: {subject}")

        for keyword in keywords:
            for result in search_news(subject, keyword):
                if result["url"] not in seen_urls:
                    seen_urls.add(result["url"])
                    results.append(result)

    now = datetime.now().astimezone().isoformat(timespec="seconds")

    data = {
        "updated_at": now,
        "results": results,
        "subjects": list(SUBJECTS.keys()),
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

        if not results:
            file.write("لم تُعثر على نتائج مطابقة في هذا البحث.\n")
        else:
            for subject in SUBJECTS:
                subject_results = [
                    item for item in results
                    if item["subject"] == subject
                ]

                file.write(f"## {subject}\n\n")

                if not subject_results:
                    file.write("لم تُعثر على نتائج لهذه المادة.\n\n")
                    continue

                for item in subject_results:
                    file.write(f"- [{item['title']}]({item['url']})\n")
                    file.write(f"  - المصدر: {item['source']}\n")
                    file.write(f"  - نوع البحث: {item['keyword']}\n")

                file.write("\n")

    print(f"اكتمل البحث. عدد النتائج: {len(results)}")
    print(f"تم إنشاء: {json_path} و {md_path}")


if __name__ == "__main__":
    main()
