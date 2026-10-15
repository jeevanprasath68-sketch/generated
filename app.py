class Task:
    def __init__(self, task_id: int, title: str, priority: int = 1):
        self.task_id = task_id
        self.title = title
        self.priority = priority
        self.completed = False

class TaskManager:
    def __init__(self):
        self.tasks = {}

    def add_task(self, title: str, priority: int = 1) -> Task:
        task_id = len(self.tasks) + 1
        task = Task(task_id, title, priority)
        self.tasks[task_id] = task
        return task

    def complete_task(self, task_id: int) -> bool:
        if task_id in self.tasks:
            self.tasks[task_id].completed = True
            return True
        return False

    def get_pending_tasks(self):
        # Fixed: now correctly sorts highest priority first
        pending = [t for t in self.tasks.values() if not t.completed]
        return sorted(pending, key=lambda x: x.priority, reverse=True)