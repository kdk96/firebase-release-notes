import requests
from bs4 import BeautifulSoup
import re

URL = "https://firebase.google.com/support/release-notes/android"


def parse_version(v: str):
    return tuple(map(int, v.split(".")))


def fetch_release_notes(library_name="Crashlytics",
                        start_version=None,
                        end_version=None):
    resp = requests.get(URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    content = soup.find("div", {"class": "changelog"})

    current_update_date = None
    current_lib = None
    current_version = None
    current_changes = []
    is_target = False

    def flush():
        """Save accumulated changes for a version."""
        nonlocal current_lib, current_version, current_update_date, current_changes
        if current_lib and current_version and current_changes:
            v_tuple = parse_version(current_version)
            if start_version and v_tuple < parse_version(start_version):
                pass
            elif end_version and v_tuple > parse_version(end_version):
                pass
            else:
                results.append({
                    "library": current_lib,
                    "version": current_version,
                    "date": current_update_date,
                    "changes": current_changes
                })
        current_lib, current_version, current_changes = None, None, []

    for el in content.find_all(["h2", "h3", "ul"], recursive=False):
        # Detect update section (date)
        if el.name == "h2":
            # Date headers look like "Update - July 17, 2024"
            txt = el.get_text(strip=True)
            if txt.lower().startswith("update"):
                current_update_date = txt.replace("Update -", "").strip()

        # Detect library section
        elif el.name == "h3":
            # Starting a new library section -> flush previous one
            flush()

            header_text = el.get_text(" ", strip=True)

            # Example: "Cloud Firestore version 25.0.0"
            match = re.match(r"(.*?)\s+version\s+(\d+\.\d+\.\d+)", header_text)
            if match:
                current_lib = match.group(1).strip()
                current_version = match.group(2).strip()
                is_target = library_name.lower() in current_lib.lower()
            else:
                current_lib, current_version, is_target = None, None, False

        # Collect changes if the last h3 matched
        elif el.name == "ul" and is_target and current_lib and current_version:
            for li in el.find_all("li", recursive=False):
                current_changes.append(li.get_text(" ", strip=True))

    # Flush the last one
    flush()
    return results


if __name__ == "__main__":
    notes = fetch_release_notes("Remote Config", start_version="21.4.1")
    for n in notes:
        print(f"\n[{n['date']}] {n['library']} {n['version']}")
        for change in n["changes"]:
            print(f"  - {change}")
