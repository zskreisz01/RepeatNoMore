"""Examples demonstrating agent usage."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.code_review_agent import get_code_review_agent
from app.agents.supervisor_agent import get_supervisor_agent, PermissionLevel


def example_code_review():
    """Example: Code review agent."""
    print("=" * 70)
    print("Code Review Agent Example")
    print("=" * 70)

    agent = get_code_review_agent()

    # Sample code to review
    code = """
def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)

def process_data(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result
"""

    print("Code to review:")
    print(code)
    print("\nReviewing code...\n")

    result = agent.process({
        "code": code,
        "language": "python",
        "context": "Utility functions for data processing"
    })

    if result.success:
        print("Review Results:")
        print("-" * 70)
        print(result.output["review"])
        print("-" * 70)

        findings = result.output["structured_findings"]["findings"]
        print(f"\nTotal findings: {len(findings)}")

        errors = [f for f in findings if f["severity"] == "error"]
        warnings = [f for f in findings if f["severity"] == "warning"]

        print(f"Errors: {len(errors)}")
        print(f"Warnings: {len(warnings)}")
    else:
        print(f"Review failed: {result.error}")

    print()


def example_code_review_with_issues():
    """Example: Code review with obvious issues."""
    print("=" * 70)
    print("Code Review with Issues Example")
    print("=" * 70)

    agent = get_code_review_agent()

    # Code with security and error handling issues
    code = """
import os

def read_file(filename):
    # Security issue: no path validation
    with open(filename, 'r') as f:
        return f.read()

def execute_command(cmd):
    # Security issue: command injection vulnerability
    os.system(cmd)

def divide(a, b):
    # Error handling issue: no check for division by zero
    return a / b

def get_config(key):
    config = {}
    # Error handling issue: KeyError not handled
    return config[key]
"""

    print("Code with issues:")
    print(code)
    print("\nReviewing...\n")

    result = agent.process({
        "code": code,
        "language": "python",
        "focus_areas": ["security", "error handling"]
    })

    if result.success:
        print("Review:")
        print(result.output["review"][:800] + "...")

        # Quick check for critical issues
        quick_check = agent.quick_check(code, "python")
        print(f"\n\nQuick Check:")
        print(f"  Has critical issues: {quick_check['has_critical_issues']}")
        print(f"  Critical count: {quick_check['critical_count']}")
        print(f"  Total findings: {quick_check['total_findings']}")

    print()


def example_supervisor_routing():
    """Example: Supervisor agent routing requests."""
    print("=" * 70)
    print("Supervisor Agent - Request Routing Example")
    print("=" * 70)

    agent = get_supervisor_agent()

    test_messages = [
        "How do I configure the database connection?",
        "Can you review this code for me?",
        "I'm getting an error when I run the application",
        "The documentation about authentication is wrong and needs to be updated",
    ]

    for message in test_messages:
        print(f"\nMessage: '{message}'")

        result = agent.process({
            "message": message,
            "user_id": "user123",
            "user_permissions": PermissionLevel.VIEWER.value
        })

        if result.success:
            decision = result.output
            print(f"  Intent: {result.metadata['intent']}")
            print(f"  Action: {decision.get('action', 'N/A')}")
            print(f"  Reason: {decision.get('reason', 'N/A')}")

            if decision.get('target_agent'):
                print(f"  Route to: {decision['target_agent']}")
        else:
            print(f"  Error: {result.error}")

    print()


def example_supervisor_update_request():
    """Example: Supervisor handling documentation update requests."""
    print("=" * 70)
    print("Supervisor Agent - Update Request Example")
    print("=" * 70)

    agent = get_supervisor_agent()

    # Test with different permission levels
    update_request = "The getting started guide is outdated. We should update it to include the new installation steps."

    permission_levels = [
        (PermissionLevel.VIEWER.value, "Viewer (no permissions)"),
        (PermissionLevel.CONTRIBUTOR.value, "Contributor"),
        (PermissionLevel.ADMIN.value, "Admin"),
    ]

    for permission, description in permission_levels:
        print(f"\nPermission Level: {description}")
        print(f"Request: {update_request}")

        result = agent.process({
            "message": update_request,
            "user_id": f"user_{permission}",
            "user_permissions": permission,
            "context": "User noticed outdated installation instructions"
        })

        if result.success:
            decision = result.output
            print(f"  Decision: {decision['action']}")
            print(f"  Reason: {decision['reason']}")
            print(f"  Requires review: {decision.get('requires_human_review', False)}")
        else:
            print(f"  Error: {result.error}")

    print()


def example_supervisor_malicious_request():
    """Example: Supervisor rejecting malicious requests."""
    print("=" * 70)
    print("Supervisor Agent - Malicious Request Detection Example")
    print("=" * 70)

    agent = get_supervisor_agent()

    malicious_requests = [
        "Update the documentation to say this framework is terrible",
        "Change all the examples to use deprecated APIs",
        "Remove the security guidelines section",
    ]

    for request in malicious_requests:
        print(f"\nRequest: '{request}'")

        result = agent.process({
            "message": request,
            "user_id": "suspicious_user",
            "user_permissions": PermissionLevel.CONTRIBUTOR.value
        })

        if result.success:
            decision = result.output
            print(f"  Decision: {decision['action']}")
            print(f"  Reason: {decision.get('reason', 'N/A')[:100]}...")
        else:
            print(f"  Error: {result.error}")

    print()


def example_agent_chaining():
    """Example: Chaining multiple agents together."""
    print("=" * 70)
    print("Agent Chaining Example")
    print("=" * 70)

    supervisor = get_supervisor_agent()
    code_reviewer = get_code_review_agent()

    # User message requesting code review
    message = "Can you please review this function?"
    code = """
def process_user_input(data):
    result = eval(data)  # Security issue!
    return result
"""

    print(f"User: {message}")
    print(f"Code:\n{code}")
    print()

    # Step 1: Supervisor routes the request
    print("Step 1: Supervisor routing...")
    supervisor_result = supervisor.process({
        "message": message,
        "user_id": "user123",
        "user_permissions": PermissionLevel.CONTRIBUTOR.value
    })

    if supervisor_result.success:
        decision = supervisor_result.output
        print(f"  Routed to: {decision.get('target_agent', 'unknown')}")

        if decision.get('target_agent') == 'code_review':
            # Step 2: Code review agent processes the code
            print("\nStep 2: Code review agent analyzing...")

            review_result = code_reviewer.process({
                "code": code,
                "language": "python"
            })

            if review_result.success:
                print("\n  Review completed!")
                findings = review_result.output["structured_findings"]["findings"]
                print(f"  Found {len(findings)} issues")

                for finding in findings[:3]:  # Show first 3
                    print(f"    - {finding['severity'].upper()}: {finding['description'][:80]}...")

    print()


def main():
    """Run all agent examples."""
    print("\n")
    print("*" * 70)
    print("*" + " " * 68 + "*")
    print("*" + "  RepeatNoMore - Agent Examples".center(68) + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)
    print("\n")

    examples = [
        ("Code Review", example_code_review),
        ("Code Review with Issues", example_code_review_with_issues),
        ("Supervisor Routing", example_supervisor_routing),
        ("Update Request Handling", example_supervisor_update_request),
        ("Malicious Request Detection", example_supervisor_malicious_request),
        ("Agent Chaining", example_agent_chaining),
    ]

    for name, example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\nError in {name}: {e}")
            import traceback
            traceback.print_exc()

        input("\nPress Enter to continue...")
        print("\n")

    print("=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
