# RAG Framework Feature Comparison Matrix

This matrix compares LlamaIndex, Haystack, LangChain, and LlamaStack across the major capabilities relevant to building and operating Retrieval-Augmented Generation (RAG) applications.

## 1. Framework Feature Matrix

| Capability         | LlamaIndex                                             | Haystack                                         | LangChain                                                                                      | LlamaStack                                             |
| ------------------ | ------------------------------------------------------ | ------------------------------------------------ | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| Primary focus      | RAG and data-connected AI applications                 | Modular AI pipelines and agents                  | LLM applications and agent development                                                         | Standardized APIs and AI runtime                       |
| Document ingestion | Readers, data connectors, and ingestion pipelines      | Converters, preprocessors, and components        | Document loaders and integrations                                                              | Files API and provider-dependent RAG runtime           |
| Chunking           | Node parsers and transformation components             | Document splitters and preprocessing components  | Text splitters                                                                                 | Depends on the RAG runtime and provider implementation |
| Embedding          | Embedding model integrations                           | Embedder components                              | Embedding integrations                                                                         | Inference and embedding APIs                           |
| Vector storage     | VectorStoreIndex and vector-store integrations         | DocumentStore abstractions                       | Vector-store integrations                                                                      | Vector IO API and provider adapters                    |
| Retrieval          | Retrievers, query engines, and chat engines            | Retriever components and pipelines               | Retrievers and retrieval chains                                                                | Vector IO and RAG Runtime APIs                         |
| Agents             | Agent abstractions and workflows                       | Agent components                                 | Agent development framework, with LangGraph for advanced orchestration                         | Agents API                                             |
| Tool integration   | Function tools and integrations                        | Tools and tool components                        | Tool calling and integrations                                                                  | Tool Runtime API                                       |
| Observability      | Instrumentation and third-party integrations           | Tracing, logging, and OpenTelemetry integrations | LangSmith and other integrations                                                               | Telemetry API and provider implementations             |
| Evaluation         | Evaluation modules and datasets                        | Evaluation components and metrics                | Evaluation integrations, including LangSmith                                                   | Evaluation API and provider-dependent implementations  |
| Deployment         | Deploy as a custom application or service              | Serve pipelines through deployment integrations  | Deploy custom applications; LangGraph provides additional orchestration and deployment options | Run provider-based distributions                       |
| Extensibility      | Custom readers, transformations, retrievers, and tools | Custom components and pipelines                  | Custom tools, integrations, and middleware                                                     | Pluggable API providers                                |

## 2. Engineering Interpretation

### LlamaIndex

LlamaIndex is strongly oriented towards connecting external data sources to LLM applications. Its architecture provides components for document ingestion, parsing, indexing, retrieval, and query execution.

Its ingestion pipeline and node-based architecture make it useful when an application requires control over how documents are processed and retrieved. It also supports agents, tools, and workflows for applications that need capabilities beyond basic RAG.

Engineering consideration: A strong choice when document processing, indexing, retrieval quality, and data-connected applications are the primary concerns.

### Haystack

Haystack uses a component-based architecture in which individual components are connected to form pipelines. These pipelines can handle document conversion, preprocessing, embedding, retrieval, and generation.

Its modular approach allows developers to replace individual components without redesigning the entire application. It also supports agent-based workflows and integrations for tracing, logging, and monitoring.

Engineering consideration: Suitable for teams that want explicit pipeline control, modular components, and structured RAG workflows.

### LangChain

LangChain provides a broad ecosystem for building LLM-powered applications. It includes document loaders, text splitters, embedding integrations, vector stores, retrievers, and tools.

Its ecosystem also includes LangGraph for more advanced agent orchestration and LangSmith for tracing, debugging, and evaluation.

Engineering consideration: Useful when building applications that combine multiple LLM integrations, tools, retrieval workflows, and agent capabilities.

### LlamaStack

LlamaStack takes a different architectural approach. Rather than focusing exclusively on a collection of RAG components, it provides standardized APIs for capabilities such as inference, vector storage, agents, tools, safety, and telemetry.

Its provider-based architecture allows developers to configure different implementations behind these APIs. This can make the runtime more consistent across different model and infrastructure providers.

Engineering consideration: Useful when a project needs a standardized AI runtime with configurable providers and APIs for multiple AI capabilities.

## 3. Important Scope and Benchmarking Notes

The feature matrix describes documented framework capabilities. It does not mean every capability was implemented or benchmarked in this project.

The practical RAG comparison used a shared corpus, preprocessed chunks, embeddings, retrieval settings, and evaluation questions across all four frameworks.

Consequently:

- Native document ingestion and chunking capabilities were reviewed but not independently benchmarked.
- Agent execution and tool-calling capabilities were not part of the practical benchmark.
- Observability and production deployment capabilities were compared at the feature level, not through a production deployment test.
- The practical evaluation focused on ingestion preparation, vector indexing, retrieval, answer generation, retrieval relevance, answer quality, and execution time.

The comparison therefore separates what each framework supports from what was actually tested in the experiment.

Great. The next section is Production Readiness Comparison. Append the following to the bottom of your existing `feature-comparison-matrix.md`.

## 4. Production Readiness Comparison

Production readiness involves more than successfully generating answers. A production RAG application also needs reliable deployment, monitoring, evaluation, security controls, and the ability to handle changing workloads.

## 4.1 Production Readiness Matrix

| Area                       | LlamaIndex                                                                    | Haystack                                                                    | LangChain                                                                       | LlamaStack                                                                                             |
| -------------------------- | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Application deployment     | Deployed as a custom application or service                                   | Pipelines can be served through deployment integrations                     | Custom applications; LangGraph supports more advanced orchestration             | Server-based runtime with configurable distributions                                                   |
| Observability              | Instrumentation and integrations with OpenTelemetry and third-party platforms | Built-in tracing integrations, logging, and OpenTelemetry support           | LangSmith provides tracing, debugging, and monitoring                           | Telemetry API with provider-dependent implementation                                                   |
| Evaluation                 | Evaluation modules and integrations for measuring RAG performance             | Evaluation components and metrics for pipelines and generators              | Evaluation through LangSmith and other integrations                             | Evaluation API with available provider implementations                                                 |
| Workflow reliability       | Workflows support stateful and multi-step execution                           | Explicit pipelines provide structured execution paths                       | LangGraph supports stateful orchestration and durable execution                 | Agents API provides standardized agent execution through configured providers                          |
| Infrastructure flexibility | Supports multiple LLM, embedding, and vector-store integrations               | Supports interchangeable components and integrations                        | Broad ecosystem of model, tool, and vector-store integrations                   | Provider architecture supports different model and infrastructure backends                             |
| Security and governance    | Requires application-level security and appropriate integrations              | Requires application-level security and deployment controls                 | Requires application-level security; additional controls depend on integrations | Provides a Safety API, with capabilities dependent on configured providers                             |
| Operational complexity     | Depends on the number of integrations and application components              | Pipeline structure improves visibility but requires component configuration | Broad ecosystem offers flexibility but can introduce integration complexity     | Centralized APIs simplify client integration, but runtime and provider configuration require attention |

## 4.2 Production Engineering Considerations

### LlamaIndex

LlamaIndex provides instrumentation for monitoring LLM calls, prompts, indexing operations, and retrieval activity. It can export traces through OpenTelemetry and integrate with observability platforms.

Its workflow capabilities also support stateful, multi-step execution, making it suitable for more advanced RAG and agent applications.

Production consideration: Teams need to select and configure their observability backend, deployment infrastructure, and supporting services. LlamaIndex provides the application framework rather than a complete managed production platform.

### Haystack

Haystack provides structured pipelines that make application execution easier to inspect and debug. Its production documentation covers evaluation, tracing, and logging. It supports integrations such as OpenTelemetry, Datadog, MLflow, and Langfuse.

Tracing is configurable rather than automatically enabled. Content tracing is disabled by default, helping avoid unintentionally sending sensitive input and output data to tracing backends.

Production consideration: Its explicit pipeline architecture is useful for teams that need predictable execution and component-level monitoring. However, deployment infrastructure and monitoring backends still need to be configured.

### LangChain

LangChain provides integrations for building LLM applications, while LangGraph supports more advanced stateful workflows and orchestration.

LangSmith extends the ecosystem with tracing, evaluation, debugging, and production monitoring. It can help teams inspect model calls, retrieved context, tool execution, latency, and application behavior.

Production consideration: The ecosystem provides a broad set of capabilities, but teams should plan how LangChain, LangGraph, LangSmith, and external services fit together. LangSmith is an additional platform, not an automatic capability of every LangChain deployment.

### LlamaStack

LlamaStack provides a server-based architecture with standardized APIs for inference, agents, vector storage, safety, evaluation, and telemetry.

Its provider architecture allows different implementations to be configured behind these APIs. The same API layer can support different deployment environments, including local development, on-premises infrastructure, and cloud environments.

Production consideration: Its centralized API approach can simplify integration between applications and AI infrastructure. However, production readiness depends on the maturity, availability, and configuration of the selected providers. Not every API has the same range of provider implementations.

## 4.3 Overall Production Assessment

| Framework  | Main production advantage                                          | Main operational consideration                                      |
| ---------- | ------------------------------------------------------------------ | ------------------------------------------------------------------- |
| LlamaIndex | Strong data and RAG abstractions with instrumentation integrations | Requires additional infrastructure and observability configuration  |
| Haystack   | Structured pipelines and component-level tracing                   | Requires pipeline and deployment configuration                      |
| LangChain  | Broad integrations and an extended agent-development ecosystem     | Multiple ecosystem components may increase architectural complexity |
| LlamaStack | Standardized APIs and configurable provider architecture           | Provider maturity and runtime configuration must be evaluated       |

## 4.4 Important Assessment Notes

This production-readiness comparison is based on documented framework capabilities and engineering interpretation. It is not the result of a production-scale deployment test.

The practical experiment did not test:

- Horizontal scaling or concurrent user workloads.
- High availability and disaster recovery.
- Authentication, authorization, or multi-tenant isolation.
- Production monitoring and alerting.
- Load balancing and infrastructure failure recovery.
- Production security and compliance requirements.

These areas would require additional testing before selecting a framework for a real production deployment.

## Documentation Sources

- [LlamaIndex Observability](https://developers.llamaindex.ai/python/framework/module_guides/observability/?utm_source=chatgpt.com)
- [LlamaIndex Workflows and Observability](https://developers.llamaindex.ai/python/llamaagents/workflows/observability/?utm_source=chatgpt.com)
- [Haystack Production Usage](https://docs.haystack.deepset.ai/docs/production-usage?utm_source=chatgpt.com)
- [Haystack Tracing](https://docs.haystack.deepset.ai/docs/tracing?utm_source=chatgpt.com)
- [LangSmith Observability](https://www.langchain.com/langsmith/observability?utm_source=chatgpt.com)
- [LlamaStack 0.2.19 Documentation](https://ogx-ai.github.io/v0.2.19/?utm_source=chatgpt.com)

Great. Let's complete the report with the final section: Framework Decision Guide.

Append the following to `feature-comparison-matrix.md`. This section uses the benchmark results from your experiment to explain when each framework is the most appropriate choice.

## 5. Framework Decision Guide

Selecting a RAG framework depends on the application's requirements, the development team's experience, the infrastructure environment, and the level of control required over retrieval and generation.

No single framework is the best choice for every application. The results of this experiment provide a practical basis for comparing their strengths and trade-offs.

## 5.1 Benchmark Results Summary

The following table summarizes the results from the 15-question evaluation.

| Evaluation Metric           | LlamaIndex | Haystack   | LangChain  | LlamaStack |
| --------------------------- | ---------- | ---------- | ---------- | ---------- |
| Successful evaluations      | 15/15      | 15/15      | 15/15      | 15/15      |
| Average execution time      | 343.56 sec | 292.28 sec | 272.69 sec | 194.87 sec |
| Total execution time        | 85.89 min  | 73.07 min  | 68.17 min  | 48.72 min  |
| Average retrieved chunks    | 4          | 4          | 4          | 3          |
| Topic-page precision        | 55.00%     | 55.00%     | 55.00%     | 62.22%     |
| Topic-page hit rate         | 100%       | 100%       | 100%       | 93.33%     |
| Manual answer-quality score | 83.33%     | 83.33%     | 83.33%     | 84.17%     |

Interpretation:

- All four frameworks completed all 15 evaluation questions successfully.
- LlamaStack recorded the lowest average end-to-end execution time in this experiment.
- LlamaIndex, Haystack, and LangChain achieved a 100% topic-page hit rate.
- LlamaStack achieved the highest topic-page precision, but returned three chunks per question instead of the configured top four.
- LlamaStack achieved the highest manual answer-quality score, although the difference between frameworks was small.

The answer-quality scores were based on a manual review of correctness, completeness, context grounding, and relevance. They should be treated as project-specific assessment results rather than standardized benchmark scores.

## 5.2 When to Choose Each Framework

### Choose LlamaIndex when:

- The application is heavily focused on document ingestion and retrieval.
- You need control over document parsing, transformations, indexing, and retrieval.
- The application connects to multiple external data sources.
- You need to build knowledge assistants or document-based question-answering systems.

Reason: LlamaIndex provides a data-oriented architecture with dedicated abstractions for ingestion, indexing, and retrieval.

### Choose Haystack when:

- You prefer modular, component-based application architecture.
- You need explicit control over RAG pipeline execution.
- Your application requires replaceable preprocessing, embedding, retrieval, and generation components.
- You want structured pipelines that can be inspected and monitored.

Reason: Haystack's component-based architecture makes it suitable for building structured and modular AI pipelines.

### Choose LangChain when:

- You need integrations with different LLM providers and external services.
- Your application combines retrieval, tools, and model interactions.
- You intend to develop applications with more advanced agent workflows.
- You want to use LangGraph for stateful orchestration and LangSmith for observability and evaluation.

Reason: LangChain provides a broad ecosystem for connecting models, tools, retrieval systems, and application workflows.

### Choose LlamaStack when:

- You want standardized APIs for accessing AI capabilities.
- You need to configure different inference and infrastructure providers.
- Your application requires a centralized AI runtime.
- You want a consistent interface for inference, vector storage, agents, tools, and safety capabilities.

Reason: LlamaStack focuses on providing a provider-based runtime with standardized APIs rather than requiring every application to implement its own integrations.

## 5.3 Decision Matrix

| Application Requirement                       | Recommended Framework    | Reason                                                    |
| --------------------------------------------- | ------------------------ | --------------------------------------------------------- |
| Document-heavy RAG applications               | LlamaIndex               | Dedicated ingestion, indexing, and retrieval abstractions |
| Modular RAG pipelines                         | Haystack                 | Component-based pipeline architecture                     |
| Applications requiring broad LLM integrations | LangChain                | Extensive model, tool, and vector-store integrations      |
| Advanced agent orchestration                  | LangChain with LangGraph | Stateful workflow and agent orchestration capabilities    |
| Standardized AI infrastructure APIs           | LlamaStack               | Provider-based runtime and standardized APIs              |
| Custom document-processing workflows          | LlamaIndex               | Flexible document transformations and ingestion pipelines |
| Explicit pipeline control                     | Haystack                 | Components can be connected and replaced within pipelines |

## 5.4 Final Recommendation

Based on the experiment, all four frameworks demonstrated that they can support a functional RAG pipeline using the same corpus, embeddings, retrieval configuration, and language model.

However, their architectural approaches make them suitable for different engineering requirements.

- LlamaIndex is a strong option for applications where document ingestion, indexing, and retrieval are central.
- Haystack is suitable for applications that require modular components and clearly structured execution pipelines.
- LangChain is a strong option for applications that need broad integrations and more advanced agent development.
- LlamaStack is worth considering when standardized APIs and a configurable AI runtime are important architectural requirements.

In this experiment, LlamaStack recorded the lowest average execution time and the highest manual answer-quality score. However, it returned fewer retrieval results than the other frameworks and had a lower topic-page hit rate. Its apparent performance advantage should therefore not be interpreted as proof that it is universally faster or more accurate.

For a production selection, the benchmark should be extended with repeated latency measurements, concurrent-user testing, retrieval-quality evaluation using semantic metrics, failure testing, and production deployment assessments.

## 5.5 Limitations of the Experiment

The following limitations should be considered when interpreting the results:

1. Corpus size: The experiment used a 10-page DevOps corpus, which is relatively small compared with production knowledge bases.
2. Evaluation size: Only 15 questions were used to evaluate retrieval and answer generation.
3. Execution time: Each framework's measurements came from a single evaluation run. Model warmup, CPU utilization, and server conditions may have influenced the results.
4. Retrieval differences: LlamaStack returned three chunks per question, while the other frameworks returned four, affecting direct precision comparisons.
5. Answer-quality assessment: Manual scoring involves reviewer judgment and is not a standardized evaluation method.
6. Production testing: The experiment did not evaluate high availability, horizontal scaling, concurrent requests, or production security.
7. Native ingestion: Shared preprocessed chunks and embeddings were used to ensure a controlled retrieval comparison. Native ingestion and chunking capabilities were not independently benchmarked.

These limitations mean the results should be interpreted as a controlled, small-scale comparison rather than a definitive ranking of the frameworks.

