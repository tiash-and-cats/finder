from django import template
from django.template.loader import render_to_string

register = template.Library()

@register.simple_tag(takes_context=True)
def searchbox_js(context, id_, datalist_id, common):
    return render_to_string("searchbox.html", {
        "common": context.get("common", []),
        "id": id_,
        "datalist_id": datalist_id,
    })