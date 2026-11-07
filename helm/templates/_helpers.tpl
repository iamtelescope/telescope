{{/*
App name - supports nameOverride
*/}}
{{- define "telescope.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Full name - supports fullnameOverride 
*/}}
{{- define "telescope.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name (include "telescope.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "telescope.labels" -}}
app.kubernetes.io/name: {{ include "telescope.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}



{{/*
The alert scheduler container: its own Deployment, or a sidecar of the web pod on SQLite.
*/}}
{{- define "telescope.schedulerContainer" -}}
- name: scheduler
  image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
  imagePullPolicy: {{ .Values.image.pullPolicy }}
  args: ["scheduler"]
  env:
    - name: TELESCOPE_CONFIG_FILE
      value: "/etc/telescope/config.yaml"
  envFrom:
    - secretRef:
        name: {{ .Values.secretName }}
  volumeMounts:
    - name: config
      mountPath: /etc/telescope
      readOnly: true
    {{- if eq .Values.database.type "sqlite" }}
    - name: sqlite-data
      mountPath: /app/data
    {{- end }}
  resources:
    {{- toYaml .Values.scheduler.resources | nindent 4 }}
  securityContext:
    allowPrivilegeEscalation: false
{{- end }}
