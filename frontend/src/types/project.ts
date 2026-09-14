export interface Project {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
  revision: number;
  created_at: string;
  updated_at: string;
  role?: string;
  tasks_count?: number;
}

export interface Task {
  id: string;
  project_id: string;
  title: string;
  description?: string;
  status: "TODO" | "IN_PROGRESS" | "DONE" | string;
  priority: "LOW" | "MEDIUM" | "HIGH" | "URGENT" | string;
  assignee_id?: string;
  due_date?: string;
  tags: string[];
  version: number;
  is_deleted: boolean;
  created_by?: string;
  last_modified_by?: string;
  created_at: string;
  updated_at: string;
}

export interface Activity {
  id: string;
  project_id: string;
  user_id?: string;
  action_type: string;
  entity_id: string;
  metadata?: any;
  created_at: string;
}

export interface TaskComment {
  id: string;
  task_id: string;
  user_id: string;
  content: string;
  created_at: string;
}
