"""Extract numbered INCI names from the EU 2025/1175 glossary PDF."""

import csv
from pathlib import Path

import pdfplumber


def extract_inci_dictionary(pdf_path):
    records = []
    current = None

    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            words = page.extract_words()
            header = next((w for w in words if w["text"] == "Entry"), None)
            if header is None:
                page.close()
                continue

            footer = min(
                (w["top"] for w in words if w["text"] == "ELI:"),
                default=page.height,
            )
            body = sorted(
                (w for w in words if header["bottom"] < w["top"] < footer - 2),
                key=lambda w: (w["top"], w["x0"]),
            )

            lines = []
            for word in body:
                if not lines or abs(word["top"] - lines[-1][0]["top"]) > 2:
                    lines.append([])
                lines[-1].append(word)

            for line in lines:
                line.sort(key=lambda w: w["x0"])
                markers = [w for w in line if w["x0"] < 120]
                name = " ".join(w["text"] for w in line if w["x0"] >= 120)
                if markers:
                    if len(markers) != 1 or not markers[0]["text"].isdigit():
                        raise ValueError(f"Unexpected entry column on page {page_number}")
                    number = int(markers[0]["text"])
                    if number != len(records) + 1:
                        raise ValueError(f"Entry sequence error on page {page_number}: {number}")
                    current = {"entry_number": number, "inci_name": name}
                    records.append(current)
                elif name:
                    if current is None:
                        raise ValueError("Continuation before the first ingredient")
                    # Join wrapped names, preserving punctuation at line boundaries.
                    separator = "" if (
                        current["inci_name"].endswith(("/", "-"))
                        or name.startswith(("/", "-"))
                    ) else " "
                    current["inci_name"] += separator + name

            page.close()
            if page_number % 100 == 0:
                print(f"Read {page_number} pages; extracted {len(records)} entries", flush=True)

    if not records or any(not row["inci_name"] for row in records):
        raise ValueError("No entries found, or an ingredient name is empty")
    return records


if __name__ == "__main__":
    source = Path("data/inci_glossary.pdf")
    output = Path("data/inci_dictionary.csv")
    records = extract_inci_dictionary(source)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["entry_number", "inci_name"])
        writer.writeheader()
        writer.writerows(records)
    print(f"Saved {len(records)} ingredients to {output}")
