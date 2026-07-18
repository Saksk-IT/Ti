import type {
  SecurityRateLimitErrorEnvelope as P4aPublicBankRateLimitEnvelope,
  SecurityUnavailableErrorEnvelope as P4aPublicBankUnavailableEnvelope,
} from '@/api/generated/phase4aPublicBank/types.gen';
import type {
  SecurityRateLimitErrorEnvelope as P4aSubjectRateLimitEnvelope,
  SecurityUnavailableErrorEnvelope as P4aSubjectUnavailableEnvelope,
} from '@/api/generated/phase4aSubjectDirectory/types.gen';

// These aliases intentionally remain source-qualified. The contracts share names,
// but their header, security and source-relative reference semantics are distinct.
export type P4aPublicBankSecurityRateLimitError = P4aPublicBankRateLimitEnvelope;
export type P4aPublicBankSecurityUnavailableError = P4aPublicBankUnavailableEnvelope;
export type P4aSubjectSecurityRateLimitError = P4aSubjectRateLimitEnvelope;
export type P4aSubjectSecurityUnavailableError = P4aSubjectUnavailableEnvelope;
