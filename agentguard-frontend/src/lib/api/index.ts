/**
 * API module re-exports.
 */

export { apiFetch, ApiError, buildQueryString } from './client';
export {
  loginApi,
  verifyMfaLoginApi,
  setupMfaApi,
  confirmMfaSetupApi,
  disableMfaApi,
  registerApi,
  refreshTokenApi,
  getMeApi,
  logoutApi,
  forgotPasswordApi,
  resetPasswordApi,
  updateProfileApi,
} from './auth';
export type { RegisterInput, UserProfile } from './auth';
export { createWebSocketTicket } from './websocket';
export type { WebSocketTicket } from './websocket';
export {
  getBillingStatus,
  createCheckoutSession,
  createCustomerPortal,
} from './billing';
export { getCostAnalytics } from './cost-analytics';
export { getDashboardMetrics, getSlaMetrics, getDetectionEfficacy, getProviderComparison, getTimeSeries, getRiskScore } from './dashboard';
export type { ProviderPerformance, ProviderComparisonData, TimeSeriesBucket, TimeSeriesData, RiskScoreData, CategoryRisk, RiskTrendPoint } from './dashboard';
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
export {
  updateOrgSettings,
  getDataResidency,
  updateDataResidency,
  listMembers,
  listRoles,
  updateMemberRole,
  removeMember,
  inviteMember,
} from './organizations';
export type { DataResidencyConfig, DataResidencyResponse, RegionInfo, Member, MemberListResponse, RoleInfo, RolesResponse } from './organizations';
export {
  listAuditLogs,
  verifyAuditChain,
  createComplianceReport,
  listComplianceReports,
  downloadReport,
  getFrameworkScores,
  downloadCefExport,
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
export { listRedTeamRuns, getRedTeamRun, getRedTeamStats, createRedTeamRun, getTestCategories, getMultiTurnSequences, getMutationStrategies, generateMutations } from './red-team';
export type { RedTeamRun, RedTeamRunDetail, RedTeamFinding, RedTeamStats, RedTeamRunCreate, CategoriesResponse, MultiTurnSequenceInfo, MutationVariant } from './red-team';
export { listIndicators, getThreatSummary, createIndicator, updateIndicator, seedPlatformIndicators } from './threat-intel';
export type { ThreatIndicator, ThreatIndicatorFilters, ThreatSummary, IndicatorCreateData } from './threat-intel';
export { listTraces, getTrace } from './traces';
export type { TraceListItem, TraceDetail, TraceFilters } from './traces';
export {
  listSiemFormats,
  previewSiemFormat,
  listSiemDestinations,
  createSiemDestination,
  updateSiemDestination,
  deleteSiemDestination,
} from './siem';
export type { SiemFormat, SiemDestination, SiemDestinationCreate, SiemDestinationList, FormatPreview } from './siem';
export {
  listModels,
  getModel,
  getModelSummary,
  createModel,
  updateModel,
  deleteModel,
} from './model-registry';
export type { AIModel, AIModelListResponse, ModelSummary, AIModelCreate, AIModelFilters } from './model-registry';
export { getNotificationPreferences, updateNotificationPreferences } from './notifications';
export type { NotificationPreferences } from './notifications';
