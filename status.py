from flask import Flask, jsonify, render_template_string
import datetime
import textwrap

class Status:    
    def __init__(self, history_limit=100):
        self.services = {}
        self.history_limit = history_limit
    
    def add_service(self, name):
        self.services[name] = []
    
    def service_request(self, name, status):
        try:
            code = int(status.split(" ", 1)[0])
        except (IndexError, ValueError) as e:
            raise ValueError(f"Invalid status {status!r}") from e
        
        healthy = code < 500 # 40x is considered healthy because it's not our
                             # fault so we don't need to worry about it!
        self.services[name].append(healthy)
        # trim history
        if len(self.services[name]) > self.history_limit:
            self.services[name].pop(0)
    
    def success_rate(self, name=None):
        if name:
            reqs = self.services.get(name, [])
        else:
            reqs = [r for lst in self.services.values() for r in lst]
        return (sum(reqs) / len(reqs)) if reqs else None

    def summary(self):
        return {
            name: {
                "checks": len(results),
                "healthy": sum(results),
                "unhealthy": len(results) - sum(results),
                "success_rate": (sum(results) / len(results)) if results else None
            }
            for name, results in self.services.items()
        }

def create_app(status):
    def headline_class_and_text():
        rate = status.success_rate()
        if rate is None:
            return "sad", "Not all systems operational..."
        elif rate >= 0.95:
            return "happy", "All systems operational!"
        elif rate >= 0.80:
            return "pensive", "Most systems operational"
        else:
            return "sad", "Not all systems operational..."

    app = Flask(__name__)

    @app.route("/status/api")
    def status_json():
        return jsonify({
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "services": status.summary(),
            "overall_success_rate": status.success_rate()
        })

    @app.route("/status")
    def status_html():
        summary = status.summary()
        headline_class, headline_text = headline_class_and_text()
        html = textwrap.dedent("""\
        <!DOCTYPE html>
        <html>
        <head>
        <title>Finder Status: {{headline_text}}</title>
        <style>
        body {
          margin: 0;
          padding: 40px;
          font-family: Verdana, Tahoma, sans-serif;
        }
        
        .home {
          float: right;
        }
        
        .home img {
          height: 2rem;
        }

        h1, div h2 {
          margin-top: 0;
        }

        h1.happy { color: green; }
        h1.pensive { color: orange; }
        h1.sad { color: red; }

        div p {
          margin-block: .375rem;
        }

        meter {
          /* Reset default OS styling */
          appearance: none;
          -webkit-appearance: none;
          -moz-appearance: none;
          
          /* Dimensions */
          width: 100%;
          
          /* Fallback track styling for older browsers */
          background: white;
          border: none;
        }

        /* TRACK STYLING (The background behind the bar) */

        /* Webkit (Chrome, Safari, Edge) */
        meter::-webkit-meter-bar {
          background: white;
          outline: 1px solid grey;
          border: none;
          height: 1.25rem;
        }

        /* BAR VALUE STYLING (The filled portions based on thresholds) */

        /* --- OPTIMUM RANGE (Green by default/Good) --- */
        meter::-webkit-meter-optimum-value {
          background: green;
        }
        meter::-moz-meter-bar { /* Firefox handles all states via this main pseudo-element */
          background: green;
        }

        /* --- SUB-OPTIMAL RANGE (Yellow/Warning) --- */
        meter::-webkit-meter-suboptimum-value {
          background: #f1c40f;
        }
        /* Firefox equivalent targeting via attribute fallback state */
        meter:-moz-meter-suboptimum::-moz-meter-bar {
          background: #f1c40f;
        }

        /* --- CRITICAL / AT-RISK RANGE (Red/Bad) --- */
        meter::-webkit-meter-even-less-good-value {
          background: #e74c3c;
        }
        /* Firefox equivalent targeting via attribute fallback state */
        meter:-moz-meter-sub-suboptimum::-moz-meter-bar {
          background: #e74c3c;
        }

        .card {
          box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
          transition: 0.3s;
          padding: 1rem;
        }

        .card:hover {
          box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
        }

        .healthy { color: green; }
        .unhealthy { color: red; }
        .percent { float: right; }
        </style>
        </head>
        <body>

        <h1 class="{{headline_class}}">{{headline_text}} <a class="home" href="/"><img src="/static/logo.svg"></a></h1>
        
        <p>Confused? See the docs <a href="/docs/user/status.html">here</a>.</p>

        {% for name, data in summary.items() %}
        <p><div class="card">
          <h2>{{name}}</h2>
          <p><meter min="0" max="100" low="80" high="95" optimum="100"
              value="{{(data.success_rate or 0) * 100}}">
            {{data.healthy}}/{% if data.checks == limit %}last {% endif %}
            {{data.checks}} are healthy.
          </meter></p>
          <p><span class="healthy">{{data.healthy}} healthy,</span> 
             <span class="unhealthy">{{data.unhealthy}} unhealthy</span> 
             <span class="percent">
               {{((data.success_rate or 0) * 100) | round | int}}% 
               success rate {% if data.checks == limit %}
                 (last {{limit}})
               {% endif %}
             </span></p>
        </div></p>
        {% endfor %}

        </body>
        </html>""")
        return render_template_string(html, summary=summary, 
                                      limit=status.history_limit,
                                      headline_class=headline_class,
                                      headline_text=headline_text)

    return app