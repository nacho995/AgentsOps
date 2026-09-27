import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import {
  AgentExecution,
  CreateExecutionRequest,
  UpdateExecutionStatusRequest,
} from '../models/execution.model';

@Injectable({
  providedIn: 'root',
})
export class ExecutionService {
  private readonly http = inject(HttpClient);

  private readonly apiUrl = 'http://127.0.0.1:8000/executions';

  getAll() {
    return this.http.get<AgentExecution[]>(this.apiUrl);
  }

  create(payload: CreateExecutionRequest) {
    return this.http.post<AgentExecution>(this.apiUrl, payload);
  }
  updateStatus(id: string, payload: UpdateExecutionStatusRequest) {
    return this.http.patch<AgentExecution>(`${this.apiUrl}/${id}/status`, payload);
  }
}
