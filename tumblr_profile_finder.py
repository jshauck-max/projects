#!/usr/bin/env python3
"""
Tumblr Profile Finder
Searches Tumblr for blogs matching specific themes and located in California/Bay Area
"""

import pytumblr
import argparse
import json
import csv
import os
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict

# Default theme tags to search
DEFAULT_THEME_TAGS = [
    "dd/lg",
    "ddlg",
    "abdl",
    "ab/dl",
    "little",
    "big/little",
    "littlespace",
    "agere",
    "ageplay",
    "age regression",
    "adult baby",
    "caregiver/little",
    "caregiver space",
    "regression space"
]

# Location indicators for California/Bay Area
LOCATION_INDICATORS = {
    # States/Regions
    "california", "ca", "cali", "norcal", "socal", "bay area", "silicon valley",
    "east bay", "south bay", "peninsula",
    # Cities
    "san francisco", "sf", "oakland", "berkeley", "san jose", "los angeles",
    "san diego", "sacramento", "palo alto", "mountain view", "fremont",
    "santa clara", "cupertino", "menlo park", "redwood city", "sunnyvale",
    "santa monica", "venice beach", "pasadena"
}


class TumblrProfileFinder:
    """Main class for finding and filtering Tumblr blog profiles"""

    def __init__(self, consumer_key: str, consumer_secret: str,
                 oauth_token: str, oauth_secret: str):
        """Initialize with Tumblr API credentials"""
        self.client = pytumblr.TumblrRestClient(
            consumer_key,
            consumer_secret,
            oauth_token,
            oauth_secret
        )
        self.discovered_blogs = {}  # blog_name -> blog_data
        self.blog_themes = defaultdict(set)  # blog_name -> set of theme tags

    def find_location_match(self, text_fields: Dict[str, str],
                           tags: List[str]) -> Optional[Tuple[str, str]]:
        """
        Check if any location indicator matches in the provided fields.

        Args:
            text_fields: Dict with keys like 'url', 'title', 'description'
            tags: List of blog tags

        Returns:
            Tuple of (matched_term, source) if found, None otherwise
        """
        # Check text fields (url, title, description)
        for source, text in text_fields.items():
            if not text:
                continue
            text_lower = text.lower()

            for location in LOCATION_INDICATORS:
                # Use word boundary regex for more accurate matching
                pattern = r'\b' + re.escape(location.lower()) + r'\b'
                if re.search(pattern, text_lower):
                    return (location, source)

        # Check tags
        if tags:
            tags_lower = [tag.lower() for tag in tags]
            for location in LOCATION_INDICATORS:
                for tag in tags_lower:
                    pattern = r'\b' + re.escape(location.lower()) + r'\b'
                    if re.search(pattern, tag):
                        return (location, 'tags')

        return None

    def get_blog_info(self, blog_name: str) -> Optional[Dict]:
        """
        Fetch full blog information from Tumblr API.

        Args:
            blog_name: Name of the blog

        Returns:
            Blog info dict or None if error
        """
        try:
            response = self.client.blog_info(blog_name)
            if 'blog' in response:
                return response['blog']
            else:
                print(f"  Warning: Could not fetch info for {blog_name}: {response.get('meta', {}).get('msg', 'Unknown error')}")
                return None
        except Exception as e:
            print(f"  Error fetching blog info for {blog_name}: {e}")
            return None

    def meets_criteria(self, blog_info: Dict, min_followers: int,
                       max_days_inactive: int) -> Tuple[bool, Optional[datetime]]:
        """
        Check if blog meets filtering criteria.

        Args:
            blog_info: Blog information dict
            min_followers: Minimum follower count
            max_days_inactive: Maximum days since last post

        Returns:
            Tuple of (meets_criteria, last_post_date)
        """
        # Check follower count
        followers = blog_info.get('total_followers', 0)
        if followers < min_followers:
            return (False, None)

        # Check last post date
        updated = blog_info.get('updated', 0)
        if not updated:
            return (False, None)

        last_post_date = datetime.fromtimestamp(updated)
        days_since_post = (datetime.now() - last_post_date).days

        if days_since_post > max_days_inactive:
            return (False, last_post_date)

        return (True, last_post_date)

    def check_post_content_for_location(self, post: Dict) -> Optional[Tuple[str, str]]:
        """
        Check if post content mentions any location keywords.

        Args:
            post: Post dict from Tumblr API

        Returns:
            Tuple of (matched_term, source) if found, None otherwise
        """
        # Get post content - different fields depending on post type
        content_fields = []

        # Post body/caption
        if 'body' in post:
            content_fields.append(('body', post['body']))
        if 'caption' in post:
            content_fields.append(('caption', post['caption']))

        # Ask/answer content
        if 'question' in post:
            content_fields.append(('question', post['question']))
        if 'answer' in post:
            content_fields.append(('answer', post['answer']))

        # Check all content fields for location keywords
        for source, text in content_fields:
            if not text:
                continue

            # Strip HTML tags if present
            import re as regex_module
            text_clean = regex_module.sub(r'<[^>]+>', '', str(text))
            text_lower = text_clean.lower()

            for location in LOCATION_INDICATORS:
                pattern = r'\b' + re.escape(location.lower()) + r'\b'
                if re.search(pattern, text_lower):
                    return (location, f'post_{source}')

        return None

    def search_theme_tag(self, theme: str, max_posts: int = 500) -> Dict[str, Set[str]]:
        """
        Search for posts with a specific theme tag and extract blog names.
        Also checks post content for location mentions.

        Args:
            theme: Theme tag to search
            max_posts: Maximum number of posts to retrieve

        Returns:
            Dict mapping blog_name -> set of location match sources
        """
        blog_locations = defaultdict(set)
        before = None
        posts_retrieved = 0

        print(f"\nSearching theme: '{theme}'")

        while posts_retrieved < max_posts:
            try:
                # Tumblr API returns max 20 posts per request
                limit = min(20, max_posts - posts_retrieved)

                if before:
                    response = self.client.tagged(theme, before=before, limit=limit)
                else:
                    response = self.client.tagged(theme, limit=limit)

                if not response:
                    print(f"  No more posts found")
                    break

                # Extract blog names and check post content for locations
                for post in response:
                    if 'blog_name' in post:
                        blog_name = post['blog_name']

                        # Check if this post mentions a location
                        location_match = self.check_post_content_for_location(post)
                        if location_match:
                            location_term, source = location_match
                            blog_locations[blog_name].add(f"{location_term} (in {source})")

                        # Add blog even if no location found (we'll check profile later)
                        if blog_name not in blog_locations:
                            blog_locations[blog_name] = set()

                    # Update 'before' timestamp for pagination
                    if 'timestamp' in post:
                        before = post['timestamp']

                posts_retrieved += len(response)
                blogs_with_location = sum(1 for locs in blog_locations.values() if locs)
                print(f"  Retrieved {posts_retrieved} posts, found {len(blog_locations)} blogs ({blogs_with_location} with location mentions)")

                # Break if we got fewer posts than requested (end of results)
                if len(response) < limit:
                    break

                # Rate limiting - wait between requests
                time.sleep(2)

            except Exception as e:
                print(f"  Error searching tag '{theme}': {e}")
                break

        blogs_with_location = sum(1 for locs in blog_locations.values() if locs)
        print(f"  Total: {len(blog_locations)} blogs, {blogs_with_location} mentioned locations in posts")
        return blog_locations

    def process_blogs(self, blog_locations: Dict[str, Set[str]], theme: str,
                      min_followers: int, max_days_inactive: int):
        """
        Fetch and filter blog information.

        Args:
            blog_locations: Dict mapping blog_name -> set of location mentions from posts
            theme: Theme tag these blogs were found under
            min_followers: Minimum follower count
            max_days_inactive: Maximum days since last post
        """
        print(f"\nProcessing {len(blog_locations)} blogs from theme '{theme}'...")

        processed = 0
        qualified = 0

        for blog_name, post_location_mentions in blog_locations.items():
            processed += 1

            # Skip if already processed
            if blog_name in self.discovered_blogs:
                self.blog_themes[blog_name].add(theme)
                continue

            # Fetch blog info
            blog_info = self.get_blog_info(blog_name)
            if not blog_info:
                continue

            # Check if meets criteria
            meets_criteria, last_post_date = self.meets_criteria(
                blog_info, min_followers, max_days_inactive
            )

            if not meets_criteria:
                continue

            # Check location match - first from post content, then from profile
            location_match = None
            location_term = None
            location_source = None

            # Priority 1: Location found in post content
            if post_location_mentions:
                # Use the first location mention from posts
                first_mention = list(post_location_mentions)[0]
                # Extract just the location term (before " (in")
                location_term = first_mention.split(' (in')[0] if ' (in' in first_mention else first_mention
                location_source = 'post_content'
                location_match = True

            # Priority 2: Check blog profile
            if not location_match:
                text_fields = {
                    'url': blog_info.get('url', ''),
                    'title': blog_info.get('title', ''),
                    'description': blog_info.get('description', '')
                }

                # Get blog tags (if available)
                blog_tags = []
                if 'tags' in blog_info:
                    blog_tags = blog_info.get('tags', [])

                profile_match = self.find_location_match(text_fields, blog_tags)
                if profile_match:
                    location_term, location_source = profile_match
                    location_match = True

            if not location_match:
                continue

            # Blog qualifies - store it
            qualified += 1

            self.discovered_blogs[blog_name] = {
                'blog_name': blog_name,
                'blog_url': blog_info.get('url', ''),
                'title': blog_info.get('title', ''),
                'description': blog_info.get('description', ''),
                'follower_count': blog_info.get('total_followers', 0),
                'total_posts': blog_info.get('posts', 0),
                'last_post_date': last_post_date.strftime('%Y-%m-%d') if last_post_date else '',
                'location_match_term': location_term,
                'location_match_source': location_source,
                'blog_tags': blog_info.get('tags', []) if 'tags' in blog_info else [],
                'theme_matched': theme
            }

            self.blog_themes[blog_name].add(theme)

            # Progress update
            if processed % 10 == 0:
                print(f"  Processed {processed}/{len(blog_locations)}, qualified: {qualified}")

            # Rate limiting - increased to avoid API limits
            time.sleep(2)

        print(f"  Finished processing. Qualified: {qualified}/{len(blog_locations)}")

    def run_search(self, themes: List[str], max_posts_per_theme: int,
                   min_followers: int, max_days_inactive: int):
        """
        Run the complete search across all themes.

        Args:
            themes: List of theme tags to search
            max_posts_per_theme: Maximum posts to retrieve per theme
            min_followers: Minimum follower count
            max_days_inactive: Maximum days since last post
        """
        print(f"Starting search for {len(themes)} theme tags...")
        print(f"Filters: min_followers={min_followers}, max_days_inactive={max_days_inactive}")

        for theme in themes:
            # Search for posts with this theme tag (returns dict of blog -> location mentions)
            blog_locations = self.search_theme_tag(theme, max_posts_per_theme)

            # Process and filter blogs
            if blog_locations:
                self.process_blogs(blog_locations, theme, min_followers, max_days_inactive)

        # Update theme_matched for blogs found in multiple themes
        for blog_name, themes_set in self.blog_themes.items():
            if blog_name in self.discovered_blogs:
                self.discovered_blogs[blog_name]['theme_matched'] = ', '.join(sorted(themes_set))

        print(f"\n{'='*60}")
        print(f"Search complete! Total qualifying blogs: {len(self.discovered_blogs)}")
        print(f"{'='*60}")

    def export_results(self, output_base: str):
        """
        Export results to JSON and CSV files.

        Args:
            output_base: Base filename for output files
        """
        if not self.discovered_blogs:
            print("No blogs to export.")
            return

        # Export to JSON
        json_file = f"{output_base}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.discovered_blogs.values()), f, indent=2, ensure_ascii=False)
        print(f"\nExported to JSON: {json_file}")

        # Export to CSV
        csv_file = f"{output_base}.csv"
        fieldnames = [
            'blog_name', 'blog_url', 'title', 'description', 'follower_count',
            'total_posts', 'last_post_date', 'location_match_term',
            'location_match_source', 'blog_tags', 'theme_matched'
        ]

        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for blog in self.discovered_blogs.values():
                # Convert blog_tags list to string for CSV
                row = blog.copy()
                row['blog_tags'] = ', '.join(blog['blog_tags']) if blog['blog_tags'] else ''
                writer.writerow(row)

        print(f"Exported to CSV: {csv_file}")


def load_env_file():
    """Load environment variables from .env file if it exists"""
    if os.path.exists('.env'):
        print("Loading credentials from .env file...")
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        return True
    return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Find Tumblr blogs matching specific themes and locations'
    )
    parser.add_argument(
        '--themes',
        type=str,
        help='Comma-separated list of theme tags to search (default: predefined list)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='results',
        help='Base filename for output files (default: results)'
    )
    parser.add_argument(
        '--max-posts-per-theme',
        type=int,
        default=500,
        help='Maximum posts to retrieve per theme (default: 500)'
    )
    parser.add_argument(
        '--min-followers',
        type=int,
        default=10,
        help='Minimum follower count (default: 10)'
    )
    parser.add_argument(
        '--max-days-inactive',
        type=int,
        default=90,
        help='Maximum days since last post (default: 90)'
    )

    args = parser.parse_args()

    # Try to load from .env file first
    load_env_file()

    # Load API credentials from environment
    consumer_key = os.getenv('TUMBLR_CONSUMER_KEY')
    consumer_secret = os.getenv('TUMBLR_CONSUMER_SECRET')
    oauth_token = os.getenv('TUMBLR_OAUTH_TOKEN')
    oauth_secret = os.getenv('TUMBLR_OAUTH_SECRET')

    if not all([consumer_key, consumer_secret, oauth_token, oauth_secret]):
        print("Error: Missing Tumblr API credentials.")
        print("Please run 'python get_tumblr_credentials.py' to set up your credentials,")
        print("or set the following environment variables:")
        print("  TUMBLR_CONSUMER_KEY")
        print("  TUMBLR_CONSUMER_SECRET")
        print("  TUMBLR_OAUTH_TOKEN")
        print("  TUMBLR_OAUTH_SECRET")
        return 1

    # Parse theme tags
    if args.themes:
        themes = [t.strip() for t in args.themes.split(',')]
    else:
        themes = DEFAULT_THEME_TAGS

    # Initialize finder
    finder = TumblrProfileFinder(
        consumer_key,
        consumer_secret,
        oauth_token,
        oauth_secret
    )

    # Run search
    try:
        finder.run_search(
            themes,
            args.max_posts_per_theme,
            args.min_followers,
            args.max_days_inactive
        )

        # Export results
        finder.export_results(args.output)

        print("\nDone!")
        return 0

    except KeyboardInterrupt:
        print("\n\nSearch interrupted by user.")
        if finder.discovered_blogs:
            print(f"Exporting {len(finder.discovered_blogs)} blogs found so far...")
            finder.export_results(args.output)
        return 1
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
