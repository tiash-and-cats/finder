from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import loader
from django.db.models import Q
from django.conf import settings
from api.models import Indexed
from .models import CommonSearch
from shlex import split
import snowballstemmer

def parse_query(query):
    try:
        splitquery = split(query)
    except ValueError:
        splitquery = query.split()

    site = None
    for idx, x in enumerate(splitquery):
        if x.startswith("site:"):
            site = splitquery.pop(idx).removeprefix("site:")

    qexp = Q()
    for x in splitquery:
        qexp &= Q(keywds__icontains=x) | Q(title__icontains=x) | Q(content__icontains=x)

    if site:
        qexp &= Q(url__icontains=site)

    return qexp, splitquery  # return the raw terms too

def search_results(request):
    if request.GET and request.GET.get("q", "").strip():
        query = request.GET["q"]
        qexp, terms = parse_query(query)

        stemmer = snowballstemmer.stemmer("english")
        stemmed_terms = set(stemmer.stemWords([w.lower() for w in terms]))

        results = Indexed.objects.filter(qexp).order_by("-rank").values()
        scored = []

        for row in results:
            content = (row.get("content") or "").lower().split()
            content_stemmed = set(stemmer.stemWords(content))
            hit_count = len(stemmed_terms & content_stemmed)
            row["score"] = row["rank"] + hit_count
            scored.append(row)

        scored.sort(key=lambda r: r["score"], reverse=True)
        
        query = request.GET.get("q", "").strip().lower()
        if query:
            obj, created = CommonSearch.objects.get_or_create(phrase=query)
            obj.count += 1
            obj.save()

        context = {
            'query': query,
            'total': len(scored),
            'results': scored,
            "common": list(CommonSearch.objects.order_by("-count").values_list("phrase", flat=True))[:100]
        }
        template = loader.get_template('results.html')
        return HttpResponse(template.render(context, request))
    else:
        return redirect("search:search")

def indexed(request):
    indexed = Indexed.objects.all().order_by("-rank").values()
    template = loader.get_template('indexed.html')
    context = {
      'indexed': indexed,
      "total": len(indexed)
    }
    return HttpResponse(template.render(context, request))

def search(request):
    template = loader.get_template('search.html')
    context = {
      "common": list(CommonSearch.objects.order_by("-count").values_list("phrase", flat=True))[:100],
      "prod": not settings.DEBUG
    }
    return HttpResponse(template.render(context, request))