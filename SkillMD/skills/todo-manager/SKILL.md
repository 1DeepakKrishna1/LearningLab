---
name: todo-manager
description: Manage a personal to-do list. Use this skill whenever the user wants to add, list, complete, or delete tasks, mentions a to-do list, task list, or wants to track tasks that persist between sessions.
entrypoint: scripts/todo.py
---

# Todo Manager

Manage a persistent command-line to-do list. Tasks are stored as JSON on disk.

## Subcommands

```bash
add "<text>"   # add a task
list           # show all tasks with numbers + status
done <n>       # mark task #n complete
remove <n>     # delete task #n
clear          # wipe the whole list
```
