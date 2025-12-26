# Tumblr Profile Finder

A Python program that searches Tumblr for blog profiles matching specific themes and located in California/Bay Area.

## Features

- Searches Tumblr posts by theme tags
- Extracts and analyzes blog profiles
- Filters blogs by location (California/Bay Area cities)
- Filters by activity level and follower count
- Exports results to JSON and CSV formats
- Handles API rate limiting and pagination
- Deduplicates blogs found across multiple theme searches

## Requirements

- Python 3.7 or higher
- Tumblr API credentials (OAuth 1.0a)

## Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Tumblr API credentials (see next section)

## Getting Tumblr API Credentials

1. Go to https://www.tumblr.com/oauth/apps
2. Click "Register application"
3. Fill in the application details:
   - Application Name: (your choice)
   - Application Website: (can be http://localhost for testing)
   - Default callback URL: (can be http://localhost for testing)
4. After registration, you'll receive:
   - OAuth Consumer Key
   - OAuth Consumer Secret
5. Click "Explore API" or use a tool to get your OAuth Token and OAuth Secret

## Configuration

Set the following environment variables with your Tumblr API credentials:

**Windows (Command Prompt):**
```cmd
set TUMBLR_CONSUMER_KEY=your_consumer_key_here
set TUMBLR_CONSUMER_SECRET=your_consumer_secret_here
set TUMBLR_OAUTH_TOKEN=your_oauth_token_here
set TUMBLR_OAUTH_SECRET=your_oauth_secret_here
```

**Windows (PowerShell):**
```powershell
$env:TUMBLR_CONSUMER_KEY="your_consumer_key_here"
$env:TUMBLR_CONSUMER_SECRET="your_consumer_secret_here"
$env:TUMBLR_OAUTH_TOKEN="your_oauth_token_here"
$env:TUMBLR_OAUTH_SECRET="your_oauth_secret_here"
```

**Linux/Mac:**
```bash
export TUMBLR_CONSUMER_KEY=your_consumer_key_here
export TUMBLR_CONSUMER_SECRET=your_consumer_secret_here
export TUMBLR_OAUTH_TOKEN=your_oauth_token_here
export TUMBLR_OAUTH_SECRET=your_oauth_secret_here
```

Alternatively, create a `.env` file (see `.env.example`) and load it before running.

## Usage

### Basic Usage

Run with default theme tags:
```bash
python tumblr_profile_finder.py
```

### Custom Theme Tags

Search specific themes:
```bash
python tumblr_profile_finder.py --themes "ddlg,littlespace,agere"
```

### Full Command Line Options

```bash
python tumblr_profile_finder.py --themes "theme1,theme2" --output results --max-posts-per-theme 500 --min-followers 10 --max-days-inactive 90
```

**Arguments:**

- `--themes`: Comma-separated list of theme tags to search (default: uses predefined list)
- `--output`: Base filename for output files (default: `results`)
- `--max-posts-per-theme`: Maximum posts to retrieve per theme (default: 500)
- `--min-followers`: Minimum follower count (default: 10)
- `--max-days-inactive`: Maximum days since last post (default: 90)

## Default Theme Tags

The program searches these themes by default:
- dd/lg
- ddlg
- abdl
- ab/dl
- little
- big/little
- littlespace
- agere
- ageplay
- age regression
- adult baby
- caregiver/little
- caregiver space
- regression space

## Location Matching

Blogs are filtered to include only those with location indicators for California/Bay Area:

**States/Regions:** California, CA, Cali, NorCal, SoCal, Bay Area, Silicon Valley, East Bay, South Bay, Peninsula

**Cities:** San Francisco, SF, Oakland, Berkeley, San Jose, Los Angeles, LA, San Diego, Sacramento, Palo Alto, Mountain View, Fremont, Santa Clara, Cupertino, Menlo Park, Redwood City, Sunnyvale, Santa Monica, Venice Beach, Pasadena

Location matching checks:
- Blog URL
- Blog title
- Blog description
- Blog tags

## Filtering Criteria

A blog must meet ALL of these to be included:
- Has at least one location indicator match
- Follower count greater than the minimum (default: 10)
- Most recent post within the maximum days inactive (default: 90 days)

## Output

The program generates two files:

### JSON Output (`results.json`)
Contains full blog data with all fields in JSON array format.

### CSV Output (`results.csv`)
Contains the same data in spreadsheet-friendly CSV format with columns:
- blog_name
- blog_url
- title
- description
- follower_count
- total_posts
- last_post_date
- location_match_term
- location_match_source
- blog_tags
- theme_matched

## Rate Limiting

The program includes built-in delays to respect Tumblr's API rate limits:
- 1 second between tag search requests
- 0.5 seconds between blog info requests

## Error Handling

- API errors are logged but don't stop the search
- Missing blog data is handled gracefully
- Keyboard interrupt (Ctrl+C) will save results found so far

## Example Output

```
Starting search for 14 theme tags...
Filters: min_followers=10, max_days_inactive=90

Searching theme: 'dd/lg'
  Retrieved 20 posts, found 15 unique blogs so far
  Retrieved 40 posts, found 28 unique blogs so far
  ...
  Total blogs found for 'dd/lg': 150

Processing 150 blogs from theme 'dd/lg'...
  Processed 10/150, qualified: 3
  Processed 20/150, qualified: 7
  ...
  Finished processing. Qualified: 25/150

============================================================
Search complete! Total qualifying blogs: 127
============================================================

Exported to JSON: results.json
Exported to CSV: results.csv

Done!
```

## Troubleshooting

**"Missing Tumblr API credentials" error:**
- Make sure all four environment variables are set correctly

**No results found:**
- Try reducing `--min-followers` threshold
- Try increasing `--max-days-inactive` threshold
- Verify your API credentials are valid

**Rate limit errors:**
- The program includes delays, but if you still hit limits, try searching fewer themes at once

## License

This is a utility script for personal use. Respect Tumblr's Terms of Service and API usage guidelines.
