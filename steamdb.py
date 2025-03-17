import requests
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import time
import sys
import csv
from datetime import datetime

# Configuration
UAH_TO_IDR = 380  # 1 UAH = 380 IDR (approximate)
DEFAULT_PAGES = 20  # Number of pages to fetch from Steam (50 games per page)

def get_steam_games(max_pages: int = DEFAULT_PAGES, max_retries: int = 3) -> List[Dict]:
    games = []
    
    try:
        print("\nStarting Steam game search...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
            'Accept': 'text/javascript, text/html, application/xml, text/xml, */*',
            'Accept-Language': 'en',
            'X-Requested-With': 'XMLHttpRequest',
            'X-Prototype-Version': '1.7'
        }
        
        # Steam search endpoint
        search_url = "https://store.steampowered.com/search/results"
        
        for page in range(max_pages):
            # Add longer delay between pages
            if page > 0:
                sleep_time = 3
                print(f"Waiting {sleep_time}s before fetching next page...")
                time.sleep(sleep_time)
                
            print(f"\nFetching page {page + 1}...")
            
            # Try multiple times with exponential backoff
            for attempt in range(max_retries):
                if attempt > 0:
                    sleep_time = min(2 ** attempt, 16)  # Cap at 16 seconds
                    print(f"Retrying page {page + 1} after {sleep_time}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(sleep_time)
                
                response = requests.get(
                    search_url,
                    headers=headers,
                    params={
                        'force_infinite': '1',
                        'supportedlang': 'english',
                        'ndl': '1',
                        'json': '1',
                        'category1': '998',  # Games category
                        'specials': '1',    # Games with discounts
                        'start': page * 50,
                        'count': 50,
                        'cc': 'ua',
                        'l': 'english',
                        'sort_by': '_ASC',   # Sort by relevance/popularity
                    }
                )
                
                if response.status_code == 429:  # Rate limited
                    if attempt == max_retries - 1:
                        print(f"Rate limited when fetching page {page + 1}")
                        return games
                    continue
            
                if response.status_code == 200:
                    data = response.json()
                    items = data.get('items', [])
                    
                    if not items:
                        print("No more games found.")
                        return games
                    
                    print(f"\nGames on page {page + 1}:")
                    for item in items:
                        name = item.get('name')
                        logo_url = item.get('logo', '')
                        
                        # Extract appid from logo URL
                        # Format: https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/2543990/...
                        import re
                        appid_match = re.search(r'/apps/([0-9]+)/', logo_url)
                        appid = appid_match.group(1) if appid_match else None
                        
                        if appid and name:
                            print(f"- {name} (ID: {appid})")
                            games.append({
                                'appid': str(appid),
                                'name': name
                            })
                    
                    # Success, move to next page
                    break
                elif response.status_code != 429:  # If not rate limited, show error
                    print(f"HTTP {response.status_code} when fetching page {page + 1}")
                    if attempt == max_retries - 1:
                        return games
            else:
                print(f"Error fetching page {page + 1}: {response.text}")
                break
                
    except Exception as e:
        print(f"Error fetching games: {e}")
    
    print(f"Total unique games found: {len(games)}")
    return games

def get_game_details(app_id: str, region: str, max_retries: int = 5) -> Optional[Dict]:
    url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc={region}"
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                sleep_time = min(2 ** attempt, 16)  # Cap at 16 seconds
                print(f"Retrying {app_id} after {sleep_time}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(sleep_time)
            
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if not data:
                    print(f"No data for {app_id}")
                    return None
                
                app_data = data.get(app_id, {})
                if not app_data.get("success"):
                    print(f"Unsuccessful response for {app_id}")
                    return None
                    
                # Add delay after successful request
                time.sleep(3)
                return app_data["data"]
                
            elif response.status_code == 429:  # Too Many Requests
                if attempt == max_retries - 1:
                    print(f"Rate limited for {app_id} after {max_retries} retries")
                continue
            else:
                print(f"HTTP {response.status_code} for {app_id}")
                if attempt < max_retries - 1:
                    continue
                return None
                
        except Exception as e:
            print(f"Error for {app_id}: {e}")
            if attempt < max_retries - 1:
                continue
            return None
            
    return None

def get_price_info(game_data: Dict, region: str) -> Optional[Dict]:
    try:
        price_overview = game_data.get("price_overview")
        if not price_overview:
            # Game might be free, unreleased, or not available in region
            return None
            
        return {
            'currency': price_overview.get('currency'),
            'initial': price_overview.get('initial', 0) / 100,  # Convert to actual currency
            'final': price_overview.get('final', 0) / 100,
            'discount_percent': price_overview.get('discount_percent', 0)
        }
    except Exception as e:
        print(f"Error getting price info for region {region}: {e}")
    return None

def calculate_price_difference(id_price: float, ua_price: float) -> Tuple[float, float]:
    """Calculate absolute and percentage difference between prices"""
    if id_price == 0 or ua_price == 0:
        return 0, 0
    difference = abs(id_price - ua_price)
    percentage = (difference / max(id_price, ua_price)) * 100
    return difference, percentage

def get_idr_equivalent(uah_price: float) -> float:
    """Convert UAH price to IDR"""
    return uah_price * UAH_TO_IDR

def compare_prices(app_id: str) -> Optional[Dict]:
    """Compare prices between UA and ID regions"""
    try:
        # Get game details for both regions with delay between requests
        ua_details = get_game_details(app_id, "ua")
        if not ua_details:
            return None
            
        # Add extra delay between regions
        time.sleep(3)
        
        id_details = get_game_details(app_id, "id")
        if not id_details:
            return None
            
        # Get price info
        ua_price = get_price_info(ua_details, "ua")
        id_price = get_price_info(id_details, "id")
        
        if not ua_price:
            print(f"No UA price data for {app_id}")
            return None
        if not id_price:
            print(f"No ID price data for {app_id}")
            return None
            
        # Convert UA price to IDR for comparison
        ua_price_idr = get_idr_equivalent(ua_price['final'])
        
        # Calculate difference
        difference, percentage = calculate_price_difference(id_price['final'], ua_price_idr)
        
        return {
            'name': ua_details.get('name', ''),
            'ua_price': ua_price,
            'id_price': id_price,
            'ua_price_idr': ua_price_idr,
            'difference': difference,
            'difference_percent': percentage
        }
    except Exception as e:
        print(f"Error comparing prices for {app_id}: {e}")
        return None

def main(pages: int = DEFAULT_PAGES):
    print("Fetching Steam games list...")
    games = get_steam_games(pages)
    
    # Deduplicate games by appid
    unique_games = {}
    for game in games:
        unique_games[game['appid']] = game
    games = list(unique_games.values())
    
    total_games = len(games)
    print(f"\nStarting price comparison for {total_games} unique games...")
    
    # Compare prices for each game
    price_comparisons = []
    completed = 0
    
    # Reduce concurrent workers to avoid rate limits
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(compare_prices, game['appid']) for game in games]
        for future, game in zip(futures, games):
            completed += 1
            print(f"Processing {completed}/{total_games}: {game['name']}", end="")
            result = future.result()
            if result:
                price_comparisons.append(result)
                print(f" - ✓ Found prices")
            else:
                print(" - ✗ No price data")
    
    # Sort by price difference (highest first)
    price_comparisons.sort(key=lambda x: x['difference'], reverse=True)
    
    print(f"Found {len(price_comparisons)} games with valid prices")
    print("\nGames sorted by price difference (highest savings first):")
    print("-" * 80)
    
    # Create CSV filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'steam_price_comparison_{timestamp}.csv'
    
    # Write results to CSV
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Name', 'UA Price (UAH)', 'UA Price (IDR)', 'ID Price (IDR)', 'Savings (IDR)', 'Savings (%)']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for game in price_comparisons:
            ua_price = game['ua_price']['final']
            id_price = game['id_price']['final']
            
            writer.writerow({
                'Name': game['name'],
                'UA Price (UAH)': f'{ua_price:,.2f}',
                'UA Price (IDR)': f'{game["ua_price_idr"]:,.2f}',
                'ID Price (IDR)': f'{id_price:,.2f}',
                'Savings (IDR)': f'{game["difference"]:,.2f}',
                'Savings (%)': f'{game["difference_percent"]:.2f}'
            })
    
    print(f"\nResults have been exported to: {csv_filename}")
    
    # Also print to console
    for game in price_comparisons:
        ua_price = game['ua_price']['final']
        id_price = game['id_price']['final']
        
        print(f"{game['name']}")
        print(f"  UA Price: ₴{ua_price:,.2f} (Rp{game['ua_price_idr']:,.2f})")
        print(f"  ID Price: Rp{id_price:,.2f}")
        print(f"  Savings: Rp{game['difference']:,.2f} ({game['difference_percent']:.2f}%)")
        print("-" * 80)

if __name__ == "__main__":
    pages = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PAGES
    main(pages)
