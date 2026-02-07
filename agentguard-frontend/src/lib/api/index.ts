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
export { getDashboardMetrics, getSlaMetrics, getDetectionEfficacy, getProviderComparison, getTimeSeries } from './dashboard';
export type { ProviderPerformance, ProviderComparisonData, TimeSeriesBucket, TimeSeriesData } from './dashboard';
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
export { updateOrgSettings, getDataResidency, updateDataResidency } from './organizations';
export type { DataResidencyConfig, DataResidencyResponse, RegionInfo } from './organizations';
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
export { listReviews, getReviewStats, decideReview, escalateReview } from './reviews';
export type { ReviewItem, ReviewFilters, ReviewStats } from './reviews';
export { listDiscoveries, getShadowAISummary, updateDiscoveryStatus } from './shadow-ai';
export type { ShadowAIDiscovery, ShadowAIFilters, ShadowAISummary } from './shadow-ai';
export { listConversations, getConversation, getConversationStats, updateConversationStatus } from './conversations';
export type { Conversation, ConversationDetail, ConversationTurn, ConversationFilters, ConversationStats } from './conversations';
export { listIndicators, getThreatSummary, createIndicator, updateIndicator, seedPlatformIndicators } from './threat-intel';
export type { ThreatIndicator, ThreatIndicatorFilters, ThreatSummary, IndicatorCreateData } from './threat-intel';
export { listTraces, getTrace } from './traces';
export type { TraceListItem, TraceDetail, TraceFilters } from './traces';
