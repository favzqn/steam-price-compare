import requests
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import time
import sys

# Exchange rate (approximate)
UAH_TO_IDR = 380  # 1 UAH = 380 IDR (approximate)

def get_steam_games(max_pages: int = 100) -> List[Dict]:
    games = set()
    
    try:
        print("\nStarting Steam game search...")
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        }
        
        # Get all games from Steam's search API
        search_url = "https://store.steampowered.com/api/featuredcategories"
        print(f"\nFetching featured categories from: {search_url}")
        
        response = requests.get(
            search_url,
            headers=headers,
            params={
                'cc': 'ua',
                'l': 'english'
            }
        )
        print(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response data keys: {list(data.keys())}")
            
            # Process each category
            for category in data.values():
                if isinstance(category, dict):
                    print(f"\nProcessing category: {category.get('name', 'Unknown')}")
                    items = category.get('items', [])
                    print(f"Found {len(items)} items in category")
                    
                    for item in items:
                        app_id = str(item.get('id'))
                        name = item.get('name')
                        print(f"Found game: {name} (ID: {app_id})")
                        
                        if app_id and name:
                            if (app_id, name) not in games:
                                print(f"Adding new game: {name}")
                            games.add((app_id, name))
            
            print(f"\nTotal featured games found: {len(games)}")
            
            # Now get top sellers
            print("\nFetching top sellers...")
            top_sellers_url = "https://store.steampowered.com/api/featuredcategories/TopSellers"
            
            response = requests.get(
                top_sellers_url,
                headers=headers,
                params={
                    'cc': 'ua',
                    'l': 'english'
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                print(f"Found {len(items)} top sellers")
                
                for item in items:
                    app_id = str(item.get('id'))
                    name = item.get('name')
                    print(f"Found top seller: {name} (ID: {app_id})")
                    
                    if app_id and name:
                        if (app_id, name) not in games:
                            print(f"Adding new game: {name}")
                        games.add((app_id, name))
                
                print(f"Total games after adding top sellers: {len(games)}")
            else:
                print(f"Error fetching top sellers: {response.text}")
        else:
            print(f"Error in initial request: {response.text}")
    except Exception as e:
        print(f"Error fetching games: {e}")
    
    filtered_games = [{'appid': id, 'name': name} for id, name in games if name]
    print(f"Total unique games found: {len(filtered_games)}")
    return filtered_games

def get_game_details(app_id: str, region: str) -> Optional[Dict]:
    url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc={region}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data and data.get(app_id, {}).get("success"):
                return data[app_id]["data"]
        time.sleep(1)  # Rate limiting
    except Exception as e:
        print(f"Error fetching {app_id} for region {region}: {e}")
    return None

def get_price_info(game_data: Dict, region: str) -> Optional[Dict]:
    try:
        price_overview = game_data.get("price_overview", {})
        if price_overview:
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
        # Get game details for both regions
        ua_details = get_game_details(app_id, "ua")
        id_details = get_game_details(app_id, "id")
        
        if not ua_details or not id_details:
            return None
            
        # Get price info
        ua_price = get_price_info(ua_details, "ua")
        id_price = get_price_info(id_details, "id")
        
        if not ua_price or not id_price:
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

def main(pages: int = 100):
    print("Fetching Steam games list...")
    games = get_steam_games(pages)
    
    # Compare prices for each game
    price_comparisons = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(compare_prices, game['appid']) for game in games]
        for future in futures:
            result = future.result()
            if result:
                price_comparisons.append(result)
    
    # Sort by price difference (highest first)
    price_comparisons.sort(key=lambda x: x['difference'], reverse=True)
    
    print(f"Found {len(price_comparisons)} games with valid prices")
    print("\nGames sorted by price difference (highest savings first):")
    print("-" * 80)
    
    for game in price_comparisons:
        ua_price = game['ua_price']['final']
        id_price = game['id_price']['final']
        
        print(f"{game['name']}")
        print(f"  UA Price: ₴{ua_price:,.2f} (Rp{game['ua_price_idr']:,.2f})")
        print(f"  ID Price: Rp{id_price:,.2f}")
        print(f"  Savings: Rp{game['difference']:,.2f} ({game['difference_percent']:.2f}%)")
        print("-" * 80)

if __name__ == "__main__":
    pages = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    main(pages)
