export type ExecutionStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export type Priority = 'low' | 'medium' | 'high' | 'critical';

export type TaskType =
  'security_analysis' | 'summarization' | 'classification' | 'code_review' | 'incident_triage';

export interface AgentExecution {
  id: string;
  agent_name: string;
  model: string;
  priority: Priority;
  task_type: TaskType;
  input_text: string;
  status: ExecutionStatus;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  cost: number | null;
  error_type: string | null;
  error_retryable: boolean | null;
}

export interface CreateExecutionRequest {
  agent_name: string;
  model: string;
  priority: Priority;
  task_type: TaskType;
  input_text: string;
}
export interface UpdateExecutionStatusRequest {
  status: ExecutionStatus;
  error_type?: string | null;
  error_retryable?: boolean | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  cost?: number | null;
}
