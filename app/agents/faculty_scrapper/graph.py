import asyncio
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from .scrappers import directory_to_profiles, scrape_profiles, infer_university_from_url
from .llm import summarize_batch
from .utils import normalize_record, to_csv_base64

class ScrapeState(TypedDict, total=False):
    directory_url: str
    provider: str | None
    max_profiles: int | None
    profile_urls: List[str]
    raw_profiles: List[Dict[str, str]]      # {"url","text","email_hint"}
    summaries: List[Dict[str, Any]]         # raw LLM JSONs
    normalized: List[Dict[str, Any]]        # normalized to flat schema
    csv_filename: str
    csv_base64: str

async def node_collect(state: ScrapeState) -> ScrapeState:
    urls = await directory_to_profiles(state["directory_url"], state.get("max_profiles"))
    return {**state, "profile_urls": urls}

async def node_profile_scrape(state: ScrapeState) -> ScrapeState:
    raw = await scrape_profiles(state["profile_urls"])
    return {**state, "raw_profiles": raw}

async def node_summarize(state: ScrapeState) -> ScrapeState:
    uni_hint = infer_university_from_url(state["directory_url"]) or ""
    batch = [{"url": r["url"], "text": r["text"], "university": uni_hint} for r in state["raw_profiles"]]
    out = summarize_batch(batch, provider_override=state.get("provider"))
    return {**state, "summaries": out}

async def node_aggregate(state: ScrapeState) -> ScrapeState:
    norm = [normalize_record(x) for x in state["summaries"]]
    return {**state, "normalized": norm}

async def node_export(state: ScrapeState) -> ScrapeState:
    fname, b64 = to_csv_base64(state["normalized"])
    return {**state, "csv_filename": fname, "csv_base64": b64}

def build_graph():
    g = StateGraph(ScrapeState)
    g.add_node("collect", node_collect)
    g.add_node("profile_scrape", node_profile_scrape)
    g.add_node("summarize", node_summarize)
    g.add_node("aggregate", node_aggregate)
    g.add_node("export", node_export)

    g.set_entry_point("collect")
    g.add_edge("collect", "profile_scrape")
    g.add_edge("profile_scrape", "summarize")
    g.add_edge("summarize", "aggregate")
    g.add_edge("aggregate", "export")
    g.add_edge("export", END)
    return g.compile()

async def run_scraper(directory_url: str, provider: str | None, max_profiles: int | None):
    graph = build_graph()
    initial = {"directory_url": directory_url, "provider": provider, "max_profiles": max_profiles}
    return await graph.ainvoke(initial)


"""

 ┌───────────────────────┐
 │   Entry Point         │
 │   "collect"           │
 │   Input: directory URL│
 └──────────┬────────────┘
            ▼
 ┌───────────────────────┐
 │ Node: collect         │
 │ • Finds profile links │
 │ • Adds profile_urls   │
 └──────────┬────────────┘
            ▼
 ┌───────────────────────┐
 │ Node: profile_scrape  │
 │ • Visits each profile │
 │ • Extracts raw text   │
 │ • Adds raw_profiles   │
 └──────────┬────────────┘
            ▼
 ┌───────────────────────┐
 │ Node: summarize       │
 │ • Calls LLM (Gemini / │
 │   local)              │
 │ • Extracts JSON fields│
 │ • Adds summaries      │
 └──────────┬────────────┘
            ▼
 ┌───────────────────────┐
 │ Node: aggregate       │
 │ • Normalizes fields   │
 │ • Ensures flat schema │
 │ • Adds normalized[]   │
 └──────────┬────────────┘
            ▼
 ┌───────────────────────┐
 │ Node: export          │
 │ • Builds CSV + base64 │
 │ • Adds csv_filename   │
 │ • Adds csv_base64     │
 └──────────┬────────────┘
            ▼
 ┌───────────────────────┐
 │         END           │
 │ Final State: {        │
 │  directory_url,        │
 │  profile_urls,         │
 │  raw_profiles,         │
 │  summaries,            │
 │  normalized,           │
 │  csv_filename,         │
 │  csv_base64 }          │
 └───────────────────────┘




"""