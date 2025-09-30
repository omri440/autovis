# -*- coding: utf-8 -*-
"""
Indentation Fixer Module
Normalizes Python code indentation to consistent 4-space format.
Handles mixed tabs/spaces, inconsistent indentation, and common formatting issues.
"""

import re
from typing import List, Tuple


class IndentationFixer:
    """
    Fixes and normalizes Python code indentation.
    Converts all indentation to 4 spaces and handles edge cases.
    """

    def __init__(self, target_indent: int = 4):
        self.target_indent = target_indent

    def fix(self, code: str) -> str:
        """
        Main entry point: fix all indentation issues in Python code.

        Args:
            code: Raw Python code with potentially inconsistent indentation

        Returns:
            Normalized Python code with consistent 4-space indentation
        """
        if not code or not code.strip():
            return code

        lines = code.split('\n')

        # Step 1: Convert tabs to spaces
        lines = self._convert_tabs_to_spaces(lines)

        # Step 2: Detect original indentation unit
        indent_unit = self._detect_indent_unit(lines)

        # Step 3: Normalize all indentation
        lines = self._normalize_indentation(lines, indent_unit)

        # Step 4: Fix common issues
        lines = self._fix_common_issues(lines)

        return '\n'.join(lines)

    def _convert_tabs_to_spaces(self, lines: List[str]) -> List[str]:
        """Convert all tabs to spaces (1 tab = 4 spaces)."""
        return [line.replace('\t', '    ') for line in lines]

    def _detect_indent_unit(self, lines: List[str]) -> int:
        """
        Detect the indentation unit used in the code.
        Returns the most common indentation step (e.g., 2, 4, or 8 spaces).
        """
        indents = []

        for line in lines:
            if not line.strip():
                continue

            # Count leading spaces
            stripped = line.lstrip()
            if not stripped:
                continue

            spaces = len(line) - len(stripped)
            if spaces > 0:
                indents.append(spaces)

        if not indents:
            return self.target_indent

        # Find the GCD of all indentation levels (likely the unit)
        from math import gcd
        from functools import reduce

        try:
            indent_gcd = reduce(gcd, indents)
            # Common indentation units are 2, 4, or 8
            if indent_gcd in (2, 4, 8):
                return indent_gcd
            # If we got 1 (inconsistent), assume 4
            return self.target_indent
        except:
            return self.target_indent

    def _normalize_indentation(self, lines: List[str], source_indent: int) -> List[str]:
        """
        Normalize indentation from source_indent to target_indent.
        """
        if source_indent == self.target_indent:
            return lines

        normalized = []

        for line in lines:
            if not line.strip():
                # Keep empty lines empty
                normalized.append('')
                continue

            # Count original indentation
            stripped = line.lstrip()
            original_spaces = len(line) - len(stripped)

            # Calculate indentation level
            indent_level = original_spaces // source_indent if source_indent > 0 else 0

            # Apply target indentation
            new_line = (' ' * (indent_level * self.target_indent)) + stripped
            normalized.append(new_line)

        return normalized

    def _fix_common_issues(self, lines: List[str]) -> List[str]:
        """
        Fix common indentation-related issues:
        - Remove trailing whitespace
        - Fix inline comments spacing
        - Ensure blank lines are truly blank
        """
        fixed = []

        for line in lines:
            # Remove trailing whitespace
            line = line.rstrip()

            # Ensure blank lines are empty (no spaces)
            if not line.strip():
                fixed.append('')
                continue

            # Fix inline comment spacing: ensure one space before #
            if '#' in line:
                # Don't touch string literals
                if not self._is_in_string(line, line.index('#')):
                    parts = line.split('#', 1)
                    if len(parts) == 2:
                        code_part = parts[0].rstrip()
                        comment_part = parts[1].lstrip()
                        line = f"{code_part} # {comment_part}".rstrip()

            fixed.append(line)

        return fixed

    def _is_in_string(self, line: str, position: int) -> bool:
        """
        Check if a position in the line is inside a string literal.
        Simple heuristic: count quotes before the position.
        """
        before = line[:position]

        # Count unescaped quotes
        single_quotes = before.count("'") - before.count("\\'")
        double_quotes = before.count('"') - before.count('\\"')

        # If odd number of quotes, we're inside a string
        return (single_quotes % 2 == 1) or (double_quotes % 2 == 1)


def fix_indentation(code: str, target_indent: int = 4) -> str:
    """
    Convenience function to fix Python code indentation.

    Args:
        code: Python code to fix
        target_indent: Target indentation width (default: 4 spaces)

    Returns:
        Fixed Python code with normalized indentation

    Example:
        >>> code = '''
        ... def foo():
        ...   if True:
        ...     print("hello")
        ... '''
        >>> fixed = fix_indentation(code)
        >>> print(fixed)
        def foo():
            if True:
                print("hello")
    """
    fixer = IndentationFixer(target_indent=target_indent)
    return fixer.fix(code)


# Test cases for validation
if __name__ == "__main__":
    # Test 1: Mixed tabs and spaces
    test1 = """def foo():
\tif True:
\t    print("hello")
\t\treturn 1"""

    print("Test 1 - Mixed tabs/spaces:")
    print(fix_indentation(test1))
    print()

    # Test 2: 2-space indentation
    test2 = """def bar():
  x = 1
  if x:
    return x
  else:
    return 0"""

    print("Test 2 - 2-space to 4-space:")
    print(fix_indentation(test2))
    print()

    # Test 3: Inconsistent indentation
    test3 = """def baz():
   x = 1
     y = 2
  return x + y"""

    print("Test 3 - Inconsistent indentation:")
    print(fix_indentation(test3))
    print()

    # Test 4: Nested structures
    test4 = """class Matrix:
  def setZeroes(self, matrix):
    rows = len(matrix)
    for i in range(rows):
      for j in range(len(matrix[0])):
        if matrix[i][j] == 0:
          matrix[i][j] = -1
    return matrix"""

    print("Test 4 - Nested structures:")
    print(fix_indentation(test4))
    print()

    # Test 5: Real LeetCode example
    test5 = """def twoSum(nums, target):
    hashmap = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in hashmap:
            return [hashmap[complement], i]
        hashmap[num] = i
    return []"""

    print("Test 5 - Already correct (should preserve):")
    print(fix_indentation(test5))