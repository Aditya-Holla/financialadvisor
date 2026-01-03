"""Tutor agent for user education and guidance.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories

Tutor Agent Responsibilities:
- Explain fundamentals, technical indicators, and risks in plain English
- Support user-selected stocks or general investing concepts
- Use neutral, explanatory language only
- Act as a finance professor explaining tools, not an advisor

Hard Constraints:
- MUST NOT use words like "buy", "sell", "invest", or "you should"
- MUST NOT rank, score, or recommend securities
- MUST NOT predict future performance
- MUST NOT provide financial advice
- Only explains concepts and existing data
"""

from typing import Optional, List, Dict, Any
from app.agents.schemas import (
    AdvisorDecision,
    FinancialState,
    TutorExplanation,
    TeachingPoint,
    GuardrailReason,
    GuardrailStatus,
)
from app.integrations.llm import LLMIntegration
from app.integrations.mystockdna import analyze_stock
from app.models.mystockdna import StockDNAAnalysis


class TutorAgent:
    """
    Tutor agent for providing strictly educational guidance.
    
    This agent functions as an educational module that:
    - Explains fundamentals, technical indicators, and risks in plain English
    - Supports user-selected stocks or general investing concepts
    - Uses neutral, explanatory language only
    - Explains existing data without making recommendations
    
    This agent does NOT:
    - Use words like "buy", "sell", "invest", or "you should"
    - Rank, score, or recommend securities
    - Predict future performance
    - Provide financial advice
    
    This agent acts like a finance professor explaining tools,
    not an advisor telling users what to do.
    """
    
    def __init__(self, llm_integration: Optional[LLMIntegration] = None):
        """
        Initialize the tutor agent.
        
        Args:
            llm_integration: Optional LLM integration (creates new if not provided)
        """
        self.llm = llm_integration or LLMIntegration()
    
    async def explain_stock(
        self,
        symbol: str,
        include_technical: bool = True,
        include_fundamentals: bool = True
    ) -> TutorExplanation:
        """
        Explain a stock in educational terms using available data.
        
        This method explains what a stock is, its characteristics, and
        relevant concepts without making recommendations or predictions.
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            include_technical: Whether to include technical indicator explanations
            include_fundamentals: Whether to include fundamental analysis concepts
            
        Returns:
            TutorExplanation with educational content about the stock
            
        Note:
            This method does NOT recommend, rank, or predict performance.
            It only explains concepts and existing data.
        """
        # Get stock data from mystockdna integration
        try:
            stock_data = analyze_stock(symbol)
        except Exception:
            # If mystockdna fails, provide basic educational explanation
            stock_data = None
        
        explanation_parts = []
        teaching_points = []
        
        # Basic stock explanation
        explanation_parts.append(
            f"{symbol} is a publicly traded security. "
            "Publicly traded securities represent ownership shares in companies "
            "that are listed on stock exchanges."
        )
        
        # Explain mystockdna data if available (educational only)
        if stock_data:
            explanation_parts.append(
                self._explain_stock_data_educationally(stock_data)
            )
            
            # Add teaching points about concepts
            if include_fundamentals:
                teaching_points.extend(
                    self._create_fundamental_teaching_points(stock_data)
                )
            
            if include_technical:
                teaching_points.extend(
                    self._create_technical_teaching_points(stock_data)
                )
        else:
            # Generic educational content
            teaching_points.append(TeachingPoint(
                topic="Stock Market Basics",
                explanation="Stocks represent ownership in companies. When companies perform well, stock prices may increase, though past performance does not predict future results.",
                relevance=f"Understanding what {symbol} represents in the market."
            ))
        
        explanation_text = " ".join(explanation_parts)
        
        return TutorExplanation(
            explanation_text=explanation_text,
            teaching_points=teaching_points,
            guardrail_references=[],
            proposal_referenced=False
        )
    
    def _explain_stock_data_educationally(self, stock_data: StockDNAAnalysis) -> str:
        """
        Explain stock data in neutral, educational terms.
        
        This method explains what the data means without making recommendations
        or predictions.
        
        Args:
            stock_data: Stock analysis data from mystockdna
            
        Returns:
            Educational explanation text
        """
        parts = []
        
        # Explain scores as descriptive metrics, not recommendations
        if stock_data.risk_score is not None:
            risk_level = "higher" if stock_data.risk_score > 0.6 else "moderate" if stock_data.risk_score > 0.4 else "lower"
            parts.append(
                f"This security shows a {risk_level} risk profile based on historical volatility patterns. "
                "Risk measures how much a security's price has fluctuated historically."
            )
        
        if stock_data.growth_potential is not None:
            growth_level = "higher" if stock_data.growth_potential > 0.6 else "moderate" if stock_data.growth_potential > 0.4 else "lower"
            parts.append(
                f"Historical growth metrics indicate {growth_level} growth characteristics. "
                "Growth metrics reflect past performance patterns, not future guarantees."
            )
        
        if stock_data.value_score is not None:
            value_level = "higher" if stock_data.value_score > 0.6 else "moderate" if stock_data.value_score > 0.4 else "lower"
            parts.append(
                f"Valuation metrics suggest {value_level} value characteristics relative to historical norms. "
                "Value metrics compare current price to fundamental measures like earnings or book value."
            )
        
        if stock_data.sector:
            parts.append(
                f"This security operates in the {stock_data.sector} sector. "
                "Sectors group companies by their primary business activities."
            )
        
        return " ".join(parts)
    
    def _create_fundamental_teaching_points(self, stock_data: StockDNAAnalysis) -> List[TeachingPoint]:
        """Create educational teaching points about fundamental concepts."""
        points = []
        
        points.append(TeachingPoint(
            topic="Fundamental Analysis",
            explanation="Fundamental analysis examines a company's financial health, including revenue, earnings, debt levels, and competitive position. Analysts use these metrics to understand a company's intrinsic value.",
            relevance="Understanding how fundamental metrics are used in security analysis."
        ))
        
        if stock_data.value_score is not None:
            points.append(TeachingPoint(
                topic="Valuation Metrics",
                explanation="Valuation metrics like price-to-earnings (P/E) ratio compare a stock's price to its earnings. Lower ratios may indicate relatively cheaper valuations, though context matters significantly.",
                relevance="Understanding how value scores reflect valuation comparisons."
            ))
        
        return points
    
    def _create_technical_teaching_points(self, stock_data: StockDNAAnalysis) -> List[TeachingPoint]:
        """Create educational teaching points about technical concepts."""
        points = []
        
        points.append(TeachingPoint(
            topic="Technical Analysis",
            explanation="Technical analysis studies price patterns, trading volume, and historical price movements. Technical indicators are tools used to identify patterns, though patterns do not guarantee future outcomes.",
            relevance="Understanding how technical indicators are used in market analysis."
        ))
        
        if stock_data.momentum_score is not None:
            points.append(TeachingPoint(
                topic="Momentum Indicators",
                explanation="Momentum indicators measure the rate of price change over time. They reflect recent price trends but do not predict future price movements.",
                relevance="Understanding what momentum scores represent in technical analysis."
            ))
        
        return points
    
    async def explain_concept(
        self,
        concept: str
    ) -> TutorExplanation:
        """
        Explain a general investing concept in educational terms.
        
        This method explains concepts like diversification, risk, asset allocation,
        etc. without making recommendations.
        
        Args:
            concept: Concept to explain (e.g., "diversification", "risk", "asset allocation")
            
        Returns:
            TutorExplanation with educational content about the concept
        """
        concept_lower = concept.lower()
        
        # Map concepts to educational explanations
        concept_explanations = {
            "diversification": {
                "text": (
                    "Diversification is a risk management strategy that involves spreading investments "
                    "across different assets, sectors, or geographic regions. The principle is that "
                    "different investments may perform differently under various market conditions, "
                    "potentially reducing overall portfolio volatility. However, diversification does "
                    "not guarantee profits or protect against losses."
                ),
                "teaching_points": [
                    TeachingPoint(
                        topic="Diversification Principles",
                        explanation="Diversification works by reducing exposure to any single investment. Academic research suggests that holding 20-30 different securities can meaningfully reduce unsystematic risk, though market risk remains.",
                        relevance="Understanding how diversification works in portfolio construction."
                    )
                ]
            },
            "risk": {
                "text": (
                    "Risk in investing refers to the possibility of losing money or not achieving expected returns. "
                    "Common types include market risk (overall market declines), credit risk (borrower defaults), "
                    "and liquidity risk (difficulty selling assets). Risk and return are generally related: "
                    "investments with higher potential returns typically carry higher risk. Understanding "
                    "one's risk tolerance is important for portfolio construction."
                ),
                "teaching_points": [
                    TeachingPoint(
                        topic="Risk and Return Relationship",
                        explanation="The risk-return tradeoff is a fundamental principle: securities with higher potential returns typically have higher volatility. This relationship is not guaranteed and varies across market conditions.",
                        relevance="Understanding the relationship between risk and potential returns."
                    )
                ]
            },
            "asset allocation": {
                "text": (
                    "Asset allocation is the process of dividing investments among different asset categories, "
                    "such as stocks, bonds, and cash. Different asset classes have different risk and return "
                    "characteristics. Academic research suggests that asset allocation decisions may have "
                    "significant impact on portfolio performance over time, though individual security selection "
                    "and market timing also play roles."
                ),
                "teaching_points": [
                    TeachingPoint(
                        topic="Asset Classes",
                        explanation="Stocks (equities) represent ownership in companies and tend to have higher volatility. Bonds represent debt and typically have lower volatility but also lower potential returns. Cash provides stability but minimal growth potential.",
                        relevance="Understanding the characteristics of different asset classes."
                    )
                ]
            }
        }
        
        # Get explanation or provide generic one
        if concept_lower in concept_explanations:
            explanation_data = concept_explanations[concept_lower]
            return TutorExplanation(
                explanation_text=explanation_data["text"],
                teaching_points=explanation_data["teaching_points"],
                guardrail_references=[],
                proposal_referenced=False
            )
        else:
            # Generic educational response
            return TutorExplanation(
                explanation_text=(
                    f"{concept} is a financial concept that investors may consider when making decisions. "
                    "Understanding financial concepts can help investors make informed choices, though "
                    "past performance and concepts do not guarantee future results."
                ),
                teaching_points=[],
                guardrail_references=[],
                proposal_referenced=False
            )
    
    async def explain_decision(
        self,
        decision: AdvisorDecision,
        financial_state: FinancialState
    ) -> TutorExplanation:
        """
        Explain an AdvisorDecision in educational terms.
        
        Tries LLM first (if available), falls back to template-based explanation.
        
        Args:
            decision: The advisor decision to explain
            financial_state: User's financial state (for context)
            
        Returns:
            TutorExplanation with explanation text and teaching points
            
        Safety guarantees:
        - Numbers are preserved exactly as in decision
        - No new recommendations are introduced
        - No decisions are overridden
        - Only explains existing decision and proposal
        """
        # Try LLM first (if available)
        llm_explanation = await self._try_llm_explanation(decision, financial_state)
        
        if llm_explanation:
            # LLM generated valid explanation, use it
            # Still generate teaching points from templates (they're safe)
            teaching_points = []
            guardrail_references = []
            proposal_referenced = False
            
            guardrail_status = decision.metadata.get("guardrail_status")
            guardrail_reasons = decision.metadata.get("guardrail_reasons", [])
            
            if guardrail_status and guardrail_status != GuardrailStatus.ALLOW.value:
                guardrail_references.extend(guardrail_reasons)
                for reason_code in guardrail_reasons:
                    teaching_point = self._create_guardrail_teaching_point(reason_code)
                    if teaching_point:
                        teaching_points.append(teaching_point)
            
            if decision.proposal:
                proposal_referenced = True
                proposal_teaching = self._create_proposal_teaching_points(decision.proposal)
                teaching_points.extend(proposal_teaching)
            
            general_teaching = self._create_general_teaching_points(financial_state, decision)
            teaching_points.extend(general_teaching)
            
            return TutorExplanation(
                explanation_text=llm_explanation,
                teaching_points=teaching_points,
                guardrail_references=guardrail_references,
                proposal_referenced=proposal_referenced
            )
        
        # Fallback to template-based explanation
        return await self._explain_with_templates(decision, financial_state)
    
    async def _try_llm_explanation(
        self,
        decision: AdvisorDecision,
        financial_state: FinancialState
    ) -> Optional[str]:
        """
        Try to generate explanation using LLM.
        
        Returns explanation text if successful, None if LLM unavailable or fails validation.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.llm.is_available():
            logger.warning("LLM not available, falling back to templates")
            return None
        
        # Build summaries for LLM
        decision_summary = {
            "decision_type": decision.decision.value,
            "status": "approved" if decision.decision.value == "approve" else decision.decision.value
        }
        
        financial_state_summary = {
            "emergency_fund_months": financial_state.emergency_fund_months,
            "net_cashflow": financial_state.cashflow.net_cashflow
        }
        
        guardrail_info = None
        guardrail_status = decision.metadata.get("guardrail_status")
        guardrail_reasons = decision.metadata.get("guardrail_reasons", [])
        if guardrail_status and guardrail_reasons:
            guardrail_info = {
                "status": guardrail_status,
                "reasons": [
                    {"code": code, "message": self._get_reason_description(code)}
                    for code in guardrail_reasons
                ]
            }
        
        proposal_info = None
        if decision.proposal:
            proposal_info = {
                "allocation": {
                    "stocks": decision.proposal.target_allocation.stocks,
                    "bonds": decision.proposal.target_allocation.bonds,
                    "cash": decision.proposal.target_allocation.cash,
                    "other": decision.proposal.target_allocation.other
                },
                "trade_count": len(decision.proposal.trades) if decision.proposal.trades else 0,
                "risk_delta": decision.proposal.risk_delta
            }
        
        # Try LLM generation
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Attempting LLM explanation generation...")
        result = await self.llm.generate_explanation(
            decision_summary=decision_summary,
            financial_state_summary=financial_state_summary,
            guardrail_info=guardrail_info,
            proposal_info=proposal_info
        )
        if result:
            logger.info("LLM explanation generated successfully")
        else:
            logger.warning("LLM explanation returned None, falling back to templates")
        return result
    
    async def _explain_with_templates(
        self,
        decision: AdvisorDecision,
        financial_state: FinancialState
    ) -> TutorExplanation:
        """
        Generate explanation using template-based approach (fallback).
        
        This is the original template-based implementation.
        """
        explanation_parts = []
        teaching_points = []
        guardrail_references = []
        proposal_referenced = False
        
        # Start with decision explanation
        decision_explanation = self._explain_decision_type(decision.decision)
        explanation_parts.append(decision_explanation)
        
        # Explain guardrail reasons if present
        guardrail_status = decision.metadata.get("guardrail_status")
        guardrail_reasons = decision.metadata.get("guardrail_reasons", [])
        
        if guardrail_status and guardrail_status != GuardrailStatus.ALLOW.value:
            guardrail_explanation = self._explain_guardrails(
                guardrail_status,
                guardrail_reasons,
                decision.explanation_inputs
            )
            explanation_parts.append(guardrail_explanation)
            guardrail_references.extend(guardrail_reasons)
            
            # Add teaching points for guardrail reasons
            for reason_code in guardrail_reasons:
                teaching_point = self._create_guardrail_teaching_point(reason_code)
                if teaching_point:
                    teaching_points.append(teaching_point)
        
        # Explain portfolio proposal if present
        if decision.proposal:
            proposal_explanation = self._explain_proposal(decision.proposal)
            explanation_parts.append(proposal_explanation)
            proposal_referenced = True
            
            # Add teaching points for proposal
            proposal_teaching = self._create_proposal_teaching_points(decision.proposal)
            teaching_points.extend(proposal_teaching)
        
        # Add general financial education teaching points
        general_teaching = self._create_general_teaching_points(financial_state, decision)
        teaching_points.extend(general_teaching)
        
        # Combine explanation parts
        explanation_text = " ".join(explanation_parts)
        
        return TutorExplanation(
            explanation_text=explanation_text,
            teaching_points=teaching_points,
            guardrail_references=guardrail_references,
            proposal_referenced=proposal_referenced
        )
    
    def _explain_decision_type(self, decision_type) -> str:
        """Explain the decision type in neutral, educational terms."""
        explanations = {
            "approve": "This portfolio proposal has been reviewed and passes safety checks. The proposal is available for review.",
            "modify": "This portfolio proposal includes additional considerations that warrant attention. The proposal includes safety warnings.",
            "reject": "This portfolio proposal was blocked by safety guardrails. Safety checks identified concerns that prevent proceeding.",
            "request_info": "Additional information is needed before a portfolio proposal can be generated.",
            "defer": "This portfolio proposal has been deferred. Reviewing financial situation may be helpful before proceeding."
        }
        return explanations.get(decision_type.value, "A decision has been made regarding this portfolio proposal.")
    
    def _explain_guardrails(
        self,
        status: str,
        reason_codes: List[str],
        explanation_inputs: List
    ) -> str:
        """Explain guardrail results in neutral, educational terms."""
        if status == GuardrailStatus.BLOCK.value:
            explanation = "This portfolio proposal was blocked by safety guardrails. "
        elif status == GuardrailStatus.WARN.value:
            explanation = "This portfolio proposal includes safety warnings that warrant attention. "
        else:
            explanation = "Safety guardrails were evaluated. "
        
        # Add specific reasons in educational terms
        if reason_codes:
            reason_descriptions = []
            for code in reason_codes:
                desc = self._get_reason_description(code)
                if desc:
                    reason_descriptions.append(desc)
            
            if reason_descriptions:
                explanation += "Safety considerations: " + "; ".join(reason_descriptions) + "."
        
        return explanation
    
    def _get_reason_description(self, reason_code: str) -> str:
        """Get human-readable description of guardrail reason code in neutral terms."""
        descriptions = {
            "NEGATIVE_CASHFLOW_INVEST": "Negative cash flow indicates expenses exceed income, which may create financial stress",
            "LOW_EMERGENCY_FUND_RISK_INCREASE": "Emergency fund coverage is below the commonly recommended 3-month minimum",
            "LOW_EMERGENCY_FUND_INVESTMENT": "Emergency fund coverage is below commonly recommended levels",
            "LOW_EMERGENCY_FUND_LARGE_INVESTMENT": "Emergency fund coverage may be insufficient relative to the proposed investment amount",
            "HIGH_INTEREST_DEBT_LUMP_SUM": "High-interest debt exists, which some financial strategies prioritize addressing before large investments",
            "SHORT_TERM_GOAL_EQUITY_HEAVY": "Short-term goals may conflict with equity-heavy allocations due to stock market volatility",
            "NO_VIOLATIONS": "All safety checks passed"
        }
        return descriptions.get(reason_code, f"Safety check: {reason_code}")
    
    def _explain_proposal(self, proposal) -> str:
        """Explain the portfolio proposal in neutral, educational terms."""
        explanation = "The portfolio allocation consists of: "
        
        allocation = proposal.target_allocation
        parts = []
        if allocation.stocks > 0:
            parts.append(f"{allocation.stocks:.1f}% stocks")
        if allocation.bonds > 0:
            parts.append(f"{allocation.bonds:.1f}% bonds")
        if allocation.cash > 0:
            parts.append(f"{allocation.cash:.1f}% cash")
        if allocation.other > 0:
            parts.append(f"{allocation.other:.1f}% other")
        
        explanation += ", ".join(parts) + "."
        
        # Mention trades if present (neutral description)
        if proposal.trades:
            trade_count = len(proposal.trades)
            explanation += f" This allocation would require {trade_count} transaction(s) to implement."
        
        # Mention risk change if significant (neutral description)
        if abs(proposal.risk_delta) > 0.05:
            direction = "increases" if proposal.risk_delta > 0 else "decreases"
            explanation += f" This allocation {direction} the portfolio's risk profile based on historical patterns."
        
        return explanation
    
    def _create_guardrail_teaching_point(self, reason_code: str) -> Optional[TeachingPoint]:
        """Create a teaching point for a guardrail reason in neutral, educational terms."""
        teaching_points = {
            "NEGATIVE_CASHFLOW_INVEST": TeachingPoint(
                topic="Cash Flow Management",
                explanation="Positive cash flow means income exceeds expenses, providing financial stability. Negative cash flow indicates expenses exceed income, which may create financial stress and limit ability to cover unexpected costs.",
                relevance="This proposal was blocked due to negative cash flow patterns."
            ),
            "LOW_EMERGENCY_FUND_RISK_INCREASE": TeachingPoint(
                topic="Emergency Fund Importance",
                explanation="Emergency funds are reserves set aside for unexpected expenses. Many financial strategies recommend 3-6 months of expenses as a safety buffer. Emergency funds provide liquidity during financial disruptions.",
                relevance="This proposal was flagged due to emergency fund coverage below commonly recommended levels."
            ),
            "HIGH_INTEREST_DEBT_LUMP_SUM": TeachingPoint(
                topic="Debt vs. Investment Considerations",
                explanation="High-interest debt (typically 15%+ APR) carries guaranteed costs. Some financial strategies prioritize paying down high-interest debt because the guaranteed interest cost may exceed uncertain investment returns. This is a risk management consideration, not a guarantee.",
                relevance="This proposal was flagged due to existing high-interest debt."
            ),
            "SHORT_TERM_GOAL_EQUITY_HEAVY": TeachingPoint(
                topic="Investment Time Horizon",
                explanation="Stocks historically show higher volatility than bonds or cash. Academic research suggests stocks may be more suitable for long-term goals (5+ years) due to their volatility patterns. Short-term goals may benefit from more stable asset classes, though this depends on individual risk tolerance.",
                relevance="This proposal was flagged due to short-term goals combined with equity-heavy allocation."
            )
        }
        return teaching_points.get(reason_code)
    
    def _create_proposal_teaching_points(self, proposal) -> List[TeachingPoint]:
        """Create teaching points about the proposal in neutral, educational terms."""
        points = []
        
        # Asset allocation teaching
        if proposal.target_allocation.stocks > 60:
            points.append(TeachingPoint(
                topic="Equity-Heavy Portfolios",
                explanation="Portfolios with more than 60% stocks are commonly considered equity-heavy. Historical data shows equity-heavy portfolios have exhibited higher volatility and higher potential returns over long periods, though past performance does not predict future results.",
                relevance="This proposal allocates a significant portion to stocks."
            ))
        
        # Diversification teaching
        if len(proposal.trades) > 1:
            points.append(TeachingPoint(
                topic="Portfolio Diversification",
                explanation="Diversification involves spreading investments across different assets, sectors, or geographic regions. Academic research suggests diversification may reduce portfolio volatility because different investments may perform differently under various market conditions. Diversification does not guarantee profits or protect against losses.",
                relevance="This proposal includes multiple transactions that may increase diversification."
            ))
        
        return points
    
    def _create_general_teaching_points(
        self,
        financial_state: FinancialState,
        decision: AdvisorDecision
    ) -> List[TeachingPoint]:
        """Create general financial education teaching points in neutral terms."""
        points = []
        
        # Emergency fund teaching
        if financial_state.emergency_fund_months < 3:
            points.append(TeachingPoint(
                topic="Emergency Fund Concepts",
                explanation="Emergency funds are reserves set aside for unexpected expenses or income loss. Many financial strategies recommend 3-6 months of expenses as a target, though individual needs vary. Emergency funds are typically held in liquid accounts like high-yield savings accounts.",
                relevance="Emergency fund coverage is below commonly recommended levels."
            ))
        
        # Debt management teaching
        if financial_state.debt_summary.total_debt > 0:
            points.append(TeachingPoint(
                topic="Debt Management Concepts",
                explanation="Debt management strategies often involve prioritizing high-interest debt, making consistent payments, and understanding the total cost of debt. Different strategies exist for managing debt, and the appropriate approach depends on individual circumstances.",
                relevance="Outstanding debt exists in the financial profile."
            ))
        
        return points
    
    async def respond(self, request, messages: List) -> "AgentResponse":
        """
        Generate educational response to user query.
        
        This method is kept for backward compatibility but explain_decision()
        should be used for explaining AdvisorDecisions.
        """
        from app.agents.schemas import AgentRequest, AgentResponse
        return AgentResponse(
            success=False,
            message="Use explain_decision() method for explaining decisions",
            data=None
        )
    
    async def explain_recommendation(self, request, recommendation_data: Dict) -> "AgentResponse":
        """
        Explain a recommendation in educational terms.
        
        This method is kept for backward compatibility but explain_decision()
        should be used for explaining AdvisorDecisions.
        """
        from app.agents.schemas import AgentRequest, AgentResponse
        return AgentResponse(
            success=False,
            message="Use explain_decision() method for explaining decisions",
            data=None
        )

