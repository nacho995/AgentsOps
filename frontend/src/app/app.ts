import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import {
  AgentExecution,
  CreateExecutionRequest,
  ExecutionStatus,
  Priority,
  TaskType,
  UpdateExecutionStatusRequest,
} from './models/execution.model';
import { ExecutionService } from './services/execution.services';

/** Warm, human status words shown to the person watching their agents. */
const STATUS_LABELS: Record<ExecutionStatus, string> = {
  pending: 'En cola',
  running: 'Trabajando',
  completed: 'Completada',
  failed: 'Falló',
  cancelled: 'Cancelada',
};

const PRIORITY_LABELS: Record<Priority, string> = {
  low: 'Baja',
  medium: 'Media',
  high: 'Alta',
  critical: 'Crítica',
};

const TASK_TYPE_LABELS: Record<TaskType, string> = {
  security_analysis: 'Análisis de seguridad',
  summarization: 'Resumen',
  classification: 'Clasificación',
  code_review: 'Revisión de código',
  incident_triage: 'Triaje de incidente',
};

@Component({
  selector: 'app-root',
  imports: [ReactiveFormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  private readonly executionService = inject(ExecutionService);
  private readonly formBuilder = inject(FormBuilder);

  protected readonly executions = signal<AgentExecution[]>([]);
  protected readonly loading = signal(true);
  protected readonly submitting = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly executionForm = this.formBuilder.nonNullable.group({
    agent_name: ['', [Validators.required, Validators.maxLength(100)]],
    model: ['', [Validators.required, Validators.maxLength(100)]],
    priority: ['medium' as Priority, Validators.required],
    task_type: ['security_analysis' as TaskType, Validators.required],
    input_text: ['', [Validators.required, Validators.maxLength(10_000)]],
  });

  // --- Fleet metrics (derived from the executions signal) -----------------
  protected readonly totalExecutions = computed(() => this.executions().length);
  protected readonly runningExecutions = computed(() => this.countByStatus('running'));
  protected readonly completedExecutions = computed(() => this.countByStatus('completed'));
  protected readonly failedExecutions = computed(() => this.countByStatus('failed'));

  protected readonly totalCost = computed(() =>
    this.executions().reduce((total, execution) => total + (execution.cost ?? 0), 0),
  );

  /** One warm sentence summarising what the team is doing right now. */
  protected readonly summary = computed(() => {
    const running = this.runningExecutions();
    const opener =
      running === 0
        ? 'Todo tranquilo: ningún agente trabajando ahora mismo.'
        : running === 1
          ? 'Hay 1 agente trabajando ahora mismo.'
          : `Hay ${running} agentes trabajando ahora mismo.`;

    return `${opener} Hoy van ${this.completedExecutions()} completadas y ${this.eur(
      this.totalCost(),
    )} € gastados.`;
  });

  constructor() {
    this.loadExecutions();
  }

  protected refreshExecutions(): void {
    this.loading.set(true);
    this.error.set(null);
    this.loadExecutions();
  }

  protected createExecution(): void {
    if (this.executionForm.invalid) {
      this.executionForm.markAllAsTouched();
      return;
    }

    const payload = this.executionForm.getRawValue() as CreateExecutionRequest;
    this.submitting.set(true);

    this.executionService.create(payload).subscribe({
      next: (execution) => {
        this.executions.update((current) => [execution, ...current]);
        this.executionForm.reset({
          agent_name: '',
          model: '',
          priority: 'medium',
          task_type: 'security_analysis',
          input_text: '',
        });
        this.submitting.set(false);
      },
      error: () => {
        this.error.set('No pudimos encargar la tarea. Revisa que el backend esté en marcha.');
        this.submitting.set(false);
      },
    });
  }

  protected changeStatus(execution: AgentExecution, nextStatus: ExecutionStatus): void {
    const payload: UpdateExecutionStatusRequest = { status: nextStatus };

    if (nextStatus === 'completed') {
      // No real agent runs behind this demo, so we attach lifelike metering
      // to keep the cost/token figures meaningful.
      Object.assign(payload, this.simulatedMetering());
    }

    if (nextStatus === 'failed') {
      payload.error_type = 'manual_failure';
      payload.error_retryable = false;
    }

    this.executionService.updateStatus(execution.id, payload).subscribe({
      next: (updatedExecution) => {
        this.executions.update((current) =>
          current.map((item) => (item.id === updatedExecution.id ? updatedExecution : item)),
        );
      },
      error: () => {
        this.error.set('No pudimos actualizar el estado. Inténtalo de nuevo.');
      },
    });
  }

  // --- Template helpers ---------------------------------------------------
  protected statusLabel(status: ExecutionStatus): string {
    return STATUS_LABELS[status];
  }

  protected priorityLabel(priority: Priority): string {
    return PRIORITY_LABELS[priority];
  }

  protected taskTypeLabel(taskType: TaskType): string {
    return TASK_TYPE_LABELS[taskType];
  }

  /** First letter of the agent name, for the avatar. */
  protected agentInitial(name: string): string {
    return (name.trim()[0] ?? '?').toUpperCase();
  }

  protected fmtTokens(value: number): string {
    return value.toLocaleString('es-ES');
  }

  protected eur(value: number): string {
    return value.toLocaleString('es-ES', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  /** Per-run cost, with enough decimals that a cheap run is not shown as 0. */
  protected eurPrecise(value: number): string {
    return value.toLocaleString('es-ES', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,
    });
  }

  /** Human "hace 4 min" style stamp from an ISO date. */
  protected relativeTime(iso: string): string {
    const seconds = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));

    if (seconds < 45) {
      return 'justo ahora';
    }
    if (seconds < 3600) {
      return `hace ${Math.round(seconds / 60)} min`;
    }
    if (seconds < 86_400) {
      const hours = Math.round(seconds / 3600);
      return `hace ${hours} ${hours === 1 ? 'hora' : 'horas'}`;
    }
    const days = Math.round(seconds / 86_400);
    return `hace ${days} ${days === 1 ? 'día' : 'días'}`;
  }

  /** One warm line describing how a finished run went, or null if still open. */
  protected outcome(execution: AgentExecution): string | null {
    const took = this.duration(execution);

    if (execution.status === 'completed') {
      const cost = execution.cost !== null ? ` y gastó ${this.eurPrecise(execution.cost)} €` : '';
      return took ? `Terminó en ${took}${cost}` : `Terminó${cost}`;
    }

    if (execution.status === 'failed') {
      const reason = execution.error_type ? ` por ${execution.error_type}` : '';
      return took ? `Se detuvo tras ${took}${reason}` : `Se detuvo${reason}`;
    }

    return null;
  }

  private duration(execution: AgentExecution): string | null {
    if (!execution.started_at || !execution.finished_at) {
      return null;
    }

    const seconds = Math.max(
      0,
      Math.round(
        (new Date(execution.finished_at).getTime() - new Date(execution.started_at).getTime()) /
          1000,
      ),
    );

    if (seconds < 60) {
      return `${seconds} s`;
    }

    const minutes = Math.floor(seconds / 60);
    return `${minutes} min ${seconds % 60} s`;
  }

  private countByStatus(status: ExecutionStatus): number {
    return this.executions().filter((execution) => execution.status === status).length;
  }

  private simulatedMetering(): Pick<
    UpdateExecutionStatusRequest,
    'input_tokens' | 'output_tokens' | 'cost'
  > {
    const inputTokens = 500 + Math.floor(Math.random() * 8_000);
    const outputTokens = 100 + Math.floor(Math.random() * 2_000);
    // Blended ~$0.000012/token, only to produce a believable demo figure.
    const cost = Number(((inputTokens + outputTokens) * 0.000012).toFixed(6));

    return {
      input_tokens: inputTokens,
      output_tokens: outputTokens,
      cost,
    };
  }

  private loadExecutions(): void {
    this.executionService.getAll().subscribe({
      next: (executions) => {
        this.executions.set(executions);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No pudimos cargar las ejecuciones. Revisa que el backend esté en marcha.');
        this.loading.set(false);
      },
    });
  }
}
