import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { ExecutionService } from './execution.services';
import { CreateExecutionRequest } from '../models/execution.model';

const API_URL = 'http://127.0.0.1:8000/executions';

describe('ExecutionService', () => {
  let service: ExecutionService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ExecutionService, provideHttpClient(), provideHttpClientTesting()],
    });

    service = TestBed.inject(ExecutionService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('getAll issues a GET to the executions endpoint', () => {
    service.getAll().subscribe();

    const req = httpMock.expectOne(API_URL);
    expect(req.request.method).toBe('GET');
    req.flush([]);
  });

  it('create issues a POST carrying the payload', () => {
    const payload: CreateExecutionRequest = {
      agent_name: 'triage-agent',
      model: 'claude-sonnet-5',
      priority: 'medium',
      task_type: 'incident_triage',
      input_text: 'Triage the alert.',
    };

    service.create(payload).subscribe();

    const req = httpMock.expectOne(API_URL);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(payload);
    req.flush({});
  });

  it('updateStatus issues a PATCH to the status sub-resource', () => {
    service.updateStatus('exec-123', { status: 'running' }).subscribe();

    const req = httpMock.expectOne(`${API_URL}/exec-123/status`);
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ status: 'running' });
    req.flush({});
  });
});
