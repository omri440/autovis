# # -*- coding: utf-8 -*-
# """
# Instrumented Translator Module
# Translates Python to JavaScript with automatic Algorithm Visualizer instrumentation.
# Integrates with EnhancedAnalyzer output to inject tracers at optimal points.
# """
#
# import ast
# from typing import Dict, List, Set, Optional, Tuple
#
#
# # ==================== PARAMETER PROPAGATION ====================
#
# def _collect_param_bindings(module: ast.Module) -> Dict[str, Dict[str, Optional[str]]]:
#     """
#     Map function parameters to their actual argument names from top-level calls.
#     Supports one level of propagation (top-level → nested).
#     """
#     func_params: Dict[str, List[str]] = {}
#     func_bodies: Dict[str, List[ast.stmt]] = {}
#
#     for stmt in module.body:
#         if isinstance(stmt, ast.FunctionDef):
#             func_params[stmt.name] = [a.arg for a in stmt.args.args]
#             func_bodies[stmt.name] = stmt.body
#
#     bindings: Dict[str, Dict[str, Optional[str]]] = {}
#
#     # Collect top-level calls
#     for stmt in module.body:
#         if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
#             if isinstance(stmt.value.func, ast.Name):
#                 fname = stmt.value.func.id
#                 if fname in func_params and fname not in bindings:
#                     m: Dict[str, Optional[str]] = {}
#                     params = func_params[fname]
#                     for i, p in enumerate(params):
#                         if i < len(stmt.value.args):
#                             a = stmt.value.args[i]
#                             m[p] = a.id if isinstance(a, ast.Name) else None
#                         else:
#                             m[p] = None
#                     bindings[fname] = m
#
#     # Propagate one level deep
#     for fname, param_map in list(bindings.items()):
#         body = func_bodies.get(fname, [])
#         for stmt in body:
#             if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
#                 call = stmt.value
#                 if isinstance(call.func, ast.Name):
#                     gname = call.func.id
#                     if gname in func_params and gname not in bindings:
#                         gparams = func_params[gname]
#                         gm: Dict[str, Optional[str]] = {}
#                         for i, gp in enumerate(gparams):
#                             if i < len(call.args):
#                                 arg = call.args[i]
#                                 if isinstance(arg, ast.Name):
#                                     gm[gp] = param_map.get(arg.id) or None
#                                 else:
#                                     gm[gp] = None
#                             else:
#                                 gm[gp] = None
#                         bindings[gname] = gm
#
#     return bindings
#
#
# # ==================== MAIN TRANSLATOR CLASS ====================
#
# class InstrumentedTranslator(ast.NodeVisitor):
#     """
#     Translates Python AST to instrumented JavaScript for Algorithm Visualizer.
#     Automatically injects select/deselect, patch/depatch, and logger calls.
#     """
#
#     def __init__(
#             self,
#             summary: Dict,
#             traceable_1d: Optional[Set[str]] = None,
#             traceable_2d: Optional[Set[str]] = None,
#             param_bindings: Optional[Dict[str, Dict[str, Optional[str]]]] = None,
#     ):
#         self.summary = summary
#         self.lines: List[str] = []
#         self.ind = 0
#         self._tmp_counter = 0
#
#         # Scope tracking
#         self.scope_stack: List[Set[str]] = [set()]
#         self.func_stack: List[str] = []
#
#         # Traceable variables
#         self.traceable_1d = set(traceable_1d or [])
#         self.traceable_2d = set(traceable_2d or [])
#
#         # Parameter bindings for cross-function tracing
#         self.param_bindings = param_bindings or {}
#
#         # Helper polyfills needed
#         self.helpers_needed: Set[str] = set()
#
#         # Loop context
#         self.loop_stack: List[str] = []
#
#     # ==================== UTILITIES ====================
#
#     def emit(self, s: str):
#         """Emit a line of JavaScript code."""
#         self.lines.append("  " * self.ind + s)
#
#     def _gensym(self, prefix="__tmp"):
#         """Generate a unique temporary variable name."""
#         self._tmp_counter += 1
#         return f"{prefix}{self._tmp_counter}"
#
#     def _is_declared(self, name: str) -> bool:
#         """Check if variable is declared in current scope chain."""
#         return any(name in s for s in self.scope_stack)
#
#     def _declare(self, name: str):
#         """Mark variable as declared in current scope."""
#         self.scope_stack[-1].add(name)
#
#     def _emit_decl_or_assign(self, name: str, rhs_js: str):
#         """Emit declaration or assignment depending on scope."""
#         if self._is_declared(name):
#             self.emit(f"{name} = {rhs_js};")
#         else:
#             self.emit(f"let {name} = {rhs_js};")
#             self._declare(name)
#
#     def _mapped_tracer_base(self, base_name: str) -> str:
#         """Map parameter name to actual argument name for tracing."""
#         if self.func_stack:
#             fname = self.func_stack[-1]
#             m = self.param_bindings.get(fname, {})
#             arg = m.get(base_name)
#             if arg:
#                 return arg
#         return base_name
#
#     # ==================== HELPER CODE GENERATION ====================
#
#     def _get_helper_code(self) -> List[str]:
#         """Generate polyfill code for helpers."""
#         code = []
#
#         if "IDX" in self.helpers_needed:
#             code.append("function __idx(arr, i) { return i < 0 ? arr.length + i : i; }")
#
#         if "ZIP" in self.helpers_needed:
#             code.extend([
#                 "function __zip(...arrs) {",
#                 "  const m = Math.min(...arrs.map(a => a.length));",
#                 "  return Array.from({length: m}, (_, i) => arrs.map(a => a[i]));",
#                 "}",
#             ])
#
#         if "DEFAULTDICT" in self.helpers_needed:
#             code.extend([
#                 "function __defaultdict(factory) {",
#                 "  return new Proxy({}, {",
#                 "    get(t, k) { if (!(k in t)) t[k] = factory(); return t[k]; },",
#                 "    set(t, k, v) { t[k] = v; return true; }",
#                 "  });",
#                 "}",
#             ])
#
#         if "COUNTER" in self.helpers_needed:
#             code.extend([
#                 "function __counter(seq) {",
#                 "  const c = {};",
#                 "  for (const x of seq) { c[x] = (c[x] || 0) + 1; }",
#                 "  return c;",
#                 "}",
#             ])
#
#         if "HEAP" in self.helpers_needed:
#             code.extend([
#                 "function __heappush(h, x) {",
#                 "  h.push(x);",
#                 "  let i = h.length - 1;",
#                 "  while (i > 0) {",
#                 "    const p = (i - 1) >> 1;",
#                 "    if (h[p] <= h[i]) break;",
#                 "    [h[p], h[i]] = [h[i], h[p]];",
#                 "    i = p;",
#                 "  }",
#                 "}",
#                 "function __heappop(h) {",
#                 "  if (h.length === 0) return undefined;",
#                 "  const top = h[0];",
#                 "  const x = h.pop();",
#                 "  if (h.length) {",
#                 "    h[0] = x;",
#                 "    let i = 0, n = h.length;",
#                 "    while (true) {",
#                 "      let l = 2 * i + 1, r = l + 1, s = i;",
#                 "      if (l < n && h[l] < h[s]) s = l;",
#                 "      if (r < n && h[r] < h[s]) s = r;",
#                 "      if (s === i) break;",
#                 "      [h[i], h[s]] = [h[s], h[i]];",
#                 "      i = s;",
#                 "    }",
#                 "  }",
#                 "  return top;",
#                 "}",
#             ])
#
#         if "SUM" in self.helpers_needed:
#             code.append("const __sum = arr => arr.reduce((a, b) => a + b, 0);")
#         if "SORTED" in self.helpers_needed:
#             code.append("const __sorted = arr => [...arr].sort((a, b) => a - b);")
#         if "REVERSED" in self.helpers_needed:
#             code.append("const __reversed = arr => [...arr].reverse();")
#
#         return code
#
#     # ==================== EXPRESSION TRANSLATION ====================
#
#     def js_expr(self, node: ast.AST) -> str:
#         """Main expression translator dispatcher."""
#         if not isinstance(node, ast.AST):
#             if isinstance(node, (int, float)):
#                 return repr(node)
#             return "/*expr*/"
#
#         if isinstance(node, ast.Constant):
#             return self._handle_constant(node)
#         if isinstance(node, ast.Name):
#             return node.id
#         if isinstance(node, ast.UnaryOp):
#             return self._handle_unary_op(node)
#         if isinstance(node, ast.BinOp):
#             return self._handle_binary_op(node)
#         if isinstance(node, ast.BoolOp):
#             return self._handle_bool_op(node)
#         if isinstance(node, ast.Compare):
#             return self._handle_compare(node)
#         if isinstance(node, ast.Subscript):
#             return self._handle_subscript(node)
#         if isinstance(node, ast.Attribute):
#             return f"{self.js_expr(node.value)}.{node.attr}"
#         if isinstance(node, ast.Call):
#             return self._handle_call(node)
#         if isinstance(node, ast.List):
#             return "[" + ", ".join(self.js_expr(e) for e in node.elts) + "]"
#         if isinstance(node, ast.Tuple):
#             return "[" + ", ".join(self.js_expr(e) for e in node.elts) + "]"
#         if isinstance(node, ast.Set):
#             return "new Set([" + ", ".join(self.js_expr(e) for e in node.elts) + "])"
#         if isinstance(node, ast.Dict):
#             pairs = [f"[{self.js_expr(k)}, {self.js_expr(v)}]"
#                      for k, v in zip(node.keys, node.values)]
#             return f"Object.fromEntries([{', '.join(pairs)}])"
#         if isinstance(node, ast.ListComp):
#             return self._handle_list_comp(node)
#         if isinstance(node, ast.GeneratorExp):
#             return self._handle_generator_exp(node)
#
#         return "/*expr*/"
#
#     def _handle_constant(self, node: ast.Constant) -> str:
#         v = node.value
#         if v is None: return "null"
#         if isinstance(v, bool): return "true" if v else "false"
#         if isinstance(v, float) and v == float("inf"): return "Infinity"
#         return repr(v)
#
#     def _handle_unary_op(self, node: ast.UnaryOp) -> str:
#         if isinstance(node.op, ast.Not):
#             return f"!({self.js_expr(node.operand)})"
#         if isinstance(node.op, ast.USub):
#             inner = node.operand
#             if isinstance(inner, ast.Constant) and isinstance(inner.value, (int, float)):
#                 return f"-{repr(inner.value)}"
#             return f"-({self.js_expr(inner)})"
#         return f"/*unary*/({self.js_expr(node.operand)})"
#
#     def _handle_binary_op(self, node: ast.BinOp) -> str:
#         from ast import Add, Sub, Mult, Div, Mod, FloorDiv
#
#         # Special case: [x] * n
#         if isinstance(node.op, Mult):
#             if isinstance(node.left, ast.List) and len(node.left.elts) == 1:
#                 n_js = self.js_expr(node.right)
#                 elem_js = self.js_expr(node.left.elts[0])
#                 return f"new Array({n_js}).fill({elem_js})"
#             if isinstance(node.right, ast.List) and len(node.right.elts) == 1:
#                 n_js = self.js_expr(node.left)
#                 elem_js = self.js_expr(node.right.elts[0])
#                 return f"new Array({n_js}).fill({elem_js})"
#
#         L = self.js_expr(node.left)
#         R = self.js_expr(node.right)
#
#         if isinstance(node.op, Add):      return f"({L} + {R})"
#         if isinstance(node.op, Sub):      return f"({L} - {R})"
#         if isinstance(node.op, Mult):     return f"({L} * {R})"
#         if isinstance(node.op, Div):      return f"({L} / {R})"
#         if isinstance(node.op, Mod):      return f"({L} % {R})"
#         if isinstance(node.op, FloorDiv): return f"Math.floor({L} / {R})"
#
#         return f"({L} /*op*/ {R})"
#
#     def _handle_bool_op(self, node: ast.BoolOp) -> str:
#         from ast import And, Or
#         parts = [self.js_expr(v) for v in node.values]
#         if isinstance(node.op, And): return "(" + " && ".join(parts) + ")"
#         if isinstance(node.op, Or):  return "(" + " || ".join(parts) + ")"
#         return "(" + " /*bool*/ ".join(parts) + ")"
#
#     def _handle_compare(self, node: ast.Compare) -> str:
#         from ast import Eq, NotEq, Lt, LtE, Gt, GtE, Is, IsNot, In, NotIn
#
#         left_js = self.js_expr(node.left)
#         parts = []
#         cur_left = left_js
#
#         for op, comp in zip(node.ops, node.comparators):
#             right_js = self.js_expr(comp)
#
#             if isinstance(op, Eq):
#                 parts.append(f"({cur_left} === {right_js})")
#             elif isinstance(op, NotEq):
#                 parts.append(f"({cur_left} !== {right_js})")
#             elif isinstance(op, Lt):
#                 parts.append(f"({cur_left} < {right_js})")
#             elif isinstance(op, LtE):
#                 parts.append(f"({cur_left} <= {right_js})")
#             elif isinstance(op, Gt):
#                 parts.append(f"({cur_left} > {right_js})")
#             elif isinstance(op, GtE):
#                 parts.append(f"({cur_left} >= {right_js})")
#             elif isinstance(op, Is):
#                 parts.append(f"({cur_left} === {right_js})")
#             elif isinstance(op, IsNot):
#                 parts.append(f"({cur_left} !== {right_js})")
#             elif isinstance(op, In):
#                 parts.append(f"(({right_js} instanceof Set) ? {right_js}.has({cur_left}) : ({cur_left} in {right_js}))")
#             elif isinstance(op, NotIn):
#                 parts.append(
#                     f"!((({right_js} instanceof Set) ? {right_js}.has({cur_left}) : ({cur_left} in {right_js})))")
#             else:
#                 parts.append(f"({cur_left} /*cmp*/ {right_js})")
#
#             cur_left = right_js
#
#         return "(" + " && ".join(parts) + ")"
#
#     def _handle_subscript(self, node: ast.Subscript) -> str:
#         base, idxs = self._subscript_chain(node)
#         if not base:
#             return "/*subscript*/"
#
#         # Handle slicing
#         if isinstance(node.slice, ast.Slice):
#             return self._handle_slice(base, node.slice)
#
#         # Single index
#         if len(idxs) == 1:
#             i = self._norm_idx(base, idxs[0])
#             return f"{base}[{i}]"
#
#         # Double index (matrix)
#         if len(idxs) == 2:
#             i = self._norm_idx(base, idxs[0])
#             j = self.js_expr(idxs[1])
#             return f"{base}[{i}][{j}]"
#
#         return "/*multi_subscript*/"
#
#     def _handle_slice(self, base: str, slc: ast.Slice) -> str:
#         lower = self.js_expr(slc.lower) if slc.lower else "0"
#         upper = self.js_expr(slc.upper) if slc.upper else f"{base}.length"
#         step = self.js_expr(slc.step) if slc.step else ""
#
#         if not step or step == "1" or step == "null":
#             return f"{base}.slice({lower}, {upper})"
#         elif step == "-1":
#             self.helpers_needed.add("REVERSED")
#             return f"__reversed({base}.slice({lower}, {upper}))"
#         else:
#             return f"/*slice_step*/ {base}.slice({lower}, {upper})"
#
#     def _norm_idx(self, arr_js: str, idx_node: ast.AST) -> str:
#         """Normalize negative indices."""
#         if isinstance(idx_node, ast.UnaryOp) and isinstance(idx_node.op, ast.USub):
#             if isinstance(idx_node.operand, ast.Constant):
#                 v = idx_node.operand.value
#                 if isinstance(v, int):
#                     return f"({arr_js}.length - {v})"
#
#         if isinstance(idx_node, ast.Constant) and isinstance(idx_node.value, int):
#             if idx_node.value < 0:
#                 return f"({arr_js}.length + {idx_node.value})"
#
#         self.helpers_needed.add("IDX")
#         return f"__idx({arr_js}, {self.js_expr(idx_node)})"
#
#     def _subscript_chain(self, node: ast.Subscript) -> Tuple[Optional[str], List[ast.AST]]:
#         """Extract base variable and index chain from subscript."""
#         idxs: List[ast.AST] = []
#         cur = node
#
#         while isinstance(cur, ast.Subscript):
#             idxs.insert(0, cur.slice.value if hasattr(cur.slice, "value") else cur.slice)
#             cur = cur.value
#             if len(idxs) > 10:  # Safety
#                 break
#
#         if isinstance(cur, ast.Name):
#             return cur.id, idxs
#
#         return None, idxs
#
#     def _handle_call(self, node: ast.Call) -> str:
#         """Handle function calls with builtin support."""
#         # float('inf')
#         if (isinstance(node.func, ast.Name) and node.func.id == "float" and
#                 node.args and isinstance(node.args[0], ast.Constant)):
#             if str(node.args[0].value).lower() in ("inf", "infinity"):
#                 return "Infinity"
#
#         # len()
#         if isinstance(node.func, ast.Name) and node.func.id == "len" and node.args:
#             return f"{self.js_expr(node.args[0])}.length"
#
#         # heapq.heappush/heappop
#         if isinstance(node.func, ast.Attribute):
#             if isinstance(node.func.value, ast.Name) and node.func.value.id == "heapq":
#                 self.helpers_needed.add("HEAP")
#                 if node.func.attr == "heappush":
#                     return f"__heappush({self.js_expr(node.args[0])}, {self.js_expr(node.args[1])})"
#                 if node.func.attr == "heappop":
#                     return f"__heappop({self.js_expr(node.args[0])})"
#
#         # TreeNode constructor
#         if isinstance(node.func, ast.Name) and node.func.id == "TreeNode":
#             args_js = ", ".join(self.js_expr(a) for a in node.args)
#             return f"new TreeNode({args_js})"
#
#         # Builtin functions
#         if isinstance(node.func, ast.Name):
#             fname = node.func.id
#             builtin_result = self._handle_builtin(fname, node)
#             if builtin_result:
#                 return builtin_result
#
#             # Generic function call
#             args_js = ", ".join(self.js_expr(a) for a in node.args)
#             return f"{fname}({args_js})"
#
#         # Method calls
#         if isinstance(node.func, ast.Attribute):
#             obj_js = self.js_expr(node.func.value)
#             method = node.func.attr
#             args_js = ", ".join(self.js_expr(a) for a in node.args)
#
#             # Map deque methods
#             if method == "appendleft": return f"{obj_js}.unshift({args_js})"
#             if method == "popleft": return f"{obj_js}.shift()"
#
#             return f"{obj_js}.{method}({args_js})"
#
#         return "/*call*/"
#
#     def _handle_builtin(self, fname: str, node: ast.Call) -> Optional[str]:
#         """Handle Python builtin functions."""
#         if not node.args:
#             return None
#
#         # Collections
#         if fname == "list":
#             return f"[...{self.js_expr(node.args[0])}]"
#         if fname == "tuple":
#             return f"[...{self.js_expr(node.args[0])}]"
#         if fname == "set":
#             return f"new Set({self.js_expr(node.args[0])})"
#         if fname == "dict":
#             if node.keywords:
#                 pairs = [f"[{repr(kw.arg)}, {self.js_expr(kw.value)}]"
#                          for kw in node.keywords]
#                 return f"Object.fromEntries([{', '.join(pairs)}])"
#             return f"Object.fromEntries({self.js_expr(node.args[0])})"
#
#         # Math functions - handle multiple args vs single array
#         if fname == "max":
#             if len(node.args) > 1:
#                 # max(a, b, c) → Math.max(a, b, c)
#                 args = ", ".join(self.js_expr(a) for a in node.args)
#                 return f"Math.max({args})"
#             else:
#                 # max(arr) → Math.max(...arr)
#                 return f"Math.max(...{self.js_expr(node.args[0])})"
#
#         if fname == "min":
#             if len(node.args) > 1:
#                 # min(a, b, c) → Math.min(a, b, c)
#                 args = ", ".join(self.js_expr(a) for a in node.args)
#                 return f"Math.min({args})"
#             else:
#                 # min(arr) → Math.min(...arr)
#                 return f"Math.min(...{self.js_expr(node.args[0])})"
#
#         if fname == "sum":
#             self.helpers_needed.add("SUM")
#             return f"__sum({self.js_expr(node.args[0])})"
#
#         if fname == "abs":
#             return f"Math.abs({self.js_expr(node.args[0])})"
#
#         if fname == "sorted":
#             self.helpers_needed.add("SORTED")
#             return f"__sorted({self.js_expr(node.args[0])})"
#
#         if fname == "reversed":
#             self.helpers_needed.add("REVERSED")
#             return f"__reversed({self.js_expr(node.args[0])})"
#
#         # Iteration
#         if fname == "enumerate":
#             return f"Array.from({self.js_expr(node.args[0])}.entries())"
#         if fname == "zip":
#             self.helpers_needed.add("ZIP")
#             args = ", ".join(self.js_expr(a) for a in node.args)
#             return f"__zip({args})"
#
#         # Collections
#         if fname == "defaultdict":
#             self.helpers_needed.add("DEFAULTDICT")
#             return "__defaultdict(() => [])"
#         if fname == "Counter":
#             self.helpers_needed.add("COUNTER")
#             return f"__counter({self.js_expr(node.args[0])})"
#
#         # heapq direct calls
#         if fname == "heappush" and len(node.args) == 2:
#             self.helpers_needed.add("HEAP")
#             return f"__heappush({self.js_expr(node.args[0])}, {self.js_expr(node.args[1])})"
#         if fname == "heappop":
#             self.helpers_needed.add("HEAP")
#             return f"__heappop({self.js_expr(node.args[0])})"
#
#         return None
#
#     def _handle_list_comp(self, node: ast.ListComp) -> str:
#         """Handle list comprehensions."""
#         if len(node.generators) == 1:
#             g = node.generators[0]
#             it = self.js_expr(g.iter)
#             var = self.js_expr(g.target)
#             elt = self.js_expr(node.elt)
#
#             if g.ifs:
#                 cond = " && ".join(self.js_expr(c) for c in g.ifs)
#                 return f"{it}.filter(({var}) => ({cond})).map(({var}) => {elt})"
#
#             return f"{it}.map(({var}) => {elt})"
#
#         return "/*listcomp*/"
#
#     def _handle_generator_exp(self, node: ast.GeneratorExp) -> str:
#         """Handle generator expressions."""
#         if len(node.generators) == 1:
#             g = node.generators[0]
#             it = self.js_expr(g.iter)
#             var = self.js_expr(g.target)
#             elt = self.js_expr(node.elt)
#
#             if g.ifs:
#                 cond = " && ".join(self.js_expr(c) for c in g.ifs)
#                 return f"{it}.filter(({var}) => ({cond})).map(({var}) => {elt})"
#
#             return f"{it}.map(({var}) => {elt})"
#
#         return "/*genexp*/"
#
#     # ==================== STATEMENT VISITORS ====================
#
#     def visit_Module(self, node: ast.Module):
#         """Visit module - entry point."""
#         for stmt in node.body:
#             self.visit(stmt)
#
#         # Prepend helpers if needed
#         helpers = self._get_helper_code()
#         if helpers:
#             return "\n".join(helpers + [""] + self.lines)
#
#         return "\n".join(self.lines)
#
#     def visit_ClassDef(self, node: ast.ClassDef):
#         """Handle class definitions (mainly TreeNode)."""
#         if node.name == "TreeNode":
#             self.emit("class TreeNode {")
#             self.ind += 1
#             self.emit("constructor(val = 0, left = null, right = null) {")
#             self.ind += 1
#             self.emit("this.val = val;")
#             self.emit("this.left = left;")
#             self.emit("this.right = right;")
#             self.ind -= 1
#             self.emit("}")
#             self.ind -= 1
#             self.emit("}")
#         else:
#             self.emit(f"/* unsupported class {node.name} */")
#
#     def visit_FunctionDef(self, node: ast.FunctionDef):
#         """Handle function definitions."""
#         args = [a.arg for a in node.args.args]
#         self.emit(f"function {node.name}({', '.join(args)}) {{")
#         self.ind += 1
#
#         self.func_stack.append(node.name)
#         self.scope_stack.append(set(args))
#
#         # Log function entry
#         self.emit(f"logger.println('→ {node.name}({', '.join(args)})');")
#         self.emit("Tracer.delay();")
#
#         for stmt in node.body:
#             self.visit(stmt)
#
#         self.scope_stack.pop()
#         self.func_stack.pop()
#
#         self.ind -= 1
#         self.emit("}")
#
#     def visit_Assign(self, node: ast.Assign):
#         """Handle assignments with tracer instrumentation."""
#         if len(node.targets) != 1:
#             return
#
#         target = node.targets[0]
#
#         # Destructuring
#         if isinstance(target, (ast.Tuple, ast.List)):
#             self._handle_destructuring(target, node.value)
#             return
#
#         # Simple assignment
#         if isinstance(target, ast.Name):
#             name = target.id
#             rhs_js = self.js_expr(node.value)
#             self._emit_decl_or_assign(name, rhs_js)
#             return
#
#         # Subscript assignment with tracing
#         if isinstance(target, ast.Subscript):
#             self._handle_subscript_assign(target, node.value)
#             return
#
#     def _handle_destructuring(self, target, value):
#         """Handle tuple/list unpacking - including swap patterns."""
#         names = [el.id for el in target.elts if isinstance(el, ast.Name)]
#         subscripts = [el for el in target.elts if isinstance(el, ast.Subscript)]
#
#         # Detect swap pattern: arr[i], arr[j] = arr[j], arr[i]
#         if (len(subscripts) >= 2 and
#                 isinstance(value, (ast.Tuple, ast.List)) and
#                 len(value.elts) == len(target.elts)):
#
#             is_swap = True
#             for left_sub, right_val in zip(subscripts, value.elts):
#                 if not isinstance(right_val, ast.Subscript):
#                     is_swap = False
#                     break
#
#             if is_swap:
#                 # Generate proper swap code
#                 swap_pairs = []
#                 for i, (tgt, val) in enumerate(zip(target.elts, value.elts)):
#                     swap_pairs.append((self.js_expr(tgt), self.js_expr(val)))
#
#                 # Use destructuring syntax: [a, b] = [b, a]
#                 left_side = "[" + ", ".join(pair[0] for pair in swap_pairs) + "]"
#                 right_side = "[" + ", ".join(pair[1] for pair in swap_pairs) + "]"
#                 self.emit(f"{left_side} = {right_side};")
#
#                 # Add tracer for swaps if applicable
#                 if len(swap_pairs) == 2:
#                     for tgt_expr, _ in swap_pairs:
#                         # Check if this is array access
#                         if '[' in tgt_expr:
#                             base_match = tgt_expr.split('[')[0]
#                             tracer_base = self._mapped_tracer_base(base_match)
#                             if tracer_base in self.traceable_1d:
#                                 idx_match = tgt_expr.split('[')[1].rstrip(']')
#                                 self.emit(f"logger.println('Swap elements');")
#                                 self.emit(f"{tracer_base}Tracer.patch({idx_match}, {tgt_expr});")
#                                 self.emit("Tracer.delay();")
#                                 self.emit(f"{tracer_base}Tracer.depatch({idx_match});")
#                                 break
#                 return
#
#         # Regular destructuring
#         if isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) == len(names):
#             for name, val_node in zip(names, value.elts):
#                 rhs_js = self.js_expr(val_node)
#                 self._emit_decl_or_assign(name, rhs_js)
#         else:
#             tmp = self._gensym()
#             self.emit(f"const {tmp} = {self.js_expr(value)};")
#             for idx, name in enumerate(names):
#                 self._emit_decl_or_assign(name, f"{tmp}[{idx}]")
#
#     def _handle_subscript_assign(self, target: ast.Subscript, value):
#         """Handle subscript assignment with visualization - fixed for dicts."""
#         base, idxs = self._subscript_chain(target)
#         rhs = self.js_expr(value)
#
#         if not base:
#             return
#
#         # 1D assignment (array or dict)
#         if len(idxs) == 1:
#             # Get the full index expression (crucial for dict keys like nums[i])
#             idx_js = self.js_expr(idxs[0])
#
#             # Check for defaultdict pattern
#             if "defaultdict" in base.lower():
#                 self.emit(f"{base}[{idx_js}].push({rhs});")
#             else:
#                 # Regular assignment - works for both arrays and dicts
#                 self.emit(f"{base}[{idx_js}] = {rhs};")
#
#             # Add tracer visualization (only for traceable arrays, not dicts)
#             tracer_base = self._mapped_tracer_base(base)
#             if tracer_base in self.traceable_1d:
#                 self.emit(f"logger.println('Update {base}[' + {idx_js} + '] = ' + {rhs});")
#                 self.emit(f"{tracer_base}Tracer.patch({idx_js}, {rhs});")
#                 self.emit("Tracer.delay();")
#                 self.emit(f"{tracer_base}Tracer.depatch({idx_js});")
#             return
#
#         # 2D assignment
#         if len(idxs) == 2:
#             i = self._norm_idx(base, idxs[0])
#             j = self.js_expr(idxs[1])
#             self.emit(f"{base}[{i}][{j}] = {rhs};")
#
#             # Add tracer visualization
#             tracer_base = self._mapped_tracer_base(base)
#             if tracer_base in self.traceable_2d:
#                 self.emit(f"logger.println('Update {base}[' + {i} + '][' + {j} + '] = ' + {rhs});")
#                 self.emit(f"{tracer_base}Tracer.patch({i}, {j}, {rhs});")
#                 self.emit("Tracer.delay();")
#                 self.emit(f"{tracer_base}Tracer.depatch({i}, {j});")
#             return
#
#     def visit_AugAssign(self, node: ast.AugAssign):
#         """Handle augmented assignments."""
#         from ast import Add, Sub, Mult, Div, Mod
#
#         target_js = self.js_expr(node.target)
#         value_js = self.js_expr(node.value)
#
#         op_map = {Add: "+", Sub: "-", Mult: "*", Div: "/", Mod: "%"}
#         op = next((op_map[type(node.op)] for t in op_map if isinstance(node.op, t)), None)
#
#         if op:
#             self.emit(f"{target_js} = ({target_js} {op} {value_js});")
#         else:
#             self.emit("/* unsupported augassign */")
#
#     def visit_If(self, node: ast.If):
#         """Handle if statements with smart select/deselect."""
#         cond = self.js_expr(node.test)
#
#         # Extract indices from comparison for visualization
#         select_info = self._extract_comparison_indices(node.test)
#
#         # Add select before condition
#         if select_info:
#             for base, indices in select_info:
#                 tracer_base = self._mapped_tracer_base(base)
#                 if tracer_base in self.traceable_1d and len(indices) == 2:
#                     idx1, idx2 = indices
#                     self.emit(f"{tracer_base}Tracer.select({idx1}, {idx2});")
#                 elif tracer_base in self.traceable_2d and len(indices) == 2:
#                     i, j = indices
#                     self.emit(f"{tracer_base}Tracer.select({i}, {j});")
#             self.emit("Tracer.delay();")
#
#         self.emit(f"if ({cond}) {{")
#         self.ind += 1
#
#         for stmt in node.body:
#             self.visit(stmt)
#
#         self.ind -= 1
#
#         if node.orelse:
#             self.emit("} else {")
#             self.ind += 1
#             for stmt in node.orelse:
#                 self.visit(stmt)
#             self.ind -= 1
#
#         self.emit("}")
#
#         # Deselect after if block
#         if select_info:
#             for base, indices in select_info:
#                 tracer_base = self._mapped_tracer_base(base)
#                 if tracer_base in self.traceable_1d and len(indices) == 2:
#                     idx1, idx2 = indices
#                     self.emit(f"{tracer_base}Tracer.deselect({idx1}, {idx2});")
#                 elif tracer_base in self.traceable_2d and len(indices) == 2:
#                     i, j = indices
#                     self.emit(f"{tracer_base}Tracer.deselect({i}, {j});")
#
#     def _extract_comparison_indices(self, test_node) -> List[Tuple[str, List[str]]]:
#         """
#         Extract array indices from comparison for select/deselect.
#         Returns: [(base_name, [idx1, idx2, ...]), ...]
#         """
#         result = []
#
#         if isinstance(test_node, ast.Compare):
#             # Collect all subscripts in the comparison
#             subscripts = []
#             for node in ast.walk(test_node):
#                 if isinstance(node, ast.Subscript):
#                     base, idxs = self._subscript_chain(node)
#                     if base and idxs:
#                         subscripts.append((base, idxs))
#
#             # Group by base variable
#             from collections import defaultdict
#             by_base = defaultdict(list)
#             for base, idxs in subscripts:
#                 # For 1D: arr[i], arr[j] → select(i, j)
#                 if len(idxs) == 1:
#                     by_base[base].append(self.js_expr(idxs[0]))
#                 # For 2D: matrix[i][j] → select(i, j)
#                 elif len(idxs) == 2:
#                     by_base[base].append(self.js_expr(idxs[0]))
#                     by_base[base].append(self.js_expr(idxs[1]))
#
#             # Convert to result format
#             for base, indices in by_base.items():
#                 if len(indices) >= 2:
#                     # Take first 2 unique indices
#                     unique_indices = []
#                     seen = set()
#                     for idx in indices:
#                         if idx not in seen:
#                             unique_indices.append(idx)
#                             seen.add(idx)
#                         if len(unique_indices) >= 2:
#                             break
#
#                     if len(unique_indices) >= 2:
#                         result.append((base, unique_indices[:2]))
#
#         return result
#
#     def visit_For(self, node: ast.For):
#         """Handle for loops with tracing."""
#         it = node.iter
#         target_is_name = isinstance(node.target, ast.Name)
#         loop_var = self.js_expr(node.target)
#
#         # range() loops
#         if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range":
#             self._handle_range_loop(node, loop_var, target_is_name)
#             return
#
#         # for-of loops
#         iterable_js = self.js_expr(it)
#
#         if target_is_name and not self._is_declared(loop_var):
#             self.emit(f"for (let {loop_var} of {iterable_js}) {{")
#             self._declare(loop_var)
#         else:
#             self.emit(f"for ({loop_var} of {iterable_js}) {{")
#
#         self.ind += 1
#         self.loop_stack.append(loop_var)
#
#         for stmt in node.body:
#             self.visit(stmt)
#
#         self.loop_stack.pop()
#         self.ind -= 1
#         self.emit("}")
#
#     def _handle_range_loop(self, node: ast.For, loop_var: str, target_is_name: bool):
#         """Handle range-based for loops with smart select/deselect."""
#         args = node.iter.args
#
#         if len(args) == 1:
#             n = self.js_expr(args[0])
#             init = f"let {loop_var} = 0" if target_is_name and not self._is_declared(loop_var) else f"{loop_var} = 0"
#             test = f"{loop_var} < {n}"
#             step = f"{loop_var}++"
#         elif len(args) == 2:
#             a = self.js_expr(args[0])
#             b = self.js_expr(args[1])
#             init = f"let {loop_var} = {a}" if target_is_name and not self._is_declared(
#                 loop_var) else f"{loop_var} = {a}"
#             test = f"{loop_var} < {b}"
#             step = f"{loop_var}++"
#         elif len(args) == 3:
#             a = self.js_expr(args[0])
#             b = self.js_expr(args[1])
#             c = self.js_expr(args[2])
#             comp = ">" if (isinstance(args[2], ast.Constant) and args[2].value < 0) else "<"
#             init = f"let {loop_var} = {a}" if target_is_name and not self._is_declared(
#                 loop_var) else f"{loop_var} = {a}"
#             test = f"{loop_var} {comp} {b}"
#             step = f"{loop_var} += {c}"
#         else:
#             init = "let i = 0"
#             test = "i < 0"
#             step = "i++"
#
#         if target_is_name and "let" in init:
#             self._declare(loop_var)
#
#         self.emit(f"for ({init}; {test}; {step}) {{")
#         self.ind += 1
#         self.loop_stack.append(loop_var)
#
#         # Auto-select loop index if we're iterating over a traceable array
#         primary_array = self._find_primary_array_in_loop(node.body)
#
#         if primary_array:
#             tracer_base = self._mapped_tracer_base(primary_array)
#             if tracer_base in self.traceable_1d:
#                 self.emit(f"{tracer_base}Tracer.select({loop_var});")
#                 self.emit("Tracer.delay();")
#
#         for stmt in node.body:
#             self.visit(stmt)
#
#         # Deselect after loop body
#         if primary_array:
#             tracer_base = self._mapped_tracer_base(primary_array)
#             if tracer_base in self.traceable_1d:
#                 self.emit(f"{tracer_base}Tracer.deselect({loop_var});")
#
#         self.loop_stack.pop()
#         self.ind -= 1
#         self.emit("}")
#
#     def _find_primary_array_in_loop(self, body: List[ast.stmt]) -> Optional[str]:
#         """
#         Find the primary array being accessed in loop body.
#         Returns the array name if found.
#         """
#         # Look for subscript accesses in the loop body
#         for stmt in body:
#             for node in ast.walk(stmt):
#                 if isinstance(node, ast.Subscript):
#                     base, idxs = self._subscript_chain(node)
#                     if base and base in self.traceable_1d:
#                         return base
#                     if base and base in self.traceable_2d:
#                         return base
#         return None
#
#     def visit_While(self, node: ast.While):
#         """Handle while loops with smart visualization."""
#         cond = self.js_expr(node.test)
#
#         # Extract variables for visualization
#         viz_info = self._extract_while_viz_info(node.test)
#
#         self.emit(f"while ({cond}) {{")
#         self.ind += 1
#
#         # Add select at start of loop body
#         if viz_info:
#             for base, indices in viz_info:
#                 tracer_base = self._mapped_tracer_base(base)
#                 if tracer_base in self.traceable_1d and len(indices) <= 2:
#                     idx_str = ", ".join(indices)
#                     self.emit(f"{tracer_base}Tracer.select({idx_str});")
#                     self.emit("Tracer.delay();")
#
#         for stmt in node.body:
#             self.visit(stmt)
#
#         # Deselect at end of loop body
#         if viz_info:
#             for base, indices in viz_info:
#                 tracer_base = self._mapped_tracer_base(base)
#                 if tracer_base in self.traceable_1d and len(indices) <= 2:
#                     idx_str = ", ".join(indices)
#                     self.emit(f"{tracer_base}Tracer.deselect({idx_str});")
#
#         self.ind -= 1
#         self.emit("}")
#
#     def _extract_while_viz_info(self, test_node) -> List[Tuple[str, List[str]]]:
#         """
#         Extract indices from while condition for visualization.
#         Similar to comparison extraction but for while loops.
#         """
#         result = []
#
#         # Collect all subscripts and names in the condition
#         subscripts = []
#         var_names = set()
#
#         for node in ast.walk(test_node):
#             if isinstance(node, ast.Subscript):
#                 base, idxs = self._subscript_chain(node)
#                 if base and idxs:
#                     subscripts.append((base, idxs))
#             elif isinstance(node, ast.Name):
#                 var_names.add(node.id)
#
#         # Group subscripts by base
#         from collections import defaultdict
#         by_base = defaultdict(list)
#         for base, idxs in subscripts:
#             if len(idxs) == 1:
#                 by_base[base].append(self.js_expr(idxs[0]))
#
#         # Convert to result format
#         for base, indices in by_base.items():
#             if len(indices) >= 1:
#                 unique_indices = []
#                 seen = set()
#                 for idx in indices:
#                     if idx not in seen:
#                         unique_indices.append(idx)
#                         seen.add(idx)
#                     if len(unique_indices) >= 2:
#                         break
#
#                 if unique_indices:
#                     result.append((base, unique_indices))
#
#         # If no subscripts but we have simple variable comparisons
#         # like "left <= right", add those for visualization
#         if not result and len(var_names) >= 2:
#             # Find traceable arrays mentioned
#             for vname in var_names:
#                 if vname in self.traceable_1d:
#                     # This is likely an index variable
#                     other_vars = [v for v in var_names if v != vname and v not in self.traceable_1d]
#                     if other_vars:
#                         result.append((vname, other_vars[:2]))
#                     break
#
#         return result
#
#     def visit_Expr(self, node: ast.Expr):
#         """Handle expression statements."""
#         if isinstance(node.value, ast.Call):
#             call = node.value
#
#             # Handle append with tracing
#             if isinstance(call.func, ast.Attribute) and call.func.attr == "append":
#                 base = self.js_expr(call.func.value)
#                 arg_js = self.js_expr(call.args[0]) if call.args else "undefined"
#                 self.emit(f"{base}.push({arg_js});")
#
#                 tracer_base = self._mapped_tracer_base(base)
#                 if tracer_base in self.traceable_1d:
#                     self.emit(f"logger.println('Append {arg_js} to {base}');")
#                     self.emit(f"{tracer_base}Tracer.patch({base}.length - 1, {arg_js});")
#                     self.emit("Tracer.delay();")
#                     self.emit(f"{tracer_base}Tracer.depatch({base}.length - 1);")
#                 return
#
#             # Handle print()
#             if isinstance(call.func, ast.Name) and call.func.id == "print":
#                 msg = self.js_expr(call.args[0]) if call.args else "''"
#                 self.emit(f"logger.println({msg});")
#                 return
#
#         self.emit(self.js_expr(node.value) + ";")
#
#     def visit_Break(self, node: ast.Break):
#         self.emit("break;")
#
#     def visit_Continue(self, node: ast.Continue):
#         self.emit("continue;")
#
#     def visit_Pass(self, node: ast.Pass):
#         self.emit("/* pass */")
#
#     def visit_Return(self, node: ast.Return):
#         if node.value is None:
#             self.emit("logger.println('← return');")
#             self.emit("return;")
#         else:
#             v_js = self.js_expr(node.value)
#             self.emit(f"logger.println('← return ' + JSON.stringify({v_js}));")
#             self.emit(f"return {v_js};")
#
#     def generic_visit(self, node: ast.AST):
#         pass
#
#
# # ==================== PUBLIC API ====================
#
# def translate_to_js(code: str, summary: Dict) -> str:
#     """
#     Translate Python code to instrumented JavaScript.
#
#     Args:
#         code: Python source code
#         summary: Analysis summary from EnhancedAnalyzer
#
#     Returns:
#         Instrumented JavaScript code
#     """
#     tree = ast.parse(code)
#     bindings = _collect_param_bindings(tree)
#
#     # Get traceable variables from summary
#     traceable_1d = set(summary.get("vars_1d", []))
#     traceable_2d = set(summary.get("vars_2d", []))
#
#     translator = InstrumentedTranslator(
#         summary=summary,
#         traceable_1d=traceable_1d,
#         traceable_2d=traceable_2d,
#         param_bindings=bindings,
#     )
#
#     js = translator.visit(tree)
#     return js or "\n".join(translator.lines)

# -*- coding: utf-8 -*-
"""
Instrumented Translator Module
Translates Python to JavaScript with automatic Algorithm Visualizer instrumentation.
Integrates with EnhancedAnalyzer output to inject tracers at optimal points.
"""

import ast
from typing import Dict, List, Set, Optional, Tuple


# ==================== PARAMETER PROPAGATION ====================

def _collect_param_bindings(module: ast.Module) -> Dict[str, Dict[str, Optional[str]]]:
    """
    Map function parameters to their actual argument names from top-level calls.
    Supports one level of propagation (top-level → nested).
    """
    func_params: Dict[str, List[str]] = {}
    func_bodies: Dict[str, List[ast.stmt]] = {}

    for stmt in module.body:
        if isinstance(stmt, ast.FunctionDef):
            func_params[stmt.name] = [a.arg for a in stmt.args.args]
            func_bodies[stmt.name] = stmt.body

    bindings: Dict[str, Dict[str, Optional[str]]] = {}

    # Collect top-level calls
    for stmt in module.body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            if isinstance(stmt.value.func, ast.Name):
                fname = stmt.value.func.id
                if fname in func_params and fname not in bindings:
                    m: Dict[str, Optional[str]] = {}
                    params = func_params[fname]
                    for i, p in enumerate(params):
                        if i < len(stmt.value.args):
                            a = stmt.value.args[i]
                            m[p] = a.id if isinstance(a, ast.Name) else None
                        else:
                            m[p] = None
                    bindings[fname] = m

    # Propagate one level deep
    for fname, param_map in list(bindings.items()):
        body = func_bodies.get(fname, [])
        for stmt in body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                call = stmt.value
                if isinstance(call.func, ast.Name):
                    gname = call.func.id
                    if gname in func_params and gname not in bindings:
                        gparams = func_params[gname]
                        gm: Dict[str, Optional[str]] = {}
                        for i, gp in enumerate(gparams):
                            if i < len(call.args):
                                arg = call.args[i]
                                if isinstance(arg, ast.Name):
                                    gm[gp] = param_map.get(arg.id) or None
                                else:
                                    gm[gp] = None
                            else:
                                gm[gp] = None
                        bindings[gname] = gm

    return bindings


# ==================== MAIN TRANSLATOR CLASS ====================

class InstrumentedTranslator(ast.NodeVisitor):
    """
    Translates Python AST to instrumented JavaScript for Algorithm Visualizer.
    Automatically injects select/deselect, patch/depatch, and logger calls.
    """

    def __init__(
            self,
            summary: Dict,
            traceable_1d: Optional[Set[str]] = None,
            traceable_2d: Optional[Set[str]] = None,
            param_bindings: Optional[Dict[str, Dict[str, Optional[str]]]] = None,
    ):
        self.summary = summary
        self.lines: List[str] = []
        self.ind = 0
        self._tmp_counter = 0

        # Scope tracking
        self.scope_stack: List[Set[str]] = [set()]
        self.func_stack: List[str] = []

        # Traceable variables
        self.traceable_1d = set(traceable_1d or [])
        self.traceable_2d = set(traceable_2d or [])

        # Parameter bindings for cross-function tracing
        self.param_bindings = param_bindings or {}

        # Helper polyfills needed
        self.helpers_needed: Set[str] = set()

        # Loop context
        self.loop_stack: List[str] = []

    # ==================== UTILITIES ====================

    def emit(self, s: str):
        """Emit a line of JavaScript code."""
        self.lines.append("  " * self.ind + s)

    def _gensym(self, prefix="__tmp"):
        """Generate a unique temporary variable name."""
        self._tmp_counter += 1
        return f"{prefix}{self._tmp_counter}"

    def _is_declared(self, name: str) -> bool:
        """Check if variable is declared in current scope chain."""
        return any(name in s for s in self.scope_stack)

    def _declare(self, name: str):
        """Mark variable as declared in current scope."""
        self.scope_stack[-1].add(name)

    def _emit_decl_or_assign(self, name: str, rhs_js: str):
        """Emit declaration or assignment depending on scope."""
        if self._is_declared(name):
            self.emit(f"{name} = {rhs_js};")
        else:
            self.emit(f"let {name} = {rhs_js};")
            self._declare(name)

    def _mapped_tracer_base(self, base_name: str) -> str:
        """Map parameter name to actual argument name for tracing."""
        if self.func_stack:
            fname = self.func_stack[-1]
            m = self.param_bindings.get(fname, {})
            arg = m.get(base_name)
            if arg:
                return arg
        return base_name

    # ==================== HELPER CODE GENERATION ====================

    def _get_helper_code(self) -> List[str]:
        """Generate polyfill code for helpers."""
        code = []

        if "IDX" in self.helpers_needed:
            code.append("function __idx(arr, i) { return i < 0 ? arr.length + i : i; }")

        if "ZIP" in self.helpers_needed:
            code.extend([
                "function __zip(...arrs) {",
                "  const m = Math.min(...arrs.map(a => a.length));",
                "  return Array.from({length: m}, (_, i) => arrs.map(a => a[i]));",
                "}",
            ])

        if "DEFAULTDICT" in self.helpers_needed:
            code.extend([
                "function __defaultdict(factory) {",
                "  return new Proxy({}, {",
                "    get(t, k) { if (!(k in t)) t[k] = factory(); return t[k]; },",
                "    set(t, k, v) { t[k] = v; return true; }",
                "  });",
                "}",
            ])

        if "COUNTER" in self.helpers_needed:
            code.extend([
                "function __counter(seq) {",
                "  const c = {};",
                "  for (const x of seq) { c[x] = (c[x] || 0) + 1; }",
                "  return c;",
                "}",
            ])

        if "HEAP" in self.helpers_needed:
            code.extend([
                "function __heappush(h, x) {",
                "  h.push(x);",
                "  let i = h.length - 1;",
                "  while (i > 0) {",
                "    const p = (i - 1) >> 1;",
                "    if (h[p] <= h[i]) break;",
                "    [h[p], h[i]] = [h[i], h[p]];",
                "    i = p;",
                "  }",
                "}",
                "function __heappop(h) {",
                "  if (h.length === 0) return undefined;",
                "  const top = h[0];",
                "  const x = h.pop();",
                "  if (h.length) {",
                "    h[0] = x;",
                "    let i = 0, n = h.length;",
                "    while (true) {",
                "      let l = 2 * i + 1, r = l + 1, s = i;",
                "      if (l < n && h[l] < h[s]) s = l;",
                "      if (r < n && h[r] < h[s]) s = r;",
                "      if (s === i) break;",
                "      [h[i], h[s]] = [h[s], h[i]];",
                "      i = s;",
                "    }",
                "  }",
                "  return top;",
                "}",
            ])

        if "SUM" in self.helpers_needed:
            code.append("const __sum = arr => arr.reduce((a, b) => a + b, 0);")
        if "SORTED" in self.helpers_needed:
            code.append("const __sorted = arr => [...arr].sort((a, b) => a - b);")
        if "REVERSED" in self.helpers_needed:
            code.append("const __reversed = arr => [...arr].reverse();")

        return code

    # ==================== EXPRESSION TRANSLATION ====================

    def js_expr(self, node: ast.AST) -> str:
        """Main expression translator dispatcher."""
        if not isinstance(node, ast.AST):
            if isinstance(node, (int, float)):
                return repr(node)
            return "/*expr*/"

        if isinstance(node, ast.Constant):
            return self._handle_constant(node)
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.UnaryOp):
            return self._handle_unary_op(node)
        if isinstance(node, ast.BinOp):
            return self._handle_binary_op(node)
        if isinstance(node, ast.BoolOp):
            return self._handle_bool_op(node)
        if isinstance(node, ast.Compare):
            return self._handle_compare(node)
        if isinstance(node, ast.Subscript):
            return self._handle_subscript(node)
        if isinstance(node, ast.Attribute):
            return f"{self.js_expr(node.value)}.{node.attr}"
        if isinstance(node, ast.Call):
            return self._handle_call(node)
        if isinstance(node, ast.List):
            return "[" + ", ".join(self.js_expr(e) for e in node.elts) + "]"
        if isinstance(node, ast.Tuple):
            return "[" + ", ".join(self.js_expr(e) for e in node.elts) + "]"
        if isinstance(node, ast.Set):
            return "new Set([" + ", ".join(self.js_expr(e) for e in node.elts) + "])"
        if isinstance(node, ast.Dict):
            pairs = [f"[{self.js_expr(k)}, {self.js_expr(v)}]"
                     for k, v in zip(node.keys, node.values)]
            return f"Object.fromEntries([{', '.join(pairs)}])"
        if isinstance(node, ast.ListComp):
            return self._handle_list_comp(node)
        if isinstance(node, ast.GeneratorExp):
            return self._handle_generator_exp(node)

        return "/*expr*/"

    def _handle_constant(self, node: ast.Constant) -> str:
        v = node.value
        if v is None: return "null"
        if isinstance(v, bool): return "true" if v else "false"
        if isinstance(v, float) and v == float("inf"): return "Infinity"
        return repr(v)

    def _handle_unary_op(self, node: ast.UnaryOp) -> str:
        if isinstance(node.op, ast.Not):
            return f"!({self.js_expr(node.operand)})"
        if isinstance(node.op, ast.USub):
            inner = node.operand
            if isinstance(inner, ast.Constant) and isinstance(inner.value, (int, float)):
                return f"-{repr(inner.value)}"
            return f"-({self.js_expr(inner)})"
        return f"/*unary*/({self.js_expr(node.operand)})"

    def _handle_binary_op(self, node: ast.BinOp) -> str:
        from ast import Add, Sub, Mult, Div, Mod, FloorDiv

        # Special case: [x] * n
        if isinstance(node.op, Mult):
            if isinstance(node.left, ast.List) and len(node.left.elts) == 1:
                n_js = self.js_expr(node.right)
                elem_js = self.js_expr(node.left.elts[0])
                return f"new Array({n_js}).fill({elem_js})"
            if isinstance(node.right, ast.List) and len(node.right.elts) == 1:
                n_js = self.js_expr(node.left)
                elem_js = self.js_expr(node.right.elts[0])
                return f"new Array({n_js}).fill({elem_js})"

        L = self.js_expr(node.left)
        R = self.js_expr(node.right)

        if isinstance(node.op, Add):      return f"({L} + {R})"
        if isinstance(node.op, Sub):      return f"({L} - {R})"
        if isinstance(node.op, Mult):     return f"({L} * {R})"
        if isinstance(node.op, Div):      return f"({L} / {R})"
        if isinstance(node.op, Mod):      return f"({L} % {R})"
        if isinstance(node.op, FloorDiv): return f"Math.floor({L} / {R})"

        return f"({L} /*op*/ {R})"

    def _handle_bool_op(self, node: ast.BoolOp) -> str:
        from ast import And, Or
        parts = [self.js_expr(v) for v in node.values]
        if isinstance(node.op, And): return "(" + " && ".join(parts) + ")"
        if isinstance(node.op, Or):  return "(" + " || ".join(parts) + ")"
        return "(" + " /*bool*/ ".join(parts) + ")"

    def _handle_compare(self, node: ast.Compare) -> str:
        from ast import Eq, NotEq, Lt, LtE, Gt, GtE, Is, IsNot, In, NotIn

        left_js = self.js_expr(node.left)
        parts = []
        cur_left = left_js

        for op, comp in zip(node.ops, node.comparators):
            right_js = self.js_expr(comp)

            if isinstance(op, Eq):
                parts.append(f"({cur_left} === {right_js})")
            elif isinstance(op, NotEq):
                parts.append(f"({cur_left} !== {right_js})")
            elif isinstance(op, Lt):
                parts.append(f"({cur_left} < {right_js})")
            elif isinstance(op, LtE):
                parts.append(f"({cur_left} <= {right_js})")
            elif isinstance(op, Gt):
                parts.append(f"({cur_left} > {right_js})")
            elif isinstance(op, GtE):
                parts.append(f"({cur_left} >= {right_js})")
            elif isinstance(op, Is):
                parts.append(f"({cur_left} === {right_js})")
            elif isinstance(op, IsNot):
                parts.append(f"({cur_left} !== {right_js})")
            elif isinstance(op, In):
                parts.append(f"(({right_js} instanceof Set) ? {right_js}.has({cur_left}) : ({cur_left} in {right_js}))")
            elif isinstance(op, NotIn):
                parts.append(
                    f"!((({right_js} instanceof Set) ? {right_js}.has({cur_left}) : ({cur_left} in {right_js})))")
            else:
                parts.append(f"({cur_left} /*cmp*/ {right_js})")

            cur_left = right_js

        return "(" + " && ".join(parts) + ")"

    def _handle_subscript(self, node: ast.Subscript) -> str:
        base, idxs = self._subscript_chain(node)
        if not base:
            return "/*subscript*/"

        # Handle slicing
        if isinstance(node.slice, ast.Slice):
            return self._handle_slice(base, node.slice)

        # Single index
        if len(idxs) == 1:
            i = self._norm_idx(base, idxs[0])
            return f"{base}[{i}]"

        # Double index (matrix)
        if len(idxs) == 2:
            i = self._norm_idx(base, idxs[0])
            j = self.js_expr(idxs[1])
            return f"{base}[{i}][{j}]"

        return "/*multi_subscript*/"

    def _handle_slice(self, base: str, slc: ast.Slice) -> str:
        lower = self.js_expr(slc.lower) if slc.lower else "0"
        upper = self.js_expr(slc.upper) if slc.upper else f"{base}.length"
        step = self.js_expr(slc.step) if slc.step else ""

        if not step or step == "1" or step == "null":
            return f"{base}.slice({lower}, {upper})"
        elif step == "-1":
            self.helpers_needed.add("REVERSED")
            return f"__reversed({base}.slice({lower}, {upper}))"
        else:
            return f"/*slice_step*/ {base}.slice({lower}, {upper})"

    def _norm_idx(self, arr_js: str, idx_node: ast.AST) -> str:
        """Normalize negative indices - skip for loop variables."""
        # If it's a simple Name (like 'i', 'j'), check if it's a loop variable
        if isinstance(idx_node, ast.Name):
            var_name = idx_node.id
            # Loop variables are always positive, no need for __idx
            if var_name in self.loop_stack or var_name in ('i', 'j', 'k', 'mid', 'left', 'right', 'c', 'r'):
                return var_name

        # Negative constant
        if isinstance(idx_node, ast.UnaryOp) and isinstance(idx_node.op, ast.USub):
            if isinstance(idx_node.operand, ast.Constant):
                v = idx_node.operand.value
                if isinstance(v, int):
                    return f"({arr_js}.length - {v})"

        if isinstance(idx_node, ast.Constant) and isinstance(idx_node.value, int):
            if idx_node.value < 0:
                return f"({arr_js}.length + {idx_node.value})"
            else:
                # Positive constant, use directly
                return str(idx_node.value)

        # Binary operations with loop vars (like j+1, i-1) - no __idx needed
        if isinstance(idx_node, ast.BinOp):
            # Check if base is a loop var
            if isinstance(idx_node.left, ast.Name) and idx_node.left.id in self.loop_stack:
                return self.js_expr(idx_node)

        # Fallback: use helper
        self.helpers_needed.add("IDX")
        return f"__idx({arr_js}, {self.js_expr(idx_node)})"

    def _subscript_chain(self, node: ast.Subscript) -> Tuple[Optional[str], List[ast.AST]]:
        """Extract base variable and index chain from subscript."""
        idxs: List[ast.AST] = []
        cur = node

        while isinstance(cur, ast.Subscript):
            # Always use the slice directly (Python 3.9+)
            idxs.insert(0, cur.slice)
            cur = cur.value
            if len(idxs) > 10:  # Safety
                break

        if isinstance(cur, ast.Name):
            return cur.id, idxs

        return None, idxs

    def _handle_call(self, node: ast.Call) -> str:
        """Handle function calls with builtin support."""
        # float('inf')
        if (isinstance(node.func, ast.Name) and node.func.id == "float" and
                node.args and isinstance(node.args[0], ast.Constant)):
            if str(node.args[0].value).lower() in ("inf", "infinity"):
                return "Infinity"

        # len()
        if isinstance(node.func, ast.Name) and node.func.id == "len" and node.args:
            return f"{self.js_expr(node.args[0])}.length"

        # heapq.heappush/heappop
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "heapq":
                self.helpers_needed.add("HEAP")
                if node.func.attr == "heappush":
                    return f"__heappush({self.js_expr(node.args[0])}, {self.js_expr(node.args[1])})"
                if node.func.attr == "heappop":
                    return f"__heappop({self.js_expr(node.args[0])})"

        # TreeNode constructor
        if isinstance(node.func, ast.Name) and node.func.id == "TreeNode":
            args_js = ", ".join(self.js_expr(a) for a in node.args)
            return f"new TreeNode({args_js})"

        # Builtin functions
        if isinstance(node.func, ast.Name):
            fname = node.func.id
            builtin_result = self._handle_builtin(fname, node)
            if builtin_result:
                return builtin_result

            # Generic function call
            args_js = ", ".join(self.js_expr(a) for a in node.args)
            return f"{fname}({args_js})"

        # Method calls
        if isinstance(node.func, ast.Attribute):
            obj_js = self.js_expr(node.func.value)
            method = node.func.attr
            args_js = ", ".join(self.js_expr(a) for a in node.args)

            # Map deque methods
            if method == "appendleft": return f"{obj_js}.unshift({args_js})"
            if method == "popleft": return f"{obj_js}.shift()"

            return f"{obj_js}.{method}({args_js})"

        return "/*call*/"

    def _handle_builtin(self, fname: str, node: ast.Call) -> Optional[str]:
        """Handle Python builtin functions."""
        if not node.args:
            return None

        # Collections
        if fname == "list":
            return f"[...{self.js_expr(node.args[0])}]"
        if fname == "tuple":
            return f"[...{self.js_expr(node.args[0])}]"
        if fname == "set":
            return f"new Set({self.js_expr(node.args[0])})"
        if fname == "dict":
            if node.keywords:
                pairs = [f"[{repr(kw.arg)}, {self.js_expr(kw.value)}]"
                         for kw in node.keywords]
                return f"Object.fromEntries([{', '.join(pairs)}])"
            return f"Object.fromEntries({self.js_expr(node.args[0])})"

        # Math functions - handle multiple args vs single array
        if fname == "max":
            if len(node.args) > 1:
                # max(a, b, c) → Math.max(a, b, c)
                args = ", ".join(self.js_expr(a) for a in node.args)
                return f"Math.max({args})"
            else:
                # max(arr) → Math.max(...arr)
                return f"Math.max(...{self.js_expr(node.args[0])})"

        if fname == "min":
            if len(node.args) > 1:
                # min(a, b, c) → Math.min(a, b, c)
                args = ", ".join(self.js_expr(a) for a in node.args)
                return f"Math.min({args})"
            else:
                # min(arr) → Math.min(...arr)
                return f"Math.min(...{self.js_expr(node.args[0])})"

        if fname == "sum":
            self.helpers_needed.add("SUM")
            return f"__sum({self.js_expr(node.args[0])})"

        if fname == "abs":
            return f"Math.abs({self.js_expr(node.args[0])})"

        if fname == "sorted":
            self.helpers_needed.add("SORTED")
            return f"__sorted({self.js_expr(node.args[0])})"

        if fname == "reversed":
            self.helpers_needed.add("REVERSED")
            return f"__reversed({self.js_expr(node.args[0])})"

        # Iteration
        if fname == "enumerate":
            return f"Array.from({self.js_expr(node.args[0])}.entries())"
        if fname == "zip":
            self.helpers_needed.add("ZIP")
            args = ", ".join(self.js_expr(a) for a in node.args)
            return f"__zip({args})"

        # Collections
        if fname == "defaultdict":
            self.helpers_needed.add("DEFAULTDICT")
            return "__defaultdict(() => [])"
        if fname == "Counter":
            self.helpers_needed.add("COUNTER")
            return f"__counter({self.js_expr(node.args[0])})"

        # heapq direct calls
        if fname == "heappush" and len(node.args) == 2:
            self.helpers_needed.add("HEAP")
            return f"__heappush({self.js_expr(node.args[0])}, {self.js_expr(node.args[1])})"
        if fname == "heappop":
            self.helpers_needed.add("HEAP")
            return f"__heappop({self.js_expr(node.args[0])})"

        return None

    def _handle_list_comp(self, node: ast.ListComp) -> str:
        """Handle list comprehensions."""
        if len(node.generators) == 1:
            g = node.generators[0]
            it = self.js_expr(g.iter)
            var = self.js_expr(g.target)
            elt = self.js_expr(node.elt)

            if g.ifs:
                cond = " && ".join(self.js_expr(c) for c in g.ifs)
                return f"{it}.filter(({var}) => ({cond})).map(({var}) => {elt})"

            return f"{it}.map(({var}) => {elt})"

        return "/*listcomp*/"

    def _handle_generator_exp(self, node: ast.GeneratorExp) -> str:
        """Handle generator expressions."""
        if len(node.generators) == 1:
            g = node.generators[0]
            it = self.js_expr(g.iter)
            var = self.js_expr(g.target)
            elt = self.js_expr(node.elt)

            if g.ifs:
                cond = " && ".join(self.js_expr(c) for c in g.ifs)
                return f"{it}.filter(({var}) => ({cond})).map(({var}) => {elt})"

            return f"{it}.map(({var}) => {elt})"

        return "/*genexp*/"

    # ==================== STATEMENT VISITORS ====================

    def visit_Module(self, node: ast.Module):
        """Visit module - entry point."""
        for stmt in node.body:
            self.visit(stmt)

        # Prepend helpers if needed
        helpers = self._get_helper_code()
        if helpers:
            return "\n".join(helpers + [""] + self.lines)

        return "\n".join(self.lines)

    def visit_ClassDef(self, node: ast.ClassDef):
        """Handle class definitions (mainly TreeNode)."""
        if node.name == "TreeNode":
            self.emit("class TreeNode {")
            self.ind += 1
            self.emit("constructor(val = 0, left = null, right = null) {")
            self.ind += 1
            self.emit("this.val = val;")
            self.emit("this.left = left;")
            self.emit("this.right = right;")
            self.ind -= 1
            self.emit("}")
            self.ind -= 1
            self.emit("}")
        else:
            self.emit(f"/* unsupported class {node.name} */")

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Handle function definitions."""
        args = [a.arg for a in node.args.args]
        self.emit(f"function {node.name}({', '.join(args)}) {{")
        self.ind += 1

        self.func_stack.append(node.name)
        self.scope_stack.append(set(args))

        # Log function entry
        self.emit(f"logger.println('→ {node.name}({', '.join(args)})');")
        self.emit("Tracer.delay();")

        for stmt in node.body:
            self.visit(stmt)

        self.scope_stack.pop()
        self.func_stack.pop()

        self.ind -= 1
        self.emit("}")

    def visit_Assign(self, node: ast.Assign):
        """Handle assignments with tracer instrumentation."""
        if len(node.targets) != 1:
            return

        target = node.targets[0]

        # Destructuring
        if isinstance(target, (ast.Tuple, ast.List)):
            self._handle_destructuring(target, node.value)
            return

        # Simple assignment
        if isinstance(target, ast.Name):
            name = target.id
            rhs_js = self.js_expr(node.value)
            self._emit_decl_or_assign(name, rhs_js)
            return

        # Subscript assignment with tracing
        if isinstance(target, ast.Subscript):
            self._handle_subscript_assign(target, node.value)
            return

    def _handle_destructuring(self, target, value):
        """Handle tuple/list unpacking - including swap patterns."""
        names = [el.id for el in target.elts if isinstance(el, ast.Name)]
        subscripts = [el for el in target.elts if isinstance(el, ast.Subscript)]

        # Detect swap pattern: arr[i], arr[j] = arr[j], arr[i]
        if (len(subscripts) >= 2 and
                isinstance(value, (ast.Tuple, ast.List)) and
                len(value.elts) == len(target.elts)):

            is_swap = True
            for left_sub, right_val in zip(subscripts, value.elts):
                if not isinstance(right_val, ast.Subscript):
                    is_swap = False
                    break

            if is_swap:
                # Generate proper swap code
                swap_pairs = []
                for i, (tgt, val) in enumerate(zip(target.elts, value.elts)):
                    swap_pairs.append((self.js_expr(tgt), self.js_expr(val)))

                # Use destructuring syntax: [a, b] = [b, a]
                left_side = "[" + ", ".join(pair[0] for pair in swap_pairs) + "]"
                right_side = "[" + ", ".join(pair[1] for pair in swap_pairs) + "]"
                self.emit(f"{left_side} = {right_side};")

                # Add tracer for BOTH swapped elements
                if len(swap_pairs) == 2:
                    first_expr = swap_pairs[0][0]
                    second_expr = swap_pairs[1][0]

                    # Extract base and index for both
                    if '[' in first_expr and '[' in second_expr:
                        base1 = first_expr.split('[')[0]
                        base2 = second_expr.split('[')[0]

                        if base1 == base2:  # Same array
                            tracer_base = self._mapped_tracer_base(base1)
                            if tracer_base in self.traceable_1d:
                                idx1 = first_expr.split('[')[1].rstrip(']')
                                idx2 = second_expr.split('[')[1].rstrip(']')

                                self.emit(f"logger.println('Swap elements at {idx1} and {idx2}');")
                                # Patch both elements
                                self.emit(f"{tracer_base}Tracer.patch({idx1}, {first_expr});")
                                self.emit(f"{tracer_base}Tracer.patch({idx2}, {second_expr});")
                                self.emit("Tracer.delay();")
                                self.emit(f"{tracer_base}Tracer.depatch({idx1});")
                                self.emit(f"{tracer_base}Tracer.depatch({idx2});")
                return

        # Regular destructuring
        if isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) == len(names):
            for name, val_node in zip(names, value.elts):
                rhs_js = self.js_expr(val_node)
                self._emit_decl_or_assign(name, rhs_js)
        else:
            tmp = self._gensym()
            self.emit(f"const {tmp} = {self.js_expr(value)};")
            for idx, name in enumerate(names):
                self._emit_decl_or_assign(name, f"{tmp}[{idx}]")

    def _handle_subscript_assign(self, target: ast.Subscript, value):
        """Handle subscript assignment with visualization - fixed for dicts."""
        base, idxs = self._subscript_chain(target)
        rhs = self.js_expr(value)

        if not base:
            return

        # 1D assignment (array or dict)
        if len(idxs) == 1:
            # Get the full index expression (crucial for dict keys like nums[i])
            idx_js = self.js_expr(idxs[0])

            # Check for defaultdict pattern
            if "defaultdict" in base.lower():
                self.emit(f"{base}[{idx_js}].push({rhs});")
            else:
                # Regular assignment - works for both arrays and dicts
                self.emit(f"{base}[{idx_js}] = {rhs};")

            # Add tracer visualization (only for traceable arrays, not dicts)
            tracer_base = self._mapped_tracer_base(base)
            if tracer_base in self.traceable_1d:
                self.emit(f"logger.println('Update {base}[' + {idx_js} + '] = ' + {rhs});")
                self.emit(f"{tracer_base}Tracer.patch({idx_js}, {rhs});")
                self.emit("Tracer.delay();")
                self.emit(f"{tracer_base}Tracer.depatch({idx_js});")
            return

        # 2D assignment
        if len(idxs) == 2:
            i = self._norm_idx(base, idxs[0])
            j = self.js_expr(idxs[1])
            self.emit(f"{base}[{i}][{j}] = {rhs};")

            # Add tracer visualization
            tracer_base = self._mapped_tracer_base(base)
            if tracer_base in self.traceable_2d:
                self.emit(f"logger.println('Update {base}[' + {i} + '][' + {j} + '] = ' + {rhs});")
                self.emit(f"{tracer_base}Tracer.patch({i}, {j}, {rhs});")
                self.emit("Tracer.delay();")
                self.emit(f"{tracer_base}Tracer.depatch({i}, {j});")
            return

    def visit_AugAssign(self, node: ast.AugAssign):
        """Handle augmented assignments."""
        from ast import Add, Sub, Mult, Div, Mod

        target_js = self.js_expr(node.target)
        value_js = self.js_expr(node.value)

        op_map = {Add: "+", Sub: "-", Mult: "*", Div: "/", Mod: "%"}
        op = next((op_map[type(node.op)] for t in op_map if isinstance(node.op, t)), None)

        if op:
            self.emit(f"{target_js} = ({target_js} {op} {value_js});")
        else:
            self.emit("/* unsupported augassign */")

    def visit_If(self, node: ast.If):
        """Handle if statements with smart select/deselect."""
        cond = self.js_expr(node.test)

        # Extract indices from comparison for visualization
        select_info = self._extract_comparison_indices(node.test)

        # Add select before condition
        if select_info:
            for base, indices in select_info:
                tracer_base = self._mapped_tracer_base(base)
                if tracer_base in self.traceable_1d and len(indices) == 2:
                    idx1, idx2 = indices
                    self.emit(f"{tracer_base}Tracer.select({idx1}, {idx2});")
                elif tracer_base in self.traceable_2d and len(indices) == 2:
                    i, j = indices
                    self.emit(f"{tracer_base}Tracer.select({i}, {j});")
            self.emit("Tracer.delay();")

        self.emit(f"if ({cond}) {{")
        self.ind += 1

        for stmt in node.body:
            self.visit(stmt)

        self.ind -= 1

        if node.orelse:
            self.emit("} else {")
            self.ind += 1
            for stmt in node.orelse:
                self.visit(stmt)
            self.ind -= 1

        self.emit("}")

        # Deselect after if block
        if select_info:
            for base, indices in select_info:
                tracer_base = self._mapped_tracer_base(base)
                if tracer_base in self.traceable_1d and len(indices) == 2:
                    idx1, idx2 = indices
                    self.emit(f"{tracer_base}Tracer.deselect({idx1}, {idx2});")
                elif tracer_base in self.traceable_2d and len(indices) == 2:
                    i, j = indices
                    self.emit(f"{tracer_base}Tracer.deselect({i}, {j});")

    def _extract_comparison_indices(self, test_node) -> List[Tuple[str, List[str]]]:
        """
        Extract array indices from comparison for select/deselect.
        Returns: [(base_name, [idx1, idx2, ...]), ...]
        """
        result = []

        if isinstance(test_node, ast.Compare):
            # Collect all subscripts in the comparison
            subscripts = []
            for node in ast.walk(test_node):
                if isinstance(node, ast.Subscript):
                    base, idxs = self._subscript_chain(node)
                    if base and idxs:
                        subscripts.append((base, idxs))

            # Group by base variable
            from collections import defaultdict
            by_base = defaultdict(list)
            for base, idxs in subscripts:
                # For 1D: arr[i], arr[j] → select(i, j)
                if len(idxs) == 1:
                    by_base[base].append(self.js_expr(idxs[0]))
                # For 2D: matrix[i][j] → select(i, j)
                elif len(idxs) == 2:
                    by_base[base].append(self.js_expr(idxs[0]))
                    by_base[base].append(self.js_expr(idxs[1]))

            # Convert to result format
            for base, indices in by_base.items():
                if len(indices) >= 2:
                    # Take first 2 unique indices
                    unique_indices = []
                    seen = set()
                    for idx in indices:
                        if idx not in seen:
                            unique_indices.append(idx)
                            seen.add(idx)
                        if len(unique_indices) >= 2:
                            break

                    if len(unique_indices) >= 2:
                        result.append((base, unique_indices[:2]))

        return result

    def visit_For(self, node: ast.For):
        """Handle for loops with tracing."""
        it = node.iter
        target_is_name = isinstance(node.target, ast.Name)
        loop_var = self.js_expr(node.target)

        # range() loops
        if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range":
            self._handle_range_loop(node, loop_var, target_is_name)
            return

        # for-of loops
        iterable_js = self.js_expr(it)

        if target_is_name and not self._is_declared(loop_var):
            self.emit(f"for (let {loop_var} of {iterable_js}) {{")
            self._declare(loop_var)
        else:
            self.emit(f"for ({loop_var} of {iterable_js}) {{")

        self.ind += 1
        self.loop_stack.append(loop_var)

        for stmt in node.body:
            self.visit(stmt)

        self.loop_stack.pop()
        self.ind -= 1
        self.emit("}")

    def _handle_range_loop(self, node: ast.For, loop_var: str, target_is_name: bool):
        """Handle range-based for loops with smart select/deselect."""
        args = node.iter.args

        if len(args) == 1:
            n = self.js_expr(args[0])
            init = f"let {loop_var} = 0" if target_is_name and not self._is_declared(loop_var) else f"{loop_var} = 0"
            test = f"{loop_var} < {n}"
            step = f"{loop_var}++"
        elif len(args) == 2:
            a = self.js_expr(args[0])
            b = self.js_expr(args[1])
            init = f"let {loop_var} = {a}" if target_is_name and not self._is_declared(
                loop_var) else f"{loop_var} = {a}"
            test = f"{loop_var} < {b}"
            step = f"{loop_var}++"
        elif len(args) == 3:
            a = self.js_expr(args[0])
            b = self.js_expr(args[1])
            c = self.js_expr(args[2])
            comp = ">" if (isinstance(args[2], ast.Constant) and args[2].value < 0) else "<"
            init = f"let {loop_var} = {a}" if target_is_name and not self._is_declared(
                loop_var) else f"{loop_var} = {a}"
            test = f"{loop_var} {comp} {b}"
            step = f"{loop_var} += {c}"
        else:
            init = "let i = 0"
            test = "i < 0"
            step = "i++"

        if target_is_name and "let" in init:
            self._declare(loop_var)

        self.emit(f"for ({init}; {test}; {step}) {{")
        self.ind += 1
        self.loop_stack.append(loop_var)

        # Auto-select loop index if we're iterating over a traceable array
        primary_array = self._find_primary_array_in_loop(node.body)

        if primary_array:
            tracer_base = self._mapped_tracer_base(primary_array)
            if tracer_base in self.traceable_1d:
                self.emit(f"{tracer_base}Tracer.select({loop_var});")
                self.emit("Tracer.delay();")

        for stmt in node.body:
            self.visit(stmt)

        # Deselect after loop body
        if primary_array:
            tracer_base = self._mapped_tracer_base(primary_array)
            if tracer_base in self.traceable_1d:
                self.emit(f"{tracer_base}Tracer.deselect({loop_var});")

        self.loop_stack.pop()
        self.ind -= 1
        self.emit("}")

    def _find_primary_array_in_loop(self, body: List[ast.stmt]) -> Optional[str]:
        """
        Find the primary array being accessed in loop body.
        Returns the array name if found.
        """
        # Look for subscript accesses in the loop body
        for stmt in body:
            for node in ast.walk(stmt):
                if isinstance(node, ast.Subscript):
                    base, idxs = self._subscript_chain(node)
                    if base and base in self.traceable_1d:
                        return base
                    if base and base in self.traceable_2d:
                        return base
        return None

    def visit_While(self, node: ast.While):
        """Handle while loops with smart visualization."""
        cond = self.js_expr(node.test)

        # Extract variables for visualization
        viz_info = self._extract_while_viz_info(node.test)

        self.emit(f"while ({cond}) {{")
        self.ind += 1

        # Find 'mid' variable assignments in the loop body for binary search
        mid_var = self._find_mid_variable(node.body)

        # Add select at start of loop body
        if viz_info:
            for base, indices in viz_info:
                tracer_base = self._mapped_tracer_base(base)
                if tracer_base in self.traceable_1d and len(indices) <= 2:
                    idx_str = ", ".join(indices)
                    self.emit(f"{tracer_base}Tracer.select({idx_str});")
                    self.emit("Tracer.delay();")

        for stmt in node.body:
            self.visit(stmt)

            # If this statement defines 'mid', add visualization
            if mid_var and isinstance(stmt, ast.Assign):
                if (len(stmt.targets) == 1 and
                        isinstance(stmt.targets[0], ast.Name) and
                        stmt.targets[0].id == mid_var):
                    # Check if we have a traceable array
                    for base in self.traceable_1d:
                        self.emit(f"{base}Tracer.select({mid_var});")
                        self.emit("Tracer.delay();")
                        self.emit(f"{base}Tracer.deselect({mid_var});")
                        break

        # Deselect at end of loop body
        if viz_info:
            for base, indices in viz_info:
                tracer_base = self._mapped_tracer_base(base)
                if tracer_base in self.traceable_1d and len(indices) <= 2:
                    idx_str = ", ".join(indices)
                    self.emit(f"{tracer_base}Tracer.deselect({idx_str});")

        self.ind -= 1
        self.emit("}")

    def _find_mid_variable(self, body: List[ast.stmt]) -> Optional[str]:
        """Find the 'mid' variable in binary search pattern."""
        for stmt in body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                target = stmt.targets[0]
                if isinstance(target, ast.Name) and target.id in ('mid', 'middle', 'm'):
                    return target.id
        return None

    def _extract_while_viz_info(self, test_node) -> List[Tuple[str, List[str]]]:
        """
        Extract indices from while condition for visualization.
        Similar to comparison extraction but for while loops.
        """
        result = []

        # Collect all subscripts and names in the condition
        subscripts = []
        var_names = set()

        for node in ast.walk(test_node):
            if isinstance(node, ast.Subscript):
                base, idxs = self._subscript_chain(node)
                if base and idxs:
                    subscripts.append((base, idxs))
            elif isinstance(node, ast.Name):
                var_names.add(node.id)

        # Group subscripts by base
        from collections import defaultdict
        by_base = defaultdict(list)
        for base, idxs in subscripts:
            if len(idxs) == 1:
                by_base[base].append(self.js_expr(idxs[0]))

        # Convert to result format
        for base, indices in by_base.items():
            if len(indices) >= 1:
                unique_indices = []
                seen = set()
                for idx in indices:
                    if idx not in seen:
                        unique_indices.append(idx)
                        seen.add(idx)
                    if len(unique_indices) >= 2:
                        break

                if unique_indices:
                    result.append((base, unique_indices))

        # If no subscripts but we have simple variable comparisons
        # like "left <= right", add those for visualization
        if not result and len(var_names) >= 2:
            # Find traceable arrays mentioned
            for vname in var_names:
                if vname in self.traceable_1d:
                    # This is likely an index variable
                    other_vars = [v for v in var_names if v != vname and v not in self.traceable_1d]
                    if other_vars:
                        result.append((vname, other_vars[:2]))
                    break

        return result

    def visit_Expr(self, node: ast.Expr):
        """Handle expression statements."""
        if isinstance(node.value, ast.Call):
            call = node.value

            # Handle append with tracing
            if isinstance(call.func, ast.Attribute) and call.func.attr == "append":
                base = self.js_expr(call.func.value)
                arg_js = self.js_expr(call.args[0]) if call.args else "undefined"
                self.emit(f"{base}.push({arg_js});")

                tracer_base = self._mapped_tracer_base(base)
                if tracer_base in self.traceable_1d:
                    self.emit(f"logger.println('Append {arg_js} to {base}');")
                    self.emit(f"{tracer_base}Tracer.patch({base}.length - 1, {arg_js});")
                    self.emit("Tracer.delay();")
                    self.emit(f"{tracer_base}Tracer.depatch({base}.length - 1);")
                return

            # Handle print()
            if isinstance(call.func, ast.Name) and call.func.id == "print":
                msg = self.js_expr(call.args[0]) if call.args else "''"
                self.emit(f"logger.println({msg});")
                return

        self.emit(self.js_expr(node.value) + ";")

    def visit_Break(self, node: ast.Break):
        self.emit("break;")

    def visit_Continue(self, node: ast.Continue):
        self.emit("continue;")

    def visit_Pass(self, node: ast.Pass):
        self.emit("/* pass */")

    def visit_Return(self, node: ast.Return):
        if node.value is None:
            self.emit("logger.println('← return');")
            self.emit("return;")
        else:
            v_js = self.js_expr(node.value)
            self.emit(f"logger.println('← return ' + JSON.stringify({v_js}));")
            self.emit(f"return {v_js};")

    def generic_visit(self, node: ast.AST):
        pass


# ==================== PUBLIC API ====================

def translate_to_js(code: str, summary: Dict) -> str:
    """
    Translate Python code to instrumented JavaScript.

    Args:
        code: Python source code
        summary: Analysis summary from EnhancedAnalyzer

    Returns:
        Instrumented JavaScript code
    """
    tree = ast.parse(code)
    bindings = _collect_param_bindings(tree)

    # Get traceable variables from summary
    traceable_1d = set(summary.get("vars_1d", []))
    traceable_2d = set(summary.get("vars_2d", []))

    translator = InstrumentedTranslator(
        summary=summary,
        traceable_1d=traceable_1d,
        traceable_2d=traceable_2d,
        param_bindings=bindings,
    )

    js = translator.visit(tree)
    return js or "\n".join(translator.lines)