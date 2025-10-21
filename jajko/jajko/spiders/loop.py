import scrapy
import re

def convert_time_to_24h(text: str) -> str:
    """Convert various time formats to HH:MM 24h format."""
    if not text:
        return "-"

    t = text.replace("\xa0", " ").lower().strip()

    # Match 24h times like 21:30 or 21:30 Uhr
    m = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\s*(?:uhr)?\b", t)
    if m:
        hh, mm = int(m.group(1)), m.group(2)
        return f"{hh:02d}:{mm}"

    # Match 12h times like 9:30 pm or 9:30 am
    m = re.search(r"\b([1-9]|1[0-2]):([0-5]\d)\s*(am|pm)\b", t)
    if m:
        hh = int(m.group(1))
        mm = m.group(2)
        ap = m.group(3)
        if ap == "pm" and hh != 12:
            hh += 12
        if ap == "am" and hh == 12:
            hh = 0
        return f"{hh:02d}:{mm}"

    return "-"


class LoopSpider(scrapy.Spider):
    name = "loop"
    allowed_domains = ["loop.co.at"]
    start_urls = ["https://loop.co.at/events"]

    custom_settings = {
        "FEEDS": {
            "loop.json": {
                "format": "json",
                "overwrite": True,
                "encoding": "utf8",
            }
        }
    }

    def parse(self, response):
        events = response.css("article.tribe-events-calendar-list__event")
        self.logger.info(f"Loop: found {len(events)} events")

        for ev in events:
            title = (ev.css("h3.tribe-events-calendar-list__event-title a::text").get() or "-").strip()
            url = ev.css("h3.tribe-events-calendar-list__event-title a::attr(href)").get()
            if url:
                url = response.urljoin(url)
            else:
                url = "-"

            # Extract date
            date_iso = (ev.css("time.tribe-events-calendar-list__event-datetime::attr(datetime)").get() or "-").strip()
            if "T" in date_iso:
                date_iso = date_iso.split("T")[0]

            # Extract all text to find time
            text_all = " ".join([t.strip() for t in ev.xpath(".//text()").getall() if t.strip()])
            time_str = convert_time_to_24h(text_all)

            if time_str == "-" and url != "-":
                yield response.follow(
                    url,
                    callback=self.parse_event,
                    cb_kwargs={"title_hint": title, "date_hint": date_iso}
                )
            else:
                content = [t.strip() for t in ev.css("*::text").getall() if t.strip()]
                yield {
                    "url": url,
                    "event": title,
                    "date": date_iso if date_iso else "-",
                    "time": time_str,
                    "content": content,
                    "location": "Loop Bar Vienna",
                    "lineup": "-"
                }

    def parse_event(self, response, title_hint, date_hint):
        title = (response.css("h1.entry-title::text").get() or title_hint or "-").strip()
        date_iso = (response.css("time::attr(datetime)").get() or date_hint or "-").strip()
        if "T" in date_iso:
            date_iso = date_iso.split("T")[0]

        # Extract text from detail page to find time
        page_text = " ".join([t.strip() for t in response.xpath("//body//text()").getall() if t.strip()])
        time_str = convert_time_to_24h(page_text)

        content = [t.strip() for t in response.css("*::text").getall() if t.strip()]

        yield {
            "url": response.url,
            "event": title,
            "date": date_iso if date_iso else "-",
            "time": time_str,
            "content": content,
            "location": "Loop Bar Vienna",
            "lineup": "-"
        }
