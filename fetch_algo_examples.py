# -*- coding: utf-8 -*-
"""
GitHub Algorithm Visualizer Example Scraper
Fetches real examples from algorithm-visualizer/algorithms repository
"""

import os
import json
import requests
from typing import List, Dict, Optional
from pathlib import Path
import time


class GitHubExampleFetcher:
    """Fetches examples from Algorithm Visualizer GitHub repo or a local directory"""

    def __init__(self, cache_dir: str = "./examples_cache", local_algorithms_dir: Optional[str] = None):
        self.base_url = "https://api.github.com/repos/algorithm-visualizer/algorithms"
        # Try both common default branches
        self.raw_base_candidates = [
            "https://raw.githubusercontent.com/algorithm-visualizer/algorithms/main",
            "https://raw.githubusercontent.com/algorithm-visualizer/algorithms/master",
        ]
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.local_algorithms_dir = Path(local_algorithms_dir) if local_algorithms_dir else None

        # GitHub token for higher rate limits (optional)
        self.token = os.getenv('GITHUB_TOKEN')
        self.headers = {}
        if self.token:
            self.headers['Authorization'] = f'token {self.token}'
        # GitHub API header recommendations
        self.headers['Accept'] = 'application/vnd.github.v3+json'

    def find_all_code_files(self, path: str = "") -> List[str]:
        """Find all JavaScript algorithm files via Trees API (not only code.js)."""
        # Prefer recursive repo tree to avoid per-directory API limits
        for branch in ("main", "master"):
            tree = self.fetch_repo_tree(branch)
            if tree:
                js_files = [item['path'] for item in tree if item.get('type') == 'blob' and item.get('path', '').lower().endswith('.js')]
                # Filter to known algorithm directories (top-level)
                allowed_prefixes = {
                    'Backtracking', 'Branch and Bound', 'Brute Force', 'Divide and Conquer',
                    'Dynamic Programming', 'Greedy', 'Simple Recursive', 'Uncategorized',
                    'Graph', 'Searching', 'Sorting', 'String'
                }
                filtered = []
                for p in js_files:
                    parts = p.split('/')
                    if len(parts) >= 2 and parts[0] in allowed_prefixes:
                        filtered.append(p)
                return filtered if filtered else js_files

        # Fallback to slower directory walk using contents API
        code_files = []
        items = self.fetch_directory_tree(path)
        for item in items:
            if item.get('type') == 'file' and item.get('name', '').lower().endswith('.js'):
                code_files.append(item['path'])
            elif item.get('type') == 'dir':
                code_files.extend(self.find_all_code_files(item['path']))
        return code_files

    def fetch_repo_tree(self, branch: str) -> Optional[List[Dict]]:
        """Fetch the entire repo tree recursively for a branch."""
        url = f"{self.base_url}/git/trees/{branch}?recursive=1"
        for attempt in range(3):
            try:
                response = requests.get(url, headers=self.headers, timeout=20)
                if response.ok:
                    data = response.json()
                    return data.get('tree', [])
                else:
                    print(f"Failed to fetch tree {branch}: {response.status_code}")
            except Exception as e:
                print(f"Error fetching tree {branch} (attempt {attempt+1}/3): {e}")
            time.sleep(1.0 * (attempt + 1))
        return None

    def fetch_directory_tree(self, path: str = "") -> List[Dict]:
        """Fetch directory structure"""
        url = f"{self.base_url}/contents/{path}"

        for attempt in range(3):
            try:
                response = requests.get(url, headers=self.headers, timeout=15)
                if response.ok:
                    return response.json()
                else:
                    print(f"Failed to fetch {path}: {response.status_code}")
            except Exception as e:
                print(f"Error fetching {path} (attempt {attempt+1}/3): {e}")
            time.sleep(1.0 * (attempt + 1))
        return []

    def fetch_file_content(self, path: str) -> Optional[str]:
        """Fetch raw file content"""
        # Attempt multiple branches for robustness
        for base in self.raw_base_candidates:
            url = f"{base}/{path}"
            try:
                # Use token as header to improve rate limits on raw too
                raw_headers = {}
                if self.token:
                    raw_headers['Authorization'] = f'token {self.token}'
                response = requests.get(url, headers=raw_headers, timeout=20)
                if response.ok and response.text:
                    return response.text
            except Exception as e:
                print(f"Error fetching file {path} from {base}: {e}")
                continue
        return None

    def find_js_files(self, path: str = "") -> List[str]:
        """Recursively find all .js files"""
        js_files = []
        items = self.fetch_directory_tree(path)

        for item in items:
            if item['type'] == 'file' and item['name'].endswith('.js'):
                js_files.append(item['path'])
            elif item['type'] == 'dir':
                # Recursively search subdirectories
                js_files.extend(self.find_js_files(item['path']))

        return js_files

    def categorize_algorithm(self, path: str) -> str:
        """Determine algorithm category from path"""
        path_lower = path.lower()

        if 'sort' in path_lower:
            return 'sorting'
        elif 'search' in path_lower:
            return 'searching'
        elif 'graph' in path_lower or 'tree' in path_lower:
            return 'graph'
        elif 'dynamic' in path_lower or 'dp' in path_lower:
            return 'dynamic_programming'
        elif 'backtrack' in path_lower:
            return 'backtracking'
        elif 'greedy' in path_lower:
            return 'greedy'
        elif 'string' in path_lower:
            return 'string'
        else:
            return 'other'

    def extract_patterns(self, code: str) -> List[str]:
        """Extract Algorithm Visualizer patterns from code"""
        patterns = []

        if 'select' in code and 'deselect' in code:
            patterns.append('select_deselect')

        if 'patch' in code and 'depatch' in code:
            patterns.append('patch_depatch')

        if 'Randomize.' in code:
            patterns.append('uses_randomize')
        elif 'const' in code and '= [' in code:
            patterns.append('custom_data')

        if 'logger.println' in code:
            patterns.append('has_logging')

        if 'ChartTracer' in code:
            patterns.append('uses_chart')

        if 'Array2DTracer' in code:
            patterns.append('uses_2d_array')

        return patterns

    def fetch_curated_examples(self) -> List[Dict]:
        """Fetch all code.js examples from the repository"""

        print("Scanning repository for code.js files...")

        # Collect all .js algorithm files across all folders
        code_files = self.find_all_code_files()
        if not code_files:
            code_files = self.find_js_files()

        print(f"Found {len(code_files)} algorithm files")

        examples = []

        for path in code_files:
            # Extract category and algorithm name from path
            # Examples:
            #   Dynamic Programming/FibonacciNumber/code.js
            #   Sorting/Bubble Sort/bubble_sort.js
            parts = path.split('/')

            if len(parts) < 2:
                continue

            category = parts[0]
            algo_name = parts[1]

            print(f"Fetching {category}/{algo_name}...")

            content = self.fetch_file_content(path)

            if content:
                example = {
                    'name': algo_name,
                    'path': path,
                    'code': content,
                    'category': self.categorize_algorithm(path),
                    'patterns': self.extract_patterns(content)
                }

                examples.append(example)

                # Cache it
                cache_file = self.cache_dir / f"{category}_{algo_name}.json"
                with open(cache_file, 'w') as f:
                    json.dump(example, f, indent=2)

                print(f"  ✓ Cached {category}/{algo_name}")
            else:
                print(f"  ✗ Failed to fetch {path}")

        return examples
    def load_from_cache(self) -> List[Dict]:
        """Load examples from cache"""
        examples = []

        for cache_file in self.cache_dir.glob('*.json'):
            with open(cache_file) as f:
                examples.append(json.load(f))

        return examples

    def get_examples(self, force_refresh: bool = False) -> List[Dict]:
        """Get examples, using cache if available"""
        # If local directory is specified, operate in LOCAL-ONLY mode (no GitHub)
        if self.local_algorithms_dir:
            if not self.local_algorithms_dir.exists():
                raise RuntimeError(f"Local algorithms directory not found: {self.local_algorithms_dir}")
            print(f"LOCAL-ONLY: Importing examples from {self.local_algorithms_dir}")
            return self.load_from_local_dir(self.local_algorithms_dir)

        # Otherwise: GitHub mode with cache-based fallback
        cached = list(self.cache_dir.glob('*.json'))
        if not force_refresh and cached:
            print("Loading examples from cache...")
            return self.load_from_cache()

        print("Fetching examples from GitHub...")
        examples = self.fetch_curated_examples()
        if examples:
            return examples

        # Robust fallbacks
        print("No examples fetched. Trying cache again...")
        cached = self.load_from_cache()
        if cached:
            return cached

        print("No cache available. Seeding with built-in minimal examples...")
        # Minimal built-ins aligned with Multi-Agent hardcoded examples
        builtins = [
            {
                'name': 'bubble_sort',
                'path': 'Sorting/bubble_sort.js',
                'code': """const { Array1DTracer, ChartTracer, Layout, LogTracer, Randomize, Tracer, VerticalLayout } = require('algorithm-visualizer');\nconst chart = new ChartTracer();\nconst tracer = new Array1DTracer('Array');\nconst logger = new LogTracer('Console');\nLayout.setRoot(new VerticalLayout([chart, tracer, logger]));\ntracer.chart(chart);\nconst D = Randomize.Array1D({ N: 10 });\ntracer.set(D);\nTracer.delay();\nfunction BubbleSort(array) { for (let i = 0; i < array.length; i++) { for (let j = 0; j < array.length - i - 1; j++) { tracer.select(j, j + 1); Tracer.delay(); if (array[j] > array[j + 1]) { [array[j], array[j + 1]] = [array[j + 1], array[j]]; tracer.patch(j, array[j]); tracer.patch(j + 1, array[j + 1]); Tracer.delay(); tracer.depatch(j); tracer.depatch(j + 1); } tracer.deselect(j, j + 1); } } }\nBubbleSort(D);""",
                'category': 'sorting',
                'patterns': ['select_deselect', 'patch_depatch', 'has_logging']
            },
            {
                'name': 'binary_search',
                'path': 'Searching/binary_search.js',
                'code': """const { Array1DTracer, ChartTracer, Layout, LogTracer, Tracer, VerticalLayout } = require('algorithm-visualizer');\nconst chart = new ChartTracer();\nconst tracer = new Array1DTracer('Sorted Array');\nconst logger = new LogTracer('Console');\nLayout.setRoot(new VerticalLayout([chart, tracer, logger]));\ntracer.chart(chart);\nconst array = [1,3,5,7,9,11,13,15];\nconst target = 13;\ntracer.set(array);\nTracer.delay();\nfunction binarySearch(arr, x) { let l = 0, r = arr.length - 1; while (l <= r) { const m = Math.floor((l + r) / 2); tracer.select(l, r); tracer.select(m); Tracer.delay(); if (arr[m] === x) { tracer.patch(m, arr[m]); Tracer.delay(); tracer.depatch(m); tracer.deselect(l, r, m); return m; } if (arr[m] < x) l = m + 1; else r = m - 1; tracer.deselect(l, r, m); } return -1; }\nconst result = binarySearch(array, target);""",
                'category': 'searching',
                'patterns': ['custom_data', 'has_logging', 'select_deselect']
            }
        ]
        # Persist built-ins to cache for future runs
        for ex in builtins:
            cache_file = self.cache_dir / f"{ex['category']}_{ex['name']}.json"
            try:
                with open(cache_file, 'w') as f:
                    json.dump(ex, f, indent=2)
            except Exception:
                pass
        return builtins

    def load_from_local_dir(self, base: Path) -> List[Dict]:
        """Traverse a local algorithms directory and cache all .js files as examples."""
        print("Scanning local algorithms directory for .js files...")
        allowed_prefixes = {
            'Backtracking', 'Branch and Bound', 'Brute Force', 'Divide and Conquer',
            'Dynamic Programming', 'Greedy', 'Simple Recursive', 'Uncategorized',
            'Graph', 'Searching', 'Sorting', 'String'
        }
        examples: List[Dict] = []
        for top in base.iterdir():
            if not top.is_dir():
                continue
            if top.name not in allowed_prefixes:
                continue
            for js_path in top.rglob('*.js'):
                rel = js_path.relative_to(base)
                parts = rel.as_posix().split('/')
                if len(parts) < 2:
                    continue
                category = parts[0]
                algo_name = parts[1]
                try:
                    content = js_path.read_text(encoding='utf-8')
                except Exception as e:
                    print(f"  ✗ Failed to read {js_path}: {e}")
                    continue

                example = {
                    'name': algo_name,
                    'path': rel.as_posix(),
                    'code': content,
                    'category': self.categorize_algorithm(rel.as_posix()),
                    'patterns': self.extract_patterns(content)
                }
                examples.append(example)

                cache_file = self.cache_dir / f"{example['category']}_{algo_name}.json"
                try:
                    with open(cache_file, 'w') as f:
                        json.dump(example, f, indent=2)
                except Exception:
                    pass
                print(f"  ✓ Cached {rel}")

        print(f"Found {len(examples)} local algorithm files")
        return examples


class ExampleDatabase:
    """Database of Algorithm Visualizer examples for RAG"""

    def __init__(self, examples: List[Dict]):
        self.examples = examples
        self._build_index()

    def _build_index(self):
        """Build search index"""
        self.by_category = {}
        self.by_pattern = {}

        for ex in self.examples:
            # Index by category
            cat = ex['category']
            if cat not in self.by_category:
                self.by_category[cat] = []
            self.by_category[cat].append(ex)

            # Index by patterns
            for pattern in ex['patterns']:
                if pattern not in self.by_pattern:
                    self.by_pattern[pattern] = []
                self.by_pattern[pattern].append(ex)

    def search(self, query: Dict) -> List[Dict]:
        """Search for relevant examples"""
        results = []
        scores = {}

        category = query.get('category')
        patterns = query.get('patterns', [])
        needs_custom_data = query.get('needs_custom_data', False)

        # Score by category
        if category and category in self.by_category:
            for ex in self.by_category[category]:
                scores[ex['name']] = scores.get(ex['name'], 0) + 3

        # Score by patterns
        for pattern in patterns:
            if pattern in self.by_pattern:
                for ex in self.by_pattern[pattern]:
                    scores[ex['name']] = scores.get(ex['name'], 0) + 1

        # Boost custom data examples if needed
        if needs_custom_data:
            for ex in self.examples:
                if 'custom_data' in ex['patterns']:
                    scores[ex['name']] = scores.get(ex['name'], 0) + 2

        # Sort by score
        sorted_names = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Return top examples
        for name, score in sorted_names[:3]:
            ex = next((e for e in self.examples if e['name'] == name), None)
            if ex:
                results.append(ex)

        return results

    def get_best_practices(self) -> Dict[str, List[str]]:
        """Extract best practices from examples"""
        practices = {
            'logging': [],
            'visualization': [],
            'data_init': [],
            'structure': []
        }

        for ex in self.examples:
            code = ex['code']

            # Extract logging patterns
            import re
            logs = re.findall(r"logger\.println\(['\"]([^'\"]+)['\"]\)", code)
            practices['logging'].extend(logs[:2])

            # Extract visualization patterns
            if 'select' in code:
                selects = re.findall(r'tracer\.select\([^)]+\);', code)
                if selects:
                    practices['visualization'].append(selects[0])

            # Extract data init patterns
            if 'const' in code and '= [' in code:
                inits = re.findall(r'const \w+ = \[[^\]]+\];', code)
                practices['data_init'].extend(inits[:1])

        # Deduplicate
        for key in practices:
            practices[key] = list(set(practices[key]))[:5]

        return practices


# ==================== CLI TOOL ====================

def main():
    """Fetch and cache examples"""
    fetcher = GitHubExampleFetcher()

    print("=" * 60)
    print("Algorithm Visualizer Example Fetcher")
    print("=" * 60)
    print()

    # Fetch examples
    examples = fetcher.get_examples(force_refresh=False)

    print(f"\n✓ Loaded {len(examples)} examples")

    # Build database
    db = ExampleDatabase(examples)

    print(f"\nCategories: {list(db.by_category.keys())}")
    print(f"Patterns: {list(db.by_pattern.keys())}")

    # Test search
    print("\n" + "=" * 60)
    print("Test Search: Binary Search")
    print("=" * 60)

    results = db.search({
        'category': 'searching',
        'needs_custom_data': True
    })

    for ex in results:
        print(f"\n✓ {ex['name']} ({ex['category']})")
        print(f"  Patterns: {', '.join(ex['patterns'])}")

    # Get best practices
    print("\n" + "=" * 60)
    print("Best Practices")
    print("=" * 60)

    practices = db.get_best_practices()

    print("\nLogging examples:")
    for log in practices['logging'][:3]:
        print(f"  - {log}")

    print("\nData init examples:")
    for init in practices['data_init'][:3]:
        print(f"  - {init}")


if __name__ == '__main__':
    main()