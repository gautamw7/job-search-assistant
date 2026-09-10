#!/usr/bin/env bash
set -e
NAME=${1:?Usage: scaffold-feature.sh <feature-name>}
BASE="frontend/src/features/$NAME"
mkdir -p "$BASE/components" "$BASE/hooks"
cat > "$BASE/$NAME.tsx" << EOF
export function ${NAME^}Page() {
  return <div className="p-6 text-slate-200">${NAME} feature - scaffolded</div>;
}
EOF
cat > "$BASE/README.md" << EOF
# Feature: $NAME
Keep this feature <250 LOC. Do not import from other features.
EOF
echo "Scaffolded $BASE"
