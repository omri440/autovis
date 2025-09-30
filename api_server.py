# -*- coding: utf-8 -*-
"""
Flask API Server for Algorithm Visualizer Chrome Extension
Provides REST API endpoint for Python to JavaScript conversion
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback
import sys

# Import your pipeline modules
from indentation_fixer import fix_indentation
from analyzer import analyze_code
from blueprint_generator import generate_blueprint
from translator import translate_to_js
from code_combiner import combine_code, validate_output

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {"origins": "*"},
    r"/health": {"origins": "*"}
})  # Enable CORS for Chrome extension


# ==================== API ENDPOINTS ====================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify server is running"""
    return jsonify({
        'status': 'online',
        'message': 'Algorithm Visualizer API is running'
    }), 200


@app.route('/api/convert', methods=['POST'])
def convert_algorithm():
    """
    Main conversion endpoint
    Accepts Python code and returns JavaScript visualization code
    """
    try:
        # Get Python code from request
        data = request.get_json()

        if not data or 'code' not in data:
            return jsonify({
                'error': 'No code provided. Send JSON with "code" field.'
            }), 400

        python_code = data['code']

        if not python_code.strip():
            return jsonify({
                'error': 'Empty code provided'
            }), 400

        # Run through pipeline
        print("\n" + "=" * 80)
        print("CONVERTING ALGORITHM")
        print("=" * 80)

        # Step 1: Fix indentation
        print("\n[1/5] Fixing indentation...")
        fixed_code = fix_indentation(python_code)
        print("✓ Indentation normalized")

        # Step 2: Analyze code
        print("\n[2/5] Analyzing code...")
        summary = analyze_code(fixed_code)
        print(f"✓ Detected:")
        print(f"  - 1D arrays: {summary.get('vars_1d', [])}")
        print(f"  - 2D arrays: {summary.get('vars_2d', [])}")
        print(f"  - Viz type: {summary.get('viz_type', 'unknown')}")

        # Step 3: Generate blueprint
        print("\n[3/5] Generating blueprint...")
        blueprint = generate_blueprint(summary)
        print(f"✓ Blueprint generated ({len(blueprint.split(chr(10)))} lines)")

        # Step 4: Translate to JavaScript
        print("\n[4/5] Translating to JavaScript...")
        algorithm = translate_to_js(fixed_code, summary)
        print(f"✓ Algorithm translated ({len(algorithm.split(chr(10)))} lines)")

        # Step 5: Combine code
        print("\n[5/5] Combining code...")
        final_js = combine_code(blueprint, algorithm)
        print(f"✓ Final code generated ({len(final_js.split(chr(10)))} lines)")

        # Validate output
        print("\n[Validation]")
        validation = validate_output(final_js)
        all_passed = all(validation.values())

        for check, passed in validation.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")

        if all_passed:
            print("\n✓ ALL CHECKS PASSED")
        else:
            print("\n✗ SOME CHECKS FAILED")

        print("=" * 80 + "\n")

        # Return successful response
        return jsonify({
            'success': True,
            'javascript': final_js,
            'analysis': {
                'vars_1d': summary.get('vars_1d', []),
                'vars_2d': summary.get('vars_2d', []),
                'viz_type': summary.get('viz_type', 'unknown'),
                'has_sorting': summary.get('has_sorting', False),
                'has_graph': summary.get('has_graph', False),
                'has_searching': summary.get('has_searching', False)
            },
            'validation': validation,
            'lines': len(final_js.split('\n'))
        }), 200

    except SyntaxError as e:
        error_msg = f"Python syntax error: {str(e)}"
        print(f"\n❌ ERROR: {error_msg}")
        return jsonify({
            'error': error_msg,
            'type': 'syntax_error'
        }), 400

    except Exception as e:
        error_msg = f"Conversion failed: {str(e)}"
        print(f"\n❌ ERROR: {error_msg}")
        print(traceback.format_exc())
        return jsonify({
            'error': error_msg,
            'type': 'conversion_error',
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/analyze', methods=['POST'])
def analyze_only():
    """
    Analysis-only endpoint
    Returns just the analysis without full conversion
    """
    try:
        data = request.get_json()

        if not data or 'code' not in data:
            return jsonify({'error': 'No code provided'}), 400

        python_code = data['code']

        # Fix indentation and analyze
        fixed_code = fix_indentation(python_code)
        summary = analyze_code(fixed_code)

        return jsonify({
            'success': True,
            'analysis': summary
        }), 200

    except Exception as e:
        return jsonify({
            'error': str(e),
            'type': 'analysis_error'
        }), 500


@app.route('/api/examples', methods=['GET'])
def get_examples():
    """
    Returns example algorithms
    """
    examples = {
        'bubble_sort': {
            'name': 'Bubble Sort',
            'code': '''def bubbleSort(arr):
    n = len(arr)
    for i in range(n - 1):
        for j in range(n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr''',
            'description': 'Simple sorting algorithm with O(n²) complexity'
        },
        'binary_search': {
            'name': 'Binary Search',
            'code': '''def binarySearch(arr, target):
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

    return -1''',
            'description': 'Efficient search in sorted arrays with O(log n) complexity'
        },
        'two_sum': {
            'name': 'Two Sum',
            'code': '''def twoSum(nums, target):
    hashmap = {}
    for i in range(len(nums)):
        complement = target - nums[i]
        if complement in hashmap:
            return [hashmap[complement], i]
        hashmap[nums[i]] = i
    return []''',
            'description': 'Find two numbers that add up to target using hash map'
        },
        'matrix_zeroes': {
            'name': 'Set Matrix Zeroes',
            'code': '''def setZeroes(matrix):
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

    return matrix''',
            'description': '2D array manipulation algorithm'
        }
    }

    return jsonify({
        'success': True,
        'examples': examples
    }), 200


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'error': 'Endpoint not found',
        'available_endpoints': [
            '/health',
            '/api/convert',
            '/api/analyze',
            '/api/examples'
        ]
    }), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        'error': 'Internal server error',
        'message': str(e)
    }), 500


# ==================== MAIN ====================

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print(" " * 20 + "ALGORITHM VISUALIZER API SERVER")
    print("=" * 80)
    print("\n🚀 Server starting on http://localhost:5000")
    print("\n📍 Available endpoints:")
    print("   GET  /health          - Health check")
    print("   POST /api/convert     - Convert Python to JavaScript")
    print("   POST /api/analyze     - Analyze Python code only")
    print("   GET  /api/examples    - Get example algorithms")
    print("\n💡 Ready to accept requests from Chrome extension")
    print("=" * 80 + "\n")

    # Run server
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)
