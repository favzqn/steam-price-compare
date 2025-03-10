# Steam Price Comparator

A Python script to compare Steam game prices between different regions, specifically focusing on finding price differences between Ukrainian and Indonesian regions.

## Features

- Fetches featured and top-selling games from Steam
- Compares prices between Ukrainian (UAH) and Indonesian (IDR) regions
- Shows potential savings by buying from different regions
- Handles currency conversion automatically

## Requirements

- Python 3.6+
- `requests` library

## Installation

1. Clone this repository:
```bash
git clone https://github.com/favzqn/steam-price-compare.git
cd steam-price-compare
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the script with:
```bash
python steamdb.py [pages]
```

Where `pages` is an optional parameter to specify how many pages of games to fetch (default: 100).

## Example Output

```
Fetching Steam games list...
Found 50 featured games
Found 25 top sellers

Total unique games found: 75
Found 60 games with valid prices

Games sorted by price difference (highest savings first):
--------------------------------------------------------------------------------
Game Title 1
  UA Price: ₴199 (Rp75,620)
  ID Price: Rp50,000
  Savings: Rp25,620 (33.88%)
--------------------------------------------------------------------------------
...
```

## Note

This script is for educational purposes only. Please respect Steam's terms of service and regional pricing policies.

## License

MIT License
