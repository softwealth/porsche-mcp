#!/usr/bin/env python3
"""Scrape Rennlist.com for Porsche 911 technical data across all generations."""

import json
import re
import time
import urllib.request
import urllib.error
from html import unescape
import ssl

# Disable SSL verification for scraping
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE_URL = "https://rennlist.com/forums"

# All 911-related forum sections
FORUMS = [
    {"slug": "911-forum-56", "name": "911 Forum (Air-Cooled)", "generation": "911 (1964-1989)", "gen_short": "911-classic"},
    {"slug": "911-turbo-930-forum-57", "name": "911 Turbo/930 Forum", "generation": "930 (1975-1989)", "gen_short": "930"},
    {"slug": "964-forum-59", "name": "964 Forum", "generation": "964 (1989-1994)", "gen_short": "964"},
    {"slug": "964-turbo-forum-79", "name": "964 Turbo Forum", "generation": "964 Turbo (1991-1994)", "gen_short": "964-turbo"},
    {"slug": "993-forum-58", "name": "993 Forum", "generation": "993 (1995-1998)", "gen_short": "993"},
    {"slug": "993-turbo-forum-62", "name": "993 Turbo Forum", "generation": "993 Turbo (1995-1998)", "gen_short": "993-turbo"},
    {"slug": "996-forum-60", "name": "996 Forum", "generation": "996 (1999-2004)", "gen_short": "996"},
    {"slug": "996-turbo-forum-61", "name": "996 Turbo Forum", "generation": "996 Turbo (2001-2005)", "gen_short": "996-turbo"},
    {"slug": "996-gt2-gt3-forum-103", "name": "996 GT2/GT3 Forum", "generation": "996 GT2/GT3", "gen_short": "996-gt"},
    {"slug": "997-forum-113", "name": "997 Forum", "generation": "997 (2005-2012)", "gen_short": "997"},
    {"slug": "997-turbo-forum-139", "name": "997 Turbo Forum", "generation": "997 Turbo (2007-2013)", "gen_short": "997-turbo"},
    {"slug": "997-gt2-gt3-forum-141", "name": "997 GT2/GT3 Forum", "generation": "997 GT2/GT3", "gen_short": "997-gt"},
    {"slug": "991-221", "name": "991 Forum", "generation": "991 (2012-2019)", "gen_short": "991"},
    {"slug": "991-gt3-gt3rs-gt2rs-and-911r-229", "name": "991 GT3/GT3RS/GT2RS/911R Forum", "generation": "991 GT3/GT2RS/911R", "gen_short": "991-gt"},
    {"slug": "991-turbo-230", "name": "991 Turbo Forum", "generation": "991 Turbo (2014-2019)", "gen_short": "991-turbo"},
    {"slug": "992-245", "name": "992 Forum", "generation": "992 (2020+)", "gen_short": "992"},
    {"slug": "992-gt3-and-gt2rs-forum-256", "name": "992 GT3/GT2RS Forum", "generation": "992 GT3/GT2RS", "gen_short": "992-gt"},
    {"slug": "992-turbo-and-turbo-s-258", "name": "992 Turbo Forum", "generation": "992 Turbo (2021+)", "gen_short": "992-turbo"},
    {"slug": "general-diy-forum-140", "name": "General DIY Forum", "generation": "All 911s", "gen_short": "general-diy"},
    {"slug": "performance-modifications-forum-66", "name": "Performance Modifications Forum", "generation": "All 911s", "gen_short": "performance"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def fetch_page(url, retries=3):
    """Fetch a page with retries."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                data = resp.read()
                try:
                    return data.decode('utf-8')
                except:
                    return data.decode('latin-1', errors='replace')
        except Exception as e:
            print(f"  Attempt {attempt+1} failed for {url}: {e}")
            if attempt < retries - 1:
                time.sleep(2)
    return None


def categorize_thread(title):
    """Categorize a thread based on its title keywords."""
    title_lower = title.lower()
    
    engine_kw = ['engine', 'motor rebuild', 'ims', 'bore score', 'cylinder', 'piston', 'oil leak',
                 'oil change', 'oil level', 'oil temp', 'coolant', 'radiator', 'turbo', 'supercharg',
                 'exhaust', 'header', 'intake', 'throttle', 'fuel', 'injector', 'spark plug',
                 'ignition', 'camshaft', 'cam chain', 'valve', 'timing chain', 'timing belt',
                 'head gasket', 'engine rebuild', 'engine swap', 'compression', 'misfire',
                 'overheat', 'smoke', 'knock', 'rattle', 'air filter', 'maf', 'o2 sensor',
                 'catalytic', 'muffler', 'tune ', 'tuning', 'ecu', 'dme', 'chip', 'horsepower',
                 'torque', 'dyno', 'boost', 'wastegate', 'intercooler', 'airbox', 'plenum',
                 'rpm', 'idle', 'stall', 'won\'t start', 'no start', 'crank', 'alternator',
                 'water pump', 'thermostat', 'fan belt', 'serpentine', 'tensioner',
                 'rear main seal', 'rms', 'air-oil separator', 'aos', 'varioram', 'variocam',
                 'sai ', 'secondary air', 'air pump', 'carrera engine', 'flat six',
                 'flat-6', 'nikasil', 'alusil', 'bore', 'piston slap']
    
    trans_kw = ['transmission', 'gearbox', 'clutch', 'flywheel', 'shift', 'gear',
                'synchro', 'tiptronic', 'pdk', 'manual trans', 'stick shift', 'linkage',
                'shift cable', 'differential', 'diff ', 'axle', 'cv joint', 'cv boot',
                'driveshaft', 'lsd', 'g50', 'g96', 'g97', 'getrag']
    
    suspension_kw = ['suspension', 'spring', 'shock', 'strut', 'coilover', 'sway bar',
                     'anti-roll', 'control arm', 'bushing', 'alignment', 'camber', 'toe ',
                     'ride height', 'lowering', 'pasm', 'damper', 'wheel bearing', 'tie rod',
                     'ball joint', 'steering rack', 'power steering', 'wheel', 'tire',
                     'rim ', 'spacer', 'hub', 'corner balance', 'handling', 'roll bar',
                     'sway', 'koni', 'bilstein', 'ohlins', 'h&r', 'eibach']
    
    brake_kw = ['brake', 'rotor', 'pad', 'caliper', 'brake fluid', 'bleed', 'abs',
                'pccb', 'ceramic brake', 'brake line', 'master cylinder', 'booster',
                'parking brake', 'e-brake', 'handbrake', 'big brake', 'bbk',
                'brembo', 'stoptech']
    
    electrical_kw = ['electrical', 'wiring', 'fuse', 'relay', 'battery', 'charging',
                     'headlight', 'tail light', 'led', 'bulb', 'switch',
                     'sensor', 'gauge', 'instrument cluster', 'speedo', 'tach',
                     'check engine', 'cel ', 'fault code', 'diagnostic', 'obd',
                     'pcm ', 'central locking', 'window regulator', 'window motor',
                     'alarm', 'immobilizer', 'key fob', 'remote',
                     'radio', 'stereo', 'speaker', 'navigation', 'nav ', 'bluetooth',
                     'carplay', 'screen', 'display', 'camera', 'radar detector']
    
    interior_kw = ['interior', 'seat', 'carpet', 'dashboard', 'dash crack', 'trim',
                   'leather', 'alcantara', 'steering wheel', 'shift knob', 'pedal',
                   'floor mat', 'headliner', 'visor', 'mirror', 'door panel', 'console',
                   'hvac', 'heater', 'air conditioning', 'a/c ', ' ac ', 'blower',
                   'vent', 'defroster', 'climate', 'upholstery']
    
    exterior_kw = ['exterior', 'paint', 'body', 'bumper', 'fender', 'hood', 'trunk lid',
                   'decklid', 'spoiler', 'wing', 'aero', 'wrap', 'clear bra', 'ppf',
                   'ceramic coat', 'wax', 'polish', 'detail', 'dent', 'scratch',
                   'rust', 'corrosion', 'convertible top', 'targa top', 'seal',
                   'weatherstrip', 'gasket', 'windshield', 'glass', 'wiper',
                   'bumperette', 'ducktail']
    
    maintenance_kw = ['maintenance', 'service', 'diy', 'how to', 'howto', 'step by step',
                      'tutorial', 'guide', 'install', 'replacement',
                      'fluid change', 'filter change', 'schedule', 'interval',
                      'mileage', 'inspection', 'pre-purchase', 'ppi', 'buying guide',
                      'common issues', 'known problems', 'faq', 'tips', 'tricks',
                      'tool', 'jack', 'lift']
    
    for kw in engine_kw:
        if kw in title_lower:
            return "engine"
    for kw in trans_kw:
        if kw in title_lower:
            return "transmission"
    for kw in suspension_kw:
        if kw in title_lower:
            return "suspension"
    for kw in brake_kw:
        if kw in title_lower:
            return "brakes"
    for kw in electrical_kw:
        if kw in title_lower:
            return "electrical"
    for kw in interior_kw:
        if kw in title_lower:
            return "interior"
    for kw in exterior_kw:
        if kw in title_lower:
            return "exterior"
    for kw in maintenance_kw:
        if kw in title_lower:
            return "maintenance"
    
    return "general"


def generate_summary(title, generation, category):
    """Generate a brief summary from the thread title and context."""
    title_clean = title.strip()
    gen = generation.split('(')[0].strip()
    
    cats = {
        "engine": "engine/powertrain",
        "transmission": "transmission/drivetrain",
        "suspension": "suspension/handling",
        "brakes": "braking system",
        "electrical": "electrical/electronics",
        "interior": "interior/comfort",
        "exterior": "exterior/body",
        "maintenance": "maintenance/DIY",
        "general": "technical"
    }
    cat_desc = cats.get(category, "technical")
    return f"Porsche {gen} {cat_desc} discussion: {title_clean}"


def extract_threads_from_html(html, forum_info):
    """Extract thread data from a forum page HTML."""
    threads = []
    
    # Find all thread blocks using td_threadtitle pattern
    # Each thread has: td_threadtitle_{ID} with a title attribute containing description
    # Then thread_title_{ID} for the actual link
    # Then a nearby div with title="Replies: X, Views: Y"
    
    # Strategy: find each thread_title link and its surrounding context
    thread_pattern = re.compile(
        r'id="td_threadtitle_(\d+)".*?'
        r'id="thread_title_\1"[^>]*>(.*?)</a>.*?'
        r'Replies:\s*([\d,]+),\s*Views:\s*([\d,]+)',
        re.DOTALL
    )
    
    # Also check for sticky markers before each thread
    sticky_sections = set()
    # Find the "Sticky Threads" section marker
    sticky_start = html.find('Sticky Threads')
    if sticky_start >= 0:
        # Find where normal threads begin (after sticky section)
        normal_start = html.find('Normal Threads', sticky_start)
        if normal_start < 0:
            # Look for the threadbit divider after stickies
            # Find thread_title IDs in the sticky section
            pass
        sticky_section = html[sticky_start:normal_start] if normal_start > sticky_start else html[sticky_start:sticky_start+50000]
        sticky_ids = re.findall(r'thread_title_(\d+)', sticky_section)
        sticky_sections = set(sticky_ids)
    
    # Also detect sticky by sticky.gif near thread
    sticky_gif_pattern = re.compile(r'sticky\.gif.*?thread_title_(\d+)|thread_title_(\d+).*?sticky\.gif', re.DOTALL)
    
    for match in thread_pattern.finditer(html):
        thread_id = match.group(1)
        title_raw = match.group(2)
        replies_str = match.group(3)
        views_str = match.group(4)
        
        title = unescape(re.sub(r'<[^>]+>', '', title_raw)).strip()
        if not title:
            continue
        
        replies = int(replies_str.replace(',', ''))
        views = int(views_str.replace(',', ''))
        
        # Get thread URL
        url_match = re.search(
            rf'id="thread_title_{thread_id}"[^>]*href="([^"]+)"',
            html
        )
        if not url_match:
            url_match = re.search(
                rf'href="([^"]+)"[^>]*id="thread_title_{thread_id}"',
                html
            )
        
        if url_match:
            url = url_match.group(1)
        else:
            url = f"{BASE_URL}/{forum_info['slug'].rsplit('-', 1)[0]}/{thread_id}.html"
        
        if not url.startswith('http'):
            url = f"https://rennlist.com{url}" if url.startswith('/') else f"https://rennlist.com/forums/{url}"
        
        is_sticky = thread_id in sticky_sections
        
        # Also check proximity to sticky.gif
        thread_pos = html.find(f'thread_title_{thread_id}')
        if thread_pos >= 0:
            nearby = html[max(0, thread_pos-500):thread_pos]
            if 'sticky.gif' in nearby:
                is_sticky = True
        
        # Get thread description from td_threadtitle title attribute
        desc_match = re.search(
            rf'id="td_threadtitle_{thread_id}"[^>]*title="([^"]*)"',
            html
        )
        description = ""
        if desc_match:
            description = unescape(desc_match.group(1)).strip()[:200]
        
        category = categorize_thread(title)
        
        thread = {
            "title": title,
            "url": url,
            "thread_id": thread_id,
            "generation": forum_info["generation"],
            "gen_short": forum_info["gen_short"],
            "forum": forum_info["name"],
            "category": category,
            "views": views,
            "replies": replies,
            "is_sticky": is_sticky,
            "description": description,
            "summary": generate_summary(title, forum_info["generation"], category)
        }
        threads.append(thread)
    
    return threads


def scrape_forum(forum_info, pages_regular=2, pages_by_views=3):
    """Scrape a forum - first by recency, then sorted by views for top threads."""
    all_threads = {}
    slug = forum_info["slug"]
    
    # Phase 1: Scrape first pages (most recent, includes stickies)
    for page in range(1, pages_regular + 1):
        if page == 1:
            url = f"{BASE_URL}/{slug}/"
        else:
            url = f"{BASE_URL}/{slug.rsplit('-', 1)[0]}-{slug.rsplit('-', 1)[1]}-{page}.html"
        
        print(f"  Page {page} (recent): {url}")
        html = fetch_page(url)
        
        if not html:
            # Try alternative URL format
            if page > 1:
                url = f"{BASE_URL}/{slug}-{page}.html"
                print(f"  Retry alt URL: {url}")
                html = fetch_page(url)
            if not html:
                continue
        
        threads = extract_threads_from_html(html, forum_info)
        for t in threads:
            all_threads[t['thread_id']] = t
        
        print(f"    Found {len(threads)} threads")
        time.sleep(1.0)
    
    # Phase 2: Scrape sorted by views (most popular threads)
    for page in range(1, pages_by_views + 1):
        if page == 1:
            url = f"{BASE_URL}/{slug}/?daysprune=-1&order=desc&sort=views"
        else:
            # vBulletin uses different page format with params
            fid = slug.rsplit('-', 1)[1]
            url = f"{BASE_URL}/forumdisplay.php?f={fid}&order=desc&sort=views&daysprune=-1&page={page}"
        
        print(f"  Page {page} (by views): {url}")
        html = fetch_page(url)
        
        if not html:
            continue
        
        threads = extract_threads_from_html(html, forum_info)
        for t in threads:
            if t['thread_id'] not in all_threads:
                all_threads[t['thread_id']] = t
            elif t['views'] > all_threads[t['thread_id']].get('views', 0):
                all_threads[t['thread_id']] = t
        
        print(f"    Found {len(threads)} threads")
        time.sleep(1.0)
    
    # Phase 3: Sort by replies (most discussed)
    url = f"{BASE_URL}/{slug}/?daysprune=-1&order=desc&sort=replycount"
    print(f"  By replies: {url}")
    html = fetch_page(url)
    if html:
        threads = extract_threads_from_html(html, forum_info)
        for t in threads:
            if t['thread_id'] not in all_threads:
                all_threads[t['thread_id']] = t
        print(f"    Found {len(threads)} threads")
    time.sleep(1.0)
    
    return list(all_threads.values())


def main():
    print("=" * 60)
    print("Rennlist.com 911 Technical Forum Scraper")
    print("=" * 60)
    
    all_threads = []
    
    for forum in FORUMS:
        print(f"\n{'='*50}")
        print(f"Scraping: {forum['name']} ({forum['generation']})")
        print(f"{'='*50}")
        
        threads = scrape_forum(forum, pages_regular=2, pages_by_views=3)
        print(f"  >>> Total unique: {len(threads)} threads from {forum['name']}")
        all_threads.extend(threads)
    
    # Final deduplication
    seen = {}
    for t in all_threads:
        tid = t['thread_id']
        if tid not in seen:
            seen[tid] = t
        elif t.get('views', 0) > seen[tid].get('views', 0):
            seen[tid] = t
    
    all_threads = list(seen.values())
    
    # Sort by views descending
    all_threads.sort(key=lambda x: x.get('views', 0), reverse=True)
    
    print(f"\n{'=' * 60}")
    print(f"TOTAL unique threads scraped: {len(all_threads)}")
    
    # Stats
    gen_counts = {}
    cat_counts = {}
    for t in all_threads:
        gen = t.get('gen_short', 'unknown')
        cat = t.get('category', 'unknown')
        gen_counts[gen] = gen_counts.get(gen, 0) + 1
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    
    print("\nBy generation:")
    for gen, count in sorted(gen_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {gen}: {count}")
    
    print("\nBy category:")
    for cat, count in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {count}")
    
    # Save
    output_path = "/Users/superdune/reno-rennsport-mcp/data/diy/rennlist_911_tech.json"
    with open(output_path, 'w') as f:
        json.dump(all_threads, f, indent=2)
    
    print(f"\nSaved {len(all_threads)} threads to {output_path}")
    
    # Top threads
    print("\nTop 30 threads by view count:")
    for i, t in enumerate(all_threads[:30]):
        views_str = f"{t.get('views', 0):>10,}"
        sticky_str = " [STICKY]" if t.get('is_sticky') else ""
        print(f"  {i+1:3}. [{t['gen_short']:12}] {views_str} views | {t['title'][:65]}{sticky_str}")


if __name__ == "__main__":
    main()
