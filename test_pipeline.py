# -*- coding: utf-8 -*-
from indentation_fixer import fix_indentation
from analyzer import analyze_code
from blueprint_generator import generate_blueprint
from translator import translate_to_js
from code_combiner import combine_code, validate_output


def test_pipeline(name: str, python_code: str):
    print("=" * 80)
    print(f"TEST: {name}")
    print("=" * 80)

    print("\n[1/5] Fixing indentation...")
    fixed_code = fix_indentation(python_code)
    print("✓ Indentation normalized")

    print("\n[2/5] Analyzing code...")
    summary = analyze_code(fixed_code)
    print(f"✓ Detected:")
    print(f"  - 1D arrays: {summary.get('vars_1d', [])}")
    print(f"  - 2D arrays: {summary.get('vars_2d', [])}")
    print(f"  - Has sorting: {summary.get('has_sorting', False)}")
    print(f"  - Viz type: {summary.get('viz_type', 'unknown')}")

    print("\n[3/5] Generating blueprint...")
    blueprint = generate_blueprint(summary)
    print(f"✓ Blueprint generated ({len(blueprint.split(chr(10)))} lines)")

    print("\n[4/5] Translating to JavaScript...")
    algorithm = translate_to_js(fixed_code, summary)
    print(f"✓ Algorithm translated ({len(algorithm.split(chr(10)))} lines)")

    print("\n[5/5] Combining code...")
    final_js = combine_code(blueprint, algorithm)
    print(f"✓ Final code generated ({len(final_js.split(chr(10)))} lines)")

    print("\n[Validation]")
    validation = validate_output(final_js)
    all_passed = all(validation.values())
    for check, passed in validation.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")

    print("\n" + "=" * 80)
    print("FINAL JAVASCRIPT OUTPUT:")
    print("=" * 80)
    print(final_js)
    print("\n" + "=" * 80)

    if all_passed:
        print("✓ ALL CHECKS PASSED")
    else:
        print("✗ SOME CHECKS FAILED")

    print("=" * 80)
    print("\n\n")

    return all_passed


def main():
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "ALGORITHM VISUALIZER PIPELINE TEST" + " " * 24 + "║")
    print("╚" + "═" * 78 + "╝")
    print("\n")

    results = []

    # TEST 1: Bubble Sort (Sorting Algorithm)
    test1 = """
def bubbleSort(arr):
    n = len(arr)
    for i in range(n - 1):
        for j in range(n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
"""
    results.append(("Bubble Sort", test_pipeline("Bubble Sort", test1)))

    # TEST 2: Two Sum (Hash Map)
    test2 = """
def twoSum(nums, target):
    hashmap = {}
    for i in range(len(nums)):
        complement = target - nums[i]
        if complement in hashmap:
            return [hashmap[complement], i]
        hashmap[nums[i]] = i
    return []
"""
    results.append(("Two Sum", test_pipeline("Two Sum", test2)))

    # TEST 3: Binary Search (Searching Algorithm)
    test3 = """
def binarySearch(arr, target):
    left = 0
    right = len(arr) - 1

    while left <= right:
        mid = (left + right) // 2

        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1
"""
    results.append(("Binary Search", test_pipeline("Binary Search", test3)))

    # TEST 4: Valid Parentheses (Stack)
    test4 = """
def isValid(s):
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}

    for char in s:
        if char in mapping:
            if not stack:
                return False
            top = stack.pop()
            if mapping[char] != top:
                return False
        else:
            stack.append(char)

    return len(stack) == 0
"""
    results.append(("Valid Parentheses", test_pipeline("Valid Parentheses", test4)))

    # TEST 5: Set Matrix Zeroes (2D Array)
    test5 = """
def setZeroes(matrix):
    rows = len(matrix)
    cols = len(matrix[0])
    zeroes = []

    for i in range(rows):
        for j in range(cols):
            if matrix[i][j] == 0:
                zeroes.append((i, j))

    for i, j in zeroes:
        for c in range(cols):
            matrix[i][c] = 0
        for r in range(rows):
            matrix[r][j] = 0

    return matrix
"""
    results.append(("Set Matrix Zeroes", test_pipeline("Set Matrix Zeroes", test5)))

    # TEST 6: Max Depth Binary Tree (Tree/Recursion)
    test6 = """
def maxDepth(root):
    if not root:
        return 0

    left_depth = maxDepth(root.left)
    right_depth = maxDepth(root.right)

    return max(left_depth, right_depth) + 1
"""
    results.append(("Max Depth Binary Tree", test_pipeline("Max Depth Binary Tree", test6)))

    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 32 + "TEST SUMMARY" + " " * 34 + "║")
    print("╚" + "═" * 78 + "╝")
    print("\n")

    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status:12} | {name}")

    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")

    if total_passed == len(results):
        print("\nAll tests passed. Pipeline is working correctly.\n")
    else:
        print("\nSome tests failed. Check output above for details.\n")


if __name__ == "__main__":
    main()