{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "cell0.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "cell0.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "cell0.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "cell0.labels" -}}
helm.sh/chart: {{ include "cell0.chart" . }}
{{ include "cell0.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "cell0.selectorLabels" -}}
app.kubernetes.io/name: {{ include "cell0.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Create the name of the service account to use
*/}}
{{- define "cell0.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
    {{ default (include "cell0.fullname" .) .Values.serviceAccount.name }}
{{- else -}}
    {{ default "default" .Values.serviceAccount.name }}
{{- end -}}
{{- end -}}

{{/*
Create the name of the secret to use
*/}}
{{- define "cell0.secretName" -}}
{{- if .Values.existingSecret -}}
{{- .Values.existingSecret -}}
{{- else -}}
{{ include "cell0.fullname" . }}-secrets
{{- end -}}
{{- end -}}

{{/*
Create the name of the configmap to use
*/}}
{{- define "cell0.configMapName" -}}
{{ include "cell0.fullname" . }}-config
{{- end -}}

{{/*
Create the name of the ingress TLS secret
*/}}
{{- define "cell0.ingressSecretName" -}}
{{- if .Values.ingress.tls.secretName -}}
{{- .Values.ingress.tls.secretName -}}
{{- else -}}
{{ include "cell0.fullname" . }}-tls
{{- end -}}
{{- end -}}

{{/*
Define the image pull policy
*/}}
{{- define "cell0.imagePullPolicy" -}}
{{- if .Values.global.imagePullPolicy -}}
{{- .Values.global.imagePullPolicy -}}
{{- else -}}
{{- .Values.image.pullPolicy -}}
{{- end -}}
{{- end -}}

{{/*
Return the proper image name
*/}}
{{- define "cell0.image" -}}
{{- $registryName := .Values.image.registry -}}
{{- $repositoryName := .Values.image.repository -}}
{{- $tag := .Values.image.tag | default .Chart.AppVersion -}}
{{- $separator := ":" -}}
{{- printf "%s/%s%s%s" $registryName $repositoryName $separator $tag -}}
{{- end -}}

{{/*
Check if autoscaling is enabled
*/}}
{{- define "cell0.autoscaling.enabled" -}}
{{- if .Values.autoscaling.enabled -}}
true
{{- else -}}
false
{{- end -}}
{{- end -}}

{{/*
Return the appropriate apiVersion for HorizontalPodAutoscaler.
*/}}
{{- define "cell0.hpa.apiVersion" -}}
{{- if $.Capabilities.APIVersions.Has "autoscaling/v2" -}}
autoscaling/v2
{{- else -}}
autoscaling/v2beta2
{{- end -}}
{{- end -}}

{{/*
Return the appropriate apiVersion for ingress.
*/}}
{{- define "cell0.ingress.apiVersion" -}}
{{- if $.Capabilities.APIVersions.Has "networking.k8s.io/v1/Ingress" -}}
networking.k8s.io/v1
{{- else -}}
networking.k8s.io/v1beta1
{{- end -}}
{{- end -}}

{{/*
Return the appropriate apiVersion for PodDisruptionBudget.
*/}}
{{- define "cell0.pdb.apiVersion" -}}
{{- if $.Capabilities.APIVersions.Has "policy/v1/PodDisruptionBudget" -}}
policy/v1
{{- else -}}
policy/v1beta1
{{- end -}}
{{- end -}}

{{/*
Convert memory resources to appropriate format
*/}}
{{- define "cell0.resources.memory" -}}
{{- if kindIs "string" . -}}
{{- . -}}
{{- else -}}
{{- printf "%dMi" . -}}
{{- end -}}
{{- end -}}

{{/*
Generate environment variables from config
*/}}
{{- define "cell0.environment" -}}
- name: POD_NAME
  valueFrom:
    fieldRef:
      fieldPath: metadata.name
- name: POD_NAMESPACE
  valueFrom:
    fieldRef:
      fieldPath: metadata.namespace
- name: POD_IP
  valueFrom:
    fieldRef:
      fieldPath: status.podIP
{{- end -}}
