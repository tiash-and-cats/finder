# Finder IFAQ (Infrequently Asked Questions)

## Q. I'm not getting the results I expect!

Yeah... you see, instead of using [vector search](https://en.wikipedia.org/wiki/Vector_database) or [semantic search](https://en.wikipedia.org/wiki/Semantic_search) like an actually competent search engine, Finder uses [keyword search](https://en.wikipedia.org/wiki/Search_engine_(computing)). This means that Finder searches for raw strings of text. On top of that, Finder only stores the first 200 characters of a website's content. This means that you have absolutely no way of knowing whether your search term will be found in the page. For example, the search "what is nvgif" has 1 search result while "nvgif" has 5. In general, the fewer search terms you have will give you more results.

## Q. Okay, so what can this search thingamajig actually do?

It does the keyword search, but then it has a filter where if a term starts with `site:` only terms from the specified site are given in the result. It also has these things called "search extensions" where if you search some specific keywords, it will put a nice, proven result on top. There are currently three available:

- If you include the keywords "define" or "meaning", it will get a definition from the [Free Dictionary API](https://dictionaryapi.dev).
- If you include the keyword "weather", it will get a forecast from [Open-Meteo](https://open-meteo.com).
- And if you search how to exit Vim... I'll leave that for you to find out.

## Q. Why "Finder"?

I don't know, I dreamt the name up 3 years ago.

## Q. Isn't Apple gonna sue you?

Shh... don't jinx it! Hopefully not.