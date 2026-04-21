import json
from nltosql.agent import run_agent

def main():
    print("Testing NL-to-SQL Agent...")
    question = "What are the top 5 most expensive products?"
    print(f"Question: {question}\n")
    
    result = run_agent(question)
    
    print(f"Success: {result['success']}")
    print(f"Attempts: {result['attempts']}")
    print(f"SQL: {result['sql']}")
    print(f"Error: {result['error']}")
    print("\nResults preview:")
    for row in result['data'][:5]:
        print(row)
    print("\nExplanation:")
    print(result['explanation'])
    print("\nAgent Log:")
    for doc in result['agent_log']:
        print(f"- [{doc['status']}] {doc['step']}: {doc['message']}")

if __name__ == '__main__':
    main()
