# -*- coding: utf-8 -*-
"""
Smart Blueprint Generator
Generates Algorithm Visualizer initialization code that matches official examples exactly.
Always uses Randomize.* for data, proper tracer setup, and correct layout patterns.
"""

from typing import Dict, List, Set, Optional


class BlueprintGenerator:
    """
    Generates the initialization/setup portion of Algorithm Visualizer code.
    Follows official patterns from algorithm-visualizer/algorithms repository.
    """

    def __init__(self, summary: Dict):
        self.summary = summary
        self.lines: List[str] = []

        # Extract analysis results
        self.vars_1d = set(summary.get("vars_1d", []))
        self.vars_2d = set(summary.get("vars_2d", []))
        self.vars_stack = set(summary.get("vars_stack", []))
        self.vars_queue = set(summary.get("vars_queue", []))
        self.vars_heap = set(summary.get("vars_heap", []))
        self.vars_graph = set(summary.get("vars_graph", []))
        self.vars_tree = set(summary.get("vars_tree", []))

        self.has_sorting = summary.get("has_sorting", False)
        self.has_graph_traversal = summary.get("has_graph_traversal", False)
        self.viz_type = summary.get("viz_type", "basic")
        self.key_vars = summary.get("key_vars", [])

    def generate(self) -> str:
        """
        Generate complete blueprint code.

        Returns:
            JavaScript initialization code as string
        """
        self.lines = []

        # 1. Imports
        self._generate_imports()

        # 2. Tracer declarations
        self._generate_tracers()

        # 3. Layout setup
        self._generate_layout()

        # 4. Data initialization with Randomize
        self._generate_data_init()

        # 5. Initial logging
        self._generate_initial_log()

        return "\n".join(self.lines)

    def _emit(self, line: str = ""):
        """Add a line to the output."""
        self.lines.append(line)

    # ==================== IMPORTS ====================

    def _generate_imports(self):
        """Generate require statement with all needed imports."""
        needed = self._determine_needed_imports()

        # Sort for consistent output
        imports = ", ".join(sorted(needed))
        self._emit(f"const {{ {imports} }} = require('algorithm-visualizer');")
        self._emit()

    def _determine_needed_imports(self) -> Set[str]:
        """Determine which Algorithm Visualizer modules are needed."""
        needed = {"Tracer", "Layout", "VerticalLayout", "LogTracer"}

        # Always add Randomize for data generation
        needed.add("Randomize")

        # Array tracers
        if self.vars_1d or self.vars_stack or self.vars_queue or self.vars_heap:
            needed.add("Array1DTracer")
            # Add chart for array visualizations
            needed.add("ChartTracer")

        if self.vars_2d:
            needed.add("Array2DTracer")

        # Graph tracer
        if self.vars_graph or self.vars_tree or self.has_graph_traversal:
            needed.add("GraphTracer")

        return needed

    # ==================== TRACERS ====================

    def _generate_tracers(self):
        """Generate all tracer declarations."""
        # Chart tracer (if needed)
        if self._needs_chart():
            self._emit("const chart = new ChartTracer();")

        # Array2D tracers
        for var in sorted(self.vars_2d):
            label = self._make_label(var)
            self._emit(f"const {var}Tracer = new Array2DTracer('{label}');")

        # Array1D tracers (including stacks, queues, heaps)
        all_1d = self.vars_1d | self.vars_stack | self.vars_queue | self.vars_heap
        for var in sorted(all_1d):
            label = self._make_label(var)

            # Add suffix for special types
            if var in self.vars_stack:
                label += " (Stack)"
            elif var in self.vars_queue:
                label += " (Queue)"
            elif var in self.vars_heap:
                label += " (Heap)"

            self._emit(f"const {var}Tracer = new Array1DTracer('{label}');")

        # Graph tracer
        if self.vars_graph or self.vars_tree or self.has_graph_traversal:
            self._emit("const graphTracer = new GraphTracer('Graph');")

        # Log tracer (always last)
        self._emit("const logger = new LogTracer('Console');")
        self._emit()

    def _needs_chart(self) -> bool:
        """Determine if ChartTracer is needed."""
        return bool(self.vars_1d or self.vars_stack or self.vars_queue or self.vars_heap)

    def _make_label(self, var: str) -> str:
        """Create a nice display label from variable name."""
        # Convert snake_case to Title Case
        words = var.replace('_', ' ').split()
        return ' '.join(word.capitalize() for word in words)

    # ==================== LAYOUT ====================

    def _generate_layout(self):
        """Generate Layout.setRoot with proper panel ordering."""
        panels = self._get_layout_panels()

        if not panels:
            panels = ["logger"]

        panels_str = ", ".join(panels)
        self._emit(f"Layout.setRoot(new VerticalLayout([{panels_str}]));")
        self._emit()

    def _get_layout_panels(self) -> List[str]:
        """
        Determine panel order for layout.
        Order: chart, graph, array2d, array1d, logger
        """
        panels = []

        # 1. Chart (if exists)
        if self._needs_chart():
            panels.append("chart")

        # 2. Graph (if exists)
        if self.vars_graph or self.vars_tree or self.has_graph_traversal:
            panels.append("graphTracer")

        # 3. 2D Arrays
        for var in sorted(self.vars_2d):
            panels.append(f"{var}Tracer")

        # 4. 1D Arrays (including stacks/queues/heaps)
        all_1d = self.vars_1d | self.vars_stack | self.vars_queue | self.vars_heap
        for var in sorted(all_1d):
            panels.append(f"{var}Tracer")

        # 5. Logger (always last)
        panels.append("logger")

        return panels

    # ==================== DATA INITIALIZATION ====================

    def _generate_data_init(self):
        """Generate data initialization using Randomize functions."""
        # Link chart to primary array if needed
        if self._needs_chart() and self.key_vars:
            primary_var = self._get_primary_1d_var()
            if primary_var:
                self._emit(f"{primary_var}Tracer.chart(chart);")

        # Initialize 2D arrays
        for var in sorted(self.vars_2d):
            self._init_array_2d(var)

        # Initialize 1D arrays
        all_1d = self.vars_1d | self.vars_stack | self.vars_queue | self.vars_heap
        for var in sorted(all_1d):
            self._init_array_1d(var)

        # Initialize graph if needed
        if self.vars_graph or self.vars_tree or self.has_graph_traversal:
            self._init_graph()

        if self.lines and self.lines[-1]:  # Add blank line if last line has content
            self._emit()

    def _init_array_1d(self, var: str):
        """Initialize a 1D array with Randomize."""
        # Determine appropriate size based on context
        size = self._get_array_size_hint(var)

        self._emit(f"const {var} = Randomize.Array1D({{ N: {size} }});")
        self._emit(f"{var}Tracer.set({var});")
        self._emit("Tracer.delay();")

    def _init_array_2d(self, var: str):
        """Initialize a 2D array with Randomize."""
        rows, cols = self._get_matrix_size_hint(var)

        self._emit(f"const {var} = Randomize.Array2D({{ N: {rows}, M: {cols} }});")
        self._emit(f"{var}Tracer.set({var});")
        self._emit("Tracer.delay();")

    def _init_graph(self):
        """Initialize graph structure."""
        # For now, use a simple random graph
        # In the future, could detect specific graph patterns
        self._emit("const G = Randomize.Graph({ N: 8, ratio: 0.3 });")
        self._emit("graphTracer.set(G);")
        self._emit("graphTracer.layoutCircle();")
        self._emit("Tracer.delay();")

    def _get_primary_1d_var(self) -> Optional[str]:
        """Get the primary 1D variable for chart linking."""
        all_1d = self.vars_1d | self.vars_stack | self.vars_queue | self.vars_heap

        # Prefer key_vars if available
        for var in self.key_vars:
            if var in all_1d:
                return var

        # Otherwise, return first 1D var
        if all_1d:
            return sorted(all_1d)[0]

        return None

    def _get_array_size_hint(self, var: str) -> int:
        """Determine appropriate size for 1D array based on context."""
        # Sorting algorithms: medium size (10-15)
        if self.has_sorting:
            return 10

        # Stacks/queues: smaller (8-10)
        if var in self.vars_stack or var in self.vars_queue:
            return 8

        # Default: 12
        return 12

    def _get_matrix_size_hint(self, var: str) -> tuple:
        """Determine appropriate dimensions for 2D array."""
        # Graph-related: square matrix (5x5 or 6x6)
        if self.has_graph_traversal:
            return (6, 6)

        # DP problems: often rectangular
        if self.summary.get("has_dp", False):
            return (5, 7)

        # Default: square
        return (5, 5)

    # ==================== INITIAL LOGGING ====================

    def _generate_initial_log(self):
        """Generate initial log message."""
        message = self._get_initial_message()
        self._emit(f"logger.println('{message}');")
        self._emit("Tracer.delay();")
        self._emit()

    def _get_initial_message(self) -> str:
        """Generate appropriate initial message based on detected pattern."""
        if self.has_sorting:
            return "Starting sorting algorithm..."
        elif self.summary.get("has_searching", False):
            return "Starting search algorithm..."
        elif self.has_graph_traversal:
            return "Starting graph traversal..."
        elif self.summary.get("has_dp", False):
            return "Starting dynamic programming solution..."
        else:
            return "Algorithm visualization initialized"


# ==================== PUBLIC API ====================

def generate_blueprint(summary: Dict) -> str:
    """
    Generate Algorithm Visualizer initialization code from analysis summary.

    Args:
        summary: Analysis dictionary from EnhancedAnalyzer

    Returns:
        JavaScript initialization code as string

    Example:
        >>> from analyzer import analyze_code
        >>> from blueprint_generator import generate_blueprint
        >>>
        >>> code = '''
        ... def bubbleSort(arr):
        ...     n = len(arr)
        ...     for i in range(n):
        ...         for j in range(n-i-1):
        ...             if arr[j] > arr[j+1]:
        ...                 arr[j], arr[j+1] = arr[j+1], arr[j]
        ... '''
        >>>
        >>> summary = analyze_code(code)
        >>> blueprint = generate_blueprint(summary)
        >>> print(blueprint)
        const { Array1DTracer, ChartTracer, Layout, LogTracer, Randomize, Tracer, VerticalLayout } = require('algorithm-visualizer');

        const chart = new ChartTracer();
        const arrTracer = new Array1DTracer('Arr');
        const logger = new LogTracer('Console');

        Layout.setRoot(new VerticalLayout([chart, arrTracer, logger]));

        arrTracer.chart(chart);
        const arr = Randomize.Array1D({ N: 10 });
        arrTracer.set(arr);
        Tracer.delay();

        logger.println('Starting sorting algorithm...');
        Tracer.delay();
    """
    generator = BlueprintGenerator(summary)
    return generator.generate()


# ==================== EXAMPLES ====================

if __name__ == "__main__":
    # Example 1: Sorting algorithm
    print("=== Example 1: Bubble Sort ===")
    summary1 = {
        "vars_1d": ["arr"],
        "vars_2d": [],
        "has_sorting": True,
        "viz_type": "sorting",
        "key_vars": ["arr"],
    }
    print(generate_blueprint(summary1))
    print()

    # Example 2: Matrix problem
    print("=== Example 2: Matrix Problem ===")
    summary2 = {
        "vars_1d": [],
        "vars_2d": ["matrix"],
        "has_sorting": False,
        "viz_type": "array2d",
        "key_vars": ["matrix"],
    }
    print(generate_blueprint(summary2))
    print()

    # Example 3: Graph traversal
    print("=== Example 3: Graph DFS ===")
    summary3 = {
        "vars_1d": ["visited"],
        "vars_2d": [],
        "vars_graph": ["graph"],
        "has_graph_traversal": True,
        "viz_type": "graph",
        "key_vars": ["graph", "visited"],
    }
    print(generate_blueprint(summary3))