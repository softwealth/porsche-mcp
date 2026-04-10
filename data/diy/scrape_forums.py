#!/usr/bin/env python3
"""
Scrape Porsche Cayenne Forums and Macan Forum for technical/DIY content.
Extracts thread titles, URLs, view counts, reply counts, and first-post summaries.
"""

import json
import os
import re
import time
import urllib.request
import urllib.error
import ssl
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

def fetch_url(url, retries=2):
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                return resp.read().decode('utf-8', errors='replace')
        except Exception as e:
            print(f"  [Attempt {attempt+1}] Error fetching {url}: {e}")
            if attempt < retries:
                time.sleep(2)
    return None


def parse_thread_listing(html, base_url):
    """Parse a XenForo/California-style forum thread listing page."""
    soup = BeautifulSoup(html, 'html.parser')
    threads = []
    
    for item in soup.find_all('div', class_='structItem'):
        thread = {}
        
        # Title - use qid attribute for the actual title link
        title_link = item.find('a', attrs={'qid': 'thread-item-title'})
        if not title_link:
            # Fallback: find the second /threads/ link (first is often sticky icon)
            links = item.find_all('a', href=re.compile(r'/threads/'))
            if len(links) >= 2:
                title_link = links[1]
            elif links:
                title_link = links[0]
        
        if title_link:
            thread['title'] = title_link.get_text(strip=True)
            href = title_link.get('href', '')
            if href.startswith('/'):
                thread['url'] = base_url + href
            else:
                thread['url'] = href
        
        if not thread.get('title') or thread['title'] == 'Sticky':
            continue
        
        # Reply count - from title attribute of reply-count div
        reply_div = item.find('div', class_='reply-count')
        if reply_div:
            t = reply_div.get('title', '')
            m = re.search(r'([\d,]+)', t)
            if m:
                thread['replies'] = int(m.group(1).replace(',', ''))
        
        # View count - from title attribute of view-count div
        view_div = item.find('div', class_='view-count')
        if view_div:
            t = view_div.get('title', '')
            m = re.search(r'([\d,]+)', t)
            if m:
                thread['views'] = int(m.group(1).replace(',', ''))
        
        # Fallback: try dl-based stats
        if 'views' not in thread:
            meta = item.find('div', class_='structItem-cell--meta')
            if meta:
                for dl in meta.find_all('dl'):
                    dt = dl.find('dt')
                    dd = dl.find('dd')
                    if dt and dd:
                        label = dt.get_text(strip=True).lower()
                        value = dd.get_text(strip=True)
                        if 'view' in label:
                            thread['views'] = parse_count(value)
                        elif 'repl' in label:
                            thread['replies'] = parse_count(value)
        
        # Sticky detection
        sticky_elem = item.find('i', attrs={'qid': 'thread-item-sticky'})
        thread['sticky'] = sticky_elem is not None
        
        thread.setdefault('views', 0)
        thread.setdefault('replies', 0)
        
        threads.append(thread)
    
    return threads


def parse_count(s):
    s = s.strip().replace(',', '')
    multiplier = 1
    if s.upper().endswith('K'):
        multiplier = 1000
        s = s[:-1]
    elif s.upper().endswith('M'):
        multiplier = 1000000
        s = s[:-1]
    try:
        return int(float(s) * multiplier)
    except:
        return 0


def get_thread_first_post(url):
    """Fetch a thread and extract the first post content as a summary."""
    html = fetch_url(url)
    if not html:
        return ""
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # XenForo first post
    article = soup.find('article', class_='message')
    if article:
        body = article.find('div', class_='bbWrapper')
        if body:
            text = body.get_text(separator=' ', strip=True)
            if len(text) > 500:
                text = text[:497] + '...'
            return text
    
    return ""


def categorize_thread(title, summary=""):
    text = (title + " " + summary).lower()
    
    categories = {
        'engine': ['engine', 'motor', 'cylinder', 'piston', 'bore scor', 'timing chain', 'timing cover',
                    'oil leak', 'oil consumption', 'coolant leak', 'turbo', 'intercooler', 'exhaust',
                    'intake manifold', 'spark plug', 'misfire', 'knock', 'idle rough', 'tune', 'ecu',
                    'fuel pump', 'fuel injector', 'camshaft', 'valve cover', 'head gasket', 'overheat',
                    'limp mode', 'thermostat', 'water pump', 'radiator', 'catalytic', 'o2 sensor',
                    'starter', 'alternator', 'crankshaft', 'bore score', 'engine fail', 'engine noise',
                    'check engine', 'cel', 'p0', 'fault code', 'engine light'],
        'transmission': ['transmission', 'gearbox', 'shift', 'clutch', 'tiptronic', 'pdk',
                         'torque converter', 'transfer case', 'differential', 'driveshaft',
                         'mechatronic', 'atf', 'reverse not available', 'gear slipp'],
        'suspension': ['suspension', 'shock', 'strut', 'spring', 'air ride', 'pasm', 'sway bar',
                        'control arm', 'ball joint', 'bushing', 'lowering', 'ride height',
                        'air suspension', 'compressor', 'suspension fail'],
        'brakes': ['brake pad', 'brake rotor', 'caliper', 'brake fluid', 'abs', 'pccb',
                    'wear sensor', 'brake squeal', 'brake job', 'brake fail'],
        'electrical': ['battery', 'wiring', 'fuse', 'relay', 'module', 'sensor', 'pcm', 'bcm',
                        'can bus', 'dtc', 'piwis', 'obd', 'diagnostic', 'headlight', 'taillight',
                        'led', 'waterlog', 'water damage', 'electrical', 'parasitic drain'],
        'electronics': ['infotainment', 'navigation', 'screen', 'radio', 'speaker', 'bluetooth',
                         'carplay', 'android auto', 'camera', 'display', 'acc retrofit',
                         'cruise control', 'parking sensor', 'tpms', 'key fob', 'remote',
                         'alarm', 'immobilizer', 'pcm update'],
        'cooling': ['cooling system', 'coolant hose', 'coolant reservoir', 'radiator flap',
                     'radiator shutter', 'coolant pipe', 'coolant level', 'overheat',
                     'temperature', 'fan clutch', 'coolant bypass'],
        'body': ['door', 'window regulator', 'sunroof', 'panoramic roof', 'trunk', 'hood latch',
                  'lock', 'seal', 'rust', 'corrosion', 'paint', 'body panel', 'bumper',
                  'mirror', 'wiper', 'windshield', 'tailgate', 'boot lid'],
        'wheels_tires': ['wheel', 'tire', 'rim', 'lug', 'hub bearing', 'alignment', 'fitment',
                          'offset', 'spacer', 'tyre'],
        'hvac': ['a/c ', 'air condition', 'heater', 'blower', 'climate', 'defrost',
                  'hvac', 'ac compressor', 'ac stopped', 'cold air'],
        'maintenance': ['oil change', 'diy oil', 'filter', 'service interval', 'maintenance',
                         'fluid change', 'brake fluid flush', 'coolant flush', 'diy',
                         'how to replace', 'step by step', 'procedure'],
    }
    
    scores = {}
    for cat, keywords in categories.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[cat] = score
    
    if scores:
        return max(scores, key=scores.get)
    return 'general'


def detect_model_years(title, url="", forum_section=""):
    text = (title + " " + forum_section + " " + url).lower()
    
    years = ""
    generation = ""
    
    year_matches = re.findall(r'\b((?:19|20)\d{2})\b', title)
    if year_matches:
        years_list = sorted(set(year_matches))
        if len(years_list) == 1:
            years = years_list[0]
        else:
            years = f"{years_list[0]}-{years_list[-1]}"
    
    if '955' in text or 'generation-1' in text or '2003-2010' in text:
        generation = '955/957'
        if not years:
            years = '2003-2010'
    elif '957' in text:
        generation = '957'
        if not years:
            years = '2008-2010'
    elif '958' in text or 'generation-2' in text or '2011-2018' in text:
        generation = '958'
        if not years:
            years = '2011-2018'
    elif 'generation-3' in text or '9y0' in text:
        generation = 'E3/9Y0'
        if not years:
            years = '2019+'
    
    return generation, years


def scrape_forum_sections(base_url, sections, default_model_prefix):
    """Generic scraper for forum sections."""
    results = []
    
    for path, section_name, default_model in sections:
        print(f"\n--- Scraping {default_model_prefix}: {section_name} ---")
        for page_num in range(1, 4):  # 3 pages per section
            url = base_url + path
            if page_num > 1:
                url = base_url + path + f"page-{page_num}"
            
            html = fetch_url(url)
            if not html:
                continue
            
            threads = parse_thread_listing(html, base_url)
            print(f"  Page {page_num}: Found {len(threads)} threads")
            
            if not threads:
                break
            
            for t in threads:
                gen, years = detect_model_years(t['title'], t.get('url', ''), section_name)
                category = categorize_thread(t['title'])
                
                # Detect specific variant
                title_lower = t['title'].lower()
                if default_model_prefix == 'Macan':
                    if 'gts' in title_lower:
                        model = 'Macan GTS'
                    elif 'turbo' in title_lower:
                        model = 'Macan Turbo'
                    elif 'macan s' in title_lower:
                        model = 'Macan S'
                    elif 'ev' in title_lower or 'electric' in title_lower:
                        model = 'Macan EV'
                    else:
                        model = default_model
                else:
                    if gen:
                        model = f"Cayenne {gen}"
                    elif 'turbo' in title_lower:
                        model = 'Cayenne Turbo'
                    elif 'gts' in title_lower:
                        model = 'Cayenne GTS'
                    elif 'cayenne s' in title_lower:
                        model = 'Cayenne S'
                    else:
                        model = default_model
                
                result = {
                    'title': t['title'],
                    'url': t.get('url', ''),
                    'model': model,
                    'years': years,
                    'category': category,
                    'summary': '',
                    'difficulty': '',
                    'views': t.get('views', 0),
                    'replies': t.get('replies', 0),
                    'source_section': section_name,
                    'sticky': t.get('sticky', False),
                }
                results.append(result)
            
            time.sleep(0.8)
    
    return results


def fetch_summaries_for_top_threads(results, max_threads=30):
    """Fetch first-post summaries for the top threads by views/replies."""
    # Prioritize: sticky DIY threads first, then by combined score
    def score(x):
        s = x.get('views', 0) + x.get('replies', 0) * 50
        if x.get('sticky'):
            s += 1000000
        if 'diy' in x.get('title', '').lower():
            s += 500000
        return s
    
    sorted_results = sorted(results, key=score, reverse=True)
    
    count = 0
    for item in sorted_results:
        if count >= max_threads:
            break
        if not item.get('url'):
            continue
        
        print(f"  Fetching [{item.get('views',0)}v {item.get('replies',0)}r] {item['title'][:55]}...")
        summary = get_thread_first_post(item['url'])
        if summary:
            item['summary'] = summary
            item['category'] = categorize_thread(item['title'], summary)
            
            sl = summary.lower()
            if any(w in sl for w in ['easy', 'simple', 'beginner', '10 minute', '15 minute', 'quick fix']):
                item['difficulty'] = 'easy'
            elif any(w in sl for w in ['moderate', 'intermediate', 'some experience', 'about an hour', 'couple hours']):
                item['difficulty'] = 'moderate'
            elif any(w in sl for w in ['difficult', 'advanced', 'professional', 'dealer only', 'complex', 'several hours', 'special tool', 'lift required']):
                item['difficulty'] = 'advanced'
            elif 'diy' in sl or 'step' in sl:
                item['difficulty'] = 'moderate'
        
        count += 1
        time.sleep(1.2)


def deduplicate(results):
    seen = set()
    unique = []
    for r in results:
        url = r.get('url', '')
        if url and url not in seen:
            seen.add(url)
            unique.append(r)
        elif not url:
            unique.append(r)
    return unique


def main():
    output_dir = '/Users/superdune/reno-rennsport-mcp/data/diy'
    os.makedirs(output_dir, exist_ok=True)
    
    # ========== CAYENNE ==========
    print("=" * 60)
    print("SCRAPING CAYENNE FORUMS")
    print("=" * 60)
    
    cayenne_sections = [
        ('/forums/porsche-cayenne-generation-1-forum-2003-2010.74/', 'Gen 1 (955/957) 2003-2010', 'Cayenne 955/957'),
        ('/forums/porsche-cayenne-generation-2-forum-2011-2018.82/', 'Gen 2 (958) 2011-2018', 'Cayenne 958'),
        ('/forums/porsche-cayenne-generation-3-forum-2019-current.90/', 'Gen 3 (E3) 2019+', 'Cayenne E3'),
        ('/forums/turbo-engine-forum.6/', 'Turbo Engine', 'Cayenne Turbo'),
        ('/forums/non-turbo-engine-forum.5/', 'Non-Turbo Engine', 'Cayenne'),
        ('/forums/porsche-cayenne-recalls-and-tsbs.7/', 'Recalls & TSBs', 'Cayenne'),
        ('/forums/porsche-cayenne-general-discussion.2/', 'General Discussion', 'Cayenne'),
        ('/forums/exterior-modifications-forum.8/', 'Exterior Modifications', 'Cayenne'),
        ('/forums/interior-modifications-forum.9/', 'Interior Modifications', 'Cayenne'),
        ('/forums/wheels-and-tires.4/', 'Wheels & Tires', 'Cayenne'),
    ]
    
    cayenne_results = scrape_forum_sections(
        "https://www.cayenneforums.com", cayenne_sections, "Cayenne"
    )
    cayenne_results = deduplicate(cayenne_results)
    print(f"\nTotal unique Cayenne threads: {len(cayenne_results)}")
    
    print("\nFetching summaries for top Cayenne threads...")
    fetch_summaries_for_top_threads(cayenne_results, max_threads=30)
    
    # Remove internal fields, clean up
    for r in cayenne_results:
        r.pop('sticky', None)
        r.pop('source_section', None) if not r.get('summary') else None
    
    cayenne_file = os.path.join(output_dir, 'cayenne_tech.json')
    with open(cayenne_file, 'w') as f:
        json.dump(cayenne_results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(cayenne_results)} Cayenne entries to {cayenne_file}")
    
    # ========== MACAN ==========
    print("\n" + "=" * 60)
    print("SCRAPING MACAN FORUM")
    print("=" * 60)
    
    macan_sections = [
        ('/forums/engine-and-technical-discussion.10/', 'Engine & Technical', 'Macan (95B)'),
        ('/forums/wheels-tires-brakes-and-suspension.12/', 'Wheels/Tires/Brakes/Suspension', 'Macan (95B)'),
        ('/forums/electronics.36/', 'Electronics', 'Macan (95B)'),
        ('/forums/complaints.217/', 'Complaints', 'Macan (95B)'),
        ('/forums/porsche-macan-recalls-warranty.218/', 'Recalls & Warranty', 'Macan (95B)'),
        ('/forums/modifications.209/', 'Modifications', 'Macan (95B)'),
        ('/forums/interior.90/', 'Interior', 'Macan (95B)'),
        ('/forums/appearance-and-body.11/', 'Appearance & Body', 'Macan (95B)'),
        ('/forums/macan-general-discussion-forum.9/', 'General Discussion', 'Macan (95B)'),
    ]
    
    macan_results = scrape_forum_sections(
        "https://www.macanforum.com", macan_sections, "Macan"
    )
    macan_results = deduplicate(macan_results)
    print(f"\nTotal unique Macan threads: {len(macan_results)}")
    
    print("\nFetching summaries for top Macan threads...")
    fetch_summaries_for_top_threads(macan_results, max_threads=30)
    
    for r in macan_results:
        r.pop('sticky', None)
        r.pop('source_section', None) if not r.get('summary') else None
    
    macan_file = os.path.join(output_dir, 'macan_tech.json')
    with open(macan_file, 'w') as f:
        json.dump(macan_results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(macan_results)} Macan entries to {macan_file}")
    
    # ========== STATS ==========
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, data in [("Cayenne", cayenne_results), ("Macan", macan_results)]:
        cats = {}
        with_summary = 0
        total_views = 0
        for r in data:
            c = r['category']
            cats[c] = cats.get(c, 0) + 1
            if r.get('summary'):
                with_summary += 1
            total_views += r.get('views', 0)
        print(f"\n{name} - {len(data)} threads, {with_summary} with summaries, {total_views:,} total views")
        print("  Categories:")
        for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
            print(f"    {cat}: {count}")


if __name__ == '__main__':
    main()
