# -*- coding: utf-8 -*-
import re
from typing import List, Dict, Optional, Tuple


class CodeCombiner:

    def __init__(self):
        self.final_lines: List[str] = []

    def combine(self, blueprint: str, algorithm: str) -> str:
        blueprint_lines = blueprint.split('\n')
        algorithm_lines = algorithm.split('\n')

        algo_imports = self._extract_imports(algorithm_lines)
        algo_helpers = self._extract_helpers(algorithm_lines)
        algo_classes = self._extract_classes(algorithm_lines)
        algo_functions = self._extract_functions(algorithm_lines)
        algo_main = self._extract_main_code(algorithm_lines)

        blueprint_imports = self._extract_imports(blueprint_lines)

        self.final_lines = []

        merged_imports = self._merge_imports(blueprint_imports, algo_imports)
        if merged_imports:
            self.final_lines.extend(merged_imports)
            self.final_lines.append('')

        if algo_helpers:
            self.final_lines.extend(algo_helpers)
            self.final_lines.append('')

        if algo_classes:
            self.final_lines.extend(algo_classes)
            self.final_lines.append('')

        blueprint_setup = self._extract_setup(blueprint_lines)
        if blueprint_setup:
            self.final_lines.extend(blueprint_setup)
            self.final_lines.append('')

        if algo_functions:
            self.final_lines.extend(algo_functions)
            self.final_lines.append('')

        main_without_calls = self._filter_out_function_calls(algo_main, algo_functions)
        if main_without_calls:
            self.final_lines.extend(main_without_calls)

        function_call = self._generate_function_call(algo_functions, blueprint_setup)
        if function_call:
            self.final_lines.append('')
            self.final_lines.extend(function_call)

        return self._clean_output('\n'.join(self.final_lines))

    def _extract_imports(self, lines: List[str]) -> List[str]:
        imports = []
        for line in lines:
            if line.strip().startswith('const {') and 'require(' in line:
                imports.append(line)
        return imports

    def _extract_helpers(self, lines: List[str]) -> List[str]:
        helpers = []
        in_helper = False
        helper_depth = 0

        for line in lines:
            stripped = line.strip()

            if stripped.startswith('function __') or stripped.startswith('const __'):
                in_helper = True
                helper_depth = 0

            if in_helper:
                helpers.append(line)
                helper_depth += line.count('{') - line.count('}')

                if helper_depth == 0 and (stripped.endswith('}') or stripped.endswith(';')):
                    in_helper = False

        return helpers

    def _extract_classes(self, lines: List[str]) -> List[str]:
        classes = []
        in_class = False
        class_depth = 0

        for line in lines:
            stripped = line.strip()

            if stripped.startswith('class '):
                in_class = True
                class_depth = 0

            if in_class:
                classes.append(line)
                class_depth += line.count('{') - line.count('}')

                if class_depth == 0 and stripped.endswith('}'):
                    in_class = False

        return classes

    def _extract_functions(self, lines: List[str]) -> List[str]:
        functions = []
        in_function = False
        func_depth = 0

        for line in lines:
            stripped = line.strip()

            if stripped.startswith('function ') and not stripped.startswith('function __'):
                in_function = True
                func_depth = 0

            if in_function:
                functions.append(line)
                func_depth += line.count('{') - line.count('}')

                if func_depth == 0 and stripped.endswith('}'):
                    in_function = False

        return functions

    def _extract_setup(self, lines: List[str]) -> List[str]:
        setup = []
        skip_imports = True

        for line in lines:
            stripped = line.strip()

            if stripped.startswith('const {') and 'require(' in stripped:
                continue

            if stripped or not skip_imports:
                setup.append(line)
                skip_imports = False

        return setup

    def _extract_main_code(self, lines: List[str]) -> List[str]:
        main = []
        in_function = False
        in_class = False
        depth = 0

        for line in lines:
            stripped = line.strip()

            if (stripped.startswith('const {') and 'require(' in stripped):
                continue
            if stripped.startswith('function __') or stripped.startswith('const __'):
                in_function = True
                depth = 0
            if stripped.startswith('class '):
                in_class = True
                depth = 0
            if stripped.startswith('function ') and not stripped.startswith('function __'):
                in_function = True
                depth = 0

            if in_function or in_class:
                depth += line.count('{') - line.count('}')
                if depth == 0 and stripped.endswith('}'):
                    in_function = False
                    in_class = False
                continue

            if not in_function and not in_class:
                main.append(line)

        return main

    def _merge_imports(self, blueprint_imports: List[str], algo_imports: List[str]) -> List[str]:
        if not blueprint_imports and not algo_imports:
            return []

        if blueprint_imports:
            return blueprint_imports

        if algo_imports:
            return algo_imports

        return []

    def _filter_out_function_calls(self, main_code: List[str], functions: List[str]) -> List[str]:
        func_names = set()
        for line in functions:
            match = re.match(r'\s*function\s+(\w+)\s*\(', line)
            if match:
                func_names.add(match.group(1))

        filtered = []
        for line in main_code:
            stripped = line.strip()
            is_call = False
            for fname in func_names:
                if re.match(rf'^{fname}\s*\(.*\)\s*;?\s*$', stripped):
                    is_call = True
                    break

            if not is_call:
                filtered.append(line)

        return filtered

    def _generate_function_call(self, functions: List[str], setup: List[str]) -> List[str]:
        main_func = self._find_main_function(functions)
        if not main_func:
            return []

        func_name, params = main_func
        initialized_vars = self._extract_initialized_vars(setup)
        args = self._match_params_to_vars(params, initialized_vars)

        if not args:
            return []

        return [
            f"// Call main algorithm",
            f"{func_name}({', '.join(args)});",
            "",
            "// Log completion",
            f"logger.println('Algorithm completed');",
            "Tracer.delay();"
        ]

    def _find_main_function(self, functions: List[str]) -> Optional[Tuple[str, List[str]]]:
        for line in functions:
            match = re.match(r'\s*function\s+(\w+)\s*\(([^)]*)\)', line)
            if match:
                func_name = match.group(1)
                params_str = match.group(2).strip()

                if func_name.startswith('__'):
                    continue

                params = []
                if params_str:
                    params = [p.strip() for p in params_str.split(',')]

                return (func_name, params)

        return None

    def _extract_initialized_vars(self, setup: List[str]) -> Dict[str, str]:
        vars_dict = {}

        for line in setup:
            match1d = re.match(r'\s*const\s+(\w+)\s*=\s*Randomize\.Array1D', line)
            if match1d:
                vars_dict[match1d.group(1)] = '1d'
                continue

            match2d = re.match(r'\s*const\s+(\w+)\s*=\s*Randomize\.Array2D', line)
            if match2d:
                vars_dict[match2d.group(1)] = '2d'
                continue

            matchGraph = re.match(r'\s*const\s+(\w+)\s*=\s*Randomize\.Graph', line)
            if matchGraph:
                vars_dict[matchGraph.group(1)] = 'graph'
                continue

        return vars_dict

    def _match_params_to_vars(self, params: List[str], initialized_vars: Dict[str, str]) -> List[str]:
        if not params:
            return []

        args = []
        used_vars = set()

        for param in params:
            matched = False

            if param in initialized_vars:
                args.append(param)
                used_vars.add(param)
                matched = True
                continue

            if not matched:
                for var_name in initialized_vars:
                    if var_name not in used_vars:
                        if (param.lower() in var_name.lower() or
                                var_name.lower() in param.lower()):
                            args.append(var_name)
                            used_vars.add(var_name)
                            matched = True
                            break

            if not matched:
                param_lower = param.lower()
                if 'matrix' in param_lower or 'grid' in param_lower or 'board' in param_lower:
                    target_type = '2d'
                elif 'graph' in param_lower:
                    target_type = 'graph'
                else:
                    target_type = '1d'

                for var_name, var_type in initialized_vars.items():
                    if var_type == target_type and var_name not in used_vars:
                        args.append(var_name)
                        used_vars.add(var_name)
                        matched = True
                        break

            if not matched:
                for var_name in initialized_vars:
                    if var_name not in used_vars:
                        args.append(var_name)
                        used_vars.add(var_name)
                        break

        return args

    def _clean_output(self, code: str) -> str:
        lines = code.split('\n')
        cleaned = []
        blank_count = 0

        for line in lines:
            line = line.rstrip()

            if not line.strip():
                blank_count += 1
                if blank_count <= 2:
                    cleaned.append(line)
            else:
                blank_count = 0
                cleaned.append(line)

        while cleaned and not cleaned[-1].strip():
            cleaned.pop()

        return '\n'.join(cleaned)


def combine_code(blueprint: str, algorithm: str) -> str:
    combiner = CodeCombiner()
    return combiner.combine(blueprint, algorithm)


def validate_output(code: str) -> Dict[str, bool]:
    return {
        "has_imports": bool(re.search(r"require\('algorithm-visualizer'\)", code)),
        "has_layout": "Layout.setRoot" in code,
        "has_logger": "logger" in code or "LogTracer" in code,
        "has_tracer_delay": "Tracer.delay()" in code,
        "has_functions": bool(re.search(r"function \w+\(", code)),
        "no_syntax_errors": _basic_syntax_check(code),
    }


def _basic_syntax_check(code: str) -> bool:
    open_braces = code.count('{')
    close_braces = code.count('}')

    if open_braces != close_braces:
        return False

    open_parens = code.count('(')
    close_parens = code.count(')')

    if open_parens != close_parens:
        return False

    open_brackets = code.count('[')
    close_brackets = code.count(']')

    if open_brackets != close_brackets:
        return False

    return True