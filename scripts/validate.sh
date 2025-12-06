#!/bin/bash
# Validation script for Wingman project structure

set -e

echo "🔍 Validating Wingman Project Structure..."
echo ""

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Run this script from the project root directory"
    exit 1
fi

# Validate Python syntax
echo "📝 Validating Python files..."
find backend/app -name "*.py" -exec python3 -m py_compile {} \;
echo "✅ Python syntax valid"
echo ""

# Validate YAML syntax
echo "📝 Validating YAML files..."
python3 -c "import yaml; yaml.safe_load(open('docker-compose.yml'))"
echo "✅ YAML syntax valid"
echo ""

# Validate JSON files
echo "📝 Validating JSON files..."
python3 -c "import json; json.load(open('frontend/package.json'))"
python3 -c "import json; json.load(open('frontend/tsconfig.json'))"
echo "✅ JSON syntax valid"
echo ""

# Check required files
echo "📁 Checking required files..."
required_files=(
    "README.md"
    "docker-compose.yml"
    ".env.example"
    ".gitignore"
    "backend/requirements.txt"
    "backend/Dockerfile"
    "backend/app/main.py"
    "backend/app/slack_bot.py"
    "backend/app/rag.py"
    "backend/app/config.py"
    "backend/app/database.py"
    "backend/app/vector_store.py"
    "frontend/package.json"
    "frontend/Dockerfile"
    "frontend/tsconfig.json"
    "frontend/app/page.tsx"
    "docs/SETUP.md"
    "docs/SLACK_AUTH.md"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Missing: $file"
        exit 1
    fi
done
echo "✅ All required files present"
echo ""

# Check directory structure
echo "📁 Checking directory structure..."
required_dirs=(
    "backend"
    "backend/app"
    "backend/tests"
    "frontend"
    "frontend/app"
    "frontend/lib"
    "docs"
)

for dir in "${required_dirs[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "❌ Missing directory: $dir"
        exit 1
    fi
done
echo "✅ Directory structure valid"
echo ""

# Check .env.example has required variables
echo "🔑 Checking environment configuration..."
required_vars=(
    "SLACK_BOT_TOKEN"
    "SLACK_APP_TOKEN"
    "SLACK_SIGNING_SECRET"
    "OPENROUTER_API_KEY"
    "DATABASE_URL"
    "CHROMA_HOST"
)

for var in "${required_vars[@]}"; do
    if ! grep -q "^$var=" .env.example; then
        echo "❌ Missing environment variable in .env.example: $var"
        exit 1
    fi
done
echo "✅ Environment configuration valid"
echo ""

echo "✨ All validations passed!"
echo ""
echo "Next steps:"
echo "  1. Copy .env.example to .env and configure"
echo "  2. Run: docker-compose up -d"
echo "  3. Visit http://localhost:3000"
