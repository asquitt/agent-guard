{{/*
Common labels for all resources.
*/}}
{{- define "agentguard.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
environment: {{ .Values.global.environment }}
{{- end }}

{{/*
Selector labels for a specific component.
*/}}
{{- define "agentguard.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Full image reference for a component.
*/}}
{{- define "agentguard.image" -}}
{{- if .Values.global.imageRegistry -}}
{{ .Values.global.imageRegistry }}/{{ .repository }}:{{ .tag }}
{{- else -}}
{{ .repository }}:{{ .tag }}
{{- end -}}
{{- end }}
