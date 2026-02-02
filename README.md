# GitHub–Jira Automation Bridge (Flask on AWS EC2)

## Project Overview

This project implements an automation bridge between GitHub and Jira using a Python Flask service deployed on an AWS EC2 instance. The system listens to GitHub webhooks for issue-related events (e.g., issue creation, comments) and automatically creates corresponding Jira issues in a target project via the Jira REST API.

The focus is on production-aligned design: secure credential handling, clear HTTP contracts, resilient request processing, and infrastructure hosted on a hardened EC2 instance. This makes the project suitable as a reference architecture for integrating developer tooling across VCS and issue tracking platforms.

---

## Problem Statement

Engineering teams frequently split their workflow between GitHub (code, pull requests, issues) and Jira (backlog, sprints, project tracking). Without integration, this creates:

- Fragmented visibility: Issues and discussions in GitHub are not reflected in Jira boards.
- Manual duplication: Developers or project managers manually create Jira tickets for GitHub issues.
- Inconsistent tracking: Some work lives only in GitHub issues, some only in Jira, making reporting noisy and unreliable.

The absence of automation leads to operational friction, missed tasks, and poor traceability from code to work items, especially in teams that standardize on Jira for planning and reporting.

This project addresses that friction by automatically translating GitHub issue events into Jira issues, ensuring Jira always reflects the latest work items without manual intervention.

---

## High-Level Architecture

At a high level, the system is an event-driven integration between GitHub and Jira, with AWS EC2 hosting the integration logic:

1. **GitHub Webhook**  
   A webhook is configured on a GitHub repository to trigger on specific events (e.g., `issues`, `issue_comment`).

2. **Flask Service on EC2**  
   An EC2-hosted Flask application exposes a public HTTP endpoint (`/createJIRA`) that receives webhook POST requests from GitHub.

3. **Event Processing & Mapping**  
   The Flask service validates the incoming webhook payload, extracts relevant information (issue title, body, URL, user, etc.), and maps it to Jira's issue schema.

4. **Jira REST API**  
   Using Jira's REST API, the service creates a Story/Task in a designated Jira project, authenticating via email + API token.

5. **Response Lifecycle**  
   The Flask service sends an appropriate HTTP status code back to GitHub, indicating success or failure (e.g., `200`, `400`, `401`, `500`).

### Logical Component View

- **Source System**: GitHub (issues, comments)  
- **Integration Layer**: Flask REST API (Python, `requests`) on EC2  
- **Target System**: Jira Cloud (REST API: `/rest/api/3/issue`)  
- **Infrastructure**: AWS EC2 (Ubuntu), Security Group, public DNS, HTTP/HTTPS  
- **Secrets & Configuration**: Environment variables on EC2 instance

---

## End-to-End Execution Flow

1. **Event Trigger (GitHub)**  
   A GitHub event occurs, such as:
   - A new issue is created
   - A comment is added to an existing issue
   - An issue is reopened or labeled (depending on configured webhook events)

2. **Webhook Delivery**  
   GitHub sends a POST request with a JSON payload to the configured webhook URL, pointing to the Flask service:
   ```text
   POST https://<ec2-public-dns-or-domain>/createJIRA
   Content-Type: application/json
   X-GitHub-Event: issues | issue_comment
   ```

3. **Flask Endpoint Handling**  
   The Flask app exposes `/createJIRA` and enforces a POST-only contract:
   ```python
   @app.route("/createJIRA", methods=["POST"])
   def create_jira():
       # 1. Validate HTTP method and content-type
       # 2. Parse JSON payload from GitHub
       # 3. Extract relevant fields (title, body, URL, user, action)
       # 4. Build Jira issue payload
       # 5. Call Jira REST API
       # 6. Return appropriate HTTP response
   ```

4. **Payload Transformation**  
   The application converts GitHub's event schema into Jira's issue schema. For example:
   - GitHub issue title → Jira `summary`
   - GitHub issue body + URL → Jira `description`
   - Optional labels / metadata → Jira `labels` or custom fields

5. **Jira REST API Call**  
   The Flask app authenticates to Jira using email + API token and issues a POST request:
   ```http
   POST /rest/api/3/issue
   Authorization: Basic <base64(email:api_token)>
   Content-Type: application/json
   ```

6. **Jira Issue Creation**  
   Jira returns a response with status code `201` on success, including the new issue key (e.g., `PROJ-123`). The service can log this and optionally include it in the response to GitHub.

7. **Webhook Response to GitHub**  
   The Flask endpoint returns:
   - `200 OK` on success (issue created or event intentionally ignored)
   - `400 Bad Request` for invalid/malformed payloads
   - `401/403` for Jira authentication/authorization issues (logged internally)
   - `500 Internal Server Error` for unexpected failures

8. **Operational Feedback**  
   Logs on the EC2 instance include:
   - Incoming webhook metadata and event type
   - Jira requests and responses (sanitized, no secrets)
   - Error traces for debugging

---

## Technologies Used

- **Python**
  - **Flask**: Lightweight web framework to expose REST endpoints.
  - **requests**: HTTP client for Jira REST API calls.
  - JSON handling, environment variable access (`os.environ`).

- **GitHub Webhooks**
  - Event source for issue-related lifecycle events.
  - Secure HTTP callbacks to the EC2-hosted service.

- **Jira Cloud REST API**
  - `/rest/api/3/issue` for issue creation.
  - `/rest/api/3/project` or similar endpoints to discover valid project keys during setup.

- **AWS EC2 (Ubuntu)**
  - Hosts the Flask application.
  - Provides public network reachability for GitHub webhooks.
  - Configurable security group for HTTP/HTTPS access.

- **Networking & HTTP**
  - HTTP methods: primarily `POST` (webhook + Jira call).
  - HTTP response codes: `200`, `201`, `400`, `401`, `403`, `405`, `500`.
  - Understanding of 405 errors when wrong methods hit the endpoint.

---

## Deployment on AWS EC2

The Flask service is deployed on an EC2 instance running Ubuntu:

1. **EC2 Instance**
   - OS: Ubuntu (e.g., 20.04 LTS).
   - Instance type: Small general purpose (e.g., t2.micro/t3.micro) is sufficient.
   - Public IP / Elastic IP for stable webhook endpoint.
   - Security Group allowing inbound HTTP/HTTPS from GitHub IP ranges or internet (depending on configuration).

2. **Application Runtime**
   - Python environment (system Python or virtualenv).
   - Dependencies installed via `pip` (e.g., `Flask`, `requests`).
   - Gunicorn or Flask's built-in server for simple setups (production should favor Gunicorn + Nginx/reverse proxy).

3. **Service Management**
   - Systemd unit or process manager (e.g., `systemd`/`supervisord`) to ensure Flask app restarts on reboot or failure.
   - Logs written to standard output or a structured logging directory for debugging and monitoring.

4. **Endpoint Exposure**
   - Direct HTTP exposure via EC2 public DNS or domain.
   - Optional Nginx reverse proxy for TLS termination (recommended).
   - Webhook URL: `https://your-domain-or-ec2-dns/createJIRA`.

---

## GitHub Webhook Configuration

GitHub is configured to send events to the Flask service:

1. **Repository Settings**
   - Navigate to: `Settings` → `Webhooks` → `Add webhook`.

2. **Payload URL**
   - Set to the EC2 endpoint:  
     `https://<ec2-public-dns-or-domain>/createJIRA`

3. **Content Type**
   - `application/json`.

4. **Secret (Optional but Recommended)**
   - Configure a webhook secret and validate signature in the Flask app (HMAC SHA256).
   - Ensures the EC2 endpoint only trusts GitHub-originated requests.

5. **Events**
   - Typically:
     - `Issues`: For create/update/close events.
     - `Issue comments` (optional): To trigger Jira updates or subtasks.
   - Can be narrowed down based on specific workflow needs.

6. **Delivery & Retry**
   - GitHub retries failed webhook deliveries; HTTP response codes and latency should be considered when designing the Flask handler.

---

## Jira API Integration

The project integrates with Jira Cloud via the REST API:

1. **Authentication**
   - Jira Cloud requires email + API token (Basic Auth).
   - Credentials are injected via environment variables:
     - `JIRA_EMAIL`
     - `JIRA_API_TOKEN`
     - `JIRA_BASE_URL` (e.g., `https://your-domain.atlassian.net`)
   - No credentials are hardcoded in the codebase.

2. **Issue Creation**
   - The Flask app constructs JSON payloads matching Jira's issue schema, for example:
   ```json
   {
     "fields": {
       "project": { "key": "PROJ" },
       "summary": "GitHub Issue: <issue title>",
       "description": "GitHub Issue URL: <url>\n\n<issue body>",
       "issuetype": { "name": "Task" }
     }
   }
   ```

3. **Project Discovery**
   - Helper scripts were used to query Jira projects and validate:
     - Which project keys exist.
     - Which issue types are allowed (e.g., `Story`, `Task`, `Bug`).
   - Typical endpoint:
     - `GET /rest/api/3/project`
   - This avoids hardcoding invalid project keys or issue type names.

4. **Error Handling**
   - Common responses:
     - `201 Created`: Issue successfully created.
     - `400 Bad Request`: Incorrect payload or invalid field values.
     - `401 Unauthorized` or `403 Forbidden`: Authentication/authorization problems.
   - Flask logs these responses for troubleshooting and learning.

---

## Security Considerations

Security is handled with a focus on practical production usage:

1. **API Tokens & Credentials**
   - Jira API token and email are stored as environment variables on the EC2 instance.
   - No tokens or passwords are committed to Git or printed in logs.
   - Recommended: use AWS Systems Manager Parameter Store or Secrets Manager in a more advanced setup.

2. **Environment Variables**
   - Values set via:
     - Shell profile (`/etc/environment`, systemd unit Environment directives, etc.).
     - Exported at runtime for the Flask process.
   - Provides a clear separation between code and configuration.

3. **Network Security**
   - EC2 Security Group:
     - Inbound: restrict to port 80/443; optionally limit to GitHub IP ranges.
     - Outbound: allow HTTPS access to Jira Cloud.
   - Using HTTPS (TLS) is strongly recommended to protect webhook payload and Jira credentials in transit.

4. **HTTP Method Restrictions**
   - `/createJIRA` accepts only POST.
   - Any GET/PUT/DELETE requests should return `405 Method Not Allowed`, preventing misuse of the endpoint.

5. **Input Validation**
   - Ensure GitHub payload is parsed and validated before passing to Jira.
   - Avoid directly trusting any incoming fields without checks (e.g., length, presence).

---

## Common Errors Faced & Learnings

During implementation, several practical issues surfaced that are typical in real integrations:

1. **HTTP 405 Method Not Allowed**
   - Cause: Accessing `/createJIRA` via browser (GET) while the route only accepts POST.
   - Learning: Make the allowed HTTP methods explicit and return clear error messages to avoid confusion during initial testing.

2. **Jira Authentication Failures (401/403)**
   - Cause: Incorrect API token, using password instead of token, wrong email, or missing Basic Auth header formatting.
   - Learning: Always test Jira API using a standalone script (`requests`) before wiring it into the Flask route to isolate errors.

3. **Invalid Project Key / Issue Type (400)**
   - Cause: Using non-existent project key or issue type not supported by that project.
   - Learning: Use helper scripts to list projects and their supported issue types before finalizing configuration.

4. **Networking & DNS Issues**
   - Cause: GitHub unable to reach EC2 due to:
     - Security group misconfiguration.
     - Missing public IP or incorrect DNS.
   - Learning: Validate connectivity via tools such as `curl`, and check GitHub webhook delivery logs for detailed error messages.

5. **Flask Debug vs. Production Mode**
   - Cause: Running Flask in debug mode on open network ports can be risky.
   - Learning: Run in non-debug mode behind a reverse proxy in production-like scenarios.

6. **Payload Mismatch Between Events**
   - Cause: Different GitHub events (`issues` vs `issue_comment`) have slightly different payload structures.
   - Learning: Normalize the input structures and handle only the events required for the automation; log unsupported event types.

---

## Testing & Validation

Testing focused on both functional correctness and integration behavior across the stack:

1. **Unit-Level Testing**
   - Local Python tests for:
     - Mapping GitHub payload → Jira payload.
     - Error handling when certain fields are missing.
   - Mocked requests to Jira using `requests` mocks.

2. **Integration Testing with Jira**
   - Standalone Python scripts calling Jira:
     - Listing projects.
     - Creating a sample issue.
   - Verified:
     - Project key is valid.
     - Issue type is allowed.
     - Authentication is correct.

3. **End-to-End Testing with GitHub Webhooks**
   - Configure webhook on a test GitHub repository.
   - Trigger events:
     - Create a new issue.
     - Add a comment.
   - Validate:
     - Webhook delivery success status in GitHub.
     - New Jira issue appears in the configured Jira project.
     - Fields (summary, description) correctly reflect GitHub content.
   - Observed webhook retry behavior on transient EC2/Flask errors.

4. **HTTP Behavior & Status Codes**
   - Verified:
     - POST to `/createJIRA` with a valid payload returns `200`.
     - GET to `/createJIRA` returns `405`.
     - Invalid/malformed JSON returns `400`.

---

## Limitations

This implementation is intentionally focused and does not attempt to cover every possible integration scenario:

- **Unidirectional Flow**
  - Integration is one-way: from GitHub to Jira.
  - Jira updates are not synchronized back to GitHub (e.g., status changes).

- **Basic Mapping Logic**
  - The mapping from GitHub issues to Jira fields is straightforward (title, body, URL).
  - No advanced mapping to components, epics, sprints, or custom fields (beyond basic configuration).

- **Error Handling**
  - Errors are logged but may not have a full alerting pipeline (e.g., no Slack/SNS notifications on failures in the base version).

- **Scalability**
  - Suitable for small to medium repositories and event volumes.
  - High-throughput setups might benefit from queueing (SQS) and asynchronous processing rather than direct synchronous calls from webhook to Jira.

- **Security Hardening**
  - While environment variables and basic network controls are used, more advanced measures (e.g., Secrets Manager, IP whitelisting, WAF) are not implemented in the minimal deployment.

---

## Future Enhancements

Potential next steps to evolve this into a more production-grade integration platform:

1. **Two-Way Synchronization**
   - Sync Jira status or comments back to GitHub (e.g., updating issue labels or comments when Jira status changes).

2. **Event Filtering & Routing**
   - Apply rules on which issues should create Jira tickets (based on labels, assignees, milestones, or repository).
   - Different Jira projects or issue types based on branch, repo, or label.

3. **Advanced Security**
   - Use AWS Secrets Manager or SSM Parameter Store for Jira credentials.
   - Validate GitHub webhook signatures using the configured secret.
   - Enforce HTTPS with a proper TLS certificate on the endpoint.

4. **Observability & Metrics**
   - Structured logging and metrics (e.g., number of Jira issues created, failure rate).
   - Integrate with CloudWatch, Prometheus, or other monitoring stacks.

5. **Queue-Based Architecture**
   - Introduce SQS or SNS between GitHub webhook and Jira calls:
     - Webhook writes to SQS.
     - Worker/consumer processes messages and calls Jira.
   - Increases resiliency and decouples webhook latency from Jira response time.

6. **Configuration Management**
   - Externalize mapping configuration (e.g., YAML/JSON) to control:
     - Target project keys.
     - Issue types per event.
     - Label/priority mappings.

7. **Support for Additional GitHub Events**
   - Pull request events.
   - Label changes or milestones.
   - Automated linking of Jira issues to specific commits or pull requests.

---

This project demonstrates a practical, production-aligned integration pattern across GitHub, Jira, and AWS, highlighting real-world considerations in automation, security, and operations that are highly relevant in DevOps and platform engineering environments.
