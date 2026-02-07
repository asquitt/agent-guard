/**
 * API module re-exports.
 */

export { apiFetch, ApiError, buildQueryString } from './client';
export {
  loginApi,
  registerApi,
  refreshTokenApi,
  getMeApi,
  logoutApi,
} from './auth';
export {
  getBillingStatus,
  createCheckoutSession,
  createCustomerPortal,
} from './billing';
export { getCostAnalytics } from './cost-analytics';
export { getDashboardMetrics, getSlaMetrics, getDetectionEfficacy, getProviderComparison } from './dashboard';
export type { ProviderPerformance, ProviderComparisonData } from './dashboard';
export {
  listIncidents,
  getIncident,
  updateIncidentStatus,
  addIncidentAction,
  bulkUpdateStatus,
} from './incidents';
export {
  listDetectors,
  getDetector,
  createDetector,
  updateDetector,
  deleteDetector,
} from './detectors';
export { listApiKeys, createApiKey, revokeApiKey } from './api-keys';
export {
  listDestinations,
  createDestination,
  updateDestination,
  deleteDestination,
  testDestination,
  listAlerts,
} from './alerts';
export { createProxyEndpoint } from './proxy-endpoints';
export { updateOrgSettings } from './organizations';
export {
  listAuditLogs,
  verifyAuditChain,
  createComplianceReport,
  listComplianceReports,
  getReportDownloadUrl,
  getFrameworkScores,
  getCefExportUrl,
} from './compliance';
export {
  getRetentionPolicy,
  updateRetentionPolicy,
  listArchives,
  retrieveArchive,
} from './retention';
export { testDetectors, getPlaygroundCategories } from './playground';
export {
  listAgents,
  getAgent,
  createAgent,
  updateAgent,
  deleteAgent,
} from './agents';
export type { AgentData, AgentFilters } from './agents';
export {
  listPolicies,
  getPolicy,
  createPolicy,
  updatePolicy,
  deletePolicy,
  listPolicyTemplates,
} from './agent-policies';
export type { AgentPolicy, PolicyCreateData, PolicyTemplate } from './agent-policies';
export { listTraces, getTrace } from './traces';
export type { TraceListItem, TraceDetail, TraceFilters } from './traces';
