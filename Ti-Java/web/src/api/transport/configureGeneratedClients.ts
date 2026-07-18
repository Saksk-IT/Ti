import { client as phase3AuthenticationClient } from '@/api/generated/phase3Authentication/client.gen';
import type { Client } from '@/api/generated/phase3Authentication/client';
import { client as phase4aPublicBankClient } from '@/api/generated/phase4aPublicBank/client.gen';
import { client as phase4aSubjectDirectoryClient } from '@/api/generated/phase4aSubjectDirectory/client.gen';

import { createRequestId, REQUEST_ID_HEADER } from './requestId';

const configuredClients = new WeakSet<object>();

function configureClient(client: Client): void {
  if (configuredClients.has(client)) {
    return;
  }

  client.setConfig({
    baseUrl: '',
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
    },
  });
  client.interceptors.request.use((request) => {
    if (request.headers.has(REQUEST_ID_HEADER)) {
      return request;
    }

    const headers = new Headers(request.headers);
    headers.set(REQUEST_ID_HEADER, createRequestId());
    return new Request(request, { headers });
  });
  configuredClients.add(client);
}

export function configureGeneratedClients(): void {
  configureClient(phase3AuthenticationClient);
  configureClient(phase4aSubjectDirectoryClient);
  configureClient(phase4aPublicBankClient);
}
