# Automation Failure Testing — 7 Scenarios

| # | Failure | Detection | Recovery |
|---|---|---|---|
|1|AI API failure|exception/error response|retry/log/notify|
|2|External API failure|HTTP timeout/error|retry and error response|
|3|Invalid document|validation exception|reject upload and explain|
|4|Invalid dataset|validation result|return invalid-record report|
|5|Workflow failure|automation exception|log activity and recovery path|
|6|Authentication failure|HTTP 401/redirect|deny access and log event|
|7|Notification failure|email/API exception|log failure without silent loss|
