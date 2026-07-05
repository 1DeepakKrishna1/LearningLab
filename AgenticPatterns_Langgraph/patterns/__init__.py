from .p01_prompt_chaining import PatternPromptChaining
from .p02_routing import PatternRouting
from .p03_parallelization import PatternParallelization
from .p04_reflection import PatternReflection
from .p05_tool_use import PatternToolUse
from .p06_planning import PatternPlanning
from .p07_multi_agent import PatternMultiAgent
from .p08_memory_management import PatternMemoryManagement
from .p09_learning_adaptation import PatternLearningAdaptation
from .p10_model_context_protocol import PatternModelContextProtocol
from .p11_goal_setting_monitoring import PatternGoalSettingMonitoring
from .p12_exception_handling_recovery import PatternExceptionHandlingRecovery
from .p13_human_in_the_loop import PatternHumanInTheLoop
from .p14_knowledge_retrieval_rag import PatternKnowledgeRetrievalRAG
from .p15_inter_agent_communication import PatternInterAgentCommunication
from .p16_resource_aware_optimization import PatternResourceAwareOptimization
from .p17_reasoning_techniques import PatternReasoningTechniques
from .p18_guardrails_safety import PatternGuardrailsSafety
from .p19_evaluation_monitoring import PatternEvaluationMonitoring
from .p20_prioritization import PatternPrioritization
from .p21_exploration_discovery import PatternExplorationDiscovery

ALL_PATTERNS = [
    PatternPromptChaining,
    PatternRouting,
    PatternParallelization,
    PatternReflection,
    PatternToolUse,
    PatternPlanning,
    PatternMultiAgent,
    PatternMemoryManagement,
    PatternLearningAdaptation,
    PatternModelContextProtocol,
    PatternGoalSettingMonitoring,
    PatternExceptionHandlingRecovery,
    PatternHumanInTheLoop,
    PatternKnowledgeRetrievalRAG,
    PatternInterAgentCommunication,
    PatternResourceAwareOptimization,
    PatternReasoningTechniques,
    PatternGuardrailsSafety,
    PatternEvaluationMonitoring,
    PatternPrioritization,
    PatternExplorationDiscovery,
]

__all__ = [
    "PatternPromptChaining",
    "PatternRouting",
    "PatternParallelization",
    "PatternReflection",
    "PatternToolUse",
    "PatternPlanning",
    "PatternMultiAgent",
    "PatternMemoryManagement",
    "PatternLearningAdaptation",
    "PatternModelContextProtocol",
    "PatternGoalSettingMonitoring",
    "PatternExceptionHandlingRecovery",
    "PatternHumanInTheLoop",
    "PatternKnowledgeRetrievalRAG",
    "PatternInterAgentCommunication",
    "PatternResourceAwareOptimization",
    "PatternReasoningTechniques",
    "PatternGuardrailsSafety",
    "PatternEvaluationMonitoring",
    "PatternPrioritization",
    "PatternExplorationDiscovery",
    "ALL_PATTERNS",
]
