import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { App } from './app';
import { AgentExecution } from './models/execution.model';

const API_URL = 'http://127.0.0.1:8000/executions';

function fakeExecution(overrides: Partial<AgentExecution> = {}): AgentExecution {
  return {
    id: crypto.randomUUID(),
    agent_name: 'recon-agent',
    model: 'claude-opus-5',
    priority: 'high',
    task_type: 'security_analysis',
    input_text: 'Scan the target scope.',
    status: 'pending',
    created_at: new Date().toISOString(),
    started_at: null,
    finished_at: null,
    input_tokens: null,
    output_tokens: null,
    cost: null,
    error_type: null,
    error_retryable: null,
    ...overrides,
  };
}

describe('App', () => {
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('requests the executions on init and renders the title', () => {
    const fixture = TestBed.createComponent(App);

    const req = httpMock.expectOne(API_URL);
    expect(req.request.method).toBe('GET');
    req.flush([]);

    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('h1')?.textContent).toContain('Tu equipo de agentes');
    expect(compiled.querySelector('.wordmark')?.textContent).toContain('AgentOps Observatory');
  });

  it('renders one card per loaded execution', () => {
    const fixture = TestBed.createComponent(App);

    httpMock
      .expectOne(API_URL)
      .flush([fakeExecution({ agent_name: 'first' }), fakeExecution({ agent_name: 'second' })]);

    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelectorAll('.agent').length).toBe(2);
  });
});
