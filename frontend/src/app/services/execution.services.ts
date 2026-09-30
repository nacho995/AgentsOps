import { inject, Injectable } from '@angular/core';
  import { HttpClient } from '@angular/common/http';
  import { map } from 'rxjs';

  import {
    AgentExecution,
    CreateExecutionRequest,
    ExecutionDto,
    UpdateExecutionStatusRequest,
  } from '../models/execution.model';

  /** Turns the wire shape into the app shape: money arrives as a decimal string. */
  const toExecution = (dto: ExecutionDto): AgentExecution => ({
    ...dto,
    cost: dto.cost === null ? null : Number(dto.cost),
  });

  @Injectable({
    providedIn: 'root',
  })
  export class ExecutionService {
    private readonly http = inject(HttpClient);

    private readonly apiUrl = 'http://127.0.0.1:8000/executions';

    getAll() {
      return this.http
        .get<ExecutionDto[]>(this.apiUrl)
        .pipe(map((items) => items.map(toExecution)));
    }

    create(payload: CreateExecutionRequest) {
      return this.http.post<ExecutionDto>(this.apiUrl, payload).pipe(map(toExecution));
    }

    updateStatus(id: string, payload: UpdateExecutionStatusRequest) {
      return this.http
        .patch<ExecutionDto>(`${this.apiUrl}/${id}/status`, payload)
        .pipe(map(toExecution));
    }
  }
