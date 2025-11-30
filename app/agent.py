# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import os
import json
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

import google.auth
from google.adk.agents import Agent
from google.adk.apps.app import App
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import Gemini
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.google_search_tool import google_search
from google.genai import types

_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")


retry_config = types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504], # Retry on these HTTP errors
)


SEVEN_TIMER_API_URL = "https://www.7timer.info/bin/api.pl"


def fetch_astro_weather_7timer(longitude: float, latitude: float, product: str = "astro", output: str = "json") -> dict:
    """
    Get astronomy-oriented weather from 7timer and return the JSON response.
    Example endpoint: https://www.7timer.info/bin/api.pl?lon=2.32&lat=48.859&product=astro&output=json

    Should be used for one location at a time.
    Args:
        longitude: Longitude of the location.
        latitude: Latitude of the location.

    Returns: json with weather data with step of 3 hours.

    """
    params = urllib.parse.urlencode({"lon": longitude, "lat": latitude, "product": product, "output": output})
    url = f"{SEVEN_TIMER_API_URL}?{params}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.load(response)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"7timer request failed: {exc}", "url": url}


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"

# Google Search agent
google_search_agent = LlmAgent(
    name="google_search_agent",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    description="Searches for locations for astronomy observations using google search. Also can search for specific info about astronomy observation locations.",
    instruction="""Use the google_search tool to find locations for astronomy observations around the user's location in a smart way. 
    Give the list with your findings. Each location should have: name, description (from the source), describe source (blog / forum / Reddit), coordinates super important (latitude, longitude), 
    When searching for locations suitable for astronomical observations, please use the Google Search Agent to prioritize information and recommendations from specialized astronomy forums, amateur astronomy blogs, and astronomy club websites.
    For your search use astronomy forums and Reddit posts primarily. It's fine to get 2-5 locations.""",
    output_key='search_findings',
    tools=[google_search]
)


astro_weather_agent = LlmAgent(
    name="astro_weather_agent",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    description="Gets the astronomy weather for given locations using the astro_weather tool. I can only search for weather if you provide including the latitude and longitude.",
    instruction="""Use the astro_weather tool to find weather for locations using (latitude, longitude) for astronomy observations. 
    Give the list with your findings. Each location should have: name, coordinates (latitude, longitude), weather details (cloud coverage, transparency, wind, temperature). Api will return you some nice weather metrics for astronomy, but some of them can be confusing.
    Clouds from 0 to 10 where 0 - is clear sky. Prioritize cloud coverage and transparency for observation quality, and wind and temperature for human comfort, call tool one by one for each location.""",
    output_key='weather_findings',
    tools=[fetch_astro_weather_7timer]
)



root_agent = Agent(
    name="AstroResearchCoordinator",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=retry_config
    ),
    # This instruction tells the root agent HOW to use its tools (which are the other agents).
    instruction="""You are a research coordinator. # You are a helpful AI assistant designed to find the nearest locations suitable for astronomy
observations. Your primary goal is to locate 3–5 good observation spots around the user’s location and produce a final summarized answer.
1. First, you MUST call the `google_search_agent` tool to find locations for astronomy observations around the user's location in a smart way with longitude and latitude.
2. Next, after receiving the research findings, you MUST call the `astro_weather_agent` tool to get the weather for this locations.
3. Finally, present the final summary clearly to the user as your response.
It’s important for interpreting the weather: the cloud cover value returned by the tool ranges from 0 to 9, where 0 means no clouds and a clear sky,
 and 9 means fully overcast. I think that a value around 3 is still acceptable for observations, and anything above 5 may not be great.""",
    # We wrap the sub-agents in `AgentTool` to make them callable tools for the root agent.
    tools=[AgentTool(google_search_agent), AgentTool(astro_weather_agent)],
)

app = App(name="app", root_agent=root_agent)

print("✅ root_agent created.")


# root_agent = Agent(
#     name="root_agent",
#     model="gemini-2.5-flash",
#     instruction=system_instruction = """
# You are a helpful AI assistant designed to find the nearest locations suitable for astronomy observations. Your primary goal is to locate 3–5 good observation spots around the user’s location and produce a final summarized answer.

# HOW YOU OPERATE

# 1. USE SEARCHAGENT (AGENT-AS-A-TOOL) TO FIND OBSERVATION SPOTS
# - You do not call a direct search tool.
# - Instead, invoke google_search_agent, which internally uses its own search tools.
# - When calling google_search_agent, provide:
#   • User location
#   • Search radius
#   • Goal: find astronomy-friendly spots
#   • Required fields per spot:
#       - Name of the spot
#       - Short description (from the source)
#       - Source (blog / forum / Reddit)
#       - Coordinates

# Radius logic:
# - If the user is in a big city → search 5–20 km
# - If the user is in the countryside → search 50–100 km

# SearchAgent returns a list. Select 3–5 best spots.

# 2. CHECK WEATHER USING MCP TOOL `astro_weather`
# For each spot returned by SearchAgent, call astro_weather.
# Include both metric categories:

# Observation metrics (primary):
# - Cloud coverage
# - Transparency

# Human comfort metrics (secondary):
# - Wind
# - Temperature

# 3. FINAL SUMMARY STRUCTURE
# For each spot include:
# 1) Description block:
#    - Name
#    - Coordinates
#    - Description
#    - Source
# 2) Weather block:
#    - Good for observation: cloud coverage, transparency
#    - Good for humans: wind, temperature

# Example:
# I found 3 spots around San Francisco within 10–20 km:

# 1) Hawk Hill (37.826, -122.499) — from a Reddit astronomy thread.
#    A hill with low light pollution and clear western horizon.
#    Weather:
#      • Good for observation — low cloud coverage, high transparency
#      • Good for humans — light wind, 15°C

# 2) Mt. Tamalpais Lookout (37.923, -122.596) — from a stargazing blog.
#    Wide open area with stable atmospheric conditions.
#    Weather:
#      • Good for observation — medium cloud coverage, good transparency
#      • Good for humans — moderate wind, 12°C

# 3) Lake Merced Overlook (37.723, -122.493) — from an astronomy forum.
#    Easy access, minimal local lights.
#    Weather:
#      • Good for observation — low clouds, medium transparency
#      • Good for humans — calm wind, 14°C

# 4. IF NO SPOTS FOUND
# Politely inform the user.

# KEY RULES
# - Always call SearchAgent first.
# - Always call astro_weather for each spot.
# - Weather must be included in the final answer.
# - Prioritize cloud coverage & transparency.
# - Structure answers cleanly and consistently.
# """
