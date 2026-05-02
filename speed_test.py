"""Quick speed test for the optimised agent."""
import time
from nltosql.agent import run_agent

start = time.time()
result = run_agent("Show me the top 5 most expensive products")
elapsed = round(time.time() - start, 1)

print(f"Total time: {elapsed}s")
print(f"Success: {result['success']}")
print(f"Attempts: {result['attempts']}")
print(f"SQL: {result['sql']}")
print(f"Rows: {len(result['data'])}")
if result["data"]:
    for row in result["data"][:5]:
        print(f"  {row}")
if result.get("error"):
    print(f"Error: {result['error']}")
print()
print("--- Agent Log ---")
for step in result["agent_log"]:
    print(f"  [{step['status']}] {step['message']}")
