from django import template
from django.utils.html import mark_safe
from html import escape

register = template.Library()

EXTS = {
    ("define", "meaning", "definition"): {
        "html": "<!--%(query)s-->",
        "js": r"""
            async function getDict(word) {
                return fetch(`https://api.dictionaryapi.dev/api/v2/entries/en/${encodeURIComponent(word)}`);
            }
            function renderMeaning(meaning, parent) {
                var pOS = document.createElement("dt");
                pOS.innerHTML = `<b>${meaning.partOfSpeech}</b>`;
                parent.appendChild(pOS);
                var root = document.createElement("dd");
                for (x of meaning.definitions) {
                    var defRoot = document.createElement("dl");
                    var def = document.createElement("dt");
                    def.innerText = x.definition;
                    defRoot.appendChild(def);
                    var ex = document.createElement("dd");
                    ex.innerHTML = `<i>example: ${x.example !== undefined ? x.example : "(unavailable)"}</i>`;
                    defRoot.appendChild(ex);
                    var syns = document.createElement("dd");
                    syns.innerHTML = `<i>synonyms: ${(x.synonyms.length != 0) ? x.synonyms.map(x => `<a href="/search/?q=${encodeURIComponent("define " + x)}">${x}</a>`).join(", ") : "(none)"}</i>`;
                    defRoot.appendChild(syns);
                    var ants = document.createElement("dd");
                    ants.innerHTML = `<i>antonyms: ${(x.antonyms.length != 0) ? x.antonyms.map(x => `<a href="/search/?q=${encodeURIComponent("define " + x)}">${x}</a>`).join(", ") : "(none)"}</i>`;
                    defRoot.appendChild(ants);
                    root.appendChild(defRoot);
                }
                parent.appendChild(root);
            }
            function getWord() {
                var word = "%(query)s".split(" ");
                var newWord = [];
                var alreadyHasMod = false;
                for (x of word) {
                    if (!["meaning", "define", "definition"].includes(x) || alreadyHasMod) {
                        newWord.push(x);
                    } else {
                        alreadyHasMod = true;
                    }
                }
                return newWord.join(" ");
            }
            function renderWord(json, parent) {
                json = JSON.parse(json)[0];
                var root = document.createElement("dl");
                var cred = document.createElement("i");
                cred.innerHTML = "Powered by the <a href='https://dictionaryapi.dev/'>Free Dictionary API</a>.";
                cred.style.float = "right";
                parent.appendChild(cred);
                var word = document.createElement("dt");
                word.innerHTML = `<b>${json.word}</b>`;
                root.appendChild(word);
                var pron = document.createElement("dd");
                pron.innerHTML = `<i>pronunciation: ${json.phonetic !== undefined ? json.phonetic : "(unavailable)"}</i>`;
                root.appendChild(pron);
                var meanRootGrandparent = document.createElement("dd");
                var meanRootHeader = document.createElement("dt");
                meanRootHeader.innerHTML = "<b>meanings:</b>";
                meanRootGrandparent.appendChild(meanRootHeader);
                var meanRootParent = document.createElement("dd");
                var meanRoot = document.createElement("dl");
                for (x of json.meanings) {
                    renderMeaning(x, meanRoot);
                }
                meanRootParent.appendChild(meanRoot);
                meanRootGrandparent.appendChild(meanRootParent);
                root.appendChild(meanRootGrandparent);
                parent.appendChild(root);
            }
            (async function() {
                var res = await getDict(getWord());
                if (res.ok) {
                    var text = await res.text();
                } else {
                    if (res.status == 404) {
                        document.getElementById("ext").innerHTML = "<i>I don't know what that means. Or at least the <a href='https://dictionaryapi.dev/'>Free Dictionary API</a> doesn't.</i>";
                    } else {
                        document.getElementById("ext").innerHTML = `<i>The request to the <a href='https://dictionaryapi.dev/'>Free Dictionary API</a> failed with code ${res.status} (${res.statusText}).</i>`;
                    }
                    return;
                }
                renderWord(text, document.getElementById("ext"));
            })();
        """
    },
    "exit vim": {
        "html": "<h1>Unplug your computer</h1><p>Just kidding, <code>:wq</code> to save before closing, and <code>:q</code> to close without saving.</p><!--%(query)s-->"
    },
    ("weather", "forecast", "temperature"): {
        "html": "<!--%(query)s-->",
        "js": r"""
            function extractLocation(raw) {
                const triggers = ["weather", "forecast", "temperature", "in", "for", "today", "now", "what's", "the", "?"];
                return raw
                    .split(" ")
                    .filter((w) => !triggers.includes(w.toLowerCase()))
                    .join(" ")
                    .trim();
            }
            
            const queryLocation = extractLocation("%(query)s");
            
            function getEmoji(code) {
                const mapping = {
                    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️", 45: "🌫️", 48: "🌫️",
                    51: "🌦️", 53: "🌦️", 55: "🌧️", 61: "🌧️", 63: "🌧️", 65: "🌧️",
                    66: "🌧️", 67: "🌧️", 71: "🌨️", 73: "🌨️", 75: "❄️", 77: "🌨️",
                    80: "🌦️", 81: "🌧️", 82: "⛈️", 85: "🌨️", 86: "❄️", 95: "⛈️",
                    96: "⛈️", 99: "🌩️"
                };
                return mapping[code] || "❓";
            }
            
            async function fetchCoordinates(city) {
                const res = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(city)}`);
                const data = await res.json();
                if (!data.results || data.results.length === 0) throw new Error("Location not found");
                return data.results[0];
            }
            
            async function fetchForecast(lat, lon) {
                const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&daily=temperature_2m_max,temperature_2m_min,weathercode&current_weather=true&timezone=auto`;
                const res = await fetch(url);
                return await res.json();
            }
            
            function renderCurrent(current) {
                const emoji = getEmoji(current.weathercode);
                return `
                    <div class="weather-current">
                        <div class="icon-big">${emoji}</div>
                        <div class="current-info">
                            <div class="temp">${current.temperature}°C</div>
                            <div class="label">Now · ${current.winddirection}° wind at ${current.windspeed} km/h</div>
                        </div>
                    </div>`;
            }
            
            function renderForecast(daily) {
                return daily.time.map((date, i) => {
                    const day = i === 0 ? "Today" :
                        new Date(date).toLocaleDateString(undefined, { weekday: "short" });
                    const emoji = getEmoji(daily.weathercode[i]);
                    return `
                        <div class="forecast-day">
                            <div class="day">${day}</div>
                            <div class="icon">${emoji}</div>
                            <div class="temps">${daily.temperature_2m_max[i]}° / ${daily.temperature_2m_min[i]}°</div>
                        </div>`;
                }).join("");
            }
            
            (async () => {
                try {
                    const geo = await fetchCoordinates(queryLocation);
                    const data = await fetchForecast(geo.latitude, geo.longitude);
            
                    document.getElementById("ext").innerHTML = `
                        <style>
                            .weather-current {
                                display: flex;
                                align-items: center;
                                gap: 12px;
                                font-family: "Segoe UI", sans-serif;
                                margin-bottom: 14px;
                            }
                            .icon-big {
                                font-size: 48px;
                            }
                            .current-info .temp {
                                font-size: 36px;
                                font-weight: bold;
                            }
                            .current-info .label {
                                font-size: 14px;
                                color: #444;
                            }
                            .forecast-container {
                                display: flex;
                                flex-wrap: wrap;
                                gap: 12px;
                            }
                            .forecast-day {
                                background: #f9f9f9;
                                border-radius: 8px;
                                padding: 8px;
                                min-width: 72px;
                                text-align: center;
                                font-family: "Segoe UI", sans-serif;
                            }
                            .forecast-day .icon {
                                font-size: 24px;
                                margin: 6px 0;
                            }
                            .forecast-day .day {
                                font-weight: bold;
                                font-size: 14px;
                            }
                            .forecast-day .temps {
                                font-size: 13px;
                                color: #333;
                            }
                            .attribution {
                              font-size: 12px;
                              font-family: system-ui, sans-serif;
                              color: #888;
                              margin-top: 12px;
                              text-align: right;
                            }
                            
                            .attribution a {
                              color: inherit;
                              text-decoration: none;
                              border-bottom: 1px dotted #aaa;
                            }
                            
                            .attribution a:hover {
                              color: #444;
                              border-bottom: 1px solid #444;
                            }
                        </style>
                        ${renderCurrent(data.current_weather)}
                        <div class="forecast-container">
                            ${renderForecast(data.daily)}
                        </div>
                        <div class="attribution">
                          Data from <a href="https://open-meteo.com/" target="_blank" rel="noopener noreferrer">Open-Meteo</a>
                        </div>
                    `;
                } catch (err) {
                    document.getElementById("ext").innerHTML = `<i>Could not load weather: ${err.message}</i>`;
                }
            })();
        """
    },
}

@register.simple_tag
def extensions_html(query):
    for key, value in EXTS.items():
        if isinstance(key, str) and key in query or isinstance(key, tuple) and any(k in query for k in key):
            return {
                "ext_match": True,
                "ext_html": value["html"] % {"query": escape(query)}
            }
    return {"ext_match": False, "ext_html": ""}

@register.simple_tag
def extensions_js(query):
    safe_query = query.replace('"', '\\"')
    for key, value in EXTS.items():
        if isinstance(key, str) and key in query or isinstance(key, tuple) and any(k in query for k in key):
            return mark_safe(value.get("js", "") % {"query": safe_query})
    return ""