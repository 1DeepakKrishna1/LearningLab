#!/usr/bin/env python3
"""A simple command-line to-do list with JSON persistence.

Usage:
    python todo.py add "Buy milk"
    python todo.py list
    python todo.py done 2
    python todo.py remove 2
    python todo.py clear
"""

import argparse
import json
from pathlib import Path

# Tasks are stored next to this script so they persist between runs.
DATA_FILE = Path(__file__).with_name("tasks.json")


def load_tasks():
    """Return the list of tasks, or an empty list if none exist yet."""
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return []


def save_tasks(tasks):
    """Write tasks back to disk as pretty-printed JSON."""
    DATA_FILE.write_text(json.dumps(tasks, indent=2))


def add(text):
    tasks = load_tasks()
    tasks.append({"text": text, "done": False})
    save_tasks(tasks)
    print(f"Added: {text}")


def show():
    tasks = load_tasks()
    if not tasks:
        print("No tasks yet. Add one with: python todo.py add \"...\"")
        return
    for i, task in enumerate(tasks, start=1):
        mark = "x" if task["done"] else " "
        print(f"{i:>2}. [{mark}] {task['text']}")


def done(index):
    tasks = load_tasks()
    if 1 <= index <= len(tasks):
        tasks[index - 1]["done"] = True
        save_tasks(tasks)
        print(f"Marked done: {tasks[index - 1]['text']}")
    else:
        print(f"No task at #{index}")


def remove(index):
    tasks = load_tasks()
    if 1 <= index <= len(tasks):
        removed = tasks.pop(index - 1)
        save_tasks(tasks)
        print(f"Removed: {removed['text']}")
    else:
        print(f"No task at #{index}")


def clear():
    save_tasks([])
    print("All tasks cleared.")


def main():
    parser = argparse.ArgumentParser(description="A simple CLI to-do list.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="add a new task")
    p_add.add_argument("text", help="task description")

    sub.add_parser("list", help="show all tasks")

    p_done = sub.add_parser("done", help="mark a task as done")
    p_done.add_argument("index", type=int, help="task number")

    p_remove = sub.add_parser("remove", help="delete a task")
    p_remove.add_argument("index", type=int, help="task number")

    sub.add_parser("clear", help="delete all tasks")

    args = parser.parse_args()

    if args.command == "add":
        add(args.text)
    elif args.command == "list":
        show()
    elif args.command == "done":
        done(args.index)
    elif args.command == "remove":
        remove(args.index)
    elif args.command == "clear":
        clear()


if __name__ == "__main__":
    main()
