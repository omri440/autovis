#!/bin/bash

# Setup script for GPT-4 Multi-Agent Polisher

echo "========================================"
echo "GPT-4 Multi-Agent Polisher Setup"
echo "========================================"
echo ""

# 1. Check Python
echo "[1/6] Checking Python..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python $python_version"
echo ""

# 2. Install dependencies
echo "[2/6] Installing dependencies..."
pip install openai requests flask flask-cors python-dotenv
echo "✓ Dependencies installed"
echo ""

# 3. Check for OpenAI API key
echo "[3/6] Checking OpenAI API key..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo "✗ OPENAI_API_KEY not set"
    echo ""
    echo "Please set your OpenAI API key:"
    echo "  export OPENAI_API_KEY='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'"
    echo ""
    echo "Get your API key from:"
    echo "  https://platform.openai.com/api-keys"
    echo ""
    echo "GPT-4 Pricing (as of 2024):"
    echo "  Input:  ~\$0.01 per 1K tokens"
    echo "  Output: ~\$0.03 per 1K tokens"
    echo "  Cost per conversion: ~\$0.02-0.05"
    echo ""
    exit 1
else
    key_preview="${OPENAI_API_KEY:0:10}...${OPENAI_API_KEY: -4}"
    echo "✓ API key configured: $key_preview"
fi
echo ""

# 4. Fetch examples
echo "[4/6] Fetching Algorithm Visualizer examples..."
python3 fetch_algo_examples.py
if [ $? -eq 0 ]; then
    echo "✓ Examples cached successfully"
else
    echo "⚠  Failed to fetch (will use hardcoded examples)"
fi
echo ""

# 5. Test GPT-4 connection
echo "[5/6] Testing GPT-4 connection..."
cat > test_openai.py << 'EOF'
import os
from openai import OpenAI

api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("✗ No API key")
    exit(1)

try:
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[{"role": "user", "content": "Say OK"}],
        max_tokens=5
    )
    result = response.choices[0].message.content.strip()
    print(f"✓ GPT-4 connection successful")
    print(f"  Response: {result}")
except Exception as e:
    print(f"✗ GPT-4 connection failed: {e}")
    exit(1)
EOF

python3 test_openai.py
test_result=$?
rm test_openai.py

if [ $test_result -ne 0 ]; then
    echo ""
    echo "⚠  GPT-4 test failed. Please check:"
    echo "   1. API key is valid"
    echo "   2. You have GPT-4 access"
    echo "   3. You have billing set up"
    exit 1
fi
echo ""

# 6. Test multi-agent
echo "[6/6] Testing multi-agent system..."
cat > test_agents.py << 'EOF'
from multi_agent_polisher_openai import polish_with_multi_agent

test_js = """const { Array1DTracer, Tracer, Layout, LogTracer, Randomize, VerticalLayout } = require('algorithm-visualizer');

const arrTracer = new Array1DTracer('Array');
const logger = new LogTracer('Console');
Layout.setRoot(new VerticalLayout([arrTracer, logger]));

const arr = Randomize.Array1D({ N: 8 });
arrTracer.set(arr);
Tracer.delay();

function sort(array) {
  for (let i = 0; i < array.length; i++) {
    for (let j = i + 1; j < array.length; j++) {
      if (array[i] > array[j]) {
        [array[i], array[j]] = [array[j], array[i]];
      }
    }
  }
}

sort(arr);"""

test_analysis = {
    'vars_1d': ['arr'],
    'viz_type': 'sorting',
    'has_sorting': True
}

print("Testing multi-agent with GPT-4...")
result = polish_with_multi_agent(test_js, "def sort(arr): pass", test_analysis)

if result['was_polished']:
    print("✓ Multi-agent test PASSED")
    print(f"  Provider: {result.get('provider')}")
    agents = result.get('agent_results', [])
    print(f"  Agents: {len(agents)}")
    for agent_result in agents:
        name = agent_result['agent']
        changed = agent_result['metadata'].get('changed', False)
        status = "✓" if changed else "-"
        print(f"    {status} {name}")
else:
    print("✗ Multi-agent test FAILED")
    print(f"  Error: {result.get('error')}")
    exit(1)
EOF

python3 test_agents.py
test_result=$?
rm test_agents.py

if [ $test_result -ne 0 ]; then
    echo ""
    echo "⚠  Multi-agent test failed"
    echo "   Check the error above"
    exit 1
fi
echo ""

# Success!
echo "========================================"
echo "✓ Setup Complete!"
echo "========================================"
echo ""
echo "Next Steps:"
echo ""
echo "1. Start the API server:"
echo "   python3 api_server_gpt4.py"
echo ""
echo "2. Server will be available at:"
echo "   http://localhost:5001"
echo ""
echo "3. Test with curl:"
echo "   curl -X POST http://localhost:5001/api/convert \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"code\": \"def sort(arr): pass\", \"enable_polish\": true}'"
echo ""
echo "4. Or use the Chrome extension"
echo ""
echo "========================================"
echo "GPT-4 Multi-Agent Configuration"
echo "========================================"
echo ""
echo "Provider: OpenAI GPT-4 Turbo"
echo "Model:    gpt-4-turbo-preview"
echo "Agents:   3 specialized agents"
echo "  1. DataInit      - Smart test data"
echo "  2. Logging       - Educational messages"
echo "  3. Visualization - Tracer optimization"
echo ""
echo "Cost Estimate:"
echo "  Per conversion: \$0.02 - \$0.05"
echo "  Per 100 conversions: ~\$2 - \$5"
echo ""
echo "Performance:"
echo "  Speed: ~20-30 seconds per conversion"
echo "  Success rate: ~85%"
echo ""
echo "========================================"