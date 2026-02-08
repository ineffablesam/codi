# Comet Opik Integration in CODI

> **AI Operation Tracking & Quality Evaluation for Flutter Development**

## 🎯 Overview

CODI integrates [Comet Opik](https://www.comet.com/docs/opik) to provide **transparent, traceable AI operations** throughout the development workflow. Every AI-powered code generation, chat response, and summarization is automatically tracked, evaluated for quality, and made visible to developers.

This integration enables developers to:
- **Understand what the AI did** - Full trace visibility with input/output
- **Measure quality** - Automated evaluations using Gemini as judge
- **Debug failures** - Complete trace history when things go wrong
- **Optimize performance** - Track token usage, costs, and latency
- **Build trust** - Professional-grade observability with Opik branding

## 🏗️ Architecture

### Backend Stack
- **Opik SDK** (`opik>=1.10.6`) - Core tracing and evaluation framework
- **Google Gemini Integration** - Native Opik support via `track_genai()`
- **FastAPI** - REST API for trace management
- **PostgreSQL** - Local trace storage with JSONB for flexibility
- **SQLAlchemy** - ORM with async support

### Key Components

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend (Flutter)                   │
│  ┌──────────────┐    ┌──────────────┐   ┌──────────────┐    │
│  │ Chat UI      │    │ Opik         │   │ Trace        │    │
│  │ + Trace      │───▶│ Dashboard    │◀──│ Detail       │    │
│  │ Indicators   │    │ (Branded)    │   │ View         │    │
│  └──────────────┘    └──────────────┘   └──────────────┘    │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP/REST API
┌────────────────────────────▼────────────────────────────────┐
│                         Backend (Python)                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ OpikService                                          │   │
│  │  • Wraps Gemini client with track_genai()          │   │
│  │  • User-level opt-in support                       │   │
│  │  • Zero overhead when disabled                     │   │
│  └────────────┬─────────────────────────────────────────┘   │
│               │                                              │
│  ┌────────────▼─────────────┐  ┌────────────────────────┐  │
│  │ SummarizationService     │  │ EvaluationService      │  │
│  │  • Chain of Density      │  │  • Code quality        │  │
│  │  • @track decorator      │  │  • Summary quality     │  │
│  │  • Automatic nesting     │  │  • Gemini as judge     │  │
│  └──────────────────────────┘  └────────────────────────┘  │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ PostgreSQL Database                                   │  │
│  │  traces │ evaluations │ experiments │ prompts         │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Comet Opik      │
                    │  Cloud Platform  │
                    │  (External)      │
                    └──────────────────┘
```

## ⚙️ Implementation Details

### 1. Opt-In Tracing System

**User Model Extensions:**
```python
class User(Base):
    # Opik preferences (opt-in)
    opik_enabled: bool = False  # Must explicitly enable
    opik_api_key: Optional[str] = None  # Can use their own
    opik_workspace: Optional[str] = None
```

**OpikService - Smart Client Selection:**
```python
def get_gemini_client(self, user_opik_enabled: bool):
    """Returns tracked or untracked client based on user preference."""
    if user_opik_enabled and self._initialized:
        return self.tracked_gemini_client  # Wrapped with track_genai()
    return self.gemini_client  # No tracing overhead
```

**Result:** When `opik_enabled=False`, there's **zero performance overhead**. The regular Gemini client is used directly.

### 2. Chain of Density Summarization

Implements the [Chain of Density](https://arxiv.org/abs/2309.04269) technique from the Opik notebook for generating information-dense summaries:

```python
@track(project_name="codi-summarization")
async def chain_of_density_summarization(
    self,
    document: str,
    instruction: str,
    user_opik_enabled: bool,
    ...
):
    # Iterative refinement (each iteration auto-tracked)
    summary = await self.iterative_density_summarization(...)
    
    # Final polish
    final_result = await self.final_summary(...)
    
    return final_result
```

**Automatic Tracing:** The `@track` decorator creates a trace with nested spans for each iteration. All Gemini calls are logged with input/output.

### 3. Automated Quality Evaluation

Uses **Gemini as a judge** to evaluate outputs:

```python
@track
async def evaluate_summary_quality(self, summary: str, instruction: str, ...):
    """Gemini evaluates summary on conciseness, accuracy, alignment."""
    
    prompt = f"""
Rate this summary on 0-1 based on:
- Conciseness, technical accuracy, instruction alignment
Summary: {summary}

Return JSON: {{"score": 0.92, "reason": "..."}}
"""
    
    response = gemini_client.models.generate_content(prompt)
    return json.loads(response.text)
```

**Stored in Database:**
```sql
CREATE TABLE evaluations (
    id UUID PRIMARY KEY,
    trace_id UUID REFERENCES traces(id),
    metric_name VARCHAR(100),  -- e.g., "summary_quality"
    score FLOAT,               -- 0.0 to 1.0
    reason TEXT,               -- Explanation from Gemini
    meta_data JSONB
);
```

### 4. API Endpoints

#### Get User Settings
```http
GET /api/v1/users/me/opik-settings
Authorization: Bearer <token>

Response:
{
  "opik_enabled": true,
  "opik_workspace": "my-workspace",
  "has_api_key": false
}
```

#### Enable Tracing
```http
PATCH /api/v1/users/me/opik-settings
{
  "opik_enabled": true,
  "opik_workspace": "my-workspace"
}
```

#### Summarize Code
```http
POST /api/v1/summarize/code
{
  "code": "def fibonacci(n): ...",
  "instruction": "Explain the algorithm",
  "density_iterations": 2,
  "model": "gemini-3-flash-preview"
}

Response:
{
  "summary": "Recursive Fibonacci implementation with O(2^n) complexity...",
  "trace_id": "uuid-here",
  "quality_score": 0.87,
  "quality_reason": "Clear explanation, mentions complexity"
}
```

#### List Traces
```http
GET /api/v1/traces?page=1&page_size=20&trace_type=summarization

Response:
{
  "traces": [
    {
      "id": "uuid",
      "trace_type": "summarization",
      "name": "Code Summary: Explain...",
      "start_time": "2026-02-06T01:00:00Z",
      "duration_ms": 1523,
      "input_data": {"code": "...", "instruction": "..."},
      "output_data": {"summary": "..."},
      "meta_data": {"model": "gemini-3-flash-preview", "tokens": 245},
      "evaluations": [
        {"metric_name": "summary_quality", "score": 0.87, "reason": "..."}
      ]
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

#### Get Trace Details
```http
GET /api/v1/traces/{trace_id}

Response: (full trace with nested spans and evaluations)
```

## 📊 Database Schema

### Traces Table
Stores every AI operation:
```sql
CREATE TABLE traces (
    id UUID PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    project_id INTEGER REFERENCES projects(id),
    parent_trace_id UUID REFERENCES traces(id), -- For nested traces
    trace_type VARCHAR(50),  -- 'summarization', 'code_generation', etc.
    name VARCHAR(255),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_ms INTEGER,
    input_data JSONB,       -- Flexible storage
    output_data JSONB,
    meta_data JSONB,         -- model, tokens, cost, etc.
    tags TEXT[],
    created_at TIMESTAMP
);
```

### Evaluations Table
Quality metrics for each trace:
```sql
CREATE TABLE evaluations (
    id UUID PRIMARY KEY,
    trace_id UUID REFERENCES traces(id),
    metric_name VARCHAR(100),
    score FLOAT,
    reason TEXT,
    meta_data JSONB,
    created_at TIMESTAMP
);
```

### Prompts Table (Versioning)
```sql
CREATE TABLE prompts (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    version INTEGER,
    template TEXT,          -- With {{variable}} placeholders
    variables JSONB,
    created_at TIMESTAMP,
    UNIQUE(name, version)
);
```

## 🎨 Frontend Integration (Flutter)

### 1. Dart Models
```dart
class Trace {
  final String id;
  final String traceType;
  final String name;
  final DateTime startTime;
  final int? durationMs;
  final Map<String, dynamic>? inputData;
  final Map<String, dynamic>? outputData;
  final List<Evaluation>? evaluations;
  // ...
}

class Evaluation {
  final String metricName;
  final double score;
  final String? reason;
  // ...
}
```

### 2. Opik Dashboard Screen
Branded interface with:
- **Settings section**: Toggle tracing on/off
- **Stats widgets**: Total traces, average quality
- **Traces list**: With filtering by type
- **Link to Comet Opik**: External dashboard access

### 3. Chat Integration
- **Trace indicators** on AI messages
- **Quality badges** showing evaluation scores
- **"View Trace" action** in message menu
- **Quick summarization** from chat input

## 🧪 Testing

### Comprehensive Test Suite
Created `tests/test_opik_integration.py` with:

1. **Service Tests**
   - `test_opik_service_initialization`
   - `test_prompt_service`
   - `test_summarization_service`
   - `test_evaluation_service`

2. **API Tests** (Simulating frontend)
   - `test_get_opik_settings`
   - `test_update_opik_settings`
   - `test_list_traces`
   - `test_get_trace_detail`
   - `test_summarize_code_endpoint`

3. **End-to-End Workflow**
   - Enable tracing → Summarize code → Fetch traces → View details

### Running Tests
```bash
# All tests
pytest tests/test_opik_integration.py -v

# Specific test
pytest tests/test_opik_integration.py::test_end_to_end_workflow -s

# With coverage
pytest tests/test_opik_integration.py --cov=app/services --cov=app/api
```

## 🚀 Deployment & Setup

### 1. Environment Configuration
```bash
# .env file
OPIK_API_KEY=your_comet_opik_api_key_here
OPIK_WORKSPACE=codi
OPIK_PROJECT_NAME=codi-ai-operations
GEMINI_API_KEY=your_gemini_api_key
```

### 2. Run Migrations
```bash
docker-compose exec api alembic upgrade head
```

### 3. Seed Prompts
```bash
docker-compose exec api python -m app.utils.seed_prompts
```

### 4. Start Services
```bash
docker-compose up -d
```

## 📈 Benefits Demonstrated

### For Developers
1. **Transparency** - See exactly what AI did, step-by-step
2. **Quality Metrics** - Know if AI output is good before using it
3. **Debugging** - Full trace history when AI fails
4. **Learning** - Understand which instructions work best

### For Teams
1. **Standardization** - Versioned prompts ensure consistency
2. **Monitoring** - Track AI performance across projects
3. **Cost Control** - See token usage and optimize
4. **Compliance** - Audit trail of all AI operations

### Technical Excellence
1. **Zero overhead** when disabled (opt-in design)
2. **Native integration** with Opik's Gemini support
3. **Automatic tracing** via decorators (no manual instrumentation)
4. **Flexible storage** with JSONB for evolving data structures

## 🏆 Hackathon Innovation

### What Makes This Special

1. **First-class Opik Integration**
   - Not just logging - full Opik ecosystem integration
   - Native Gemini support via `track_genai()`
   - Automatic nested trace creation

2. **User-Centric Design**
   - Opt-in tracing (respects performance concerns)
   - Users can use their own Opik API keys
   - Traces linked directly to chat messages

3. **Intelligent Evaluation**
   - Gemini-as-judge for automated quality assessment
   - Chain of Density for information-dense summaries
   - Real-time quality scores on every operation

4. **Production-Ready**
   - Comprehensive test suite
   - Database-backed with cloud sync
   - Proper error handling and fallbacks
   - Docker-based deployment

## 📚 Code References

### Key Files
- **Services**: `app/services/opik_service.py`, `summarization_service.py`, `evaluation_service.py`
- **Models**: `app/models/trace.py`, `app/models/user.py`
- **API**: `app/api/v1/endpoints/opik.py`
- **Schemas**: `app/schemas/opik.py`
- **Migrations**: `alembic/versions/20260206_*_opik_*.py`
- **Tests**: `tests/test_opik_integration.py`

### Example Usage

**Backend Service:**
```python
from app.services.summarization_service import SummarizationService

service = SummarizationService(db)
summary = await service.chain_of_density_summarization(
    document=code,
    instruction="Explain the algorithm",
    user_opik_enabled=user.opik_enabled,
    density_iterations=2
)
```

**Frontend API Call:**
```dart
final response = await dio.post('/api/v1/summarize/code',
  data: {
    'code': code,
    'instruction': 'Explain this',
    'density_iterations': 2
  }
);

final summary = response.data['summary'];
final traceId = response.data['trace_id'];
final quality = response.data['quality_score'];
```

## 🎯 Conclusion

This integration demonstrates **professional-grade AI observability** in a production Flutter development platform. By leveraging Comet Opik's powerful tracing and evaluation framework with Google Gemini, CODI provides developers with unprecedented visibility into AI operations while maintaining high performance through opt-in design.

**Every trace tells a story. Now developers can read them.**

---

**Built for**: EncodeClub x Comet Hackathon  
**Technology**: Comet Opik + Google Gemini + FastAPI + Flutter  
**Repository**: [github.com/codi-app/codi](https://github.com/codi-app/codi)  
**Documentation**: This file + Implementation Plan + Walkthrough
