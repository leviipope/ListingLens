import scrapy


class HardverSpider(scrapy.Spider):
    name = "hardver"
    start_urls = [
        "https://hardverapro.hu/aprok/hardver/videokartya/nvidia/geforce_7xx/index.html"
    ]

    def parse(self, response):
        breadcrumb = response.css("ol.breadcrumb")
        breadcrumb_text = breadcrumb.xpath("string(.)").get()
        if breadcrumb_text:
            breadcrumb_text = (
                breadcrumb_text.replace("\t", " ").replace("\n", " ").strip()
            )
            parts = breadcrumb_text.split()
            if len(parts) >= 2:
                product_type = parts[1]

        listings = response.css("ul.list-unstyled > li[class]")
        for listing in listings:
            data_uadid = listing.attrib.get("data-uadid")
