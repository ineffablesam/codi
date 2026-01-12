"""Attractor evaluator - Evaluates stable state satisfaction.

The evaluator continuously checks which attractors are satisfied
and derives signals from unsatisfied attractors.

This is the core loop of Antigravity:
1. Evaluate attractors
2. Derive signals from unsatisfied attractors
3. Emit signals
4. Agents produce artifacts
5. Repeat until all attractors satisfied (or timeout)
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from app.core.artifacts import ArtifactStore
from app.core.attractors.definitions import (
    Attractor,
    AttractorStatus,
    ATTRACTORS,
    get_all_attractors,
)
from app.core.signals import Signal, get_signal_engine
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AttractorResult:
    """Result of evaluating an attractor."""
    
    attractor: str
    status: AttractorStatus
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None


@dataclass
class EvaluationResult:
    """Result of evaluating all attractors."""
    
    results: Dict[str, AttractorResult] = field(default_factory=dict)
    all_satisfied: bool = False
    signals_to_emit: List[Signal] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=datetime.utcnow)


class AttractorEvaluator:
    """
    Evaluates attractor satisfaction and derives signals.
    
    The evaluator is the "brain" that decides what signals to emit
    based on the current artifact state.
    """
    
    def __init__(self, store: ArtifactStore):
        """
        Initialize evaluator with artifact store.
        
        Args:
            store: Artifact store for state queries
        """
        self.store = store
        self.signal_engine = get_signal_engine()
        
        # Cache evaluation results
        self._last_evaluation: Optional[EvaluationResult] = None
        self._evaluation_count = 0
    
    async def evaluate(
        self,
        attractors: Optional[List[str]] = None,
    ) -> EvaluationResult:
        """
        Evaluate attractors and derive signals.
        
        Args:
            attractors: Optional list of attractor names to evaluate
                       (evaluates all if not specified)
        
        Returns:
            EvaluationResult with status and signals
        """
        self._evaluation_count += 1
        
        # Get attractors to evaluate
        if attractors:
            attractor_list = [
                ATTRACTORS[name] for name in attractors
                if name in ATTRACTORS
            ]
        else:
            attractor_list = get_all_attractors()
        
        result = EvaluationResult()
        unsatisfied = []
        
        for attractor in attractor_list:
            # Check dependencies first
            deps_satisfied = await self._check_dependencies(attractor)
            
            if not deps_satisfied:
                result.results[attractor.name] = AttractorResult(
                    attractor=attractor.name,
                    status=AttractorStatus.BLOCKED,
                    error="Dependencies not satisfied",
                )
                continue
            
            # Evaluate the attractor
            try:
                if attractor.evaluator:
                    satisfied = await attractor.evaluator(self.store)
                else:
                    satisfied = True  # No evaluator = always satisfied
                
                status = AttractorStatus.SATISFIED if satisfied else AttractorStatus.UNSATISFIED
                result.results[attractor.name] = AttractorResult(
                    attractor=attractor.name,
                    status=status,
                )
                
                if not satisfied:
                    unsatisfied.append(attractor)
                    
            except Exception as e:
                logger.error(f"Error evaluating attractor {attractor.name}: {e}")
                result.results[attractor.name] = AttractorResult(
                    attractor=attractor.name,
                    status=AttractorStatus.BLOCKED,
                    error=str(e),
                )
        
        # Derive signals from unsatisfied attractors
        for attractor in unsatisfied:
            if attractor.signal_on_unsatisfied:
                result.signals_to_emit.append(attractor.signal_on_unsatisfied)
        
        # Check if all evaluated attractors are satisfied
        result.all_satisfied = all(
            r.status == AttractorStatus.SATISFIED
            for r in result.results.values()
        )
        
        self._last_evaluation = result
        
        logger.info(
            f"Attractor evaluation #{self._evaluation_count}: "
            f"{sum(1 for r in result.results.values() if r.status == AttractorStatus.SATISFIED)}/{len(result.results)} satisfied, "
            f"{len(result.signals_to_emit)} signals to emit"
        )
        
        return result
    
    async def _check_dependencies(self, attractor: Attractor) -> bool:
        """Check if all dependencies of an attractor are satisfied."""
        if not attractor.depends_on:
            return True
        
        for dep_name in attractor.depends_on:
            dep = ATTRACTORS.get(dep_name)
            if not dep:
                continue
            
            if dep.evaluator:
                try:
                    satisfied = await dep.evaluator(self.store)
                    if not satisfied:
                        return False
                except Exception:
                    return False
        
        return True
    
    async def emit_derived_signals(
        self,
        result: Optional[EvaluationResult] = None,
        source: str = "attractor_evaluator",
    ) -> List[Signal]:
        """
        Emit signals derived from evaluation result.
        
        Args:
            result: Evaluation result (uses last if not provided)
            source: Source identifier for signals
            
        Returns:
            List of emitted signals
        """
        if result is None:
            result = self._last_evaluation
        
        if result is None:
            return []
        
        emitted = []
        for signal in result.signals_to_emit:
            await self.signal_engine.emit(
                signal=signal,
                project_id=self.store.project_id,
                source=source,
                context={
                    "derived_from": "attractor_evaluation",
                    "evaluation_count": self._evaluation_count,
                },
            )
            emitted.append(signal)
        
        return emitted
    
    async def run_until_satisfied(
        self,
        attractors: Optional[List[str]] = None,
        timeout: float = 300.0,
        poll_interval: float = 1.0,
        max_iterations: int = 100,
    ) -> EvaluationResult:
        """
        Run evaluation loop until attractors are satisfied.
        
        This is the main "convergence loop" of Antigravity.
        
        Args:
            attractors: Attractors to evaluate (all if not specified)
            timeout: Maximum time to run in seconds
            poll_interval: Time between evaluations
            max_iterations: Maximum number of evaluation cycles
            
        Returns:
            Final evaluation result
        """
        start_time = datetime.utcnow()
        deadline = start_time + timedelta(seconds=timeout)
        iterations = 0
        
        logger.info(
            f"Starting attractor convergence loop "
            f"(timeout={timeout}s, max_iterations={max_iterations})"
        )
        
        while iterations < max_iterations:
            # Check timeout
            if datetime.utcnow() > deadline:
                logger.warning("Attractor convergence timed out")
                break
            
            # Evaluate
            result = await self.evaluate(attractors)
            iterations += 1
            
            # Check if done
            if result.all_satisfied:
                logger.info(f"All attractors satisfied after {iterations} iterations")
                return result
            
            # Emit signals
            await self.emit_derived_signals(result)
            
            # Wait before next iteration
            await asyncio.sleep(poll_interval)
        
        logger.warning(f"Convergence loop ended after {iterations} iterations")
        return self._last_evaluation or EvaluationResult()
    
    def get_unsatisfied(self) -> List[str]:
        """Get names of unsatisfied attractors from last evaluation."""
        if not self._last_evaluation:
            return []
        
        return [
            name for name, result in self._last_evaluation.results.items()
            if result.status == AttractorStatus.UNSATISFIED
        ]
    
    def get_blocked(self) -> List[str]:
        """Get names of blocked attractors from last evaluation."""
        if not self._last_evaluation:
            return []
        
        return [
            name for name, result in self._last_evaluation.results.items()
            if result.status == AttractorStatus.BLOCKED
        ]
    
    def is_converged(self) -> bool:
        """Check if system has converged (all attractors satisfied)."""
        return self._last_evaluation is not None and self._last_evaluation.all_satisfied
