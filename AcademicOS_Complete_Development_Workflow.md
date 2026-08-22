# AcademicOS Development Workflow

## 1. Purpose of This Roadmap

AcademicOS is being developed as a persistent, course-aware academic operating system rather than as a collection of unrelated CRUD pages or a generic chatbot.

The development workflow therefore follows a dependency-aware progression:

```text
Backend Foundation
        ↓
Document Intelligence
        ↓
Retrieval
        ↓
Chat
        ↓
Courses
        ↓
Document Organization
        ↓
Document Interaction
        ↓
Course Workspace
        ↓
Infrastructure
        ↓
Production Ingestion
        ↓
Knowledge Agent
        ↓
Supervisor
        ↓
Memory
        ↓
Learning
        ↓
Planning
        ↓
Exam Preparation
        ↓
Academic Intelligence
```

The purpose of this document is to define what should be implemented, tested, and considered complete at every phase.

---

# 2. Development Principles

## 2.1 Build in dependency order

A higher-level feature should not be implemented before the infrastructure and domain concepts it depends on are stable.

For example:

```text
Exam Prep Agent
    ↓
Knowledge Agent
    ↓
Hybrid Retrieval
    ↓
Persistent Vector Store
    ↓
Document Processing
```

This prevents the project from accumulating sophisticated interfaces backed by unfinished infrastructure.

## 2.2 Separate current implementation from target architecture

The following distinction must remain explicit:

```text
Implemented
    ≠
Architecturally designed
    ≠
Production-ready
```

A component should only be marked complete when its required implementation, integration, testing, and validation are finished.

## 2.3 Preserve abstractions

The existing repository, service, processing, embedding, and vector-store abstractions should be extended rather than bypassed.

New functionality should not unnecessarily introduce direct database access inside API routes or tightly couple the application to one infrastructure provider.

## 2.4 Test every phase before moving forward

Each phase should have:

```text
Implementation
    ↓
Unit Tests
    ↓
Integration Tests
    ↓
Frontend Tests where applicable
    ↓
Typecheck
    ↓
Lint
    ↓
Build
    ↓
Phase Sign-off
```

---

# 3. Phase 1 — Backend Foundation

## Objective

Establish a maintainable backend architecture capable of supporting authentication, users, documents, chat, and future academic domains.

## Workflow

```text
Project Structure
      ↓
FastAPI Application
      ↓
Configuration
      ↓
Database Connection
      ↓
SQLAlchemy Base
      ↓
Domain Models
      ↓
Repositories
      ↓
Services
      ↓
Pydantic Schemas
      ↓
API Routes
      ↓
Authentication
      ↓
JWT Authorization
      ↓
Alembic
      ↓
Tests
```

## Implementation

### Backend

- Create FastAPI application structure.
- Establish configuration and environment handling.
- Configure PostgreSQL connection.
- Configure SQLAlchemy.
- Create declarative model base.
- Create User model.
- Create Document model.
- Create ChatSession model.
- Create ChatMessage model.
- Implement repositories.
- Implement services.
- Implement Pydantic request/response schemas.
- Implement API routing.
- Implement authentication.
- Implement password handling.
- Implement JWT token generation and validation.
- Add ownership checks.
- Configure Alembic.
- Create initial migrations.

### Validation

- Authentication tests.
- User tests.
- Document tests.
- ChatSession tests.
- ChatMessage tests.
- Repository tests.
- Service tests.
- API tests.
- Authorization/ownership tests.
- Migration validation.

## Completion Criteria

Phase 1 is complete when:

- Backend starts successfully.
- Database connection works.
- Migrations execute correctly.
- Authentication works.
- Protected routes enforce ownership.
- Core CRUD operations work.
- Tests pass.
- Type/lint checks pass where configured.

---

# 4. Phase 2 — Intelligent Document Processing

## Objective

Convert uploaded academic files into clean, searchable, semantically meaningful chunks.

## Workflow

```text
Uploaded File
      ↓
File Identification
      ↓
Extractor
      ↓
Raw Text
      ↓
Cleaner
      ↓
Normalization
      ↓
Chunker
      ↓
Chunk Validation
      ↓
Embedding Provider
      ↓
Vector Store
```

## 2.1 Processing Abstractions

Implement and maintain:

- `BaseExtractor`
- `BaseProcessor`
- Embedding provider abstraction
- Vector store abstraction

## 2.2 Extraction

Support:

- Plain text
- PDF using PyMuPDF
- PPTX

Design extraction so additional formats can be added without rewriting the pipeline.

## 2.3 Cleaning

Implement:

- Unicode normalization.
- Whitespace normalization.
- Text cleanup.
- Empty-content handling.
- Consistent text representation.

## 2.4 Chunking

Use recursive character chunking.

Maintain the established chunk-size and overlap configuration.

Every chunk should have stable identification suitable for:

- retrieval
- deduplication
- indexing
- source attribution

## 2.5 Embeddings

Create an embedding-provider abstraction.

Support:

- Local embedding implementation.
- Mock/test implementation.

Tests must not require external embedding infrastructure.

## 2.6 Vector Store

Implement the vector-store abstraction.

Support:

- Insert/index.
- Search.
- Metadata payloads.
- Test/in-memory operation.
- Dependency injection.

## Completion Criteria

Phase 2 is complete when:

- Supported files can be extracted.
- Text is normalized.
- Documents are chunked deterministically.
- Chunks can be embedded.
- Chunks can be indexed.
- The pipeline is independently testable.
- Tests do not require production infrastructure.

---

# 5. Phase 3 — Semantic Retrieval

## Objective

Enable semantic search over the student's academic knowledge.

## Workflow

```text
User Query
      ↓
Query Embedding
      ↓
Vector Search
      ↓
Metadata Filtering
      ↓
Score Threshold
      ↓
Relevant Chunks
```

## Implementation

Extend the vector-store interface to support:

- Similarity search.
- Score thresholds.
- Metadata filters.
- Ownership filters.
- Stable chunk identifiers.

Store ownership information in vector metadata.

At minimum, retrieval must understand:

```text
owner_id
document_id
chunk_id
text
```

Additional academic metadata should be supported as the system evolves.

## Security Requirement

A retrieval query from User A must never return User B's indexed chunks.

This must be explicitly tested.

## Completion Criteria

- Semantic search works.
- Ownership filtering works.
- Score thresholds work.
- Metadata filters work.
- Cross-user retrieval leakage tests pass.

---

# 6. Phase 4 — Advanced Retrieval

## Objective

Move from basic vector search to a robust retrieval system combining multiple retrieval strategies.

## Workflow

```text
Query
  │
  ├───────────────┐
  ↓               ↓
Dense Search   Keyword Search
  │               │
  └───────┬───────┘
          ↓
    Hybrid Retrieval
          ↓
       RRF Fusion
          ↓
       Reranking
          ↓
    Deduplication
          ↓
   Final Ranked Context
```

## 6.1 Keyword Retrieval

Implement keyword-based matching for exact terms and terminology.

This is particularly important for academic queries containing:

- formulas
- component names
- abbreviations
- technical terminology
- named concepts

## 6.2 Dense Retrieval

Use the semantic vector search established in Phase 3.

## 6.3 Hybrid Fusion

Combine dense and keyword results using Reciprocal Rank Fusion.

## 6.4 Reranking

Apply reranking after fusion to improve final relevance.

## 6.5 Deduplication

Deduplicate using stable chunk IDs.

## 6.6 Metadata-Aware Retrieval

Prepare retrieval for:

```text
owner
course
document
document type
subject
semester
academic year
```

## Completion Criteria

- Dense retrieval works.
- Keyword retrieval works.
- Hybrid retrieval works.
- RRF fusion works.
- Reranking works.
- Duplicate chunks are removed.
- Case-insensitive keyword behavior is correct.
- Source metadata survives the retrieval pipeline.

---

# 7. Phase 5 — Chat System

## Objective

Expose the retrieval system through a usable academic chat interface.

## Backend Workflow

```text
Chat Request
      ↓
Authentication
      ↓
Chat Session
      ↓
Query Processing
      ↓
Retrieval
      ↓
Context Assembly
      ↓
LLM
      ↓
Answer
      ↓
Sources
      ↓
Chat Message Persistence
```

## Frontend Workflow

```text
Chat Page
   ↓
Session Sidebar
   ↓
Select Session
   ↓
Load History
   ↓
Compose Message
   ↓
Send
   ↓
Loading State
   ↓
Assistant Response
   ↓
Display Sources
```

## Implementation

Support:

- Chat sessions.
- Message history.
- Session selection.
- New sessions.
- User messages.
- Assistant messages.
- Loading states.
- Error states.
- Empty states.
- Source display.
- API integration.

## Completion Criteria

- Chat sessions persist.
- Messages persist.
- Retrieval can feed the chat pipeline.
- Sources can be displayed.
- Frontend tests pass.
- Backend tests pass.
- TypeScript passes.
- ESLint passes.
- Production build passes.

---

# 8. Phase 6A — Course Backend

## Objective

Introduce the academic Course as a first-class domain entity.

## New Hierarchy

```text
User
  ↓
Course
  ↓
Academic Resources
```

## Implementation

Create Course model with:

- `owner_id`
- `name`
- `code`
- `description`
- timestamps

Implement:

- Course repository.
- Course service.
- Course schemas.
- Course API.
- Ownership enforcement.
- Unique ownership-scoped course name constraint.
- Alembic migration.

## API

```text
GET    /api/v1/courses
POST   /api/v1/courses
GET    /api/v1/courses/{id}
PATCH  /api/v1/courses/{id}
DELETE /api/v1/courses/{id}
```

## Testing

Test:

- Create.
- List.
- Get.
- Update.
- Rename.
- Delete.
- Ownership.
- Duplicate names.
- Invalid requests.
- Missing resources.

## Completion Criteria

Course CRUD and ownership behavior are fully tested.

---

# 9. Phase 6B — Course ↔ Documents and Chat

## Objective

Connect academic resources to Courses.

## New Structure

```text
Course
 ├── Documents
 └── Chat Sessions
```

## Implementation

Add nullable:

```text
Document.course_id
ChatSession.course_id
```

Use:

```text
ON DELETE SET NULL
```

so deleting a Course does not delete academic resources.

Implement:

- Course assignment.
- Course reassignment.
- Course removal.
- Course filtering.
- Ownership validation.
- Repository support.
- Service support.
- API support.
- Migration.
- Regression tests.

## Completion Criteria

A resource can exist:

```text
inside a Course
```

or:

```text
without a Course
```

without data loss.

---

# 10. Phase 6C — Document Types and Metadata

## Objective

Make documents academically meaningful rather than generic files.

## Document Types

```text
lecture_notes
textbook
presentation
assignment
previous_year_question
reference
other
```

## Metadata

Support:

```text
author
subject
semester
academic_year
tags
```

## Implementation

- Authoritative `DocumentType`.
- Structured metadata schema.
- Strict metadata validation.
- Unknown-field rejection.
- Tag normalization.
- Case-insensitive tag deduplication.
- Database migration.
- Relevant indexes/constraints.

## PATCH Semantics

Preserve the distinction between:

```text
field omitted
```

```text
field = null
```

```text
field = value
```

For metadata:

```text
PATCH {}
```

means no modification.

```text
PATCH {"document_metadata": null}
```

means clear metadata.

## Filtering

Support:

```text
course_id
document_type
```

individually and together.

## Completion Criteria

- Metadata validates correctly.
- Types are authoritative.
- PATCH semantics are correct.
- Filtering works.
- Existing documents remain valid.
- Tests pass.

---

# 11. Phase 6D — Course and Document Frontend

## Objective

Expose the Course and Document domain through the frontend.

## Course UI

Implement:

- Course list.
- Course creation.
- Course editing.
- Course deletion.
- Course navigation.

## Document UI

Implement:

- Course display.
- Course assignment.
- Course reassignment.
- Course removal.
- Document type display.
- Document type editing.
- Metadata display.
- Metadata editing.
- Course filtering.
- Document-type filtering.
- Combined filtering.

## Upload Workflow

Extend document upload to support:

```text
Course
Document Type
Metadata
```

## Validation

- Frontend unit tests.
- Integration tests.
- Upload error tests.
- Edit-state tests.
- PATCH error tests.
- Search parameter tests.
- TypeScript.
- ESLint.

## Completion Criteria

Phase 6D is complete when the Course and Document management workflow is usable end-to-end.

---

# 12. Phase 6E — Document Detail and Document Interaction

## Objective

Turn the Document Detail page from a metadata/properties page into an actual document workspace.

## 12.1 Document Detail Foundation

Implement:

```text
/documents/[id]
```

with:

- Document information.
- Course.
- Document type.
- Metadata.
- Processing status.
- Source information.
- Actions.
- Navigation.

## 12.2 Document Editing

Support:

- Metadata editing.
- Course reassignment.
- Document type modification.
- Validation.
- Save states.
- Error handling.

## 12.3 Document Deletion

Implement:

- Delete action.
- Confirmation.
- Loading state.
- Error handling.
- Post-delete navigation.

## 12.4 Document Content Access

This is a required part of completing 6E.

Provide at least one reliable mechanism:

```text
Embedded Document Viewer
```

or:

```text
Open/View Document
```

The preferred experience is:

```text
Document Detail
      ↓
View Document
      ↓
Read actual academic content
```

The viewer should eventually support the relevant file formats, beginning with PDF if that is the primary supported academic format.

## 12.5 Chat With Document

Add:

```text
Chat with this Document
```

The action should create/open a chat context containing:

```text
document_id
```

The chat retrieval layer must use that document restriction.

Target flow:

```text
Document Detail
      ↓
Chat with Document
      ↓
/chat?documentId=<id>
      ↓
Chat Context
      ↓
Retrieval restricted to Document
      ↓
LLM
```

## 12.6 Testing

Test:

- Route loading.
- Invalid document IDs.
- Document rendering.
- Metadata.
- Editing.
- Delete.
- Viewer/open action.
- Chat navigation.
- Document-specific context propagation.
- Loading states.
- Error states.
- Permissions.

## Completion Criteria

Phase 6E is complete only when:

```text
View Document
+
Manage Document
+
Chat With Document
```

are all functional.

---

# 13. Phase 6F — Course Workspace and Resource Integration

## Objective

Give Courses a real academic workspace instead of treating them merely as database grouping objects.

## Course Workspace

Target structure:

```text
Course
 ├── Overview
 ├── Resources
 ├── Chat
 └── Settings
```

## 13.1 Resource View

Display all documents belonging to the Course.

Support:

- Document cards/list.
- Document type.
- Metadata.
- Search.
- Sorting.
- Filtering.

## 13.2 Course-Level Filtering

Support:

```text
Lecture Notes
Textbooks
Presentations
Assignments
PYQs
References
Other
```

with additional metadata filtering where appropriate.

## 13.3 Add Existing Document

Allow:

```text
Course
   ↓
Add Existing Document
   ↓
Search Unassigned Documents
   ↓
Select
   ↓
Assign to Course
```

This avoids forcing users to leave the Course workspace.

## 13.4 Course-Level Document Management

Support:

- Assign document.
- Remove document.
- Reassign document.
- Bulk assignment where useful.
- Bulk type changes where appropriate.

## 13.5 Start Course Chat

Add:

```text
Start Course Chat
```

The resulting chat should retrieve from the Course's resources rather than from the entire user corpus.

Target:

```text
Course Chat
    ↓
Course filter
    ↓
Hybrid Retrieval
    ↓
Course Documents
    ↓
LLM
```

## Completion Criteria

A Course should function as a coherent academic workspace:

```text
Course
  ├── Resources
  ├── Resource discovery
  ├── Resource management
  └── Course-aware AI chat
```

---

# 14. Phase 7 — Advanced Organization and Search

## Objective

Make a large academic library manageable.

## Features

Implement:

- Global document search.
- Course-aware search.
- Multiple filters.
- Sorting.
- Pagination or virtualized lists where needed.
- Bulk selection.
- Bulk Course assignment.
- Bulk Course removal.
- Bulk document-type modification.
- Better metadata management.
- Search result highlighting.
- Empty-state handling.

## Search Architecture

```text
Search Query
    ↓
Metadata Filters
    ↓
Keyword Search
    ↓
Optional Semantic Search
    ↓
Ranked Results
```

## Completion Criteria

The system remains usable when the user has hundreds or thousands of documents.

---

# 15. Phase 8 — Infrastructure Stabilization

## Objective

Move from development/test infrastructure toward reproducible deployment.

This phase must not be confused with merely having Dockerfiles or Qdrant integration code.

## Target Architecture

```text
Docker Compose
      │
      ├── Frontend
      ├── Backend
      ├── PostgreSQL
      └── Qdrant
```

## 15.1 Docker

Implement:

- Backend container.
- Frontend container where appropriate.
- PostgreSQL service.
- Qdrant service.
- Environment configuration.
- Service networking.
- Health checks.
- Persistent volumes.
- Dependency ordering.
- Startup commands.

## 15.2 PostgreSQL

Validate:

- Database startup.
- Connection.
- Migration execution.
- Persistent storage.
- Recovery after restart.

## 15.3 Qdrant

Validate:

- Persistent collections.
- Collection creation.
- Vector dimensions.
- Metadata payloads.
- Ownership filtering.
- Course filtering.
- Document filtering.
- Search.
- Persistence across restarts.

## 15.4 Alembic

Ensure startup/deployment process handles migrations predictably.

## Completion Criteria

The complete environment can be started reproducibly without manually reconstructing infrastructure.

---

# 16. Phase 9 — Production Document Ingestion

## Objective

Connect the existing document-processing architecture to persistent production infrastructure.

## Workflow

```text
Upload
  ↓
Document Record
  ↓
File Storage
  ↓
Processing Job
  ↓
Extraction
  ↓
Cleaning
  ↓
Chunking
  ↓
Embedding
  ↓
Qdrant
  ↓
Processing Complete
```

## Processing States

Introduce explicit states such as:

```text
uploaded
processing
processed
failed
```

Potential future states:

```text
queued
retrying
```

## Requirements

- Persistent file location.
- Persistent processing state.
- Background processing.
- Error handling.
- Retry behavior.
- Idempotent processing.
- Document reprocessing.
- Cleanup of obsolete vectors.
- Processing status in UI.

## Completion Criteria

An uploaded document automatically becomes searchable in persistent Qdrant.

---

# 17. Phase 10 — Knowledge Agent

## Objective

Turn the retrieval architecture into a grounded academic reasoning system.

## Workflow

```text
User Question
      ↓
Query Understanding
      ↓
Context Detection
      ↓
Retrieval Filters
      ↓
Hybrid Retrieval
      ↓
Reranking
      ↓
Context Assembly
      ↓
LLM
      ↓
Grounded Answer
      ↓
Sources
```

## Retrieval Context

The Knowledge Agent should understand:

```text
User
Course
Document
Document Type
Subject
Semester
Academic Year
```

## Capabilities

- Document questions.
- Course questions.
- Source-grounded explanations.
- Comparisons between documents.
- Citation/source display.
- Retrieval confidence handling.
- Insufficient-context detection.

## Critical Behavior

If the student's documents do not contain enough evidence, the agent should not manufacture a confident academic answer from retrieved noise.

## Completion Criteria

The Knowledge Agent can answer grounded questions using the student's persistent academic corpus.

---

# 18. Phase 11 — Supervisor Agent

## Objective

Introduce intelligent routing between academic capabilities.

## Workflow

```text
User Request
      ↓
Supervisor
      ↓
Task Classification
      │
      ├── Knowledge
      ├── Learning
      ├── Planning
      ├── Exam Prep
      └── General Academic Task
```

## Examples

```text
"What is slip in an induction motor?"
        ↓
Knowledge Agent
```

```text
"Explain this topic with examples."
        ↓
Learning Agent
```

```text
"Create a 7-day study plan."
        ↓
Planner Agent
```

```text
"Find important questions from this chapter."
        ↓
Exam Prep Agent
```

## Completion Criteria

The user should not need to manually choose which agent handles a normal academic task.

---

# 19. Phase 12 — Memory Manager

## Objective

Introduce persistent academic context.

## Memory Categories

Potential categories:

```text
Learning history
Weak topics
Completed topics
Study plans
Important concepts
Interaction history
Learning preferences
Exam goals
Revision history
```

## Architecture

```text
Agent
  ↓
Memory Manager
  ↓
Memory Store
  ↓
Relevant Context
  ↓
Agent
```

## Requirements

Memory should be:

- Explicitly structured.
- Relevant.
- Retrievable.
- Updatable.
- Deletable.
- Scoped correctly to the user.

Avoid storing every conversation detail indiscriminately.

## Completion Criteria

Agents can retrieve useful long-term academic context without contaminating unrelated interactions.

---

# 20. Phase 13 — Learning Agent

## Objective

Transform retrieved knowledge into personalized teaching.

## Workflow

```text
Student
   ↓
Course
   ↓
Topic
   ↓
Known/Weak Areas
   ↓
Learning Objective
   ↓
Explanation
   ↓
Examples
   ↓
Practice
   ↓
Evaluation
   ↓
Updated Learning State
```

## Capabilities

- Explanations.
- Examples.
- Concept comparisons.
- Quizzes.
- Practice questions.
- Step-by-step problem solving.
- Revision material.
- Difficulty adaptation.
- Knowledge checks.

## Completion Criteria

The Learning Agent can conduct a complete learning interaction rather than merely generate isolated answers.

---

# 21. Phase 14 — Planner Agent

## Objective

Create resource-aware academic study plans.

## Inputs

```text
Exam date
Available hours
Course
Syllabus
Weak topics
Current progress
Available documents
Prior study plans
```

## Workflow

```text
Academic Goal
      ↓
Time Available
      ↓
Course Requirements
      ↓
Weak Areas
      ↓
Available Resources
      ↓
Priority Calculation
      ↓
Study Schedule
      ↓
Daily Tasks
      ↓
Progress Tracking
```

## Requirements

Plans should reference actual AcademicOS resources where possible.

Example:

```text
19:00–20:00
Transformer Equivalent Circuit
Source: Electrical Machines Lecture 4
Practice: PYQ Set 2024
```

## Completion Criteria

Generated plans are connected to real courses, documents, topics, and progress.

---

# 22. Phase 15 — Exam Prep Agent

## Objective

Transform the academic corpus into exam-focused intelligence.

## Inputs

```text
Lecture Notes
Textbooks
Assignments
Previous-Year Questions
Course Metadata
Student Weaknesses
```

## Workflow

```text
Academic Corpus
      ↓
Topic Extraction
      ↓
PYQ Analysis
      ↓
Topic Frequency
      ↓
Question Pattern Analysis
      ↓
Weakness Correlation
      ↓
Exam Priorities
      ↓
Revision Plan
```

## Capabilities

- PYQ analysis.
- Topic frequency.
- Important concepts.
- Question-type classification.
- Revision plans.
- Mock tests.
- Answer evaluation.
- Topic prioritization.
- Course-specific exam preparation.

## Completion Criteria

The Exam Prep Agent can produce exam preparation grounded in the student's actual academic resources.

---

# 23. Phase 16 — Academic Analytics

## Objective

Create measurable insight into academic progress.

## Metrics

Potential metrics:

```text
Course progress
Topic mastery
Study time
Question performance
Revision frequency
Weak areas
Completed resources
Exam readiness
```

## Example

```text
Electrical Machines
    │
    ├── Transformers       85%
    ├── Induction Motor    62%
    ├── Synchronous Motor  74%
    └── DC Machines        91%
```

## Completion Criteria

Analytics are based on actual interaction and assessment data rather than arbitrary AI-generated percentages.

---

# 24. Phase 17 — Academic Knowledge Graph

## Objective

Represent relationships between academic entities explicitly.

## Target Model

```text
Course
 │
 ├── Topic
 │    ├── Concept
 │    ├── Formula
 │    └── Problem
 │
 ├── Document
 │
 ├── Assignment
 │
 └── Exam Question
```

## Example Relationship

```text
Transformer
    ↓
Equivalent Circuit
    ↓
Voltage Regulation
    ↓
Related Lecture
    ↓
Related PYQ
    ↓
Student Weakness
    ↓
Revision Recommendation
```

## Potential Uses

- Cross-document reasoning.
- Topic dependency analysis.
- Learning-path generation.
- Exam prediction support.
- Weakness detection.
- Resource recommendation.

This should be implemented only after the simpler relational and retrieval systems are mature.

---

# 25. Phase 18 — Production Hardening

## Objective

Prepare AcademicOS for reliable real-world usage.

## Areas

### Security

- Authentication hardening.
- Authorization auditing.
- Input validation.
- File validation.
- Upload restrictions.
- Secret management.
- Rate limiting.
- Secure headers.
- Cross-user isolation testing.

### Reliability

- Background job monitoring.
- Retry mechanisms.
- Failure recovery.
- Database backups.
- Vector-store recovery.
- Logging.

### Observability

- Structured logs.
- Error tracking.
- Processing metrics.
- Retrieval metrics.
- LLM latency.
- Agent execution traces.

### Performance

- Database indexes.
- Query optimization.
- Retrieval optimization.
- Caching where appropriate.
- Background processing.
- Frontend performance.

---

# 26. Phase Completion Protocol

Every phase should end with a formal verification cycle.

```text
Feature Implementation
        ↓
Backend Tests
        ↓
Frontend Tests
        ↓
Integration Tests
        ↓
Security Checks
        ↓
TypeScript
        ↓
ESLint
        ↓
Production Build
        ↓
Manual UX Verification
        ↓
Documentation Update
        ↓
Git Commit
        ↓
Phase Sign-Off
```

A phase should not be declared complete merely because the main screen renders.

---

# 27. Current Known Status

Based on the current project state:

| Phase | Status |
|---|---|
| Phase 1 — Backend Foundation | Complete |
| Phase 2 — Document Processing | Implemented |
| Phase 3 — Semantic Retrieval | Implemented |
| Phase 4 — Hybrid Retrieval + Reranking | Implemented |
| Phase 5 — Chat | Complete |
| Phase 6A — Course Backend | Complete |
| Phase 6B — Course ↔ Resources | Complete |
| Phase 6C — Document Types + Metadata | Complete |
| Phase 6D — Course + Document Frontend | Complete |
| Phase 6E — Document Detail | In progress |
| Phase 6F — Course Workspace | Not started |
| Phase 7 — Advanced Organization | Not started |
| Phase 8 — Infrastructure | Not finalized |
| Phase 9 — Production Ingestion | Not started |
| Phase 10 — Knowledge Agent | Not started |
| Phase 11 — Supervisor Agent | Not started |
| Phase 12 — Memory Manager | Not started |
| Phase 13 — Learning Agent | Not started |
| Phase 14 — Planner Agent | Not started |
| Phase 15 — Exam Prep Agent | Not started |
| Phase 16 — Academic Analytics | Not started |
| Phase 17 — Knowledge Graph | Not started |
| Phase 18 — Production Hardening | Not started |

---

# 28. Immediate Execution Plan

The next work should follow this exact sequence:

```text
CURRENT
Phase 6E
Document Detail
    │
    ├── Complete viewer/open-document capability
    ├── Add Chat with Document
    ├── Validate document-specific retrieval context
    └── Full regression testing
    │
    ▼
Phase 6E SIGN-OFF
    │
    ▼
Phase 6F
Course Workspace
    │
    ├── Resources view
    ├── Course filtering
    ├── Add Existing Document
    ├── Course resource management
    └── Start Course Chat
    │
    ▼
Phase 6F SIGN-OFF
    │
    ▼
Phase 7
Advanced Organization
    │
    ├── Search
    ├── Advanced filters
    ├── Sorting
    └── Bulk operations
    │
    ▼
Phase 7 SIGN-OFF
    │
    ▼
Phase 8
Docker + PostgreSQL + Qdrant
    │
    ▼
Phase 9
Persistent Production Ingestion
    │
    ▼
Phase 10
Knowledge Agent
    │
    ▼
Phase 11
Supervisor Agent
    │
    ▼
Phase 12
Memory Manager
    │
    ▼
Phase 13
Learning Agent
    │
    ▼
Phase 14
Planner Agent
    │
    ▼
Phase 15
Exam Prep Agent
    │
    ▼
Phase 16
Academic Analytics
    │
    ▼
Phase 17
Knowledge Graph
    │
    ▼
Phase 18
Production Hardening
```

---

# 29. Final Target Architecture

The completed system should evolve toward:

```text
                              STUDENT
                                 │
                                 ▼
                         ┌───────────────┐
                         │   Next.js UI  │
                         └───────┬───────┘
                                 │
                                 ▼
                       ┌──────────────────┐
                       │    Supervisor    │
                       │      Agent       │
                       └────────┬─────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
   Knowledge Agent        Learning Agent        Planner Agent
          │                     │                     │
          └─────────────────────┼─────────────────────┘
                                │
                         Exam Prep Agent
                                │
                                ▼
                       ┌──────────────────┐
                       │  Memory Manager  │
                       └────────┬─────────┘
                                │
              ┌─────────────────┼──────────────────┐
              ▼                 ▼                  ▼
         PostgreSQL          Qdrant          File Storage
              │                 │                  │
              └─────────────────┼──────────────────┘
                                │
                                ▼
                       Document Processing
                                │
                     ┌──────────┼──────────┐
                     ▼          ▼          ▼
                 Extract     Chunk      Embed
                                │
                                ▼
                           Retrieval
                                │
                  ┌─────────────┼─────────────┐
                  ▼             ▼             ▼
               Keyword        Dense        Metadata
                  │             │             │
                  └─────────────┼─────────────┘
                                ▼
                           Reranking
                                │
                                ▼
                              LLM
                                │
                                ▼
                   Grounded Academic Response
```

The fundamental product progression is:

```text
Phase 1–5
Build the technical foundation.

Phase 6A–6D
Build the academic organization layer.

Phase 6E–7
Make academic resources genuinely usable.

Phase 8–9
Make the infrastructure persistent and production-like.

Phase 10–12
Make the system context-aware and intelligent.

Phase 13–15
Make it capable of teaching, planning, and exam preparation.

Phase 16–17
Make the academic state measurable and relational.

Phase 18
Make the entire system production-grade.
```

The architectural goal is not to maximize the number of AI agents. It is to create a reliable chain:

```text
Academic Resources
        ↓
Structured Knowledge
        ↓
Retrieval
        ↓
Context
        ↓
Reasoning
        ↓
Memory
        ↓
Personalization
        ↓
Learning
        ↓
Planning
        ↓
Exam Intelligence
```

That chain is the actual AcademicOS product.
