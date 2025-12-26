#!/usr/bin/env python3
"""
Tumblr Profile Finder with Automatic Rate Limit Management
Automatically manages Tumblr API limits: 1000 calls/hour, 5000 calls/day
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

# Import configuration from original script
from tumblr_profile_finder import (
    DEFAULT_THEME_TAGS,
    LOCATION_INDICATORS,
    TumblrProfileFinder,
    load_env_file
)


class RateLimitTracker:
    """Tracks API calls and manages rate limiting"""

    def __init__(self, hourly_limit=1000, daily_limit=5000):
        self.hourly_limit = hourly_limit
        self.daily_limit = daily_limit
        self.hourly_calls = 0
        self.daily_calls = 0
        self.hour_start = datetime.now()
        self.day_start = datetime.now()
        self.total_calls = 0

    def record_call(self):
        """Record an API call"""
        self.hourly_calls += 1
        self.daily_calls += 1
        self.total_calls += 1

    def check_and_wait(self):
        """Check limits and wait if necessary"""
        now = datetime.now()

        # Check if hour has passed (reset hourly counter)
        if (now - self.hour_start).total_seconds() >= 3600:
            print(f"\n[Rate Limit] Hour completed. Made {self.hourly_calls} calls.")
            self.hourly_calls = 0
            self.hour_start = now

        # Check if day has passed (reset daily counter)
        if (now - self.day_start).total_seconds() >= 86400:
            print(f"\n[Rate Limit] Day completed. Made {self.daily_calls} calls.")
            self.daily_calls = 0
            self.day_start = now

        # Check if approaching hourly limit
        if self.hourly_calls >= self.hourly_limit - 10:
            time_elapsed = (now - self.hour_start).total_seconds()
            time_remaining = 3600 - time_elapsed

            if time_remaining > 0:
                print(f"\n[Rate Limit] Approaching hourly limit ({self.hourly_calls}/{self.hourly_limit})")
                print(f"[Rate Limit] Waiting {int(time_remaining/60)} minutes until next hour...")
                time.sleep(time_remaining + 10)  # Wait until next hour + buffer
                self.hourly_calls = 0
                self.hour_start = datetime.now()
                print("[Rate Limit] Resuming...")

        # Check if approaching daily limit
        if self.daily_calls >= self.daily_limit - 10:
            print(f"\n[Rate Limit] Reached daily limit ({self.daily_calls}/{self.daily_limit})")
            print("[Rate Limit] Stopping for today.")
            return False

        return True

    def get_status(self):
        """Get current rate limit status"""
        return {
            'hourly_calls': self.hourly_calls,
            'hourly_limit': self.hourly_limit,
            'daily_calls': self.daily_calls,
            'daily_limit': self.daily_limit,
            'total_calls': self.total_calls
        }


class AutoTumblrProfileFinder(TumblrProfileFinder):
    """Extended finder with automatic rate limit management"""

    def __init__(self, consumer_key: str, consumer_secret: str,
                 oauth_token: str, oauth_secret: str):
        super().__init__(consumer_key, consumer_secret, oauth_token, oauth_secret)
        self.rate_tracker = RateLimitTracker()
        self.progress_file = 'search_progress.json'

    def save_progress(self):
        """Save current progress to file"""
        progress = {
            'discovered_blogs': self.discovered_blogs,
            'blog_themes': {k: list(v) for k, v in self.blog_themes.items()},
            'rate_limit_status': self.rate_tracker.get_status(),
            'timestamp': datetime.now().isoformat()
        }

        with open(self.progress_file, 'w') as f:
            json.dump(progress, f, indent=2)

        print(f"[Progress] Saved to {self.progress_file}")

    def load_progress(self):
        """Load progress from file if it exists"""
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                progress = json.load(f)

            self.discovered_blogs = progress.get('discovered_blogs', {})
            blog_themes_lists = progress.get('blog_themes', {})
            self.blog_themes = defaultdict(set)
            for k, v in blog_themes_lists.items():
                self.blog_themes[k] = set(v)

            print(f"[Progress] Loaded {len(self.discovered_blogs)} previously discovered blogs")
            return True
        return False

    def get_blog_info(self, blog_name: str) -> Optional[Dict]:
        """Fetch blog info with rate limiting"""
        # Check rate limits before making call
        if not self.rate_tracker.check_and_wait():
            return None

        self.rate_tracker.record_call()
        return super().get_blog_info(blog_name)

    def search_theme_tag(self, theme: str, max_posts: int = 500) -> Dict[str, Set[str]]:
        """Search with rate limiting"""
        blog_locations = defaultdict(set)
        before = None
        posts_retrieved = 0

        print(f"\nSearching theme: '{theme}'")

        while posts_retrieved < max_posts:
            # Check rate limits before making call
            if not self.rate_tracker.check_and_wait():
                print("[Rate Limit] Daily limit reached, stopping search")
                break

            try:
                limit = min(20, max_posts - posts_retrieved)

                if before:
                    response = self.client.tagged(theme, before=before, limit=limit)
                else:
                    response = self.client.tagged(theme, limit=limit)

                self.rate_tracker.record_call()

                if not response:
                    print(f"  No more posts found")
                    break

                # Process posts
                for post in response:
                    if 'blog_name' in post:
                        blog_name = post['blog_name']
                        location_match = self.check_post_content_for_location(post)
                        if location_match:
                            location_term, source = location_match
                            blog_locations[blog_name].add(f"{location_term} (in {source})")
                        if blog_name not in blog_locations:
                            blog_locations[blog_name] = set()

                    if 'timestamp' in post:
                        before = post['timestamp']

                posts_retrieved += len(response)
                blogs_with_location = sum(1 for locs in blog_locations.values() if locs)

                # Show status including rate limits
                status = self.rate_tracker.get_status()
                print(f"  Retrieved {posts_retrieved} posts, {len(blog_locations)} blogs ({blogs_with_location} with locations) | API calls: {status['hourly_calls']}/hr, {status['daily_calls']}/day")

                if len(response) < limit:
                    break

                time.sleep(2)

            except Exception as e:
                print(f"  Error searching tag '{theme}': {e}")
                break

        blogs_with_location = sum(1 for locs in blog_locations.values() if locs)
        print(f"  Total: {len(blog_locations)} blogs, {blogs_with_location} mentioned locations")
        return blog_locations

    def process_blogs(self, blog_locations: Dict[str, Set[str]], theme: str,
                      min_followers: int, max_days_inactive: int):
        """Process blogs with rate limiting and progress saving"""
        print(f"\nProcessing {len(blog_locations)} blogs from theme '{theme}'...")

        processed = 0
        qualified = 0

        for blog_name, post_location_mentions in blog_locations.items():
            processed += 1

            # Skip if already processed
            if blog_name in self.discovered_blogs:
                self.blog_themes[blog_name].add(theme)
                continue

            # Fetch blog info (with rate limiting)
            blog_info = self.get_blog_info(blog_name)
            if not blog_info:
                # If None returned, we hit rate limit
                if not self.rate_tracker.check_and_wait():
                    print("[Rate Limit] Stopping processing, saving progress...")
                    self.save_progress()
                    return
                continue

            # Check criteria
            meets_criteria, last_post_date = self.meets_criteria(
                blog_info, min_followers, max_days_inactive
            )

            if not meets_criteria:
                continue

            # Check location
            location_match = None
            location_term = None
            location_source = None

            if post_location_mentions:
                first_mention = list(post_location_mentions)[0]
                location_term = first_mention.split(' (in')[0] if ' (in' in first_mention else first_mention
                location_source = 'post_content'
                location_match = True

            if not location_match:
                text_fields = {
                    'url': blog_info.get('url', ''),
                    'title': blog_info.get('title', ''),
                    'description': blog_info.get('description', '')
                }
                blog_tags = blog_info.get('tags', []) if 'tags' in blog_info else []
                profile_match = self.find_location_match(text_fields, blog_tags)
                if profile_match:
                    location_term, location_source = profile_match
                    location_match = True

            if not location_match:
                continue

            # Qualified blog
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

            # Progress update and save
            if processed % 10 == 0:
                status = self.rate_tracker.get_status()
                print(f"  Processed {processed}/{len(blog_locations)}, qualified: {qualified} | API: {status['hourly_calls']}/hr, {status['daily_calls']}/day")
                self.save_progress()

            time.sleep(2)

        print(f"  Finished processing. Qualified: {qualified}/{len(blog_locations)}")
        self.save_progress()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Find Tumblr blogs with automatic rate limit management'
    )
    parser.add_argument('--themes', type=str, help='Comma-separated theme tags')
    parser.add_argument('--output', type=str, default='results_auto', help='Output filename')
    parser.add_argument('--max-posts-per-theme', type=int, default=1000)
    parser.add_argument('--min-followers', type=int, default=0)
    parser.add_argument('--max-days-inactive', type=int, default=90)
    parser.add_argument('--resume', action='store_true', help='Resume from saved progress')

    args = parser.parse_args()

    # Load credentials
    load_env_file()
    consumer_key = os.getenv('TUMBLR_CONSUMER_KEY')
    consumer_secret = os.getenv('TUMBLR_CONSUMER_SECRET')
    oauth_token = os.getenv('TUMBLR_OAUTH_TOKEN')
    oauth_secret = os.getenv('TUMBLR_OAUTH_SECRET')

    if not all([consumer_key, consumer_secret, oauth_token, oauth_secret]):
        print("Error: Missing API credentials")
        return 1

    # Parse themes
    if args.themes:
        themes = [t.strip() for t in args.themes.split(',')]
    else:
        themes = DEFAULT_THEME_TAGS

    # Initialize finder
    finder = AutoTumblrProfileFinder(consumer_key, consumer_secret, oauth_token, oauth_secret)

    # Load previous progress if resuming
    if args.resume:
        finder.load_progress()

    print(f"\n{'='*60}")
    print("AUTO RATE-LIMITED SEARCH")
    print(f"{'='*60}")
    print(f"Limits: 1000 calls/hour, 5000 calls/day")
    print(f"Themes: {len(themes)}")
    print(f"Max posts per theme: {args.max_posts_per_theme}")
    print(f"{'='*60}\n")

    try:
        finder.run_search(themes, args.max_posts_per_theme, args.min_followers, args.max_days_inactive)
        finder.export_results(args.output)

        status = finder.rate_tracker.get_status()
        print(f"\n{'='*60}")
        print(f"Final Stats:")
        print(f"  Total API calls: {status['total_calls']}")
        print(f"  Hourly: {status['hourly_calls']}/{status['hourly_limit']}")
        print(f"  Daily: {status['daily_calls']}/{status['daily_limit']}")
        print(f"  Qualified blogs: {len(finder.discovered_blogs)}")
        print(f"{'='*60}")

        return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Saving progress...")
        finder.save_progress()
        if finder.discovered_blogs:
            finder.export_results(args.output)
        return 1


if __name__ == '__main__':
    exit(main())
