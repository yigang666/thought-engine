# Thought Engine
## Project Requirements & Technical Architecture — v1.1

**Document status:** MVP implementation baseline  
**Version:** 1.1  
**Date:** 23 November 2026  
**Product type:** Single-user, AI-assisted thought-to-publication system

---

# 1. Executive Summary

Thought Engine turns deep conversations between a person and AI into a structured, reviewable record of that person's thinking, then helps transform that record into high-quality Chinese and English articles for publication on a personal blog.

The product is not intended to be an autonomous article generator. Its primary responsibility is to preserve the user's original ideas, reasoning, uncertainty, and intellectual development while improving clarity, structure, and communication.

The core product promise is:

> Give Thought Engine a meaningful conversation. It will help identify and organize the user's thinking, let the user verify that representation, produce Chinese and English articles, and publish only after the user approves them.

The MVP is an **end-to-end product**, not merely a bilingual blog and not a full autonomous multi-agent platform. It must demonstrate the essential workflow:

**Import conversation → Extract thoughts → Review Thought Map → Generate bilingual articles → Edit and approve → Publish to personal blog.**

The first release should use a simple modular application and a small number of LLM calls. The system should be designed so that its modules can evolve into specialized agents later, but independent agents, vector databases, complex research workflows, and large-scale infrastructure are explicitly outside the MVP.

## 1.1 Product principles

1. **User thinking is the source of truth.** AI may clarify and organize ideas, but must not silently invent or attribute ideas to the user.
2. **Attribution must be explicit.** Distinguish user-originated statements, AI-originated suggestions, user-adopted ideas, and unresolved hypotheses.
3. **Structure before prose.** Generate articles from a reviewed Thought Map, not directly from an unstructured conversation.
4. **Human approval before publication.** Nothing becomes public without explicit user approval.
5. **Private source, public output.** Raw conversations and private Thought Maps must not be committed to the public blog repository.
6. **End-to-end value before architectural sophistication.** A working, trustworthy workflow is more important than a visually impressive multi-agent architecture.
7. **Evolutionary architecture.** Define stable data contracts early so modules can later be separated into agents or services without rewriting the product.

---

# 2. Product Vision and Goals

## 2.1 Vision

Build a personal intellectual publishing system that compounds in value over time.

Each meaningful conversation can become:
- A structured record of what the user thinks.
- A traceable set of arguments, evidence, assumptions, and open questions.
- A polished Chinese article.
- A separately adapted English article for international readers.
- A permanent, searchable public contribution to the user's personal knowledge and professional identity.

Over time, the system may help the user observe how their ideas evolve, identify recurring themes, connect related arguments, and build a coherent body of work.

## 2.2 MVP goals

The MVP must prove five things:

1. A user can import a conversation without manually rewriting it.
2. The system can extract a reasonably faithful representation of the user's thinking.
3. The user can inspect and correct that representation before article generation.
4. The system can generate publishable Chinese and English drafts from the approved Thought Map.
5. The user can approve and publish the articles to a real public website through a controlled workflow.

## 2.3 Non-goals for MVP

The following are intentionally excluded from the first release:

- Fully autonomous publishing without user approval.
- Automatic ingestion from every ChatGPT, Claude, Gemini, or other platform API.
- A production-grade multi-tenant SaaS product.
- Five or more independently deployed AI agents.
- Autonomous web research and comprehensive fact-checking.
- A sophisticated knowledge graph.
- Vector database and semantic search.
- Automatic newsletter, social-media, or multi-platform distribution.
- Mobile applications.
- Kubernetes, microservices, or complex cloud infrastructure.
- Advanced analytics, billing, team collaboration, or role-based access control.

These may be considered after the core workflow has been validated.

---

# 3. Target User and Primary Use Case

## 3.1 Initial target user

The initial target is one individual who:
- Frequently has long, substantive conversations with AI.
- Thinks through problems verbally or conversationally.
- Wants to publish ideas but may not naturally express them in polished written form.
- Wants both Chinese and English output.
- Values intellectual accuracy and ownership over generic AI-generated content.
- Is willing to review and approve drafts before publication.

## 3.2 Primary user journey

1. The user opens the private Thought Engine workspace.
2. The user pastes a conversation or uploads a Markdown file.
3. The system parses the conversation and identifies speakers and message boundaries.
4. The system extracts a structured Thought Map.
5. The user reviews, edits, accepts, or rejects extracted items.
6. The system generates a Chinese article and an English adaptation.
7. The user edits both drafts and checks the preview.
8. The user explicitly approves publication.
9. The system commits only approved public article files to the publishing repository.
10. CI/CD builds and deploys the public blog.
11. The workspace records the publication result and article URL.

---

# 4. Product Scope and Release Priorities

## 4.1 MVP definition: Minimum End-to-End Product

The MVP is complete only when the essential workflow works from imported conversation to a live public article.

A bilingual blog by itself is not the MVP. A Thought Map prototype by itself is also not the MVP. Both are necessary parts of the end-to-end product, but implementation should validate the riskiest capability first.

## 4.2 P0 — Required for MVP

| ID | Capability | Minimum acceptance criteria |
|---|---|---|
| P0-01 | Conversation import | User can paste conversation text or upload a Markdown file. |
| P0-02 | Conversation parsing | System identifies messages and speakers where the input format makes this possible; uncertain speaker attribution is marked as uncertain. |
| P0-03 | Thought extraction | System produces a structured Thought Map containing the user's ideas, AI suggestions, adopted ideas, reasoning, conclusions, assumptions, and open questions. |
| P0-04 | Thought Map review | User can inspect and edit extracted items and explicitly confirm the Thought Map. |
| P0-05 | Chinese generation | System generates a coherent Chinese article based on the confirmed Thought Map. |
| P0-06 | English generation | System generates an English article adapted for English-speaking readers, not merely a sentence-by-sentence translation. |
| P0-07 | Human review | User can edit and preview both drafts before publication. |
| P0-08 | Publication approval | Publication requires an explicit user action. |
| P0-09 | Publishing integration | Approved article files can be committed to the configured GitHub publishing repository. |
| P0-10 | Automated deployment | GitHub Actions builds the site and deploys it to the configured hosting provider. |
| P0-11 | Public bilingual blog | Visitors can browse article lists, open article pages, and switch between Chinese and English versions. |
| P0-12 | Private/public separation | Raw conversations and private Thought Maps are never included in the public publishing commit. |
| P0-13 | Basic error handling | Import, LLM, GitHub, build, and deployment failures are visible to the user and do not silently mark the workflow as complete. |

## 4.3 P1 — Valuable, but may follow immediately after MVP

- Article tags and categories.
- Draft history and version comparison.
- Retry individual pipeline stages without restarting the entire workflow.
- Basic article quality checklist.
- Source conversation reference attached privately to each article.
- Search by article title and tags.
- A simple dashboard showing drafts, approved articles, and published articles.
- Configurable LLM provider and model.
- Basic token and cost tracking.
- A small evaluation dataset of real conversations.

## 4.4 P2 — Future capabilities

- Direct ChatGPT and Claude export ingestion.
- Browser extension or share-to-workspace workflow.
- Autonomous research and source citation.
- Fact-checking workflow with evidence tracking.
- Semantic search and vector database.
- Knowledge graph and concept relationships.
- Idea evolution tracking across multiple conversations.
- Multiple users and collaboration.
- Newsletter and social-media publishing.
- Dedicated mobile experience.
- Independent multi-agent orchestration.

## 4.5 MVP implementation rule

Do not interpret the P0 list as a requirement to build a large enterprise application. Each capability should be implemented at its smallest useful level.

For example:
- Import can initially be a text box and a Markdown file upload.
- Thought Map review can initially be a structured editable form.
- Publishing can initially be a single GitHub commit operation.
- The blog can initially use a clean template with article list, article page, and language switcher.
- The pipeline can initially run synchronously for one user and one conversation at a time.

---

# 5. Thought Integrity: The Core Product Requirement

The most important quality risk is that an article may sound excellent while misrepresenting what the user actually thinks.

Thought Engine must evaluate **thought fidelity** separately from writing quality.

## 5.1 Required attribution categories

Every extracted thought item must have an origin/status category:

| Category | Meaning |
|---|---|
| `user_original` | The user explicitly expressed this idea or position. |
| `ai_suggestion` | The AI introduced this idea; the user has not clearly adopted it. |
| `user_adopted` | The user explicitly agreed with, adopted, or meaningfully developed an AI suggestion. |
| `jointly_developed` | The idea emerged through back-and-forth reasoning and cannot confidently be attributed to only one speaker. |
| `inferred` | The system inferred this from the conversation; it requires user verification. |
| `uncertain` | The source or meaning is ambiguous and must not be presented as a confirmed user belief. |

The system must not convert an `ai_suggestion` or `inferred` item into a `user_original` claim.

## 5.2 Thought Map structure

A Thought Map should contain, where applicable:

- Central question or problem.
- Main thesis or position.
- Supporting arguments.
- Reasoning steps and causal relationships.
- Examples and analogies.
- Evidence or factual claims mentioned in the conversation.
- Assumptions.
- Counterarguments and objections.
- Conclusions.
- Open questions.
- Uncertainties or contradictions.
- Potential article angles.
- Attribution and confidence for each item.

## 5.3 Thought Map review requirements

The user must be able to:
- Read the extracted items in a clear hierarchy.
- See the attribution category for each item.
- Edit wording without losing the source attribution.
- Change an item's attribution/status.
- Remove irrelevant or incorrectly extracted items.
- Add missing thoughts manually.
- Confirm the Thought Map as the source for article generation.

The system should preserve the original extraction separately from user-edited changes, at least in the underlying data model.

## 5.4 Quality dimensions

The initial evaluation rubric is:

| Dimension | Weight | Evaluation question |
|---|---:|---|
| Thought preservation | 30% | Does the output preserve the user's actual ideas and intent? |
| Attribution accuracy | 25% | Does it correctly distinguish user ideas from AI suggestions and inferences? |
| Reasoning integrity | 20% | Does it preserve the important logical steps and relationships? |
| Chinese writing quality | 10% | Is the Chinese article clear, coherent, and readable? |
| English writing quality | 10% | Is the English article natural and suitable for its audience? |
| Factual reliability | 5% | Are factual claims represented cautiously and without invented evidence? |

These weights are an initial human evaluation rubric, not an objective scientific measurement.

**Important:** Do not rely only on an LLM asking another LLM to score the result. Evaluate with real conversations and human review.

---

# 6. Functional Requirements

## 6.1 Conversation import

### MVP requirements
- Accept pasted plain text.
- Accept uploaded `.md` files.
- Store the original input privately.
- Record import time and a user-provided conversation title, if available.
- Support a simple speaker format such as `User:` and `Assistant:`.
- If speaker labels are missing or inconsistent, mark attribution as uncertain rather than guessing silently.

### Deferred
- Platform-specific JSON exports.
- Direct platform APIs.
- Automatic conversation synchronization.

## 6.2 Parsing and normalization

Normalize imported content into a consistent internal structure:
- Conversation ID.
- Message ID.
- Speaker.
- Message content.
- Message order.
- Optional timestamp.
- Parsing confidence or warning.

The original source should remain unchanged and privately accessible.

## 6.3 Thought extraction

The extraction stage should produce structured JSON validated against a schema.

At minimum, it should identify:
- Central question.
- Main user positions.
- Supporting arguments.
- Reasoning chain.
- Conclusions.
- AI suggestions.
- Explicitly adopted suggestions.
- Assumptions.
- Unresolved questions.
- Contradictions or ambiguities.
- Potential article themes.

Extraction must be conservative. When uncertain, it should preserve uncertainty rather than invent certainty.

## 6.4 Logic review

For the MVP, logic review may be a lightweight LLM call or a deterministic validation step. It is not a separate autonomous agent.

It should flag:
- Missing steps in an argument.
- Unsupported conclusions.
- Contradictions within the conversation.
- Statements whose speaker attribution is uncertain.
- Claims that may need external evidence.
- Places where the article would otherwise overstate the user's position.

It must not silently rewrite the Thought Map as if the user had confirmed the changes.

## 6.5 Article generation

Generate two distinct outputs from the confirmed Thought Map.

### Chinese article
- Preserve the user's original reasoning and position.
- Improve structure, transitions, and clarity.
- Avoid generic AI-style introductions and conclusions.
- Do not add unsupported claims.
- Use examples from the conversation where useful.
- Preserve meaningful uncertainty and nuance.

### English article
- Adapt the argument for an international English-speaking audience.
- Use natural English structure and terminology.
- Explain context that may be implicit in the Chinese source.
- Do not translate mechanically sentence by sentence.
- Do not change the underlying thesis or attribution.
- Avoid adding facts or arguments merely to make the article sound more authoritative.

### Article metadata
Each article should support:
- Title.
- Slug.
- Language.
- Summary or excerpt.
- Tags.
- Publication date.
- Draft status.
- Optional canonical relationship to the other language version.

## 6.6 Human review and editing

The user must be able to:
- Edit Chinese and English drafts.
- Preview the final article.
- Return to the Thought Map if the draft reveals a missing or distorted idea.
- Save drafts without publishing.
- Approve publication explicitly.

A draft must never be published just because generation succeeded.

## 6.7 Publishing

### MVP publishing flow
1. Validate that the article has required metadata and content.
2. Confirm that the user has approved the article.
3. Generate public Markdown/content files.
4. Ensure private conversation data and Thought Map data are excluded.
5. Commit the approved files to the configured GitHub repository.
6. Trigger or allow the configured CI/CD workflow to run.
7. Record the commit identifier and deployment status.
8. Display the public URL only after it can be verified from the deployment result or configured deployment process.

### Failure handling
- If GitHub authentication fails, show an actionable error.
- If a commit fails, preserve the approved draft.
- If the build fails, report the failure and retain the source draft.
- Do not display a success state before the relevant operation reports success.
- Retrying should not create duplicate article entries.

## 6.8 Public blog

The public blog should provide:
- Home page with recent articles.
- Article detail page.
- Chinese and English versions.
- Language switcher.
- Article title, summary, date, and tags.
- Responsive layout for desktop and mobile.
- Basic SEO metadata.
- RSS feed may be added after the initial release.

The blog should prioritize readability and loading speed over complex visual effects.

---

# 7. MVP Architecture

## 7.1 Architecture decision

Use a **modular monolith** for the MVP.

The application should have clear internal modules and stable data contracts, but it does not need independently deployed agents or microservices.

This keeps development, debugging, deployment, and cost manageable for a single-user product.

## 7.2 High-level architecture

```text
                         PRIVATE WORKSPACE
┌────────────────────────────────────────────────────────────┐
│                        Web UI                               │
│  Import → Thought Map Review → Article Editor → Publish     │
└──────────────────────────────┬─────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────┐
│                    Application Backend                      │
│                                                            │
│  1. Conversation Import & Parser                            │
│  2. Thought Extraction                                      │
│  3. Logic / Attribution Validation                          │
│  4. Chinese Article Generator                               │
│  5. English Article Generator                               │
│  6. Quality Checks                                          │
│  7. Publishing Service                                      │
└──────────────────────────────┬─────────────────────────────┘
                               │
                  ┌────────────┴────────────┐
                  ▼                         ▼
          LLM Provider(s)             Private Storage
       OpenAI / Anthropic              SQLite + files
                  │
                  ▼
         Structured Thought Map
         + Article Drafts
                  │
            User approval
                  │
                  ▼
          GitHub Publishing Repo
                  │
                  ▼
            GitHub Actions
                  │
                  ▼
          Static Site Build
                  │
                  ▼
          Cloudflare Pages
                  │
                  ▼
             Public Blog
```

## 7.3 Suggested technology stack

| Layer | MVP choice | Reason |
|---|---|---|
| Public website | Astro + TypeScript | Excellent static content and Markdown support. |
| Styling | Lightweight CSS or Tailwind CSS | Keep the visual system simple. |
| Private workspace UI | Simple web UI; may initially be served by the backend | Avoid building a separate complex frontend too early. |
| Backend | Python + FastAPI | Familiar, practical, and suitable for LLM workflows. |
| Data validation | Pydantic | Strong typed schemas for structured LLM output. |
| LLM integration | Provider adapter for OpenAI / Anthropic | Avoid coupling the application to one provider. |
| Private database | SQLite | Sufficient for a single-user MVP. |
| Private source files | Local private storage | Keep raw conversations out of the public repository. |
| Public content | Markdown / Astro content collections | Simple, portable, Git-friendly publishing format. |
| Source control | GitHub | Version history and publishing workflow. |
| CI/CD | GitHub Actions | Automated build and deployment. |
| Hosting | Cloudflare Pages | Simple static hosting for the public blog. |

The exact UI framework and hosting arrangement for the private workspace can be chosen during implementation. Do not introduce additional infrastructure unless a concrete requirement demands it.

## 7.4 Explicitly avoid in MVP

- Kubernetes.
- Microservices.
- Redis.
- Kafka.
- Vector database.
- Graph database.
- Multi-agent orchestration framework.
- Complex workflow engine.
- Separate production cloud backend, unless local operation proves insufficient.

These technologies may be useful later, but they do not help validate the primary product hypothesis.

---

# 8. AI Pipeline and Agent Evolution Strategy

## 8.1 MVP pipeline

Implement the workflow as a small number of explicit stages:

```text
Conversation
    │
    ▼
[1] Parse & Normalize
    │
    ▼
[2] Extract Thought Map
    │
    ▼
[3] Validate Attribution & Logic
    │
    ▼
[4] User Reviews and Confirms
    │
    ▼
[5] Generate Chinese Article
    │
    ▼
[6] Generate English Article
    │
    ▼
[7] Quality Checks
    │
    ▼
[8] User Edits and Approves
    │
    ▼
[9] Publish
```

Each stage should have:
- A clear input schema.
- A clear output schema.
- A recorded status.
- A useful error message.
- A retry path where practical.

## 8.2 LLM call strategy

A reasonable initial implementation may use:

| Stage | Initial implementation |
|---|---|
| Thought extraction | One structured-output LLM call. |
| Attribution / logic review | One LLM call plus deterministic checks; may be simplified initially. |
| Chinese article | One LLM call. |
| English article | One LLM call. |
| Quality check | One LLM call plus programmatic validation. |

This is a starting point, not a fixed requirement. Combine or split calls based on measured quality, latency, and cost.

## 8.3 Future multi-agent architecture

Only after the end-to-end workflow is stable should the modules be considered for separation into specialized agents.

Potential future roles:

1. **Conversation Analyst** — parses conversations and extracts candidate thoughts.
2. **Thought Architect** — organizes arguments, reasoning, relationships, and open questions.
3. **Research Agent** — finds and records external evidence for claims that require verification.
4. **Writing Agent** — generates Chinese and English articles from approved thought structures.
5. **Quality Reviewer** — checks fidelity, attribution, logic, clarity, and factual caution.
6. **Publishing Agent** — prepares and publishes user-approved content.

These are logical responsibilities, not a requirement to deploy six separate services.

## 8.4 Multi-agent engineering requirements for a later phase

When agent separation becomes justified, add:
- Explicit agent input/output contracts.
- Orchestration and state transitions.
- Retry and timeout handling.
- Structured logs and trace IDs.
- Human approval gates.
- Evaluation datasets and regression tests.
- Token and cost tracking per stage.
- Failure isolation.
- Prompt and model version tracking.

Do not claim that the MVP demonstrates sophisticated multi-agent orchestration merely because it has multiple prompt templates or sequential LLM calls. The portfolio documentation should accurately describe the implementation.

---

# 9. Data Model

Use versioned Pydantic models and JSON serialization. The following is a conceptual starting point; implementation may refine field names while preserving the meaning.

## 9.1 Conversation

```json
{
  "conversation_id": "uuid",
  "title": "string",
  "source_type": "paste | markdown",
  "created_at": "ISO-8601",
  "original_file_path": "private path",
  "messages": [
    {
      "message_id": "uuid",
      "sequence": 1,
      "speaker": "user | assistant | unknown",
      "content": "string",
      "timestamp": null,
      "speaker_confidence": 0.98
    }
  ]
}
```

## 9.2 Thought Map

```json
{
  "thought_map_id": "uuid",
  "conversation_id": "uuid",
  "schema_version": "1.0",
  "central_question": "string",
  "main_thesis": "string",
  "thought_items": [
    {
      "item_id": "uuid",
      "type": "thesis | argument | reasoning | example | assumption | conclusion | question | counterargument",
      "content": "string",
      "origin": "user_original | ai_suggestion | user_adopted | jointly_developed | inferred | uncertain",
      "source_message_ids": ["uuid"],
      "confidence": 0.9,
      "user_confirmed": false,
      "notes": "string"
    }
  ],
  "reasoning_chain": [
    {
      "step": 1,
      "description": "string",
      "depends_on": []
    }
  ],
  "open_questions": [],
  "contradictions": [],
  "review_status": "pending | in_review | confirmed",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}
```

## 9.3 Article

```json
{
  "article_id": "uuid",
  "thought_map_id": "uuid",
  "language": "zh-CN | en",
  "title": "string",
  "slug": "string",
  "summary": "string",
  "content_markdown": "string",
  "tags": ["string"],
  "status": "draft | approved | publishing | published | failed",
  "approved_at": null,
  "published_at": null,
  "public_url": null,
  "commit_sha": null,
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}
```

## 9.4 Pipeline run

Record each processing run:
- Run ID.
- Conversation ID.
- Stage name.
- Stage status.
- Input and output references.
- Prompt version.
- Model/provider.
- Start and finish timestamps.
- Error details, if any.
- Token usage and estimated cost, if available.

Do not store API secrets in these records.

---

# 10. Privacy and Security

Privacy is a core architectural requirement because conversations may contain personal, professional, or confidential information.

## 10.1 Data classification

| Data | Classification | Public repository? |
|---|---|---|
| Original conversation | Private | No |
| Parsed conversation messages | Private | No |
| Thought Map | Private by default | No |
| Article drafts | Private until approved | No |
| Approved public article | Public | Yes |
| API keys and access tokens | Secret | Never |
| Pipeline logs | Private; redact sensitive content | No |

## 10.2 Security requirements

- Store API keys in environment variables or a local secret manager.
- Never hardcode credentials in source code.
- Add `.env`, private data directories, SQLite databases, and temporary uploads to `.gitignore`.
- Do not send raw conversation content to analytics services.
- Do not include source conversation text in public commit messages.
- Validate file type and size for uploads.
- Sanitize generated filenames and slugs.
- Restrict publishing to the configured repository and branch.
- Require explicit approval before a public commit.
- Avoid logging full prompts or conversation contents by default.
- Provide a way to delete private source data and related drafts.

For a local single-user MVP, a simple local authentication boundary may be sufficient if the workspace is not exposed publicly. If the workspace is deployed to the internet, authentication and HTTPS become mandatory before use.

---

# 11. User Interface Requirements

## 11.1 Main workspace

The private workspace should have a simple navigation structure:

- **Conversations** — imported source conversations.
- **Thought Maps** — extracted and reviewed thinking structures.
- **Articles** — Chinese and English drafts.
- **Publishing** — approval and publication status.
- **Settings** — model provider, API configuration, and blog repository settings.

## 11.2 Conversation detail

Display:
- Conversation title.
- Import date.
- Message count.
- Original source preview.
- Extraction status.
- Link to the resulting Thought Map.

## 11.3 Thought Map view

Display the central question and thesis prominently, followed by arguments, reasoning, evidence, assumptions, conclusions, and open questions.

Attribution should be visually obvious. Use labels or restrained color coding, but do not rely on color alone.

The user must be able to edit and confirm the Thought Map.

## 11.4 Article editor

Display:
- Chinese and English drafts.
- Title and metadata fields.
- Markdown editor or practical text editor.
- Rendered preview.
- Save draft action.
- Approve and publish action.

The UI must clearly distinguish **Save Draft**, **Approve**, and **Publish**.

## 11.5 Publishing status

Show meaningful states:
- Draft.
- Awaiting review.
- Approved.
- Publishing.
- Published.
- Failed.

Display error details and a retry action when applicable.

---

# 12. Delivery Plan and Implementation Phases

The development sequence should validate the riskiest product assumption before investing in a polished website.

Time estimates assume one developer using Claude Code or a similar coding assistant, a single-user MVP, and intentionally limited scope. They are estimates, not guarantees.

## Phase 0 — Thought Extraction Prototype

**Estimated effort: 1–2 days**

### Objective
Validate whether the system can preserve the user's thinking and attribute ideas correctly.

### Tasks
1. Select 3 real, substantial conversations.
2. Save them as Markdown files.
3. Define the first Thought Map Pydantic schema.
4. Implement a simple parser.
5. Implement one LLM-based Thought Map extraction.
6. Add attribution labels and source message references.
7. Review the outputs manually against the original conversations.
8. Record extraction failures and revise the schema or prompt.

### Deliverable
A small Python prototype that converts real conversations into structured Thought Maps.

### Exit criteria
- The Thought Map captures the central question and major user positions.
- User ideas are not routinely confused with AI suggestions.
- Important reasoning steps are not lost.
- Ambiguous items are marked rather than asserted as facts.
- The user considers the output useful enough to continue.

If this phase fails, improve the extraction and attribution approach before building more UI.

## Phase 1 — Minimal Public Blog and Deployment

**Estimated effort: 2–3 days**

### Objective
Establish a real publishing destination with a reliable deployment pipeline.

### Tasks
1. Create an Astro project.
2. Configure Chinese and English article routes.
3. Implement home page, article list, article detail, and language switching.
4. Configure Markdown content collections.
5. Create a GitHub repository.
6. Configure GitHub Actions.
7. Connect Cloudflare Pages.
8. Publish one manually written test article in both languages.
9. Verify the production website and deployment workflow.

### Deliverable
A live bilingual personal blog with automated deployment.

### Exit criteria
- Both language versions render correctly.
- Navigation and language switching work.
- A GitHub commit triggers a successful build and deployment.
- The site is usable on desktop and mobile.

Keep design intentionally simple. Do not spend time on elaborate animations or branding before the publishing workflow works.

## Phase 2 — End-to-End AI Writing Pipeline

**Estimated effort: 4–6 days**

### Objective
Connect imported conversations to reviewed bilingual article drafts.

### Tasks
1. Create the FastAPI application.
2. Implement paste and Markdown import.
3. Implement private conversation storage.
4. Integrate the Phase 0 extraction logic.
5. Build a basic Thought Map review screen.
6. Add user confirmation of the Thought Map.
7. Generate Chinese article drafts.
8. Generate English adaptations.
9. Add basic quality checks.
10. Build draft editing and preview.

### Deliverable
A private workspace that turns a conversation into editable Chinese and English drafts.

### Exit criteria
- The user can import a conversation.
- The system produces a structured Thought Map.
- The user can edit and confirm the Thought Map.
- Both article drafts are generated from the confirmed Thought Map.
- Drafts can be edited and saved.
- Private source data remains outside the public repository.

## Phase 3 — Approval and Automated Publishing

**Estimated effort: 2–3 days**

### Objective
Complete the core product loop.

### Tasks
1. Implement explicit approval state.
2. Generate public article Markdown files from approved drafts.
3. Add GitHub publishing integration.
4. Commit only approved public content.
5. Track commit and deployment status.
6. Handle authentication, commit, build, and deployment failures.
7. Display the published URL when verified.
8. Test duplicate prevention and retry behavior.

### Deliverable
A working end-to-end Thought Engine MVP.

### Exit criteria
A real conversation can be imported, transformed into a reviewed Thought Map, converted into bilingual articles, approved, and published to the public blog without exposing private source data.

## Phase 4 — Evaluation, Reliability, and Multi-Agent Readiness

**Estimated effort: iterative; begin after the MVP works**

### Objective
Improve quality and make the system demonstrably reliable and technically credible.

### Tasks
- Build a fixed evaluation dataset from representative conversations.
- Track thought preservation and attribution errors.
- Add prompt/model versioning.
- Add stage-level logs and retries.
- Add token and cost tracking.
- Improve failure recovery.
- Document architecture decisions.
- Separate modules into agents only when there is a measurable reason.
- Add research and evidence workflows only when the user needs them.

### Deliverable
A more robust, measurable AI workflow suitable for a serious GitHub portfolio demonstration.

---

# 13. Testing and Evaluation Strategy

## 13.1 Test categories

### Unit tests
- Conversation parsing.
- Speaker normalization.
- Pydantic schema validation.
- Slug generation.
- Markdown generation.
- Publishing payload validation.
- Private/public file separation.

### Integration tests
- Import to Thought Map.
- Thought Map to article generation.
- Article approval to GitHub commit.
- GitHub Actions build and deployment.

### End-to-end tests
Use at least one representative conversation to test the complete workflow.

## 13.2 Thought fidelity evaluation

For each evaluation conversation, manually compare:
1. Original user messages.
2. Extracted Thought Map.
3. Confirmed Thought Map.
4. Chinese article.
5. English article.

Record:
- Missing important ideas.
- Incorrect attribution.
- Unsupported additions.
- Distorted reasoning.
- Overstated certainty.
- Meaning lost during English adaptation.

A polished article that changes the user's position is a failed result.

## 13.3 Initial acceptance threshold

For the first prototype, use a human review scorecard rather than pretending to have a statistically validated benchmark.

Suggested interpretation:
- **Pass:** No major attribution or thesis distortion; most important reasoning is preserved.
- **Needs revision:** Some important ideas are missing or attribution is ambiguous, but the output can be corrected through review.
- **Fail:** The article materially changes the user's position, attributes AI ideas to the user, or invents major reasoning.

Keep examples of failures as regression tests for future prompt and model changes.

---

# 14. Repository Structure

A practical starting structure:

```text
thought-engine/
│
├── README.md
├── PROJECT_REQUIREMENTS.md
├── .gitignore
├── .env.example
│
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   ├── models/
│   │   │   ├── schemas/
│   │   │   ├── services/
│   │   │   │   ├── conversation/
│   │   │   │   ├── extraction/
│   │   │   │   ├── validation/
│   │   │   │   ├── writing/
│   │   │   │   └── publishing/
│   │   │   └── main.py
│   │   ├── tests/
│   │   └── pyproject.toml
│   │
│   └── blog/
│       ├── src/
│       │   ├── content/
│       │   ├── components/
│       │   ├── layouts/
│       │   └── pages/
│       ├── public/
│       └── package.json
│
├── data/
│   └── .gitkeep
│
├── docs/
│   ├── architecture.md
│   ├── data-model.md
│   └── evaluation.md
│
└── .github/
    └── workflows/
        └── deploy.yml
```

The `data/` directory is for private runtime data and must be ignored by Git. Public blog content should be generated or copied into the blog content directory only after approval.

The repository structure can be adjusted as implementation proceeds; do not create empty abstractions solely to match this diagram.

---

# 15. Cost and Operational Constraints

The MVP should be inexpensive to run.

## 15.1 Cost controls
- Use a capable but cost-conscious model for extraction and drafting.
- Avoid sending the entire conversation repeatedly when a normalized or summarized representation is sufficient.
- Store intermediate outputs so failed later stages do not require rerunning earlier stages.
- Allow the user to retry a single stage.
- Track token usage and approximate cost per pipeline run.
- Set reasonable input size limits.
- Do not run background agents continuously.

## 15.2 Operational simplicity
- One user.
- Low request volume.
- No high-availability requirement for the private workspace in MVP.
- Static hosting for the public blog.
- SQLite is sufficient initially.
- Back up private data before making destructive changes.

---

# 16. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| AI misattributes ideas | High | Explicit attribution schema, source references, human review. |
| AI produces generic articles | High | Generate from confirmed Thought Map and evaluate against real conversations. |
| English adaptation changes meaning | High | Evaluate English output separately for thesis and reasoning fidelity. |
| Private data is accidentally published | Critical | Separate private storage and public repository; automated tests and publish allowlist. |
| LLM output does not match schema | Medium | Pydantic validation, structured output, bounded retry. |
| Publishing fails | Medium | Preserve approved drafts and expose actionable errors. |
| Scope expands too early | High | Enforce MVP exclusions and phase exit criteria. |
| Too much time spent on multi-agent architecture | High | Start with a modular monolith and split only when justified. |
| API costs grow unexpectedly | Medium | Stage-level usage tracking, input limits, and retry controls. |

---

# 17. Definition of Done — MVP

The MVP is done when all of the following are true:

- [ ] A user can paste a conversation.
- [ ] A user can upload a Markdown conversation file.
- [ ] The system stores the original conversation privately.
- [ ] The system extracts a structured Thought Map.
- [ ] Thought items have explicit attribution categories.
- [ ] The Thought Map can be edited and confirmed.
- [ ] Chinese and English article drafts can be generated from the confirmed Thought Map.
- [ ] The user can edit and preview both drafts.
- [ ] Publication requires explicit approval.
- [ ] Only approved public article content is sent to the publishing repository.
- [ ] Raw conversations, Thought Maps, and secrets are excluded from public commits.
- [ ] GitHub Actions builds and deploys the blog.
- [ ] The public blog displays both language versions.
- [ ] Errors are visible and drafts are not lost when publishing fails.
- [ ] At least three real conversations have been used for manual quality evaluation.
- [ ] The README explains setup, architecture, privacy boundaries, and the end-to-end workflow.

---

# 18. Instructions for AI Coding Agents

When using Claude Code or another coding assistant to implement this project, follow these rules.

## 18.1 Product rules
1. Treat this document as the product baseline.
2. Implement the smallest complete workflow before adding optional features.
3. Preserve the distinction between user-originated ideas and AI-originated suggestions.
4. Never publish without explicit user approval.
5. Never put private conversation data, Thought Maps, API keys, or private logs into the public blog repository.
6. Do not silently invent missing facts or user opinions.
7. If attribution is uncertain, represent it as uncertain.

## 18.2 Engineering rules
1. Use typed schemas for all important pipeline inputs and outputs.
2. Keep modules small and responsibilities clear.
3. Keep LLM provider integration behind an adapter.
4. Validate all LLM structured outputs.
5. Add tests for privacy boundaries and publishing behavior.
6. Use environment variables for secrets.
7. Keep the application runnable locally with a clear README.
8. Avoid unnecessary infrastructure and dependencies.
9. Do not introduce Kubernetes, microservices, vector databases, or multi-agent frameworks in the MVP without explicit approval.
10. Record significant architectural decisions in `docs/`.

## 18.3 Development workflow
For each feature:
1. Read the relevant requirements.
2. Explain the implementation plan briefly.
3. Implement the smallest complete version.
4. Add or update tests.
5. Run tests and report actual results.
6. Update documentation.
7. Do not claim that a deployment or external integration succeeded unless it was actually verified.

## 18.4 Phase 0 initial task

Start with Phase 0 only. Do not build the entire application immediately.

**Task: Build a Thought Extraction Prototype.**

Requirements:
- Create a Python project.
- Accept a Markdown conversation file.
- Parse messages into a normalized conversation structure.
- Define Pydantic schemas for the Thought Map.
- Call one configured LLM provider to extract the Thought Map.
- Require attribution categories for extracted thoughts.
- Include source message references wherever possible.
- Validate the returned JSON.
- Save the original conversation and extracted Thought Map locally.
- Provide a readable JSON or Markdown representation for manual review.
- Include at least one test conversation and automated schema/parser tests.
- Keep API keys in environment variables.
- Do not build the blog, dashboard, publishing integration, vector database, or multi-agent orchestration in this phase.

Before coding, inspect the repository and propose a concise implementation plan. Then implement Phase 0 and report:
- Files created.
- How to configure and run it.
- Tests executed and their actual results.
- Known limitations.
- How to evaluate the output against the original conversation.

---

# Appendix A — Key Product Decisions in v1.1

| Decision | v1.1 direction | Reason |
|---|---|---|
| What counts as MVP? | A complete conversation-to-publication workflow | A blog alone does not validate the core product. |
| What should be built first? | Thought Extraction Prototype | Thought fidelity is the riskiest and most differentiated capability. |
| Should the blog be built? | Yes, in Phase 1 after extraction validation | It provides a real publishing destination without delaying the first validation. |
| Should MVP use multiple agents? | No; use a modular pipeline | Easier to build, test, debug, and operate. |
| Should articles be auto-published? | No; explicit human approval is mandatory | Protects user ownership and prevents accidental publication. |
| Where should source conversations live? | Private local storage / private database | Prevents accidental public disclosure. |
| Should English be direct translation? | No; audience-aware adaptation with meaning preservation | Improves readability without changing the user's ideas. |
| What should be measured? | Thought preservation, attribution, reasoning integrity, writing quality | Quality is more than polished prose. |
| What infrastructure is needed? | Astro, FastAPI, SQLite, LLM API, GitHub Actions, Cloudflare Pages | Sufficient for a single-user MVP. |
| When should agents be separated? | After the pipeline is stable and measured | Architecture should follow demonstrated needs. |

---

# Appendix B — Product North Star

Thought Engine should ultimately become more than a tool that writes blog posts.

It should become a system that helps a person:
- Think more clearly.
- Preserve valuable ideas from conversations.
- See the structure of their own reasoning.
- Notice how their positions change over time.
- Communicate ideas across languages.
- Build a durable and attributable body of work.

The system succeeds when the published writing is clearer and more accessible, while the thinking behind it remains recognizably the user's own.
