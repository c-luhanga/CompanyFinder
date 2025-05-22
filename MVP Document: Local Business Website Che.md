MVP Document: Local Business Website Checker

Project Name

Local Business Website Checker

Objective

Develop a Python CLI tool that identifies local businesses in the user’s area that do not have websites. The tool will rely on a geolocation service and free/open business directory APIs (such as OpenStreetMap or Yelp Fusion). The main goal is to use the output to identify leads for web development services by creating MVP website mockups for those businesses.

Core Features (MVP)

1. Geolocation Detection

Automatically detect the user's current geographic coordinates via IP address.

Fallback to manual location input if geolocation fails.

2. Business Search

Use a free API (such as OpenStreetMap Nominatim or Yelp Fusion) to fetch businesses within a 5 km radius of the detected location.

Allow customization of:

Business type (e.g., “store”, “restaurant”)

Search radius (in kilometers or miles)

3. Website and Social Media Detection

Check if a business entry includes a website URL.

Also check for the presence of social media URLs (Facebook, Instagram, etc.).

Flag businesses with no website.

4. Local Saving

Save results to a local CSV file.

Each row will include:

Business name

Address

Category/type

Website (if any)

Social media (if any)

5. CLI-Based Output

Print a readable list of businesses without websites in the terminal.

Post-MVP Feature Ideas

Use ChatGPT API to describe what the business does (based on name and category).

Determine if a website is likely to benefit the business (e.g., service-based businesses).

Auto-generate a basic website mockup template (HTML/CSS/JS) tailored to the business type.

Export results as JSON in addition to CSV.

Integrate a local map view using Folium or similar for spatial reference.

Use Case / Why This Matters

This tool supports freelance developers or agencies in identifying potential clients who could benefit from a professional website. Many small, local businesses still lack a web presence, and having a targeted, automated way to detect these opportunities allows developers to:

Reach out with personalized mockups

Demonstrate initiative and value

Increase likelihood of converting cold leads into paying clients

Tech Stack

Language: Python 3.x

CLI Tooling: argparse, click (optional)

APIs: OpenStreetMap Nominatim, Yelp Fusion (or similar)

Libraries: requests, csv, geocoder, json, pandas

Optional AI: OpenAI GPT API for business description evaluation

Assumptions

Internet access is available for geolocation and API queries.

User has access to free API keys (e.g., for Yelp Fusion if used).

Businesses in results include at least minimal metadata (name, address, category).

Clarifying Answers Incorporated

✅ Manual location fallback is supported.

✅ Free APIs will be used (OpenStreetMap/Yelp Fusion).

✅ Output saved to local CSV.

✅ Tool should be cross-platform (Linux, Mac, Windows).

✅ CLI interface only (no GUI).

❌ No filtering by hours/rating; ✅ GPT API will eventually assess website need.

✅ Social links noted in addition to website.

Suggestions for Added Impact

Include email outreach templates for cold contacting businesses.

Add logic to group businesses by industry or relevance.

Create summary statistics: % of businesses with no website, by category.

Enable tagging businesses as "contacted," "interested," or "converted."

Add a lead management dashboard (post-MVP) to track progress per business.

Let me know if you want help generating the GitHub README or setting up the repo structure for this.
