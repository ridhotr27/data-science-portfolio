#!/usr/bin/env bash
set -euo pipefail

base_url="${BASE_URL:-http://localhost:8088}"
test_dir="$(mktemp -d)"
eda_id=""
customer_id=""

cleanup() {
  if [[ -n "$eda_id" ]]; then
    curl --silent --output /dev/null --request DELETE "$base_url/api/datasets/$eda_id" || true
  fi
  if [[ -n "$customer_id" ]]; then
    curl --silent --output /dev/null --request DELETE "$base_url/api/datasets/$customer_id" || true
  fi
  rm -rf "$test_dir"
}
trap cleanup EXIT

expect_status() {
  local expected="$1"
  local actual="$2"
  local label="$3"
  if [[ "$actual" != "$expected" ]]; then
    echo "FAIL: $label returned HTTP $actual (expected $expected)" >&2
    exit 1
  fi
  echo "PASS: $label"
}

cat > "$test_dir/eda.csv" <<'CSV'
id,amount,date,category
1,10,2026-01-01,A
2,20,2026-01-02,B
3,,bad,A
4,40,2026-01-04,B
CSV

cat > "$test_dir/customers.csv" <<'CSV'
customer_id,order_id,date,sales,category
C1,O1,2025-01-01,10,A
C1,O2,2025-02-01,20,B
C2,O3,2025-01-05,30,A
C2,O4,2025-03-05,40,B
CSV

root_status="$(curl --silent --show-error --output "$test_dir/root.html" --write-out '%{http_code}' "$base_url/")"
expect_status 200 "$root_status" "frontend root"
grep -q '<div id="root"></div>' "$test_dir/root.html"

spa_status="$(curl --silent --show-error --output "$test_dir/spa.html" --write-out '%{http_code}' "$base_url/projects/exploratory-data-analysis")"
expect_status 200 "$spa_status" "React SPA route"
cmp -s "$test_dir/root.html" "$test_dir/spa.html"

health_status="$(curl --silent --show-error --output "$test_dir/health.json" --write-out '%{http_code}' "$base_url/api/health")"
expect_status 200 "$health_status" "proxied FastAPI health"
python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["status"] == "ok"' "$test_dir/health.json"

eda_upload_status="$(curl --silent --show-error --output "$test_dir/eda-upload.json" --write-out '%{http_code}' --form "file=@$test_dir/eda.csv;type=text/csv" "$base_url/api/datasets/upload")"
expect_status 200 "$eda_upload_status" "EDA dataset upload through Caddy"
eda_id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["dataset_id"])' "$test_dir/eda-upload.json")"
eda_status="$(curl --silent --show-error --output "$test_dir/eda-profile.json" --write-out '%{http_code}' --header 'Content-Type: application/json' --data '{"overrides":{"date":"date"}}' "$base_url/api/eda/$eda_id/profile")"
expect_status 200 "$eda_status" "EDA profile"
python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); assert len(p["profiles"]) == 4' "$test_dir/eda-profile.json"

customer_upload_status="$(curl --silent --show-error --output "$test_dir/customer-upload.json" --write-out '%{http_code}' --form "file=@$test_dir/customers.csv;type=text/csv" "$base_url/api/datasets/upload")"
expect_status 200 "$customer_upload_status" "Customer 360 dataset upload through Caddy"
customer_id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["dataset_id"])' "$test_dir/customer-upload.json")"
mapping='{"customer_id":"customer_id","transaction_id":"order_id","transaction_date":"date","revenue":"sales","category":"category","attributes":[],"currency":"IDR"}'
configure_status="$(curl --silent --show-error --output "$test_dir/configure.json" --write-out '%{http_code}' --header 'Content-Type: application/json' --data "$mapping" "$base_url/api/customer-360/$customer_id/configure")"
expect_status 200 "$configure_status" "Customer 360 configuration"
overview_status="$(curl --silent --show-error --output "$test_dir/customer-overview.json" --write-out '%{http_code}' --header 'Content-Type: application/json' --data '{"filters":{}}' "$base_url/api/customer-360/$customer_id/overview")"
expect_status 200 "$overview_status" "Customer 360 overview"
python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["summary"]["customers"] == 2' "$test_dir/customer-overview.json"

xgboost_status="$(curl --silent --show-error --output "$test_dir/xgboost.json" --write-out '%{http_code}' --form "file=@$test_dir/eda.csv;type=text/csv" "$base_url/api/ml/upload")"
expect_status 503 "$xgboost_status" "disabled XGBoost endpoint"

dd if=/dev/zero of="$test_dir/oversized.csv" bs=1m count=7 2>/dev/null
oversized_status="$(curl --silent --show-error --output "$test_dir/oversized.json" --write-out '%{http_code}' --form "file=@$test_dir/oversized.csv;type=text/csv" "$base_url/api/datasets/upload")"
expect_status 413 "$oversized_status" "reverse-proxy request-body limit"

echo "All local Docker integration checks passed."
