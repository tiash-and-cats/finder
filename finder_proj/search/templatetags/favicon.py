from django import template
from urllib.parse import urljoin
from django.templatetags.static import static

register = template.Library()

@register.simple_tag
def favicon(page):
    if page["favicon"]:
        if page["favicon"].startswith(("http://", "https://")):
            return page["favicon"]
        return urljoin(page["url"], page["favicon"])
    return static("nofavicon.svg")