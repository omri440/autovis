# -*- coding: utf-8 -*-
"""
Multi-Agent AI Polisher with RAG - OpenAI/ChatGPT Version
Uses GPT-4 for specialized polishing agents
"""

import os
import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class AlgoExample:
    """Algorithm Visualizer example from repository"""
    name: str
    code: str
    category: str
    patterns: List[str]
    path: str = ""


class AlgoVisualizerRAG:
    """
    RAG system for Algorithm Visualizer examples.
    Retrieves relevant examples from the repository to guide polishing.
    """

    def __init__(self, examples_dir: str = "./examples_cache"):
        self.examples_dir = examples_dir
        self.examples: List[AlgoExample] = []
        self.load_examples()

    def load_examples(self):
        """Load curated examples from cache"""
        from pathlib import Path

        cache_dir = Path(self.examples_dir)
        if not cache_dir.exists():
            # Create with hardcoded examples if cache doesn't exist
            self.examples = self._get_hardcoded_examples()
            return

        # Load from cache
        for cache_file in cache_dir.glob('*.json'):
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                    self.examples.append(AlgoExample(**data))
            except Exception as e:
                print(f"Error loading {cache_file}: {e}")

    def _get_hardcoded_examples(self) -> List[AlgoExample]:
        """Fallback hardcoded examples"""
        return [
            AlgoExample(
                name="bubble_sort",
                code="""const { Array1DTracer, ChartTracer, Layout, LogTracer, Randomize, Tracer, VerticalLayout } = require('algorithm-visualizer');

const chart = new ChartTracer();
const tracer = new Array1DTracer('Array');
const logger = new LogTracer('Console');
Layout.setRoot(new VerticalLayout([chart, tracer, logger]));
tracer.chart(chart);

const D = Randomize.Array1D({ N: 15 });
tracer.set(D);
Tracer.delay();

function BubbleSort(array) {
  const length = array.length;
  logger.println(`Starting Bubble Sort on array of length ${length}`);
  Tracer.delay();

  for (let i = 0; i < length; i++) {
    logger.println(`Pass ${i + 1} of ${length}`);
    for (let j = 0; j < length - i - 1; j++) {
      tracer.select(j, j + 1);
      Tracer.delay();

      if (array[j] > array[j + 1]) {
        logger.println(`Swapping ${array[j]} and ${array[j + 1]}`);
        [array[j], array[j + 1]] = [array[j + 1], array[j]];
        tracer.patch(j, array[j]);
        tracer.patch(j + 1, array[j + 1]);
        Tracer.delay();
        tracer.depatch(j);
        tracer.depatch(j + 1);
      }

      tracer.deselect(j, j + 1);
    }
  }

  logger.println('Sorting complete!');
  Tracer.delay();
}

BubbleSort(D);""",
                category="sorting",
                patterns=["select_before_compare", "patch_after_modify", "clear_logging", "function_call_at_end"]
            ),

            AlgoExample(
                name="binary_search",
                code="""const { Array1DTracer, ChartTracer, Layout, LogTracer, Tracer, VerticalLayout } = require('algorithm-visualizer');

const chart = new ChartTracer();
const tracer = new Array1DTracer('Sorted Array');
const logger = new LogTracer('Console');
Layout.setRoot(new VerticalLayout([chart, tracer, logger]));
tracer.chart(chart);

const array = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25];
const target = 13;

tracer.set(array);
logger.println(`Searching for ${target} in sorted array`);
Tracer.delay();

function binarySearch(arr, x) {
  let left = 0;
  let right = arr.length - 1;

  while (left <= right) {
    const mid = Math.floor((left + right) / 2);

    tracer.select(left, right);
    tracer.select(mid);
    logger.println(`Checking middle element at index ${mid}: ${arr[mid]}`);
    Tracer.delay();

    if (arr[mid] === x) {
      logger.println(`Found ${x} at index ${mid}!`);
      tracer.patch(mid, arr[mid]);
      Tracer.delay();
      tracer.depatch(mid);
      tracer.deselect(left, right, mid);
      return mid;
    }

    if (arr[mid] < x) {
      logger.println(`${arr[mid]} < ${x}, searching right half`);
      left = mid + 1;
    } else {
      logger.println(`${arr[mid]} > ${x}, searching left half`);
      right = mid - 1;
    }

    tracer.deselect(left, right, mid);
    Tracer.delay();
  }

  logger.println(`${x} not found in array`);
  return -1;
}

const result = binarySearch(array, target);""",
                category="searching",
                patterns=["custom_test_data", "sorted_array", "target_parameter", "select_range", "mid_highlight"]
            ),
        ]

    def find_similar(self, analysis: Dict, code: str) -> List[AlgoExample]:
        """Find examples similar to the algorithm being polished"""
        matches = []

        viz_type = (analysis.get('viz_type') or '').lower()
        has_sorting = bool(analysis.get('has_sorting'))
        has_searching = bool(analysis.get('has_searching'))

        # Derive desired patterns from analysis/python hints
        desired_patterns = set()
        if has_sorting:
            desired_patterns.add('sorting')
        if has_searching:
            desired_patterns.add('searching')
        python_hints = ' '.join([
            (analysis.get('key_vars') or []).__repr__(),
        ]).lower() + ' ' + code.lower()
        if 'target' in python_hints or 'two sum' in python_hints:
            desired_patterns.update(['custom_test_data', 'target_parameter'])

        for example in self.examples:
            score = 0

            # Category match from viz_type/flags
            if has_sorting and example.category == 'sorting':
                score += 5
            elif has_searching and example.category == 'searching':
                score += 5
            elif 'graph' in viz_type and example.category == 'graph':
                score += 4
            elif 'array2d' in viz_type and example.category in ('matrix', 'array2d'):
                score += 3

            # Lightweight lexical/context clues
            if 'while' in code and 'while' in example.code:
                score += 1
            if 'hashmap' in code and 'hashmap' in example.code:
                score += 2

            # Pattern overlap boost
            if getattr(example, 'patterns', None):
                overlap = len(set(example.patterns) & desired_patterns)
                score += overlap * 2

            if score > 0:
                matches.append((score, example))

        matches.sort(reverse=True, key=lambda x: x[0])
        top = [ex for _, ex in matches[:2]]

        # Fallbacks to guarantee RAG guidance
        if not top:
            fallback_category = 'sorting' if has_sorting else 'searching' if has_searching else None
            if fallback_category:
                cat_examples = [ex for ex in self.examples if ex.category == fallback_category]
                top = cat_examples[:2]
        if not top and self.examples:
            top = self.examples[:1]

        return top

    def extract_patterns(self, examples: List[AlgoExample]) -> Dict[str, str]:
        """Extract best practices from examples"""
        patterns = {}

        for ex in examples:
            logs = re.findall(r"logger\.println\(`([^`]+)`\)", ex.code)
            if not logs:
                logs = re.findall(r"logger\.println\('([^']+)'\)", ex.code)

            if logs:
                patterns['logging_style'] = logs[0]

            if 'select' in ex.code and 'deselect' in ex.code:
                patterns['uses_select_deselect'] = True

            if 'patch' in ex.code and 'depatch' in ex.code:
                patterns['uses_patch_depatch'] = True

            if 'const array = [' in ex.code or 'const nums = [' in ex.code:
                patterns['uses_custom_data'] = True
                match = re.search(r'const \w+ = \[([^\]]+)\]', ex.code)
                if match:
                    patterns['data_example'] = match.group(0)

        return patterns


class PolishingAgent:
    """Base class for specialized polishing agents"""

    def __init__(self, client, name: str):
        self.client = client
        self.name = name

    def process(self, code: str, context: Dict) -> Tuple[str, Dict]:
        """Process code and return improved version with metadata"""
        raise NotImplementedError

    def _extract_code(self, text: str) -> str:
        """Extract code from markdown code blocks"""
        match = re.search(r'```(?:javascript|js)?\n(.*?)\n```', text, re.DOTALL)
        return match.group(1).strip() if match else text.strip()

    def _extract_require_idents(self, code: str) -> List[str]:
        """Extract imported identifiers from require('algorithm-visualizer')."""
        m = re.search(r"const \{([^}]+)\}\s*=\s*require\('algorithm-visualizer'\);", code)
        if not m:
            return []
        idents = [s.strip() for s in m.group(1).split(',')]
        return [i for i in idents if i]


class DataInitializationAgent(PolishingAgent):
    """Agent that improves data initialization"""

    def process(self, code: str, context: Dict) -> Tuple[str, Dict]:
        """Replace Randomize with appropriate test data if needed"""

        analysis = context['analysis']
        examples = context['similar_examples']
        python_code = context['python_code']

        needs_custom = (
                analysis.get('has_searching', False) or
                'target' in python_code.lower() or
                'two sum' in python_code.lower() or
                'binary search' in python_code.lower()
        )

        if not needs_custom:
            return code, {'changed': False, 'reason': 'Randomize appropriate'}

        # Heuristic, deterministic rewrites for common LeetCode patterns (pre-LLM)
        py_lower = python_code.lower()

        # Helper: safe structural validation
        def _valid_structure(js: str) -> bool:
            required = ["require('algorithm-visualizer')", 'Layout.setRoot']
            return all(token in js for token in required)

        # numIslands: enforce a binary 0/1 grid literal and correct function call
        if 'numislands' in py_lower or ('grid' in py_lower and 'dfs' in py_lower and 'rows' in py_lower):
            m = re.search(r"const\s+(\w+)\s*=\s*Randomize\.Array2D\([^)]*\);", code)
            if m:
                grid_var = m.group(1)
                binary_grid = (
                    "[[ '1','1','0','0','0' ],\n"
                    " [ '1','1','0','0','0' ],\n"
                    " [ '0','0','1','0','0' ],\n"
                    " [ '0','0','0','1','1' ]]"
                )
                new_code = re.sub(
                    r"const\s+" + re.escape(grid_var) + r"\s*=\s*Randomize\.Array2D\([^)]*\);",
                    f"const {grid_var} = {binary_grid};",
                    code,
                    count=1
                )
                # Fix call signature to pass only grid
                new_code = re.sub(
                    r"\bnumIslands\s*\(([^)]*)\);",
                    f"numIslands({grid_var});",
                    new_code,
                    count=1
                )
                if _valid_structure(new_code) and new_code != code:
                    return new_code, {'changed': True, 'reason': 'Set binary 2D grid literal and fixed call'}

        # canJump: include a zero to exercise edge cases
        if 'canjump' in py_lower:
            m = re.search(r"const\s+(\w+)\s*=\s*Randomize\.Array1D\([^)]*\);", code)
            if m:
                nums_var = m.group(1)
                example = "[3,2,1,0,4]"
                new_code = re.sub(
                    r"const\s+" + re.escape(nums_var) + r"\s*=\s*Randomize\.Array1D\([^)]*\);",
                    f"const {nums_var} = {example};",
                    code,
                    count=1
                )
                if _valid_structure(new_code) and new_code != code:
                    return new_code, {'changed': True, 'reason': 'Initialized nums with edge-case values'}

        # numDecodings: represent string as char array
        if 'numdecodings' in py_lower or re.search(r":type\s+\w+:\s*str", python_code):
            # Replace first Randomize.Array1D used for the string input with a char array
            m = re.search(r"const\s+(\w+)\s*=\s*Randomize\.Array1D\([^)]*\);", code)
            if m:
                s_var = m.group(1)
                example = "['1','2','1']"
                new_code = re.sub(
                    r"const\s+" + re.escape(s_var) + r"\s*=\s*Randomize\.Array1D\([^)]*\);",
                    f"const {s_var} = {example};",
                    code,
                    count=1
                )
                # Ensure function called with that var
                new_code = re.sub(
                    r"\bnumDecodings\s*\(([^)]*)\);",
                    f"numDecodings({s_var});",
                    new_code,
                    count=1
                )
                if _valid_structure(new_code) and new_code != code:
                    return new_code, {'changed': True, 'reason': 'Initialized string as char array'}

        # LCS: longestCommonSubsequence - set two strings and a zeroed 2D table
        if 'longestcommonsubsequence' in py_lower or ('text1' in py_lower and 'text2' in py_lower):
            new_code = code
            # Replace first two Randomize.Array1D as strings
            arr1d_matches = list(re.finditer(r"const\s+(\w+)\s*=\s*Randomize\.Array1D\([^)]*\);", new_code))
            if len(arr1d_matches) >= 2:
                var1 = arr1d_matches[0].group(1)
                var2 = arr1d_matches[1].group(1)
                new_code = re.sub(
                    r"const\s+" + re.escape(var1) + r"\s*=\s*Randomize\.Array1D\([^)]*\);",
                    f"const {var1} = 'AGGTAB';",
                    new_code,
                    count=1
                )
                new_code = re.sub(
                    r"const\s+" + re.escape(var2) + r"\s*=\s*Randomize\.Array1D\([^)]*\);",
                    f"const {var2} = 'GXTXAYB';",
                    new_code,
                    count=1
                )
                # If there is a 2D random table, replace with zero matrix sized by lengths
                m_expr = f"{var1}.length"
                n_expr = f"{var2}.length"
                arr2d_match = re.search(r"const\s+(\w+)\s*=\s*Randomize\.Array2D\([^)]*\);", new_code)
                if arr2d_match:
                    table_var = arr2d_match.group(1)
                    table_init = (
                        f"const {table_var} = Array({m_expr} + 1).fill(0).map(() => Array({n_expr} + 1).fill(0));"
                    )
                    new_code = re.sub(
                        r"const\s+" + re.escape(table_var) + r"\s*=\s*Randomize\.Array2D\([^)]*\);",
                        table_init,
                        new_code,
                        count=1
                    )
                if _valid_structure(new_code) and new_code != code:
                    return new_code, {'changed': True, 'reason': 'Initialized LCS strings and 2D table'}

        # Longest Palindrome (substring) heuristics: set s and dp NxN false
        if 'longestpalindrome' in py_lower:
            new_code = code
            # Find first Randomize.Array1D for s
            m = re.search(r"const\s+(\w+)\s*=\s*Randomize\.Array1D\([^)]*\);", new_code)
            if m:
                s_var = m.group(1)
                new_code = re.sub(
                    r"const\s+" + re.escape(s_var) + r"\s*=\s*Randomize\.Array1D\([^)]*\);",
                    f"const {s_var} = 'BBABCBCAB';",
                    new_code,
                    count=1
                )
                # If dp exists as Array2D random, replace with NxN false
                dm = re.search(r"const\s+(\w+)\s*=\s*Randomize\.Array2D\([^)]*\);", new_code)
                if dm:
                    dp_var = dm.group(1)
                    n_expr = f"{s_var}.length"
                    dp_init = f"const {dp_var} = Array({n_expr}).fill(false).map(() => Array({n_expr}).fill(false));"
                    new_code = re.sub(
                        r"const\s+" + re.escape(dp_var) + r"\s*=\s*Randomize\.Array2D\([^)]*\);",
                        dp_init,
                        new_code,
                        count=1)
                if _valid_structure(new_code) and new_code != code:
                    return new_code, {'changed': True, 'reason': 'Initialized palindrome string and DP table'}

        if not examples:
            # Without examples and no heuristic applied, avoid speculative changes
            return code, {'changed': False, 'reason': 'No similar examples available'}

        prompt = self._build_prompt(code, analysis, examples, python_code)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an expert in Algorithm Visualizer JavaScript code."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )

            improved = response.choices[0].message.content.strip()
            improved = self._extract_code(improved)

            # Minimal safety checks: preserve structure and avoid no-op
            if improved.strip() == code.strip():
                return code, {'changed': False, 'reason': 'No effective change'}

            must_have = ["require('algorithm-visualizer')", 'Layout.setRoot']
            if not all(token in improved for token in must_have):
                return code, {'changed': False, 'reason': 'Validation failed after data init change'}

            # Forbid introducing new tracer/import identifiers
            before_idents = set(self._extract_require_idents(code))
            after_idents = set(self._extract_require_idents(improved))
            if after_idents - before_idents:
                return code, {'changed': False, 'reason': 'New tracer imports not allowed'}

            return improved, {'changed': True, 'reason': 'Added custom test data'}

        except Exception as e:
            return code, {'changed': False, 'error': str(e)}

    def _build_prompt(self, code: str, analysis: Dict, examples: List[AlgoExample], python_code: str) -> str:
        example_data = ""
        if examples:
            for ex in examples:
                match = re.search(r'(const \w+ = \[.*?\];.*?const \w+ = .*?;)', ex.code, re.DOTALL)
                if match:
                    example_data += f"\nExample from {ex.name}:\n{match.group(1)}\n"

        # Special-case guidance
        special_rules = []
        py_lower = python_code.lower()
        viz_type = (analysis.get('viz_type') or '').lower()
        if 'numislands' in py_lower or (viz_type == 'array2d' and 'grid' in py_lower and ("'0'" in py_lower or '"0"' in py_lower)):
            special_rules.append("Initialize a small 2D grid (e.g., 5x5) with only 0/1 integers; DO NOT use Randomize for the grid")
            special_rules.append("Use Array2DTracer for the grid and set the exact matrix values")
        if re.search(r":type\s+\w+:\s*str", python_code) or 'numdecodings' in py_lower:
            special_rules.append("Represent the input string as an Array1D of single-character strings, e.g., const s = ['a','b','a']")
            special_rules.append("Do NOT use Randomize for strings; preserve algorithm semantics")
        if 'clonegraph' in py_lower or 'neighbors' in py_lower:
            special_rules.append("If a graph is required, create a tiny deterministic example (4-5 nodes) and set it on GraphTracer; avoid fabricating unrelated array operations")
        if 'canjump' in py_lower:
            special_rules.append("Initialize nums with values that include zeros to illustrate failure/edge cases (e.g., [3,2,1,0,4])")

        return f"""You are a specialist in Algorithm Visualizer data initialization.

CURRENT CODE:
```javascript
{code}
```

ALGORITHM TYPE: {analysis.get('viz_type')}

TASK: Replace Randomize with appropriate custom test data.

EXAMPLES OF GOOD DATA INITIALIZATION:
{example_data}

CRITICAL RULES:
1. Keep ALL imports exactly as they are (Tracer, Layout, LogTracer, etc.)
2. Keep ALL tracer declarations unchanged
3. Keep Layout.setRoot() exactly as is
4. Replace ONLY the data initialization section (the Randomize calls)
5. Add target/parameters if needed by algorithm
6. Update function call at the end to pass all required parameters
 7. Do NOT introduce new tracer/import identifiers not present in the original import
 8. Prefer deterministic literals over Randomize when custom data is needed

SPECIAL CASE RULES (apply if relevant):
{chr(10).join('- ' + r for r in special_rules)}

OUTPUT: Only the complete improved JavaScript code in a code block."""


class LoggingAgent(PolishingAgent):
    """Agent that improves logging messages"""

    def process(self, code: str, context: Dict) -> Tuple[str, Dict]:
        """Add better logging messages"""

        examples = context['similar_examples']

        example_logs = []
        for ex in examples:
            logs = re.findall(r"logger\.println\(`([^`]+)`\)", ex.code)
            if not logs:
                logs = re.findall(r"logger\.println\('([^']+)'\)", ex.code)
            example_logs.extend(logs[:3])

        if not examples:
            return code, {'changed': False, 'reason': 'No similar examples available'}

        prompt = f"""You are a specialist in Algorithm Visualizer logging.

CURRENT CODE:
```javascript
{code}
```

EXAMPLES OF GOOD LOGGING:
{chr(10).join('- logger.println(`' + log + '`);' for log in example_logs)}

TASK: Improve logger.println() messages to be:
1. Clear and educational
2. Show current state/values using template literals
3. Explain what's happening in the algorithm
4. Use template literals with ${{...}} for variable values

CRITICAL RULES:
- Keep ALL code structure unchanged
- Only modify/add logger.println() calls
- Use template literals: logger.println(`text ${{variable}}`)
- Always call Tracer.delay() after logger calls
- Do not remove any existing code

OUTPUT: Only the complete improved JavaScript code in a code block."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an expert in Algorithm Visualizer JavaScript code."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=3000
            )

            improved = response.choices[0].message.content.strip()
            improved = self._extract_code(improved)

            original_logs = code.count('logger.println')
            new_logs = improved.count('logger.println')

            # Only accept modest logging increases to avoid over-polish
            max_increase = 10
            if new_logs - original_logs > max_increase:
                return code, {'changed': False, 'reason': 'Excessive logging increase prevented'}

            # Forbid introducing new imports
            before_idents = set(self._extract_require_idents(code))
            after_idents = set(self._extract_require_idents(improved))
            if after_idents - before_idents:
                return code, {'changed': False, 'reason': 'New tracer imports not allowed'}

            changed = improved.strip() != code.strip() and new_logs >= original_logs
            return improved if changed else code, {
                'changed': changed,
                'original_logs': original_logs,
                'new_logs': new_logs
            }

        except Exception as e:
            return code, {'changed': False, 'error': str(e)}


class VisualizationAgent(PolishingAgent):
    """Agent that improves visualization calls"""

    def process(self, code: str, context: Dict) -> Tuple[str, Dict]:
        """Optimize select/deselect and patch/depatch"""

        examples = context['similar_examples']
        if not examples:
            return code, {'changed': False, 'reason': 'No similar examples available'}
        viz_guide = self._extract_viz_patterns(examples)

        prompt = f"""You are a specialist in Algorithm Visualizer visualization.

CURRENT CODE:
```javascript
{code}
```

VISUALIZATION PATTERNS TO FOLLOW:
{viz_guide}

TASK: Improve visualization calls by:
1. Adding tracer.select() before comparisons to highlight elements being compared
2. Adding tracer.patch() when modifying array values
3. Adding tracer.deselect() after operations complete
4. Adding Tracer.delay() after visual changes for smooth animation
5. Using tracer.select(i, j) for range highlighting
6. Always using tracer.depatch() after tracer.patch()

CRITICAL RULES:
- Keep ALL imports and structure unchanged
- Keep ALL existing code logic
- Only add/modify visualization-related calls (select, deselect, patch, depatch, Tracer.delay)
- Maintain the exact same algorithm behavior

OUTPUT: Only the complete improved JavaScript code in a code block."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an expert in Algorithm Visualizer JavaScript code."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=3000
            )

            improved = response.choices[0].message.content.strip()
            improved = self._extract_code(improved)

            # Safety: must preserve structure and keep changes bounded
            if improved.strip() == code.strip():
                return code, {'changed': False, 'reason': 'No effective change'}

            must_have = ["require('algorithm-visualizer')", 'Layout.setRoot']
            if not all(token in improved for token in must_have):
                return code, {'changed': False, 'reason': 'Validation failed after viz change'}

            # Forbid introducing new tracer/import identifiers
            before_idents = set(self._extract_require_idents(code))
            after_idents = set(self._extract_require_idents(improved))
            if after_idents - before_idents:
                return code, {'changed': False, 'reason': 'New tracer imports not allowed'}

            # Limit total tracer call inflation to avoid over-polishing
            tracer_calls = lambda s: len(re.findall(r'\btracer\.(select|deselect|patch|depatch)\s*\(', s))
            before_calls = tracer_calls(code)
            after_calls = tracer_calls(improved)
            if after_calls - before_calls > 20:
                return code, {'changed': False, 'reason': 'Excessive tracer calls prevented'}

            return improved, {'changed': True, 'reason': 'Optimized visualization'}

        except Exception as e:
            return code, {'changed': False, 'error': str(e)}

    def _extract_viz_patterns(self, examples: List[AlgoExample]) -> str:
        patterns = []

        for ex in examples:
            selects = re.findall(r'tracer\.select\([^)]+\);', ex.code)
            if selects:
                patterns.append(f"Select pattern: {selects[0]}")

            patches = re.findall(r'tracer\.patch\([^)]+\);', ex.code)
            if patches:
                patterns.append(f"Patch pattern: {patches[0]}")

        return "\n".join(
            patterns) if patterns else "Use select/deselect for comparisons, patch/depatch for modifications"


class UnifiedPolisherAgent(PolishingAgent):
    """Single agent that performs data init, logging, and visualization polish in one prompt."""

    def process(self, code: str, context: Dict) -> Tuple[str, Dict]:
        analysis = context['analysis']
        examples = context['similar_examples']
        python_code = context['python_code']

        # Build comprehensive prompt
        viz_guide = VisualizationAgent(self.client, "tmp")._extract_viz_patterns(examples)

        example_logs = []
        for ex in examples:
            logs = re.findall(r"logger\.println\(`([^`]+)`\)", ex.code)
            if not logs:
                logs = re.findall(r"logger\.println\('([^']+)'\)", ex.code)
            example_logs.extend(logs[:2])

        prompt = f"""You are an autonomous AI engineer that converts Python LeetCode solutions into visualized JavaScript compatible with algorithm-visualizer. Apply these directives strictly, preserving algorithm semantics and only decorating with visualization:

CORE DIRECTIVES:
- Always import exactly:
  const {{ Tracer, Array1DTracer, Array2DTracer, GraphTracer, ChartTracer, LogTracer, Layout, VerticalLayout }} = require('algorithm-visualizer');
- Always define and link:
  const tracer = new Array1DTracer();
  const logger = new LogTracer();
  Layout.setRoot(new VerticalLayout([tracer, logger]));
- Use Tracer.delay() between major steps.
- Arrays: use tracer.select()/deselect() and tracer.patch()/depatch().
- Graphs/Trees: use GraphTracer with select/deselect and set()/layoutCircle() (no patch).
- Choose tracers by structure: Array1D/Chart for arrays; Array2D for matrices/grids; GraphTracer for graphs/trees/recursion.
- Initialize deterministic example data unless true randomness is required.
- Maintain function signatures and logic; do not change algorithm semantics.
- Write clear logger messages narrating the algorithm’s thought process.

PIPELINE BEHAVIOR:
- Detect loops/conditionals/recursion and place select/patch/delay and logger messages appropriately.
- Output runnable JavaScript for the algorithm-visualizer live editor.

Apply THREE focused tasks:

1) Data initialization:
   - Prefer deterministic literals over Randomize when algorithm semantics require specific data.
   - For searching/specific-target or string algorithms, initialize meaningful arrays/strings.
   - Keep imports, tracer declarations, and Layout.setRoot exactly as-is.

2) Logging:
   - Improve logger.println() messages to be clear and educational.
   - Use template literals with ${{...}} for variable values.
   - Do not bloat logs (modest additions only).
   Example logs:\n{chr(10).join('- ' + l for l in example_logs)}

3) Visualization:
   - Use tracer.select()/deselect() before/after comparisons, patch/depatch for modifications, Tracer.delay() after visual changes.
   - Guidance:\n{viz_guide}

STRICT RULES:
   - Preserve all existing imports and tracer declarations.
   - Do NOT introduce new tracer/import identifiers.
   - Maintain algorithm logic and function signatures.
   - Output ONLY the full JavaScript code in a single code block.

CONTEXT:
Algorithm type: {analysis.get('viz_type')}
Python code (for understanding intent):\n```python\n{python_code}\n```

CURRENT CODE:
```javascript
{code}
```
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an expert in Algorithm Visualizer JavaScript code."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=3500
            )
            improved = response.choices[0].message.content.strip()
            improved = self._extract_code(improved)

            # Validation and bounded-change checks
            must_have = ["require('algorithm-visualizer')", 'Layout.setRoot']
            if not all(token in improved for token in must_have):
                return code, {'changed': False, 'reason': 'Validation failed'}

            before_idents = set(self._extract_require_idents(code))
            after_idents = set(self._extract_require_idents(improved))
            if after_idents - before_idents:
                return code, {'changed': False, 'reason': 'New tracer imports not allowed'}

            # Limit tracer/logging bloat
            def count_calls(s: str, name: str) -> int:
                return len(re.findall(rf"\\b{name}\\.", s))

            if count_calls(improved, 'logger') - count_calls(code, 'logger') > 15:
                return code, {'changed': False, 'reason': 'Excessive logging prevented'}

            tracer_before = count_calls(code, 'tracer')
            tracer_after = count_calls(improved, 'tracer')
            if tracer_after - tracer_before > 30:
                return code, {'changed': False, 'reason': 'Excessive tracer calls prevented'}

            if improved.strip() == code.strip():
                return code, {'changed': False, 'reason': 'No effective change'}

            return improved, {'changed': True, 'reason': 'Unified polish applied'}
        except Exception as e:
            return code, {'changed': False, 'error': str(e)}


class MultiAgentPolisher:
    """Orchestrates multiple specialized agents using GPT-4"""

    def __init__(self, api_key: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.rag = AlgoVisualizerRAG()

        # Unified single-agent strategy
        self.agent = UnifiedPolisherAgent(self.client, "Unified")

    def polish(self, javascript: str, python_code: str, analysis: Dict) -> Dict:
        """Run multi-agent polishing pipeline"""

        print("\n[Multi-Agent Polish] Starting GPT-4 pipeline...")

        # Step 1: RAG
        similar_examples = self.rag.find_similar(analysis, javascript)
        patterns = self.rag.extract_patterns(similar_examples)

        print(f"[RAG] Found {len(similar_examples)} similar examples")
        for ex in similar_examples:
            print(f"  - {ex.name} ({ex.category})")

        context = {
            'python_code': python_code,
            'analysis': analysis,
            'similar_examples': similar_examples,
            'patterns': patterns
        }

        # Step 2: Normalize obviously wrong tracer choices (LLM-free)
        current_code = self._normalize_tracers(javascript, analysis)
        agent_results = []

        print(f"\n[Agent: {self.agent.name}] Processing with GPT-4...")
        improved_code, metadata = self.agent.process(current_code, context)
        if metadata.get('changed'):
            print(f"[Agent: {self.agent.name}] ✓ Improved")
            current_code = improved_code
        else:
            print(f"[Agent: {self.agent.name}] - No changes")
        agent_results.append({'agent': self.agent.name, 'metadata': metadata})

        # Step 3: Validate
        if self._validate(current_code, analysis):
            print("\n[Multi-Agent Polish] ✓ GPT-4 pipeline complete")
            return {
                'polished': current_code,
                'was_polished': True,
                'provider': 'gpt-4',
                'agent_results': agent_results,
                'examples_used': [ex.name for ex in similar_examples]
            }
        else:
            print("\n[Multi-Agent Polish] ✗ Validation failed, using original")
            return {
                'polished': javascript,
                'was_polished': False,
                'error': 'Validation failed'
            }

    def _validate(self, code: str, analysis: Dict) -> bool:
        """Validate polished code and ensure tracer matches viz type."""
        required = ["require('algorithm-visualizer')", "Tracer", "Layout", "logger"]
        if not all(req in code for req in required):
            return False

        viz_type = (analysis.get('viz_type') or '').lower()
        uses_graph = 'GraphTracer' in code or 'Randomize.Graph' in code
        uses_arr1d = 'Array1DTracer' in code
        uses_arr2d = 'Array2DTracer' in code

        if viz_type == 'graph':
            return uses_graph
        if viz_type in ('sorting', 'array1d'):
            if uses_graph:
                return False
            return uses_arr1d
        if viz_type == 'array2d':
            if uses_graph:
                return False
            return uses_arr2d

        return True

    def _normalize_tracers(self, code: str, analysis: Dict) -> str:
        """Remove graph visualization when the problem is not a graph problem."""
        viz_type = (analysis.get('viz_type') or '').lower()
        if viz_type == 'graph':
            return code

        if 'GraphTracer' not in code:
            return code

        new_code = code

        # Remove Graph initialization and usage blocks
        patterns = [
            r"^\s*const\s+graphTracer\s*=\s*new\s+GraphTracer\([^)]*\);\s*$",
            r"^\s*const\s+G\s*=\s*Randomize\.Graph\([^)]*\);\s*$",
            r"^\s*graphTracer\.(set|layout\w+)\([^)]*\);\s*$",
            r"^\s*graphTracer\.[a-zA-Z]+\([^)]*\);\s*$",
        ]

        for pat in patterns:
            new_code = re.sub(pat, '', new_code, flags=re.MULTILINE)

        # Remove graphTracer from Layout list items
        new_code = re.sub(r"graphTracer,\s*", '', new_code)
        new_code = re.sub(r",\s*graphTracer", '', new_code)

        # Clean up extra blank lines
        new_code = re.sub(r"\n{3,}", "\n\n", new_code)

        return new_code


# ==================== PUBLIC API ====================

def polish_with_multi_agent(javascript: str, python_code: str, analysis: Dict) -> Dict:
    """
    Polish code using multi-agent system with GPT-4.

    Usage:
        result = polish_with_multi_agent(js_code, py_code, analysis)
        if result['was_polished']:
            print("Improved by GPT-4 agents:", result['agent_results'])
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return {
            'polished': javascript,
            'was_polished': False,
            'error': 'No OPENAI_API_KEY'
        }

    polisher = MultiAgentPolisher(api_key)
    return polisher.polish(javascript, python_code, analysis)