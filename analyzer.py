# -*- coding: utf-8 -*-
"""
Enhanced Analyzer Module
Performs deep analysis of Python code to detect:
- All data structures (arrays, matrices, graphs, trees, stacks, queues, heaps, etc.)
- Variable relationships and dependencies
- Visualization points (comparisons, swaps, updates)
- Algorithm patterns for optimal tracer selection
"""

import ast
from collections import defaultdict
from typing import Dict, Set, List, Tuple, Optional


class EnhancedAnalyzer(ast.NodeVisitor):
    """
    Comprehensive code analyzer for Algorithm Visualizer pipeline.
    Detects data structures, tracks relationships, identifies visualization points.
    """

    def __init__(self):
        # Data structure tracking
        self.vars_1d = set()  # Arrays/lists
        self.vars_2d = set()  # Matrices
        self.vars_graph = set()  # Graph structures
        self.vars_tree = set()  # Tree nodes
        self.vars_stack = set()  # Stack-like structures
        self.vars_queue = set()  # Queue-like structures
        self.vars_heap = set()  # Heaps
        self.vars_set = set()  # Sets
        self.vars_dict = set()  # Dictionaries
        self.vars_defaultdict = set()  # defaultdict
        self.vars_counter = set()  # Counter

        # Variable relationships
        self.var_sources = defaultdict(set)  # var -> where it came from
        self.var_depth = defaultdict(int)  # var -> max subscript depth
        self.method_calls = defaultdict(set)  # var -> methods called on it

        # Visualization points
        self.comparison_points = []  # (line, vars_involved)
        self.swap_points = []  # (line, vars_involved)
        self.update_points = []  # (line, var, index_info)

        # Algorithm patterns
        self.has_sorting = False
        self.has_searching = False
        self.has_graph_traversal = False
        self.has_dp = False
        self.has_backtracking = False

        # Context tracking
        self.current_function = None
        self.loop_depth = 0
        self.in_condition = False

    # ==================== ASSIGNMENT ANALYSIS ====================

    def visit_Assign(self, node: ast.Assign):
        """Analyze variable assignments to detect data structure types."""
        if not node.targets:
            self.generic_visit(node)
            return

        target = node.targets[0]

        # Handle destructuring: a, b = ...
        if isinstance(target, (ast.Tuple, ast.List)):
            self._handle_destructuring(target, node.value)
        # Handle simple assignment: x = ...
        elif isinstance(target, ast.Name):
            self._handle_simple_assign(target.id, node.value)
        # Handle subscript assignment: arr[i] = ...
        elif isinstance(target, ast.Subscript):
            self._handle_subscript_assign(target, node.value)

        self.generic_visit(node)

    def _handle_destructuring(self, target, value):
        """Handle tuple/list unpacking."""
        names = []
        for el in target.elts:
            if isinstance(el, ast.Name):
                names.append(el.id)

        # Track that these variables came from unpacking
        for name in names:
            self.var_sources[name].add("destructured")

    def _handle_simple_assign(self, name: str, value):
        """Analyze simple variable assignment."""
        # Literal lists
        if isinstance(value, ast.List):
            if value.elts and all(isinstance(e, ast.List) for e in value.elts):
                self.vars_2d.add(name)
                self.var_depth[name] = 2
                self.var_sources[name].add("literal_2d")
            else:
                self.vars_1d.add(name)
                self.var_depth[name] = 1
                self.var_sources[name].add("literal_1d")

        # List multiplication: [0] * n
        elif isinstance(value, ast.BinOp) and isinstance(value.op, ast.Mult):
            if isinstance(value.left, ast.List) or isinstance(value.right, ast.List):
                self.vars_1d.add(name)
                self.var_depth[name] = 1
                self.var_sources[name].add("list_mult")

        # List comprehension
        elif isinstance(value, ast.ListComp):
            # Check if nested comprehension (2D)
            has_nested = any(isinstance(gen.iter, (ast.ListComp, ast.Subscript))
                             for gen in value.generators)
            if has_nested or len(value.generators) >= 2:
                self.vars_2d.add(name)
                self.var_depth[name] = 2
                self.var_sources[name].add("list_comp_2d")
            else:
                self.vars_1d.add(name)
                self.var_depth[name] = 1
                self.var_sources[name].add("list_comp_1d")

        # Function calls
        elif isinstance(value, ast.Call):
            self._handle_call_assign(name, value)

        # Copy from another variable
        elif isinstance(value, ast.Name):
            source = value.id
            if source in self.vars_1d:
                self.vars_1d.add(name)
                self.var_sources[name].add(f"copy_of_{source}")
            elif source in self.vars_2d:
                self.vars_2d.add(name)
                self.var_sources[name].add(f"copy_of_{source}")

    def _handle_call_assign(self, name: str, call: ast.Call):
        """Handle assignment from function call."""
        if not isinstance(call.func, ast.Name):
            return

        func_name = call.func.id

        # Collections
        if func_name == "deque":
            self.vars_queue.add(name)
            self.vars_1d.add(name)
            self.var_sources[name].add("deque_init")
        elif func_name == "defaultdict":
            self.vars_defaultdict.add(name)
            self.vars_dict.add(name)
            self.var_sources[name].add("defaultdict_init")
        elif func_name == "Counter":
            self.vars_counter.add(name)
            self.vars_dict.add(name)
            self.var_sources[name].add("counter_init")
        elif func_name == "set":
            self.vars_set.add(name)
            self.var_sources[name].add("set_init")
        elif func_name == "dict":
            self.vars_dict.add(name)
            self.var_sources[name].add("dict_init")
        elif func_name == "list":
            self.vars_1d.add(name)
            self.var_sources[name].add("list_init")

        # Built-in functions that return lists
        elif func_name in ("sorted", "reversed", "map", "filter"):
            self.vars_1d.add(name)
            self.var_sources[name].add(f"{func_name}_result")

    def _handle_subscript_assign(self, target: ast.Subscript, value):
        """Track subscript assignments for update points."""
        base, depth = self._get_subscript_info(target)
        if base:
            self.update_points.append({
                "var": base,
                "depth": depth,
                "line": getattr(target, 'lineno', -1)
            })

    # ==================== SUBSCRIPT ANALYSIS ====================

    def visit_Subscript(self, node: ast.Subscript):
        """Analyze subscript access patterns."""
        base, depth = self._get_subscript_info(node)

        if base:
            # Update max depth for this variable
            if depth > self.var_depth[base]:
                self.var_depth[base] = depth

            # Classify based on depth
            if depth == 1:
                self.vars_1d.add(base)
            elif depth >= 2:
                self.vars_2d.add(base)

        self.generic_visit(node)

    def _get_subscript_info(self, node: ast.Subscript) -> Tuple[Optional[str], int]:
        """Get base variable name and subscript depth."""
        depth = 0
        current = node

        while isinstance(current, ast.Subscript):
            depth += 1
            current = current.value
            if depth > 10:  # Safety limit
                break

        if isinstance(current, ast.Name):
            return current.id, depth

        return None, depth

    # ==================== LOOP ANALYSIS ====================

    def visit_For(self, node: ast.For):
        """Analyze for loops for iteration patterns."""
        self.loop_depth += 1

        # Check for range-based iteration
        if isinstance(node.iter, ast.Call):
            if isinstance(node.iter.func, ast.Name):
                if node.iter.func.id == "range":
                    # Likely array iteration
                    pass
                elif node.iter.func.id == "enumerate":
                    # Enumerate suggests array operations
                    if node.iter.args and isinstance(node.iter.args[0], ast.Name):
                        arr_name = node.iter.args[0].id
                        self.vars_1d.add(arr_name)

        # Check for direct iteration: for x in arr
        elif isinstance(node.iter, ast.Name):
            arr_name = node.iter.id
            self.vars_1d.add(arr_name)

        # Check for nested list iteration: for row in matrix
        elif isinstance(node.iter, ast.Subscript):
            base, _ = self._get_subscript_info(node.iter)
            if base:
                self.vars_2d.add(base)
                self.has_graph_traversal = True

        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_While(self, node: ast.While):
        """Analyze while loops."""
        self.loop_depth += 1
        self.generic_visit(node)
        self.loop_depth -= 1

    # ==================== COMPARISON ANALYSIS ====================

    def visit_Compare(self, node: ast.Compare):
        """Track comparison operations for visualization."""
        self.in_condition = True

        # Extract variables involved in comparison
        vars_involved = set()

        for n in ast.walk(node):
            if isinstance(n, ast.Name):
                vars_involved.add(n.id)
            elif isinstance(n, ast.Subscript):
                base, _ = self._get_subscript_info(n)
                if base:
                    vars_involved.add(base)

        if vars_involved:
            self.comparison_points.append({
                "line": getattr(node, 'lineno', -1),
                "vars": list(vars_involved)
            })

        self.generic_visit(node)
        self.in_condition = False

    # ==================== METHOD CALL ANALYSIS ====================

    def visit_Attribute(self, node: ast.Attribute):
        """Track method calls to infer data structure types."""
        if isinstance(node.value, ast.Name):
            var_name = node.value.id
            method = node.attr

            self.method_calls[var_name].add(method)

            # Stack operations
            if method in ("append", "pop"):
                self.vars_stack.add(var_name)
                self.vars_1d.add(var_name)

            # Queue operations
            elif method in ("popleft", "appendleft"):
                self.vars_queue.add(var_name)
                self.vars_1d.add(var_name)

            # Tree operations
            elif method in ("left", "right", "parent", "val"):
                self.vars_tree.add(var_name)
                self.has_graph_traversal = True

            # Set operations
            elif method in ("add", "remove", "discard", "union", "intersection"):
                self.vars_set.add(var_name)

            # Dict operations
            elif method in ("keys", "values", "items", "get"):
                self.vars_dict.add(var_name)

        self.generic_visit(node)

    # ==================== FUNCTION CALL ANALYSIS ====================

    def visit_Call(self, node: ast.Call):
        """Detect algorithm patterns from function calls."""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id

            # Sorting
            if func_name in ("sort", "sorted"):
                self.has_sorting = True

            # Searching
            elif func_name in ("bisect", "bisect_left", "bisect_right"):
                self.has_searching = True

            # Heap operations
            elif func_name in ("heappush", "heappop", "heapify"):
                self.has_heap = True
                if node.args and isinstance(node.args[0], ast.Name):
                    self.vars_heap.add(node.args[0].id)
                    self.vars_1d.add(node.args[0].id)

        # heapq module calls
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "heapq":
                self.has_heap = True
                if node.args and isinstance(node.args[0], ast.Name):
                    self.vars_heap.add(node.args[0].id)
                    self.vars_1d.add(node.args[0].id)

        self.generic_visit(node)

    # ==================== FUNCTION DEFINITION ANALYSIS ====================

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Track function context."""
        prev_function = self.current_function
        self.current_function = node.name

        # Detect algorithm patterns from function name
        name_lower = node.name.lower()
        if any(x in name_lower for x in ["sort", "bubble", "merge", "quick"]):
            self.has_sorting = True
        elif any(x in name_lower for x in ["search", "binary", "find"]):
            self.has_searching = True
        elif any(x in name_lower for x in ["dfs", "bfs", "traverse", "graph"]):
            self.has_graph_traversal = True
        elif "dp" in name_lower or "dynamic" in name_lower:
            self.has_dp = True
        elif "backtrack" in name_lower:
            self.has_backtracking = True

        self.generic_visit(node)
        self.current_function = prev_function

    # ==================== SUMMARY GENERATION ====================

    def summarize(self) -> Dict:
        """
        Generate comprehensive analysis summary.

        Returns:
            Dict containing all analysis results for pipeline consumption.
        """
        # Remove overlaps (2D takes precedence over 1D)
        self.vars_1d -= self.vars_2d

        # Determine primary visualization type
        viz_type = self._determine_viz_type()

        # Identify key variables for tracing
        key_vars = self._identify_key_vars()

        return {
            # Data structures
            "vars_1d": sorted(self.vars_1d),
            "vars_2d": sorted(self.vars_2d),
            "vars_graph": sorted(self.vars_graph),
            "vars_tree": sorted(self.vars_tree),
            "vars_stack": sorted(self.vars_stack),
            "vars_queue": sorted(self.vars_queue),
            "vars_heap": sorted(self.vars_heap),
            "vars_set": sorted(self.vars_set),
            "vars_dict": sorted(self.vars_dict),
            "vars_defaultdict": sorted(self.vars_defaultdict),
            "vars_counter": sorted(self.vars_counter),

            # Flags
            "has_array1d": bool(self.vars_1d),
            "has_array2d": bool(self.vars_2d),
            "has_graph": bool(self.vars_graph) or self.has_graph_traversal,
            "has_tree": bool(self.vars_tree),
            "has_stack": bool(self.vars_stack),
            "has_queue": bool(self.vars_queue),
            "has_heap": bool(self.vars_heap),
            "has_set": bool(self.vars_set),
            "has_dict": bool(self.vars_dict),

            # Algorithm patterns
            "has_sorting": self.has_sorting,
            "has_searching": self.has_searching,
            "has_graph_traversal": self.has_graph_traversal,
            "has_dp": self.has_dp,
            "has_backtracking": self.has_backtracking,

            # Visualization points
            "comparison_points": self.comparison_points,
            "swap_points": self.swap_points,
            "update_points": self.update_points,

            # Metadata
            "viz_type": viz_type,
            "key_vars": key_vars,
            "var_sources": {k: sorted(v) for k, v in self.var_sources.items()},
            "method_calls": {k: sorted(v) for k, v in self.method_calls.items()},
            "var_depth": dict(self.var_depth),
        }

    def _determine_viz_type(self) -> str:
        """Determine the primary visualization type needed."""
        if self.has_graph_traversal or self.vars_graph or self.vars_tree:
            return "graph"
        elif self.vars_2d:
            return "array2d"
        elif self.has_sorting:
            return "sorting"
        elif self.vars_1d:
            return "array1d"
        elif self.vars_stack or self.vars_queue:
            return "stack_queue"
        else:
            return "basic"

    def _identify_key_vars(self) -> List[str]:
        """
        Identify the most important variables for visualization.
        Priority: arrays > matrices > other structures
        """
        key_vars = []

        # Prioritize 2D arrays (most visual impact)
        if self.vars_2d:
            key_vars.extend(sorted(self.vars_2d)[:2])  # Max 2

        # Then 1D arrays
        if self.vars_1d and len(key_vars) < 3:
            remaining = 3 - len(key_vars)
            key_vars.extend(sorted(self.vars_1d)[:remaining])

        # Then stacks/queues
        if (self.vars_stack or self.vars_queue) and len(key_vars) < 3:
            stack_queue = sorted(self.vars_stack | self.vars_queue)
            remaining = 3 - len(key_vars)
            key_vars.extend(stack_queue[:remaining])

        return key_vars


# ==================== PUBLIC API ====================

def analyze_code(code: str) -> Dict:
    """
    Analyze Python code for Algorithm Visualizer pipeline.

    Args:
        code: Python source code to analyze

    Returns:
        Comprehensive analysis dictionary

    Example:
        >>> code = '''
        ... def bubbleSort(arr):
        ...     n = len(arr)
        ...     for i in range(n):
        ...         for j in range(n-i-1):
        ...             if arr[j] > arr[j+1]:
        ...                 arr[j], arr[j+1] = arr[j+1], arr[j]
        ... '''
        >>> summary = analyze_code(code)
        >>> print(summary['has_sorting'])
        True
        >>> print(summary['vars_1d'])
        ['arr']
    """
    try:
        tree = ast.parse(code)
        analyzer = EnhancedAnalyzer()
        analyzer.visit(tree)
        return analyzer.summarize()
    except SyntaxError as e:
        return {
            "error": f"Syntax error: {e}",
            "vars_1d": [],
            "vars_2d": [],
            "has_array1d": False,
            "has_array2d": False,
        }