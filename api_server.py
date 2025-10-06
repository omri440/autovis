# -*- coding: utf-8 -*-
"""
Flask API Server - GPT-4 Multi-Agent Version
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback
import os

# Import pipeline modules
from indentation_fixer import fix_indentation
from analyzer import analyze_code
from blueprint_generator import generate_blueprint
from translator import translate_to_js
from code_combiner import combine_code, validate_output

# Import GPT-4 multi-agent system
from multi_agent_polisher_openai import polish_with_multi_agent
from fetch_algo_examples import GitHubExampleFetcher, ExampleDatabase

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {"origins": "*"},
    r"/health": {"origins": "*"}
})

# ==================== INITIALIZATION ====================

print("\n" + "=" * 80)
print("INITIALIZING GPT-4 MULTI-AGENT POLISHER")
print("=" * 80)

# Load examples
try:
    print("\n[Init] Loading Algorithm Visualizer examples...")
    local_algos = os.getenv('ALGORITHMS_LOCAL_DIR')
    fetcher = GitHubExampleFetcher(local_algorithms_dir=local_algos)
    # Local-only mode if ALGORITHMS_LOCAL_DIR is set
    if local_algos:
        print("LOCAL-ONLY mode: importing examples from local directory")
        examples = fetcher.get_examples(force_refresh=True)
    else:
        examples = fetcher.get_examples(force_refresh=False)
        # Force refresh if cache empty
        if not examples:
            print("Cache empty, forcing refresh from GitHub...")
            examples = fetcher.get_examples(force_refresh=True)
    example_db = ExampleDatabase(examples)

    print(f"✓ Loaded {len(examples)} examples")
    print(f"✓ Categories: {', '.join(example_db.by_category.keys())}")
    print(f"✓ RAG system ready")

    MULTI_AGENT_ENABLED = True
except Exception as e:
    print(f"✗ Failed to load examples: {e}")
    print("  Falling back to single-agent mode")
    MULTI_AGENT_ENABLED = False
    example_db = None

# Check for OpenAI API key
OPENAI_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_KEY:
    print("\n⚠️  No OPENAI_API_KEY found")
    print("   Set it with: export OPENAI_API_KEY='your-key'")
    print("   Get key from: https://platform.openai.com/api-keys")
    print("   Multi-agent polishing disabled")
    MULTI_AGENT_ENABLED = False
else:
    print(f"\n✓ OpenAI API key configured")
    print(f"✓ Using GPT-4 Turbo for agents")

print("=" * 80 + "\n")

AI_CONFIG = {
    'enabled': MULTI_AGENT_ENABLED and bool(OPENAI_KEY),
    'provider': 'gpt-4-multi-agent',
    'model': 'gpt-4-turbo-preview'
}


# ==================== ENDPOINTS ====================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'message': 'Algorithm Visualizer API with GPT-4',
        'ai_enabled': AI_CONFIG['enabled'],
        'ai_provider': AI_CONFIG['provider'],
        'ai_model': AI_CONFIG['model'],
        'multi_agent': MULTI_AGENT_ENABLED,
        'examples_loaded': len(example_db.examples) if example_db else 0
    }), 200


@app.route('/api/convert', methods=['POST'])
def convert_algorithm():
    """Main conversion endpoint with GPT-4 multi-agent polishing"""
    try:
        data = request.get_json()

        if not data or 'code' not in data:
            return jsonify({'error': 'No code provided'}), 400

        python_code = data['code']
        enable_polish = data.get('enable_polish', AI_CONFIG['enabled'])

        if not python_code.strip():
            return jsonify({'error': 'Empty code'}), 400

        print("\n" + "=" * 80)
        print("CONVERTING ALGORITHM")
        print("=" * 80)

        # Steps 1-5: Standard pipeline
        print("\n[1/6] Fixing indentation...")
        fixed_code = fix_indentation(python_code)
        print("✓ Indentation normalized")

        print("\n[2/6] Analyzing code...")
        summary = analyze_code(fixed_code)
        print(f"✓ Analysis complete")
        print(f"  - 1D arrays: {summary.get('vars_1d', [])}")
        print(f"  - 2D arrays: {summary.get('vars_2d', [])}")
        print(f"  - Type: {summary.get('viz_type', 'unknown')}")

        print("\n[3/6] Generating blueprint...")
        blueprint = generate_blueprint(summary)
        print(f"✓ Blueprint ready")

        print("\n[4/6] Translating to JavaScript...")
        algorithm = translate_to_js(fixed_code, summary)
        print(f"✓ Translation complete")

        print("\n[5/6] Combining code...")
        final_js = combine_code(blueprint, algorithm)
        print(f"✓ Code combined ({len(final_js.split(chr(10)))} lines)")

        # Step 6: GPT-4 Multi-Agent Polish
        polish_result = None
        if enable_polish and MULTI_AGENT_ENABLED:
            print(f"\n[6/6] GPT-4 Multi-Agent Polishing...")
            print("=" * 60)

            try:
                polish_result = polish_with_multi_agent(
                    final_js,
                    python_code,
                    summary
                )

                if polish_result['was_polished']:
                    final_js = polish_result['polished']
                    print("\n✓ GPT-4 agents completed successfully!")

                    # Show results
                    if 'agent_results' in polish_result:
                        print("\nAgent Performance:")
                        for result in polish_result['agent_results']:
                            agent = result['agent']
                            meta = result['metadata']

                            if meta.get('changed'):
                                status = "✓ IMPROVED"
                                reason = meta.get('reason', '')
                                if 'original_logs' in meta and 'new_logs' in meta:
                                    reason = f"Logger calls: {meta['original_logs']} → {meta['new_logs']}"
                                print(f"  {status} - {agent}")
                                if reason:
                                    print(f"           {reason}")
                            else:
                                print(f"  - SKIPPED - {agent}")
                                if meta.get('reason'):
                                    print(f"           {meta['reason']}")

                    if 'examples_used' in polish_result:
                        examples = polish_result['examples_used']
                        if examples:
                            print(f"\n✓ Referenced examples: {', '.join(examples)}")

                    print("=" * 60)
                else:
                    error = polish_result.get('error', 'Unknown error')
                    print(f"✗ Polishing failed: {error}")

            except Exception as e:
                print(f"✗ Polishing error: {e}")
                traceback.print_exc()
                polish_result = {'was_polished': False, 'error': str(e)}
        else:
            print("\n[6/6] AI Polishing disabled")
            if not enable_polish:
                print("  Reason: Disabled by request")
            elif not MULTI_AGENT_ENABLED:
                print("  Reason: System not available")
            elif not OPENAI_KEY:
                print("  Reason: No API key")

        # Validation
        print("\n[Validation]")
        validation = validate_output(final_js)
        all_passed = all(validation.values())

        for check, passed in validation.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")

        print("\n" + ("✓ ALL CHECKS PASSED" if all_passed else "✗ SOME CHECKS FAILED"))
        print("=" * 80 + "\n")

        # Response
        response = {
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
        }

        if polish_result:
            response['polishing'] = {
                'enabled': True,
                'was_polished': polish_result['was_polished'],
                'provider': 'gpt-4',
                'model': 'gpt-4-turbo-preview',
                'agent_results': polish_result.get('agent_results', []),
                'examples_used': polish_result.get('examples_used', []),
                'error': polish_result.get('error')
            }

        return jsonify(response), 200

    except Exception as e:
        error_msg = f"Conversion failed: {str(e)}"
        print(f"\n⌧ ERROR: {error_msg}")
        print(traceback.format_exc())
        return jsonify({
            'error': error_msg,
            'type': 'conversion_error'
        }), 500


@app.route('/api/examples', methods=['GET'])
def get_examples():
    """Get cached examples"""
    if not example_db:
        return jsonify({'error': 'Examples not loaded'}), 500

    by_category = {}
    for ex in example_db.examples:
        cat = ex['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append({
            'name': ex['name'],
            'patterns': ex['patterns']
        })

    return jsonify({
        'success': True,
        'total': len(example_db.examples),
        'categories': by_category
    }), 200


@app.route('/api/examples/refresh', methods=['POST'])
def refresh_examples():
    """Force refresh examples from GitHub and rebuild database."""
    global example_db
    try:
        payload = request.get_json(silent=True) or {}
        local_dir = payload.get('local_dir') or os.getenv('ALGORITHMS_LOCAL_DIR')
        fetcher = GitHubExampleFetcher(local_algorithms_dir=local_dir)
        examples = fetcher.get_examples(force_refresh=True)
        example_db = ExampleDatabase(examples)
        return jsonify({
            'success': True,
            'refreshed': len(examples),
            'categories': list(example_db.by_category.keys()),
            'source': 'local' if local_dir else 'github'
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    return jsonify({
        'multi_agent_enabled': MULTI_AGENT_ENABLED,
        'ai_provider': 'openai',
        'ai_model': 'gpt-4-turbo-preview',
        'examples_loaded': len(example_db.examples) if example_db else 0,
        'categories': list(example_db.by_category.keys()) if example_db else [],
        'api_key_configured': bool(OPENAI_KEY)
    }), 200


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print(" " * 15 + "ALGORITHM VISUALIZER API - GPT-4 VERSION")
    print("=" * 80)
    print("\n🚀 Server starting on http://localhost:5001")
    print("\n📍 Endpoints:")
    print("   GET  /health         - Health check")
    print("   POST /api/convert    - Convert with GPT-4 agents")
    print("   GET  /api/examples   - View examples")
    print("   GET  /api/stats      - System stats")

    print("\n🤖 AI Configuration:")
    print(f"   Provider: OpenAI GPT-4")
    print(f"   Status: {'✓ Enabled' if AI_CONFIG['enabled'] else '✗ Disabled'}")
    print(f"   Model: {AI_CONFIG['model']}")
    if MULTI_AGENT_ENABLED:
        print(f"   Examples: {len(example_db.examples) if example_db else 0}")
        print(f"   Agents: 3 (DataInit, Logging, Visualization)")

    print("\n💡 Chrome extension ready to connect")
    print("=" * 80 + "\n")

    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)