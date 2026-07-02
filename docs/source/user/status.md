# Using the status page

The <b><a href="/status">status page</a></b> shows whether Finder Services are healthy and running. It's designed to be simple and clear, so you can quickly understand what's going on. If Finder feels slow or Find4U isn't responding, check here first. During outages, you'll see which service is affected.

```{image} ./_static/status_screenshot.png
:width: 100%
```

The page begins with a headline banner showing the overall health of the system, followed by individual service cards for Finder, Find4U, Documentation, and the Status Page itself. Each card includes a colored meter bar that represents uptime percentage, along with counts of healthy and unhealthy checks and a success rate percentage.

## What do the colors mean?

The headline banner at the top changes color to reflect overall system health:

- 🟢 **Green: All systems operational!**  
  Everything is working normally. All services are responding successfully.

- 🟠 **Orange: Most systems operational**  
  One or more services are having minor issues, but the majority are still healthy. You may notice small glitches, but most features will work.

- 🔴 **Red: Not all systems operational...**  
  Significant problems are affecting one or more services. Expect outages or errors until the issue is resolved.

These same colors are used in the meter bars inside each service card:
- Green bar = high success rate (95% or more).  
- Yellow/Orange bar = moderate success rate (80–95%).  
- Red bar = low success rate (below 80%).

## Infrequently Asked Questions

### Q. Why does a 404 count as healthy? 
Because the server responded correctly, even if the page doesn't exist. It means Finder is working, not broken.

### Q. How often is the page updated?
Every time a request goes through the system, it's logged. The status page reflects the latest checks in real time.

### Q. Can I use this data elsewhere? 
Yes! Visit <code><a href="/status/api">/status/api</a></code> for a JSON feed of the same information, useful for monitoring tools or integrations.